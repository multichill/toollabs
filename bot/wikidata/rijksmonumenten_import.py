#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import Rijksmonumenten to Wikidata.
The data is coming from the monuments database, see https://commons.wikimedia.org/wiki/Commons:Monuments_database

Code is quite messy, but should be easy to reuse it for other countries.

"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib
import re
import pywikibot.data.wikidataquery as wdquery

class MonumentsBot:
    """
    A bot to enrich and create monuments on Wikidata
    """
    def __init__(self, dictGenerator, monumentIdProperty):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.
            * monumentId   - The property that's used to identify a monument

        """
        self.generator = dictGenerator
        self.repo = pywikibot.Site().data_repository()
        self.monumentIdProperty = monumentIdProperty
        self.monumentType = u'Q916333'
        self.monumentIds = self.fillCache(self.monumentIdProperty)
        
        self.iso3166_1Property = '297'
        self.iso3166_1Codes = self.fillCache(self.iso3166_1Property, cacheMaxAge=30)
        self.iso3166_2Property = '300'
        self.iso3166_2Codes = self.fillCache(self.iso3166_2Property, cacheMaxAge=30)
        
    def fillCache(self, propertyId, cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        
        query = u'CLAIM[%s]' % (propertyId,)
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
        for monument in self.generator:
            try:
                monumentItem = None
                newclaims = []
                if monument.get('id') in self.monumentIds:
                    monumentItemTitle = u'Q%s' % (self.monumentIds.get(monument.get('id')),)
                    print monument
                    print monumentItemTitle
                    monumentItem = pywikibot.ItemPage(self.repo, title=monumentItemTitle)

                else:
                    print 'bla'
                    #monumentItem = pywikibot.ItemPage(self.repo, title=u'')

                    # Fix wikitext and more shit
                    monumentName = monument.get('name')
                    

                    #monumentName = re.sub('^\[\[([^\|]+)\|([^\]]+)\]\](.+)$', u'\\2\\3', monumentName)
                    monumentName = re.sub('\[\[([^\|]+)\|([^\]]+)\]\]', u'\\2', monumentName)
                    #monumentName = re.sub('^\[\[([^\]]+)\]\](.+)$', u'\\1\\2', monumentName)
                    monumentName = re.sub('\[\[([^\]]+)\]\]', u'\\1', monumentName)

                    if len(monumentName) > 200:
                        monumentName = re.sub('^(.{20,200})\.(.+)$', u'\\1.', monumentName)

                    if len(monumentName) > 200:
                        monumentName = re.sub('^(.{20,200}),(.+)$', u'\\1.', monumentName)   

                    # Still have to do more shit

                    data = {'labels':
                                {monument.get('lang'):
                                 {'language': monument.get('lang'),
                                  'value': monumentName}
                                 }
                            }
                    identification = {}
                    summary = u'Creating new item with data from %s' % (monument.get('source'),)
                    pywikibot.output(summary)
                    #monumentItem.editEntity(data, summary=summary)
                    result = self.repo.editEntity(identification, data, summary=summary)
                    #print result
                    monumentItemTitle = result.get(u'entity').get('id')
                    monumentItem = pywikibot.ItemPage(self.repo, title=monumentItemTitle)
                    '''
    {u'success': 1, u'entity': {u'lastrevid': 134951692, u'labels': {u'nl': {u'value
    ': u'[[Elswout]]: hoofdgebouw', u'language': u'nl'}}, u'descriptions': [], u'cla
    ims': [], u'type': u'item', u'id': u'Q17000292', u'aliases': []}}
    {u'success': 1, u'entity': {u'lastrevid': 134951703, u'labels': {u'nl': {u'value
    ': u'Elswout: landgoed', u'language': u'nl'}}, u'descriptions': [], u'claims': [
    ], u'type': u'item', u'id': u'Q17000293', u'aliases': []}}
    {u'success': 1, u'entity': {u'lastrevid': 134951710, u'labels': {u'nl': {u'value
    ': u'Elswout: keermuren van het voorplein', u'language': u'nl'}}, u'descriptions
    ': [], u'claims': [], u'type': u'item', u'id': u'Q17000294', u'aliases': []}}
                    '''
                    #print monumentItem.title()

                    newclaim = pywikibot.Claim(self.repo, u'P%s' % (self.monumentIdProperty,))
                    newclaim.setTarget(monument.get('id'))
                    pywikibot.output('Adding new id claim to %s' % monumentItem)
                    monumentItem.addClaim(newclaim)


                if monumentItem and monumentItem.exists():
                    data = monumentItem.get()
                    descriptions = data.get('descriptions')
                    claims = data.get('claims')
                    print claims

                    if monument.get('address') and not descriptions.get(monument.get('lang')):
                        #FIXME: If it contains links like '[[]]' it will break
                        if not u'(' in monument.get('address'):
                            monumentDescription = u'Rijksmonument op %s' % (monument.get('address'),)
                            summary = u'Setting %s description to "%s"' % (monument.get('lang'), monumentDescription,)
                            try:
                                monumentItem.editDescriptions({monument.get('lang') : monumentDescription}, summary = summary)
                            except pywikibot.exceptions.APIError:
                                pywikibot.output(u'Ooops, that didn\'t work. Another item already has the same description')
                                

                    if u'P31' not in claims:
                        newclaim = pywikibot.Claim(self.repo, u'P31')
                        monumentTypeItem = pywikibot.ItemPage(self.repo, title=self.monumentType)
                        newclaim.setTarget(monumentTypeItem)
                        pywikibot.output('Adding instance claim to %s' % monumentItem)
                        monumentItem.addClaim(newclaim)
                        
                    
                    if monument.get('adm0') and u'P17' not in claims:
                        print u'no country found'
                        if monument.get('adm0').upper() in self.iso3166_1Codes:
                            #print u'Found an item for the ISO code'
                            adm0ItemTitle = u'Q%s' % (self.iso3166_1Codes.get(monument.get('adm0').upper()),)
                            adm0Item = pywikibot.ItemPage(self.repo, title=adm0ItemTitle)

                            newclaim = pywikibot.Claim(self.repo, u'P17')
                            newclaim.setTarget(adm0Item)
                            pywikibot.output('Adding country claim to %s' % monumentItem)
                            monumentItem.addClaim(newclaim)
                            
                    else:
                        print u'country found'

                    foundProv = False
                    if u'P131' in claims and len(claims.get('P131'))==1:
                        if monument.get('adm1').upper() in self.iso3166_2Codes:
                            if claims.get('P131')[0].getTarget().title() ==  u'Q%s' % (self.iso3166_2Codes.get(monument.get('adm1').upper()),):
                                print u'This item only contains a province claim'
                                foundProv = True
                        

                    if u'P131' not in claims or foundProv:
                        print u'no administrative thingie found'
                        for adm in [monument.get('adm1'),
                                    monument.get('adm2'),
                                    monument.get('adm3'),
                                    monument.get('adm4')]:
                            if adm:
                                if adm.upper() in self.iso3166_2Codes:
                                    if not foundProv:
                                        print u'Found an item for the ISO code'
                                        admItemTitle = u'Q%s' % (self.iso3166_2Codes.get(adm.upper()),)
                                        admItem = pywikibot.ItemPage(self.repo, title=admItemTitle)

                                        newclaim = pywikibot.Claim(self.repo, u'P131')
                                        newclaim.setTarget(admItem)
                                        pywikibot.output(u'Adding %s to %s' % (admItem.title(), monumentItem.title()))
                                        monumentItem.addClaim(newclaim)
                                    
                                    #print adm1Item.get()
                                else:
                                    adm = adm.replace(u'[', u'').replace(u']', u'')
                                    site = pywikibot.Site(monument.get('lang'), u'wikipedia')
                                    admLink = pywikibot.Link(adm, source=site, defaultNamespace=0)
                                    admPage = pywikibot.Page(admLink)
                                    if admPage.isRedirectPage():
                                        admPage = pywikibot.Page(admPage.getRedirectTarget())
                                    if not admPage.exists():
                                        pywikibot.output('[[%s]] doesn\'t exist so I can\'t link to it' % (admPage.title(),))
                                    elif admPage.isDisambig():
                                        pywikibot.output('[[%s]] is a disambiguation page so I can\'t link to it' % (admPage.title(),))
                                    else:
                                        admItem = pywikibot.ItemPage.fromPage(admPage)
                                        if admItem.exists():
                                            munFound = False
                                            if 'P31' in admItem.claims:
                                                for instClaim in admItem.claims.get('P31'):
                                                    if instClaim.getTarget().title() == 'Q2039348':
                                                        munFound = True
                                            if not munFound:
                                                # It's not an administrative division, but it might be in one
                                                if 'P131' in admItem.claims:
                                                    for possAdmClaim in admItem.claims.get('P131'):
                                                        possAdmItem = possAdmClaim.getTarget()
                                                        possAdmItem.get()
                                                        if 'P31' in possAdmItem.claims:
                                                            for instClaim in possAdmItem.claims.get('P31'):
                                                                if instClaim.getTarget().title() == 'Q2039348':
                                                                    admItem = possAdmItem
                                                                    munFound = True
                                                                    continue
           
                                                if munFound:
                                                    newclaim = pywikibot.Claim(self.repo, u'P131')
                                                    newclaim.setTarget(admItem)
                                                    pywikibot.output(u'Adding %s to %s' % (admItem.title(), monumentItem.title()))
                                                    monumentItem.addClaim(newclaim)
                    
                    else:
                        print u'administrative thingie found'

                    if monument.get('address') and u'P969' not in claims:
                        if u'[' not in monument.get('address') and u']' not in monument.get('address') and u'|' not in monument.get('address'):
                            newclaim = pywikibot.Claim(self.repo, u'P969')
                            newclaim.setTarget(monument.get('address'))
                            pywikibot.output(u'Adding %s to %s' % (monument.get('address'), monumentItem.title()))
                            monumentItem.addClaim(newclaim)
                        else:
                            print u'Contains funky chars, skipping'
                            
                        
                        
                        print u'no address found'
                        # Clean up the address and add it

                    else:
                        print u'address found'

                    if monument.get('lat') and monument.get('lon') and u'P625' not in claims:
                        print u'no coordinates found'
                        # Build coordinates and add them
                        coordinate = pywikibot.Coordinate(monument.get('lat'), monument.get('lon'), dim=100)
                        newclaim = pywikibot.Claim(self.repo, u'P625')
                        newclaim.setTarget(coordinate)
                        pywikibot.output(u'Adding %s, %s to %s' % (coordinate.lat, coordinate.lon, monumentItem.title()))
                        monumentItem.addClaim(newclaim)
                        
                    else:
                        print u'coordinates found'

                    if monument.get('image') and u'P18' not in claims:
                        print u'no image found'
                        # Construct
                        newclaim = pywikibot.Claim(self.repo, u'P18')
                        commonssite = pywikibot.Site("commons", "commons")
                        imagelink = pywikibot.Link(monument.get('image'), source=commonssite, defaultNamespace=6)
                        image = pywikibot.ImagePage(imagelink)
                        if image.isRedirectPage():
                            image = pywikibot.ImagePage(image.getRedirectTarget())
                        if not image.exists():
                            pywikibot.output('[[%s]] doesn\'t exist so I can\'t link to it' % (image.title(),))
                        else:
                            newclaim.setTarget(image)
                            pywikibot.output('Adding %s --> %s' % (newclaim.getID(), newclaim.getTarget()))
                            monumentItem.addClaim(newclaim)
                    else:
                        print u'image found'

                    # Europeana ID
                    if u'P727' not in claims:
                        europeanaID = u'2020718/DR_%s' % (monument.get('id'), )

                        newclaim = pywikibot.Claim(self.repo, u'P727')
                        newclaim.setTarget(europeanaID)
                        pywikibot.output('Adding Europeana ID claim to %s' % monumentItem)
                        monumentItem.addClaim(newclaim)

                    if monument.get('commonscat') and u'P373' not in claims:
                        print u'no image found'
                        # Construct
                        newclaim = pywikibot.Claim(self.repo, u'P373')
                        commonssite = pywikibot.Site("commons", "commons")
                        commonslink = pywikibot.Link(monument.get('commonscat'), source=commonssite, defaultNamespace=14)
                        commonscat = pywikibot.Page(commonslink)
                        if commonscat.isRedirectPage():
                            commonscat = pywikibot.Page(commonscat.getRedirectTarget())
                        if not commonscat.exists():
                            pywikibot.output('[[%s]] doesn\'t exist so I can\'t link to it' % (commonscat.title(),))
                        else:
                            newclaim.setTarget(commonscat.title(withNamespace=False))
                            pywikibot.output('Adding %s --> %s' % (newclaim.getID(), newclaim.getTarget()))
                            monumentItem.addClaim(newclaim)
            except:
                print u'Fuck this shit, I am just going to contiue anyway'
                pass

        
def getHeritageApiGenerator(query=u''):
    '''
    Bla
    '''
    #url = 'http://tools.wmflabs.org/heritage/api/api.php?action=search&srcountry=nl&srlang=nl&srmunicipality=%%27s-Gravenhage%&format=json&limit=5000'
    #url = 'http://tools.wmflabs.org/heritage/api/api.php?action=search&srcountry=nl&srlang=nl&srmunicipality=%Amsterdam%&format=json&limit=5000&srcontinue=nl|nl|518366'
    #url = 'http://tools.wmflabs.org/heritage/api/api.php?action=search&srcountry=nl&srlang=nl&srmunicipality=Bennebroek&format=json&limit=5000'
    url = 'http://tools.wmflabs.org/heritage/api/api.php?action=search&srcountry=nl&srlang=nl&format=json&limit=500&srcontinue=%s'
    srcontinue = 'nl|nl|30407'

    while srcontinue:
        apiPage = urllib.urlopen(url % (srcontinue,))
        apiData = apiPage.read()
        jsonData = json.loads(apiData)
        apiPage.close()

        if jsonData.get('continue'):
            srcontinue = jsonData.get('continue').get('srcontinue')
        else:
            srcontinue = False

        for monument in jsonData.get('monuments'):
            yield monument


def main():
    monGen = getHeritageApiGenerator()

    monumentsBot = MonumentsBot(monGen, 359)
    monumentsBot.run()
    

if __name__ == "__main__":
    main()
