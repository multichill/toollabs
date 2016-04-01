#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import aliases from ULAN. Needs to be fixed to not include non Latin languages in English

"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib2
import re
import pywikibot.data.wikidataquery as wdquery
import csv
import time
from collections import OrderedDict
import datetime
import requests
import simplejson

class UlanImportBot:
    """
    
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields wikidata item objects.

        """
        
        self.repo = pywikibot.Site().data_repository()
        self.generator = pagegenerators.PreloadingItemGenerator(generator)
        #self.viafitem = pywikibot.ItemPage(self.repo, u'Q54919')

    
    def run (self):
        '''
        Work on all items
        '''

        for item in self.generator:
            if not item.exists():
                continue

            if item.isRedirectPage():
                item = item.getRedirectTarget()

            data = item.get()
            claims = data.get('claims')
            #currentlabel = data.get('labels').get(u'en')
            
            #pywikibot.output(labels)
            #pywikibot.output(aliases)

            if not u'P245' in claims:
                print u'No ULAN  found, skipping'
                continue

            ulanid = claims.get(u'P245')[0].getTarget()
            ulanurl = u'http://www.getty.edu/vow/ULANFullDisplay?find=&role=&nation=&subjectid=%s' % (ulanid,)
            ulanvocaburl = u'http://vocab.getty.edu/ulan/%s' % (ulanid,)
            #ulanurljson = u'http://vocab.getty.edu/ulan/%s.json' % (ulanid,)
            ulanurljson = u'http://vocab.getty.edu/download/json?uri=http://vocab.getty.edu/ulan/%s.json' % (ulanid,)
            #print ulanurljson
            '''
            Host: vocab.getty.edu
User-Agent: Mozilla/5.0 (Windows NT 6.1; rv:42.0) Gecko/20100101 Firefox/42.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: nl,en-US;q=0.7,en;q=0.3
Accept-Encoding: gzip, deflate
Referer: http://www.getty.edu/vow/ULANFullDisplay?find=&role=&nation=&subjectid=500047960
Origin: http://www.getty.edu
Connection: keep-alive
            '''
            #try:
            ulanPage = requests.get(ulanurljson)
            #except urllib2.HTTPError as e:
            #    pywikibot.output('On %s the ULAN link %s returned this HTTPError %s: %s' % (item.title(), ulanurljson, e.errno, e.strerror))
            #    continue
                
                
                
            #ulanPageData = ulanPage.read()
            try:
                ulanPageDataDataObject = ulanPage.json()
            except simplejson.scanner.JSONDecodeError:
                pywikibot.output('On %s I got a json error while working on %s, skipping it' % (item.title(), ulanurljson))
                continue
            


            # That didn't work. Stupid viaf api always returns 200
            #if not viafPage.getcode()==200:
            #    pywikibot.output('On %s the VIAF link %s gave a %s http code, skipping it' % (item.title(), viafurl, viafPage.getcode()))
            #    continue

            # Don't know if the ulan json api is clean, but this catches any junk
            #try:
            #    ulanPageDataDataObject = json.loads(ulanPageData)
            #except ValueError:
            #    pywikibot.output('On %s the ULAN link %s returned this junk:\n %s' % (item.title(), ulanurljson, ulanPageData))
            #    continue

            prefLabel = u''
            allLabels = [] # Should probably be a set

            # We have everything in JSON. We loop over it and grab the preferred label (=~Wikidata label) and the labels (=~Wikidata aliases)
            if ulanPageDataDataObject.get(u'results'):
                if ulanPageDataDataObject.get(u'results').get(u'bindings'):
                    for binding in ulanPageDataDataObject.get(u'results').get(u'bindings'):
                        # We only care about this item and literals
                        if binding.get(u'Subject').get(u'type')==u'uri' and binding.get(u'Subject').get(u'value')==ulanvocaburl and binding.get(u'Object').get(u'type')==u'literal':
                            if binding.get(u'Predicate').get(u'type')==u'uri' and binding.get(u'Predicate').get(u'value')==u'http://www.w3.org/2004/02/skos/core#prefLabel':
                                prefLabel = self.normalizeName(binding.get(u'Object').get(u'value'))
                            elif binding.get(u'Predicate').get(u'type')==u'uri' and binding.get(u'Predicate').get(u'value')==u'http://www.w3.org/2000/01/rdf-schema#label':
                                allLabels.append(self.normalizeName(binding.get(u'Object').get(u'value')))
                            
                    #pywikibot.output(prefLabel)
                    #pywikibot.output(allLabels)

                    # The item doesn't have a label in my languages. Let's fix that!
                    mylangs = [u'de', u'en', u'es', u'fr', u'nl', u'pt']
                    wdlabels = data.get('labels')
                    if wdlabels:
                        currentlabel = wdlabels.get(u'en')
                    else:
                        pywikibot.output(u'This item doesn\'t have any labels!')
                        wdlabels = {}
                        currentlabel = u''
                        
                    labelschanged = 0
                    for mylang in mylangs:
                        if not wdlabels.get(mylang):
                            wdlabels[mylang] = prefLabel
                            labelschanged = labelschanged + 1
                            if mylang==u'en':
                                currentlabel=prefLabel

                    if labelschanged:
                        summary = u'Added missing labels in %s languages based on ULAN %s' % (labelschanged,ulanid)
                        pywikibot.output(summary)
                        #print 
                        # Flush it to the wiki with item.editLabels(wdlabels, summary=summary)
                        try:
                            item.editLabels(wdlabels, summary=summary)
                        except pywikibot.data.api.APIError:
                            pywikibot.output(u'Couldn\'t update the labels, conflicts with another item')
                            continue
                        # This might throw an exception if the combination already exists
                        #pywikibot.output(wdlabels)

                    # Only do this in English
                    aliases = data.get('aliases').get(u'en')

                    if not aliases:
                        pywikibot.output(u'This item doesn\'t have any English aliases!')
                        aliases = []                       
                    aliaseschanged = 0

                    for newalias in set(allLabels):
                        #FIXME: Do something to check that we don't add the label as an alias
                        #Nice condition if we just added the English alias
                        if newalias!=currentlabel and not newalias in aliases:
                            aliases.append(newalias)
                            aliaseschanged = aliaseschanged + 1

                    if aliaseschanged:
                        summary = u'Added %s missing aliases in English based on ULAN %s' % (aliaseschanged,ulanid)
                        pywikibot.output(summary)
                        #print u'%s aliases added!' % (aliaseschanged,)
                        # Flush it to the wiki with item.editAliases({u'en' : aliases}, summary=summary)
                        item.editAliases({u'en' : aliases}, summary=summary)
                        #pywikibot.output(aliases)
                    
                            
            '''    

            if viafPageDataDataObject.get(u'JPG'):
                ulanid = viafPageDataDataObject.get(u'JPG')[0]
                #print u'I found ulanid %s for item %s' % (ulanid, item.title())

                
                newclaim = pywikibot.Claim(self.repo, u'P245')
                newclaim.setTarget(ulanid)
                pywikibot.output('Adding ULAN %s claim to %s' % (ulanid, item.title(),) )

                #Default text is "‎Created claim: ULAN identifier (P245): 500204732, "

                summary = u'based on VIAF %s' % (viafid,)
                
                item.addClaim(newclaim, summary=summary)

                pywikibot.output('Adding new reference claim to %s' % item)

                refsource = pywikibot.Claim(self.repo, u'P143')
                refsource.setTarget(self.viafitem)
                
                refurl = pywikibot.Claim(self.repo, u'P854')
                refurl.setTarget(viafurl)
                
                refdate = pywikibot.Claim(self.repo, u'P813')
                today = datetime.datetime.today()
                date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
                refdate.setTarget(date)
                
                newclaim.addSources([refsource,refurl, refdate])
        '''
    def normalizeName(self, name):
        '''
        Helper function to normalize the name
        '''
        if u',' in name:
            (surname, sep, firstname) = name.partition(u',')
            name = u'%s %s' % (firstname.strip(), surname.strip(),)
        return name


