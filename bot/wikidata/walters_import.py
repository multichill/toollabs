#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Robot to import paintings from Commons to Wikidata. It uses the standard pywikibot generators.
Do 


"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib
import re
import pywikibot.data.wikidataquery as wdquery
import datetime

class PaintingsBot:
    """
    A bot to enrich and create monuments on Wikidata
    """
    def __init__(self, generator, createnew=False):
        """
        Arguments:
            * generator - A standard python generator
            * createnew - Are we creating new items?

        """
        # Do something with filtergenerator and image generator?
        self.generator = pagegenerators.FileGenerator(pagegenerators.PreloadingGenerator(generator))
        self.createnew = createnew
        self.repo = pywikibot.Site().data_repository()
        
        self.paintingIdProperty = 217
        self.paintingIds = self.fillCache(self.paintingIdProperty)
        
    def fillCache(self, propertyId, queryoverride=u'', cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        if queryoverride:
            query = queryoverride
        else:
            query = u'CLAIM[195:210081] AND CLAIM[%s]' % (propertyId,)
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
        walters = pywikibot.ItemPage(self.repo, u'Q210081')
        validFields = [u'artist',
                       u'title',
                       u'description',
                       u'date',
                       u'period',
                       u'medium',
                       u'dimensions',
                       u'accession number',
                       u'id',
                       u'provenance',
                       u'credit',
                       u'inscriptions',
                       u'exhibition',
                       u'place of origin',
                       u'references',
                       u'permission',
                       u'other_versions',
                       u'place depicted',
                       u'wikidata',
                       ]
        
        for painting in self.generator:
            if not painting.exists():
                pywikibot.output(u'Skipping, does not exist')
                continue

            pywikibot.output(u'Working on %s' % (painting.title(),))
            
            # First we extract all the stuff we might need later
            # Than we do all the fancy checking

            rawdata = {}

            for (templatePage, templateParams) in painting.templatesWithParams():
                if templatePage.title()==u'Template:Walters Art Museum artwork':
                    for param in templateParams:
                        if len(param.split(u'='))==2:
                            (fieldname, field) = param.split(u'=')
                            if fieldname in validFields:
                                rawdata[fieldname] = field.strip()
                            else:
                                pywikibot.output(u'Found unknown field %s with contents %s' % (fieldname, field))


            # Ok. We got the raw data. Let's see if we can find a wikidata item
            paintingItemTitleTemplate = u''
            paintingItemTitleWDQ = u''
            paintingItemTitle = u''
            paintingItem = None

            if rawdata.get('wikidata'):
                paintingItemTitleTemplate = rawdata.get('wikidata')
                
            if rawdata.get(u'accession number'):
                if rawdata.get(u'accession number') in self.paintingIds:
                    paintingItemTitleWDQ = u'Q%s' % (self.paintingIds.get(rawdata.get(u'accession number')),)

            if paintingItemTitleTemplate and paintingItemTitleWDQ:
                if paintingItemTitleTemplate==paintingItemTitleWDQ:
                    paintingItemTitle=paintingItemTitleTemplate
                    pywikibot.output(u'Great, both the template and WDQ returned the same item')
                else:
                    pywikibot.output(u'ERROR, something seriously wrong here! I got both %s and %s!' % (paintingItemTitleTemplate, paintingItemTitleWDQ))
                    continue
            elif paintingItemTitleTemplate:
                paintingItemTitle = paintingItemTitleTemplate
                pywikibot.output(u'Adding %s = %s to cache' % (rawdata.get(u'accession number'), rawdata.get('wikidata').replace(u'Q', u'')))
                self.paintingIds[rawdata.get(u'accession number')] = rawdata.get('wikidata').replace(u'Q', u'')
                
            elif paintingItemTitleWDQ:
                paintingItemTitle = paintingItemTitleWDQ

                # Do something with adding the Q id
                self.addWikidataBacklink(painting, paintingItemTitle, summary=u'Adding missing Wikidata link')

            if paintingItemTitle:
                print paintingItemTitle
                paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)
            else:
                if not self.createnew:
                    pywikibot.output(u'I did not find a Wikidata item and I am not going to create one')
                    continue

                pywikibot.output(u'I could not find a Wikidata item, I am just going to create a new one!')

                if rawdata.get('title') and rawdata.get('artist') and rawdata.get('accession number') and rawdata.get('id'):

                    title = rawdata.get('title').strip("'")

                    if u'{' in title:
                        print title
                        titleRegex = u'^\{\{title\|(.+)\}\}$'
                        titleMatch = re.match(titleRegex, title)
                        if not titleMatch:
                            pywikibot.output(u'O, screw this title template madness, no match, making it empty')
                            title = u''
                        else:
                            title = titleMatch.group(1)

                    if u'{' in title:
                        pywikibot.output(u'O, screw this title template madness, more {, making it empty')
                        title = u''

                    aristRegex = u'^\{\{[cC]reator:(.+)\}\}$'
                    artistMatch = re.match(aristRegex, rawdata.get('artist'))
                    if not artistMatch:
                        pywikibot.output(u'Unable to match artist, just using the raw name')
                        artist = rawdata.get('artist')
                    else:
                        artist = artistMatch.group(1)

                    inv = rawdata.get('accession number')
                    url = u'http://art.thewalters.org/detail/%s' % rawdata.get('id')

                    print title
                    print artist
                    print inv
                    print url

                    data = {'labels': {},
                            'descriptions': {},
                            }

                    data['labels']['en'] = {'language': 'en', 'value': title}
                    

                    if artist:
                        data['descriptions']['en'] = {'language': u'en', 'value' : u'painting by %s' % (artist,)}
                        data['descriptions']['nl'] = {'language': u'nl', 'value' : u'schilderij van %s' % (artist,)}
                        

                    print data

                    
                    identification = {}
                    summary = u'Creating new item with data from [[:Commons:%s]]' % (painting.title(),)
                    pywikibot.output(summary)

                    
                    result = self.repo.editEntity(identification, data, summary=summary)
                    #print result
                    paintingItemTitle = result.get(u'entity').get('id')
                    paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

                    newclaim = pywikibot.Claim(self.repo, u'P%s' % (self.paintingIdProperty,))
                    newclaim.setTarget(inv)
                    pywikibot.output('Adding new id claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)

                    self.addReference(paintingItem, newclaim, url)
                    
                    newqualifier = pywikibot.Claim(self.repo, u'P195') #Add collection, isQualifier=True
                    newqualifier.setTarget(walters)
                    pywikibot.output('Adding new qualifier claim to %s' % paintingItem)
                    newclaim.addQualifier(newqualifier)

                    collectionclaim = pywikibot.Claim(self.repo, u'P195')
                    collectionclaim.setTarget(walters)
                    pywikibot.output('Adding collection claim to %s' % paintingItem)
                    paintingItem.addClaim(collectionclaim)

                    self.addReference(paintingItem, collectionclaim, url)
                    

                    # So now we created a new item. Let's add the Wikidata link right away so we can come back to it later

                    self.addWikidataBacklink(painting, paintingItem.title())


                    # Let's prevent making the same item multiple times:
                    pywikibot.output(u'Adding %s = %s to cache' % (inv, paintingItem.title().replace(u'Q', u'')))
                    
                    self.paintingIds[inv] = paintingItem.title().replace(u'Q', u'')

            imported = pywikibot.Claim(self.repo, u'P143')
            imported.setTarget(pywikibot.ItemPage(self.repo, u'Q565'))
            
            if paintingItem and paintingItem.exists():
                pywikibot.output(u'Let\'s add some shit')
                
                data = paintingItem.get()
                claims = data.get('claims')

                # instance of always painting while working on the painting collection
                if u'P31' not in claims:
                    
                    dcformatItem = pywikibot.ItemPage(self.repo, title='Q3305213')

                    newclaim = pywikibot.Claim(self.repo, u'P31')
                    newclaim.setTarget(dcformatItem)
                    pywikibot.output('Adding instance claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)
                    newclaim.addSource(imported)

                # Let's add the image
                if u'P18' not in claims:
                    newclaim = pywikibot.Claim(self.repo, u'P18')
                    newclaim.setTarget(painting)
                    paintingItem.addClaim(newclaim)
                    newclaim.addSource(imported)
                    
                    

                
                #print claims

                # located in
                if u'P276' not in claims:
                    newclaim = pywikibot.Claim(self.repo, u'P276')
                    newclaim.setTarget(walters)
                    pywikibot.output('Adding located in claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)
                    newclaim.addSource(imported)
                    

                


                # creator        
                if u'P170' not in claims and rawdata.get('artist'):
                    # We're going to take the creator template and see if it contains a link to Wikidata

                    creatorRegex = u'^\{\{([cC]reator:.+)\}\}$'
                    creatorMatch = re.match(creatorRegex, rawdata.get('artist'))

                    if creatorMatch:
                        # Should probably do this with link
                        creatorItem = self.getCreatorItem(creatorMatch.group(1))
                        if creatorItem:
                            print u'yah, found a creator item'

                            newclaim = pywikibot.Claim(self.repo, u'P170')
                            newclaim.setTarget(creatorItem)
                            pywikibot.output('Adding creator claim to %s' % paintingItem)
                            paintingItem.addClaim(newclaim)
                            newclaim.addSource(imported)

                             
                                         
                    


                
                # date of creation
                if u'P571' not in claims:
                    if rawdata.get('date'):
                        if len(rawdata.get('date'))==4: # It's a year
                            newdate = pywikibot.WbTime(year=rawdata.get('date'))
                            newclaim = pywikibot.Claim(self.repo, u'P571')
                            newclaim.setTarget(newdate)
                            pywikibot.output('Adding date of creation claim to %s' % paintingItem)
                            paintingItem.addClaim(newclaim)
                            newclaim.addSource(imported)
                            
                # Depicted at url like http://art.thewalters.org/detail/9874/judith-with-the-head-of-holofernes/
                if u'P973' not in claims:
                    starturl = u'http://art.thewalters.org/detail/%s' % rawdata.get('id')
                    waltersPage = urllib.urlopen(starturl)
                    waltersData = waltersPage.read()
                    fullurlregex = u'\<meta property="og:url" content="(http://art.thewalters.org/detail/%s/.+/)" /\>' % (rawdata.get('id'),)

                    match = re.search(fullurlregex, waltersData)
                    if match:
                        fullurl=match.group(1)
                        newclaim = pywikibot.Claim(self.repo, u'P973')
                        newclaim.setTarget(fullurl)
                        pywikibot.output('Adding Depicted at url claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)
                        newclaim.addSource(imported)

                    waltersPage.close()
                    
                    
                    
                """
                # material used
                if u'P186' not in claims:
                    dcFormats = { u'http://vocab.getty.edu/aat/300014078' : u'Q4259259', # Canvas
                                  u'http://vocab.getty.edu/aat/300015050' : u'Q296955', # Oil paint
                                  }
                    if painting['object']['proxies'][0].get('dcFormat') and painting['object']['proxies'][0]['dcFormat'].get('def'):
                        for dcFormat in painting['object']['proxies'][0]['dcFormat']['def']:
                            if dcFormat in dcFormats:
                                dcformatItem = pywikibot.ItemPage(self.repo, title=dcFormats[dcFormat])

                                newclaim = pywikibot.Claim(self.repo, u'P186')
                                newclaim.setTarget(dcformatItem)
                                pywikibot.output('Adding material used claim to %s' % paintingItem)
                                paintingItem.addClaim(newclaim)

                                self.addReference(paintingItem, newclaim, uri)
                
                ## Handle 
                #if u'P1184' not in claims:
                #    handleUrl = painting['object']['proxies'][0]['dcIdentifier']['def'][0]
                #    handle = handleUrl.replace(u'http://hdl.handle.net/', u'')
                #    
                #    newclaim = pywikibot.Claim(self.repo, u'P1184')
                #    newclaim.setTarget(handle)
                #    pywikibot.output('Adding handle claim to %s' % paintingItem)
                #    paintingItem.addClaim(newclaim
                #    self.addReference(paintingItem, newclaim, uri)

                # Europeana ID
                #if u'P727' not in claims:
                #    europeanaID = painting['object']['about'].lstrip('/')
                #    newclaim = pywikibot.Claim(self.repo, u'P727')
                #    newclaim.setTarget(europeanaID)
                #    pywikibot.output('Adding Europeana ID claim to %s' % paintingItem)
                #    paintingItem.addClaim(newclaim)
                #    self.addReference(paintingItem, newclaim, uri)
        """
    def addWikidataBacklink(self, painting, paintingItemTitle, summary=u''):
        '''
        Add a Wikidata link to painting based on paintingItem
        '''

        artworkRegex = u'\{\{Walters Art Museum artwork'
        text = painting.get()
        if not summary:
            summary = u'Created a new item [[:d:%s|%s]] on Wikidata, adding link' % (paintingItemTitle, paintingItemTitle)

        newtext = re.sub(artworkRegex, u'{{Walters Art Museum artwork\n | wikidata = %s' % (paintingItemTitle,), text, count=1)
        pywikibot.output(summary)
        pywikibot.showDiff(text, newtext)
        painting.put(newtext, comment=summary)

    def getCreatorItem(self, creator):
        '''
        '''
        try:
            site=pywikibot.Site('commons', 'commons')
            creatorPage = pywikibot.Page(site, title=creator, ns=100)

            if creatorPage.exists():
                if creatorPage.isRedirectPage():
                    creatorPage = creatorPage.getRedirectTarget()
                pywikibot.output(u'Got a creator page %s' % (creatorPage.title(),))
            
                regex = u'\|\s*[wW]ikidata\s*=\s*(Q\d+)\s*'
                match = re.search(regex, creatorPage.get())
                if match:
                    creatorItem = pywikibot.ItemPage(self.repo, title=match.group(1))
                    return creatorItem
        except pywikibot.exceptions.InvalidTitle:
            pywikibot.output(u'Found an invalid title')
            pass
        return None
        
    def addReference(self, paintingItem, newclaim, uri):
        """
        Add a reference with a retrieval url and todays date
        """
        pywikibot.output('Adding new reference claim to %s' % paintingItem)
        refurl = pywikibot.Claim(self.repo, u'P854') # Add url, isReference=True
        refurl.setTarget(uri)
        refdate = pywikibot.Claim(self.repo, u'P813')
        today = datetime.datetime.today()
        date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
        refdate.setTarget(date)
        newclaim.addSources([refurl, refdate])

def getPaintingGenerator(query=u''):
    '''
    Bla %02d
    ''' 
    #url = 'http://europeana.eu/api/v2/record/92034/GVNRC_MAU01_%04d.json?wskey=1hfhGH67Jhs&profile=full'
    #url = 'http://europeana.eu/api/v2/record/90402/SK_C_%d.json?wskey=1hfhGH67Jhs&profile=full'
    #url = 'http://europeana.eu/api/v2/record/90402/SK_A_%d.json?wskey=1hfhGH67Jhs&profile=full'
    url = 'https://www.rijksmuseum.nl/api/nl/collection/SK-A-%d?key=NJwVKOnk&format=json'

    for i in range(3445, 3447):
        
        apiPage = urllib.urlopen(url % (i,))
        apiData = apiPage.read()
        jsonData = json.loads(apiData)
        if jsonData.get('artObject'):
            yield jsonData
        else:
            print jsonData

        

def main(*args):
    local_args = pywikibot.handle_args(args)
    genFactory = pagegenerators.GeneratorFactory()

    createnew = False

    for arg in local_args:
        if arg==u'-createnew':
            createnew = True
        elif genFactory.handleArg(arg):
            continue

    gen = genFactory.getCombinedGenerator()

    if not gen:
        return
    

    paintingsBot = PaintingsBot(gen, createnew=createnew)
    paintingsBot.run()
    
    

if __name__ == "__main__":
    main()
