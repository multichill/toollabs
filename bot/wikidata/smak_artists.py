#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
C:\pywikibot\core>add_category.py -lang:wikidata -family:wikidata -file:categories_not_category.txt -namespace:0


"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib
import re
import pywikibot.data.wikidataquery as wdquery
import csv
import time
from collections import OrderedDict

class GroeningeBot:
    """
    
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        
        self.repo = pywikibot.Site().data_repository()
        self.generator = generator
        
        self.progressPage = pywikibot.Page(self.repo, title=u'User:Multichill/SMAK creators')
        #self.progressPage.get()

        self.rkditems = self.getRKD()
        #print self.rkditems
        self.viafitems = self.getVIAF()

        self.museumitem = pywikibot.ItemPage(self.repo, title=u'Q1540707')


    def getRKD(self, cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        query = u'CLAIM[650]'
        
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset, props=[str(650),])

        if data.get('status').get('error')=='OK':
            expectedItems = data.get('status').get('items')
            props = data.get('props').get(str(650))
            for prop in props:
                # FIXME: This will overwrite id's that are used more than once.
                # Use with care and clean up your dataset first
                result[prop[2]] = u'Q%s' % (prop[0],)


            pywikibot.output('I expected %s items and now have %s items with RKD in cache' % (expectedItems, len(result)))

        return result

    def getVIAF(self, cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        query = u'CLAIM[214]'
        
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset, props=[str(214),])

        if data.get('status').get('error')=='OK':
            expectedItems = data.get('status').get('items')
            props = data.get('props').get(str(214))
            for prop in props:
                # FIXME: This will overwrite id's that are used more than once.
                # Use with care and clean up your dataset first
                result[prop[2]] = u'Q%s' % (prop[0],)

            pywikibot.output('I expected %s items and now have %s items with VIAF in cache' % (expectedItems, len(result)))

        return result
    
    def run (self):
        '''
        Work on all the painters
        '''

        
        totalFound = 0
        totalAnon = 0
        totalMissing = 0
        totalMissingAll = 0
        totalMissingRKD = 0
        totalMissingVIAF = 0
        totalMissingRKDVIAF = 0


        with open('SMAK-creators-completed.csv', 'wb') as csvfile:
            fieldnames = ['creatorId', u'creator', u'creatorOdisPid', u'creatorOdisName', 'creatorViafPid', u'creatorViafName', u'creatorRkdPid', u'creatorRkdName', u'creatorWikidataPid', u'creatorUlanPid', u'nlLabel', u'nlDesc', u'enLabel', u'enDesc']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            newtext = u'{| class="wikitable sortable"\n! creatorId !! creator !! nlLabel !! nlDesc !! enLabel !! enDesc !! creatorWikidataPid !! creatorOdisPid !! creatorViafPid !! creatorRkdPid !! creatorUlanPid\n'

            missingList = []

            for painterDict in self.generator:
                itemTitle = u''
                resultdata = {u'creatorId' : painterDict.get('creatorId'),
                              u'creator' : painterDict.get('creator'),
                              u'creatorOdisPid' : painterDict.get('creatorOdisPid'),
                              u'creatorOdisName' : painterDict.get('creatorOdisName'),
                              u'creatorViafPid' : painterDict.get('creatorViafPid'),
                              u'creatorViafName' : painterDict.get('creatorViafName'),
                              u'creatorRkdPid' : painterDict.get('creatorRkdPid'),
                              u'creatorRkdName' : painterDict.get('creatorRkdName'),
                              u'creatorWikidataPid' : painterDict.get('creatorWikidataPid'),
                              u'creatorUlanPid' : u'',
                              u'nlLabel' : '',
                              u'nlDesc' : '',
                              u'enLabel' : '',
                              u'enDesc' : '',
                              }
                if painterDict.get('creatorWikidataPid'):
                    itemTitle = painterDict.get('creatorWikidataPid').replace('http://www.wikidata.org/entity/', '').replace('http://www.wikidata.org/wiki/', '')

                if not itemTitle and painterDict.get('creatorRkdPid'):
                    print u'RKD!'
                    itemTitle = self.getItemFromRKD(painterDict.get('creatorRkdPid'))

                if not itemTitle and painterDict.get('creatorViafPid'):
                    print u'VIAF!'
                    itemTitle = self.getItemFromVIAF(painterDict.get('creatorViafPid'))
                    
                if itemTitle:
                    totalFound = totalFound + 1
                    print itemTitle
                    
                    item = pywikibot.ItemPage(self.repo, title=itemTitle)

                    if item.isRedirectPage():
                        item = item.getRedirectTarget()

                    resultdata[u'creatorWikidataPid'] = u'http://www.wikidata.org/entity/%s' % (item.title(),)
                    
                    data = item.get()
                    claims = data.get('claims')

                    if u'P650' not in claims and painterDict.get('creatorRkdPid'):
                        rkdid = painterDict.get('creatorRkdPid').replace(u'https://rkd.nl/explore/artists/', u'')
                        newclaim = pywikibot.Claim(self.repo, u'P650')
                        newclaim.setTarget(rkdid)
                        pywikibot.output('Adding RKDartists claim to %s' % item)
                        item.addClaim(newclaim)

                        newreference = pywikibot.Claim(self.repo, u'P143')
                        newreference.setTarget(self.museumitem)
                        pywikibot.output('Adding new reference claim to %s' % item)
                        newclaim.addSources([newreference])

                    if u'P214' not in claims and painterDict.get('creatorViafPid'):
                        viafid = painterDict.get('creatorViafPid').replace(u'http://viaf.org/viaf/', u'')
                        newclaim = pywikibot.Claim(self.repo, u'P214')
                        newclaim.setTarget(viafid)
                        pywikibot.output('Adding VIAF claim to %s' % item)
                        item.addClaim(newclaim)

                        newreference = pywikibot.Claim(self.repo, u'P143')
                        newreference.setTarget(self.museumitem)
                        pywikibot.output('Adding new reference claim to %s' % item)
                        newclaim.addSources([newreference])

                    if u'P650' in claims:
                        resultdata[u'creatorRkdPid'] = u'https://rkd.nl/explore/artists/%s' % (claims.get(u'P650')[0].getTarget(),)
                    if u'P214' in claims:
                        resultdata[u'creatorViafPid'] = u'http://viaf.org/viaf/%s' % (claims.get(u'P214')[0].getTarget(),)
                    if u'P245' in claims:
                        resultdata[u'creatorUlanPid'] = u'http://vocab.getty.edu/page/ulan/%s' % (claims.get(u'P245')[0].getTarget(),)

                    if data.get('labels').get('nl'):
                        resultdata[u'nlLabel'] = data.get('labels').get('nl').encode(u'utf-8')
                    if data.get('descriptions').get('nl'):
                        resultdata[u'nlDesc'] = data.get('descriptions').get('nl').encode(u'utf-8')
                    if data.get('labels').get('en'):
                        resultdata[u'enLabel'] = data.get('labels').get('en').encode(u'utf-8')
                    if data.get('descriptions').get('en'):
                        resultdata[u'enDesc'] = data.get('descriptions').get('en').encode(u'utf-8')                       
                    
                else:
                    if painterDict.get('creator').startswith('Anoniem'):
                        totalAnon = totalAnon + 1
                        resultdata[u'creatorWikidataPid'] = u'http://www.wikidata.org/entity/Q4233718'
                    else:
                        totalMissing = totalMissing + 1
                        missingList.append(painterDict.get('creator'))

                        if painterDict.get('creatorRkdPid') and painterDict.get('creatorViafPid'):
                            totalMissingRKDVIAF = totalMissingRKDVIAF + 1
                        elif painterDict.get('creatorRkdPid') and not painterDict.get('creatorViafPid'):
                            totalMissingRKD = totalMissingRKD + 1
                        elif not painterDict.get('creatorRkdPid') and painterDict.get('creatorViafPid'):
                            totalMissingVIAF = totalMissingVIAF + 1
                        else:
                            totalMissingAll = totalMissingAll + 1

                        ## Enable this later
                        #if painterDict.get('creatorRkdPid') or painterDict.get('creatorViafPid'):
                        #    print u'Going to create shit'
                        #    item = self.makeCreatorItem(unicode(resultdata.get('creator'), u'utf-8'), painterDict.get('creatorRkdPid'), painterDict.get('creatorViafPid'))
                        #    resultdata[u'creatorWikidataPid'] = u'http://www.wikidata.org/entity/%s' % (item.title(),)

                writer.writerow(resultdata)
                newtext = newtext + u'|-\n'
                newtext = newtext + u'| %s ' % unicode(resultdata.get('creatorId'), u'utf-8')
                newtext = newtext + u'|| %s ' % unicode(resultdata.get('creator'), u'utf-8')
                newtext = newtext + u'|| %s ' % unicode(resultdata.get('nlLabel'), u'utf-8')
                newtext = newtext + u'|| %s ' % unicode(resultdata.get('nlDesc'), u'utf-8')
                newtext = newtext + u'|| %s ' % unicode(resultdata.get('enLabel'), u'utf-8')
                newtext = newtext + u'|| %s ' % unicode(resultdata.get('enDesc'), u'utf-8')
                newtext = newtext + u'|| [[%s]] ' % resultdata.get('creatorWikidataPid').replace(u'http://www.wikidata.org/entity/', u'')
                newtext = newtext + u'|| %s ' % resultdata.get('creatorOdisPid')
                newtext = newtext + u'|| %s ' % resultdata.get('creatorViafPid')
                newtext = newtext + u'|| %s\n' % resultdata.get('creatorRkdPid')
                newtext = newtext + u'|| %s\n' % resultdata.get('creatorUlanPid')
                #print newtext        

        newtext = newtext + u'|}\n\n'

        print u'Start missing list\n\n\n'

        print missingList

        print u'\n\n\n\n'

        missing = u''

        missing = missing + u'* Total found: %s\n' % (totalFound,)
        missing = missing + u'* Total anon: %s\n' % (totalAnon,)
        missing = missing + u'* Total missing: %s\n' % (totalMissing,)
        missing = missing + u'** Total missing, but do have RKD and VIAF: %s\n' % (totalMissingRKDVIAF,)
        missing = missing + u'** Total missing, but do have RKD: %s\n' % (totalMissingRKD,)
        missing = missing + u'** Total missing, but do have VIAF: %s\n' % (totalMissingVIAF,)
        missing = missing + u'** Total missing, but nothing at all: %s\n' % (totalMissingAll,)

        print missing
        newtext = newtext + missing
        newtext = newtext + u'\n\n[[Category:User:Multichill|{{SUBPAGENAME}}]]'
        summary = u'Updating list'
        self.progressPage.put(newtext, summary)        
                
    def getItemFromRKD(self, rkdurl):
        '''
        Try to find the wikidata item id based on an rkd url
        '''
        rkdid = rkdurl.replace(u'https://rkd.nl/explore/artists/', u'')
        if rkdid in self.rkditems:
            return self.rkditems[rkdid]
        
        return u''

    def getItemFromVIAF(self, viafurl):
        '''
        Try to find the wikidata item id based on an viaf url
        '''
        viafid = viafurl.replace(u'http://viaf.org/viaf/', u'')
        print u'viaf id is %s' % viafid
        print len(self.viafitems)
        #18653592
        if viafid in self.viafitems:
            print u'found viaf!'
            return self.viafitems[viafid]
        
        return u''
        

    def makeCreatorItem(self, name, rkd, viaf):
        '''
        Function to create a new painter, fill it and return the id
        '''

        data = {'labels': {},
                'descriptions': {},
                }

        # We need to normalize the name
        if u',' in name:
            (surname, sep, firstname) = name.partition(u',')
            name = u'%s %s' % (firstname.strip(), surname.strip(),)

        for lang in (u'de', u'en', u'es', u'fr', u'nl'):
            data['labels'][lang] = {'language': lang, 'value': name}
            
        print data

        identification = {}
        summary = u'Creating new item for Stedelijk Museum voor Actuele Kunst artist'
        pywikibot.output(summary)

        result = self.repo.editEntity(identification, data, summary=summary)
        print result
        time.sleep(10)
        painterItemTitle = result.get(u'entity').get('id')
        painterItem = pywikibot.ItemPage(self.repo, title=painterItemTitle)
                         

        # It's a human
        humanItem = pywikibot.ItemPage(self.repo, title=u'Q5')
        newclaim = pywikibot.Claim(self.repo, u'P31')
        newclaim.setTarget(humanItem)
        painterItem.addClaim(newclaim)
        
        if rkd:
            rkdid = rkd.replace(u'https://rkd.nl/explore/artists/', u'')
            newclaim = pywikibot.Claim(self.repo, u'P650')
            newclaim.setTarget(rkdid)
            pywikibot.output('Adding RKDartists claim to %s' % painterItem)
            painterItem.addClaim(newclaim)

            newreference = pywikibot.Claim(self.repo, u'P143')
            newreference.setTarget(self.museumitem)
            pywikibot.output('Adding new reference claim to %s' % painterItem)
            newclaim.addSources([newreference])

        if viaf:
            viafid = viaf.replace(u'http://viaf.org/viaf/', u'')
            newclaim = pywikibot.Claim(self.repo, u'P214')
            newclaim.setTarget(viafid)
            pywikibot.output('Adding VIAF claim to %s' % painterItem)
            painterItem.addClaim(newclaim)

            newreference = pywikibot.Claim(self.repo, u'P143')
            newreference.setTarget(self.museumitem)
            pywikibot.output('Adding new reference claim to %s' % painterItem)
            newclaim.addSources([newreference])
            
        return painterItem.title()


      

def getPainterGenerator():
    with open('SMAK-creators-completed-2016-01-23.csv', 'rb') as csvfile:    
        reader = csv.DictReader(csvfile)
        foundit = True
        for row in reader:
            if row.get('creatorId')=="2621":
                foundit = True
            if foundit:
                yield row
    


def main():
    
        
    painterGen = getPainterGenerator()

    #for painter in painterGen:
    #    print painter
    
    groeningeBot = GroeningeBot(painterGen)
    groeningeBot.run()
    
    

if __name__ == "__main__":
    main()