def WikidataQueryPageGenerator(query, site=None):
    """Generate pages that result from the given WikidataQuery.

    @param query: the WikidataQuery query string.
    @param site: Site for generator results.
    @type site: L{pywikibot.site.BaseSite}

    """
    if site is None:
        site = pywikibot.Site()
    repo = site.data_repository()

    wd_queryset = wdquery.QuerySet(query)

    wd_query = wdquery.WikidataQuery(cacheMaxAge=0)
    data = wd_query.query(wd_queryset)

    pywikibot.output(u'retrieved %d items' % data[u'status'][u'items'])

    foundit=False
    
    for item in data[u'items']:
        if int(item) > 1708041:
            foundit=True
        if foundit:
            itempage = pywikibot.ItemPage(repo, u'Q' + unicode(item))
            yield itempage       


def main():
    query = u'CLAIM[245]'
    #query = u'CLAIM[245] AND CLAIM[106:1028181]' # Only painters

    generator = WikidataQueryPageGenerator(query)
    
    ulanImportBot = UlanImportBot(generator)
    ulanImportBot.run()

    '''

    ulanid = 500010654
    ulanurl = u'http://www.getty.edu/vow/ULANFullDisplay?find=&role=&nation=&subjectid=%s' % (ulanid,)
    ulanvocaburl = u'http://vocab.getty.edu/ulan/%s' % (ulanid,)
    ulanurljson = u'http://vocab.getty.edu/ulan/%s.json' % (ulanid,)
    ulanurljsonlong = u'http://vocab.getty.edu/download/json?uri=http://vocab.getty.edu/ulan/%s.json' % (ulanid,)
    print ulanurljson
    
    r = requests.get(ulanurljson)#, headers=headers)
    ulanPageDataDataObject = r.json()
    print ulanPageDataDataObject
    #ulanPage = urllib2.urlopen(ulanurljson)
    '''

if __name__ == "__main__":
    main()
