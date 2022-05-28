#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import NLI (National Library of Israel identifier, https://www.wikidata.org/wiki/Property:P949) statements from viaf. Could be expanded later to something more general

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

class ViafImportBot:
    """
    
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields wikidata item objects.

        """
        
        self.repo = pywikibot.Site().data_repository()
        self.generator = pagegenerators.PreloadingEntityGenerator(generator)
        self.viafitem = pywikibot.ItemPage(self.repo, u'Q54919')

    
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

            if not u'P214' in claims:
                print u'No viaf found, skipping'
                continue

            if u'P949' in claims:
                # Already has ULAN, great!
                continue

            viafid = claims.get(u'P214')[0].getTarget()

            if not viafid:
                print u'Viaf is set to novalue, skipping'
                continue
            
            viafurl = u'http://www.viaf.org/viaf/%s/' % (viafid,)
            viafurljson = u'%sjustlinks.json' % (viafurl,)
            try:
                viafPage = urllib2.urlopen(viafurljson)
            except urllib2.HTTPError as e:
                pywikibot.output('On %s the VIAF link %s returned this HTTPError %s: %s' % (item.title(), viafurljson, e.errno, e.strerror))
                
                
                
            viafPageData = viafPage.read()


            # That didn't work. Stupid viaf api always returns 200
            #if not viafPage.getcode()==200:
            #    pywikibot.output('On %s the VIAF link %s gave a %s http code, skipping it' % (item.title(), viafurl, viafPage.getcode()))
            #    continue

            # viaf json api might return junk if it's a redirect
            try:
                viafPageDataDataObject = json.loads(viafPageData)
            except ValueError:
                pywikibot.output('On %s the VIAF link %s returned this junk:\n %s' % (item.title(), viafurljson, viafPageData))
                continue

            if viafPageDataDataObject.get(u'NLI'):
                ulanid = viafPageDataDataObject.get(u'NLI')[0]
                #print u'I found ulanid %s for item %s' % (ulanid, item.title())

                
                newclaim = pywikibot.Claim(self.repo, u'P949')
                newclaim.setTarget(ulanid)
                pywikibot.output('Adding National Library of Israel identifier %s claim to %s' % (ulanid, item.title(),) )

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

    foundit=True
    
    for item in data[u'items']:
        if int(item) > 17380752:
            foundit=True
        if foundit:
            itempage = pywikibot.ItemPage(repo, u'Q' + unicode(item))
            yield itempage       


def main():
    query = u'CLAIM[214] AND NOCLAIM[949]'
    #query = u'CLAIM[214] AND NOCLAIM[245] AND CLAIM[106:1028181]' # Only painters
    #query = u'CLAIM[214] AND NOCLAIM[245] AND CLAIM[106:(TREE[329439,3391743,15296811][][279])]' # Engraver, visual artist and drawer tree
    #query = u'CLAIM[214] AND CLAIM[650] AND NOCLAIM[245]' # Has VIAF and RKDartists, but not ULAN

    generator = WikidataQueryPageGenerator(query)
    
    viafImportBot = ViafImportBot(generator)
    viafImportBot.run()

if __name__ == "__main__":
    main()
