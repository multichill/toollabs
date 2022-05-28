#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import Teylers Museum paintings to wikidata

"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib
import re
import pywikibot.data.wikidataquery as wdquery

class PaintingsBot:
    """
    A bot to enrich and create monuments on Wikidata
    """
    def __init__(self, dictGenerator, paintingIdProperty):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.generator = dictGenerator
        self.repo = pywikibot.Site().data_repository()
        
        self.paintingIdProperty = paintingIdProperty
        self.paintingIds = self.fillCache(self.paintingIdProperty)
        
    def fillCache(self, propertyId, queryoverride=u'', cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        if queryoverride:
            query = queryoverride
        else:
            query = u'CLAIM[195:474563] AND CLAIM[%s]' % (propertyId,)
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset, props=[str(propertyId),])

        if data.get('status').get('error')=='OK':
            expectedItems = data.get('status').get('items')
            props = data.get('props').get(str(propertyId))
            for prop in props:
                # FIXME: This will overwrite id's that are used more than once.
                # Use with care and clean up your dataset first
                result[prop[2]] = prop[0]

            if expectedItems==len(result):
                pywikibot.output('I now have %s items in cache' % expectedItems)

        return result
                        
    def run(self):
        """
        Starts the robot.
        """
        teylers = pywikibot.ItemPage(self.repo, u'Q474563')
        for painting in self.generator:
            # Buh, for this one I know for sure it's in there
            
            
            paintingId = painting['object']['proxies'][0]['dcIdentifier']['def'][0]
            uri = painting['object']['aggregations'][0]['webResources'][0]['about']
            europeanaUrl = u'http://europeana.eu/portal/record/%s.html' % (painting['object']['about'],)

            print paintingId
            print uri

            dcCreator = painting['object']['proxies'][0]['dcCreator']['def'][0].strip()
            #print dcCreator

            dcCreatorName = u''

            regex = u'^([^,]+), ([^\(]+) \(.+\)$'

            match = re.match(regex, dcCreator)

            

            if match:
                dcCreatorName = '%s %s' % (match.group(2).strip(), match.group(1).strip(),)
            else:
                dcCreatorName = dcCreator

            
            
            #print painting['object']['language']
            #print painting['object']['title']
            #print painting['object']['about']
            #print painting['object']['proxies'][0]['dcCreator']['def'][0]
            #print painting['object']['proxies'][0]['dcFormat']['def'][0]
            #print painting['object']['proxies'][0]['dcIdentifier']['def'][0]
            #print painting['object']['proxies'][0]['dcIdentifier']['def'][1]
            
            paintingItem = None
            newclaims = []
            if paintingId in self.paintingIds:
                paintingItemTitle = u'Q%s' % (self.paintingIds.get(paintingId),)
                print paintingItemTitle
                paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

            else:
                
                #print 'bla'
                #monumentItem = pywikibot.ItemPage(self.repo, title=u'')

                
                        #print dcCreatorName


                data = {'labels': {},
                        'descriptions': {},
                        }
                title = painting['object']['title'][0].strip()
                data['labels']['nl'] = {'language': u'nl', 'value': title}

                

                if dcCreatorName:
                    data['descriptions']['en'] = {'language': u'en', 'value' : u'painting by %s' % (dcCreatorName,)}
                    data['descriptions']['nl'] = {'language': u'nl', 'value' : u'schilderij van %s' % (dcCreatorName,)}
                    

                print data
                

                identification = {}
                summary = u'Creating new item with data from %s ' % (europeanaUrl,)
                pywikibot.output(summary)

                result = self.repo.editEntity(identification, data, summary=summary)
                #print result
                paintingItemTitle = result.get(u'entity').get('id')
                paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

                newclaim = pywikibot.Claim(self.repo, u'P%s' % (self.paintingIdProperty,))
                newclaim.setTarget(paintingId)
                pywikibot.output('Adding new id claim to %s' % paintingItem)
                paintingItem.addClaim(newclaim)

                newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                newreference.setTarget(uri)
                pywikibot.output('Adding new reference claim to %s' % paintingItem)
                newclaim.addSource(newreference)
                
                newqualifier = pywikibot.Claim(self.repo, u'P195') #Add collection, isQualifier=True
                newqualifier.setTarget(teylers)
                pywikibot.output('Adding new qualifier claim to %s' % paintingItem)
                newclaim.addQualifier(newqualifier)

                collectionclaim = pywikibot.Claim(self.repo, u'P195')
                collectionclaim.setTarget(teylers)
                pywikibot.output('Adding collection claim to %s' % paintingItem)
                paintingItem.addClaim(collectionclaim)

                newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                newreference.setTarget(europeanaUrl)
                pywikibot.output('Adding new reference claim to %s' % paintingItem)
                collectionclaim.addSource(newreference)

            if paintingItem:
                
                data = paintingItem.get()
                claims = data.get('claims')
                #print claims

                # located in
                if u'P276' not in claims:
                    newclaim = pywikibot.Claim(self.repo, u'P276')
                    newclaim.setTarget(teylers)
                    pywikibot.output('Adding located in claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)

                    newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                    newreference.setTarget(europeanaUrl)
                    pywikibot.output('Adding new reference claim to %s' % paintingItem)
                    newclaim.addSource(newreference)
                    

                # instance of always painting while working on the painting collection
                if u'P31' not in claims:
                    
                    dcformatItem = pywikibot.ItemPage(self.repo, title='Q3305213')

                    newclaim = pywikibot.Claim(self.repo, u'P31')
                    newclaim.setTarget(dcformatItem)
                    pywikibot.output('Adding instance claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)

                    newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                    newreference.setTarget(europeanaUrl)
                    pywikibot.output('Adding new reference claim to %s' % paintingItem)
                    newclaim.addSource(newreference) 

                # creator        
                if u'P170' not in claims and dcCreatorName:
                    creategen = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataItemGenerator(pagegenerators.SearchPageGenerator(dcCreatorName, step=None, total=10, namespaces=[0], site=self.repo)))
                    
                    newcreator = None


                    for creatoritem in creategen:
                        print creatoritem.title()
                        if creatoritem.get().get('labels').get('en') == dcCreatorName or creatoritem.get().get('labels').get('nl') == dcCreatorName:
                            print creatoritem.get().get('labels').get('en')
                            print creatoritem.get().get('labels').get('nl')
                            # Check occupation and country of citizinship
                            if u'P106' in creatoritem.get().get('claims') and u'P27' in creatoritem.get().get('claims'):
                                newcreator = creatoritem
                                continue
                        elif (creatoritem.get().get('aliases').get('en') and dcCreatorName in creatoritem.get().get('aliases').get('en')) or (creatoritem.get().get('aliases').get('nl') and dcCreatorName in creatoritem.get().get('aliases').get('nl')):
                            if u'P106' in creatoritem.get().get('claims') and u'P27' in creatoritem.get().get('claims'):
                                newcreator = creatoritem
                                continue        

                    if newcreator:
                        pywikibot.output(newcreator.title())

                        newclaim = pywikibot.Claim(self.repo, u'P170')
                        newclaim.setTarget(newcreator)
                        pywikibot.output('Adding creator claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                        newreference.setTarget(europeanaUrl)
                        pywikibot.output('Adding new reference claim to %s' % paintingItem)
                        newclaim.addSource(newreference)
                        
                        #creatoritem = pywikibot.ItemPage(self.repo, creatorpage)
                        print creatoritem.title()
                        print creatoritem.get()

                    else:
                        pywikibot.output('No item found for %s' % (dcCreatorName, ))
                    
                # date of creation
                if u'P571' not in claims:
                    if painting['object']['proxies'][0].get('dcDate'):
                        dccreated = painting['object']['proxies'][0]['dcDate']['def'][0].strip()
                        if len(dccreated)==4: # It's a year
                            newdate = pywikibot.WbTime(year=dccreated)
                            newclaim = pywikibot.Claim(self.repo, u'P571')
                            newclaim.setTarget(newdate)
                            pywikibot.output('Adding date of creation claim to %s' % paintingItem)
                            paintingItem.addClaim(newclaim)

                            newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                            newreference.setTarget(europeanaUrl)
                            pywikibot.output('Adding new reference claim to %s' % paintingItem)
                            newclaim.addSource(newreference)

                # Europeana ID
                if u'P727' not in claims:
                    europeanaID = painting['object']['about'].lstrip('/')

                    newclaim = pywikibot.Claim(self.repo, u'P727')
                    newclaim.setTarget(europeanaID)
                    pywikibot.output('Adding Europeana ID claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)

                    newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                    newreference.setTarget(europeanaUrl)
                    pywikibot.output('Adding new reference claim to %s' % paintingItem)
                    newclaim.addSource(newreference)

        
def getPaintingGenerator(query=u''):
    '''
    Bla %02d
    '''
    searchurl = 'http://www.europeana.eu/api/v2/search.json?wskey=fakekey&profile=minimal&rows=100&start=301&query=DATA_PROVIDER%3A"Teylers+Museum"&qf=what:schilderij'
    #url = 'http://www.europeana.eu/api/v2/search.json?wskey=fakekey&profile=minimal&rows=100&start=101&query=DATA_PROVIDER%3A%22Teylers+Museum%22&qf=identifier:KS*'
    #url = 'http://www.europeana.eu/api/v2/search.json?wskey=fakekey&profile=minimal&rows=100&start=201&query=DATA_PROVIDER%3A%22Teylers+Museum%22&qf=identifier:KS*'
    #url = 'http://www.europeana.eu/api/v2/search.json?wskey=fakekey&profile=minimal&rows=100&start=301&query=DATA_PROVIDER%3A%22Teylers+Museum%22&qf=identifier:KS*'
    #url = 'http://europeana.eu/api/v2/record/92034/GVNRC_MAU01_%04d.json?wskey=fakekey&profile=full'
    url = 'http://europeana.eu/api/v2/record/%s.json?wskey=fakekey&profile=full'

    overviewPage = urllib.urlopen(searchurl)
    overviewData = overviewPage.read()
    overviewJsonData = json.loads(overviewData)
    overviewPage.close()

    for item in overviewJsonData.get('items'):
        apiPage = urllib.urlopen(url % (item.get('id'),))
        apiData = apiPage.read()
        jsonData = json.loads(apiData)
        
        apiPage.close()
        if jsonData.get(u'success'):
            yield jsonData
        else:
            print jsonData
            

def main():
    paintingGen = getPaintingGenerator()
    
    paintingsBot = PaintingsBot(paintingGen, 217)
    paintingsBot.run()


if __name__ == "__main__":
    main()
