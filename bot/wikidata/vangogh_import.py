#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape paintings from the Van Gogh website


"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib2
import re
import pywikibot.data.wikidataquery as wdquery
import datetime
import HTMLParser
import posixpath
from urlparse import urlparse
from urllib import urlopen
import hashlib
import io
import base64
import upload
import tempfile
import os

class PaintingsBot:
    """
    A bot to enrich and create paintings on Wikidata
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
        self.paintingIds['s0029V1962'] = u'19833771'
        
    def fillCache(self, propertyId, queryoverride=u'', cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        if queryoverride:
            query = queryoverride
        else:
            query = u'CLAIM[195:224124] AND CLAIM[%s]' % (propertyId,)
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
        vangoghmuseum = pywikibot.ItemPage(self.repo, u'Q224124')
        for painting in self.generator:
            # Buh, for this one I know for sure it's in there
            
            

            print painting[u'id']
            print painting[u'url']


            
            paintingItem = None
            newclaims = []
            if painting[u'id'] in self.paintingIds:
                paintingItemTitle = u'Q%s' % (self.paintingIds.get(painting[u'id']),)
                print paintingItemTitle
                paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

            else:
                
                #print 'bla'


                data = {'labels': {},
                        'descriptions': {},
                        }

                data['labels']['nl'] = {'language': 'nl', 'value': painting[u'titlenl']}
                data['labels']['en'] = {'language': 'en', 'value': painting[u'titleen']}

                duplicates = [u'Kop van een vrouw',
                              u'Kop van een man',
                              u'Mand met appels',
                              u'Mand met aardappels',
                              u'Zelfportret',
                              u'Portret van een vrouw',
                              u'Venustorso',
                              u'Gipsen vrouwentorso',
                              u'De heuvel van Montmartre met steengroeve',
                              u'Schedel',
                              u'Vogelnesten',
                              u'Olijfgaard',
                              u'Kreupelhout',
                              ]
                              

                if painting[u'titlenl'] in duplicates:
                    painting[u'description'] = u'%s (Van Gogh Museum, %s)' % (painting[u'description'], painting[u'id'])
 
                data['descriptions']['en'] = {'language': u'en', 'value' : u'painting by %s' % (painting[u'description'],)}
                data['descriptions']['nl'] = {'language': u'nl', 'value' : u'schilderij van %s' % (painting[u'description'],)}
                    

                print data
                
                identification = {}
                summary = u'Creating new item with data from %s ' % (painting[u'url'],)
                pywikibot.output(summary)
                #monumentItem.editEntity(data, summary=summary)
                result = self.repo.editEntity(identification, data, summary=summary)
                #print result
                paintingItemTitle = result.get(u'entity').get('id')
                paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

                newclaim = pywikibot.Claim(self.repo, u'P%s' % (self.paintingIdProperty,))
                newclaim.setTarget(painting[u'id'])
                pywikibot.output('Adding new id claim to %s' % paintingItem)
                paintingItem.addClaim(newclaim)

                self.addReference(paintingItem, newclaim, painting[u'url'])
                
                newqualifier = pywikibot.Claim(self.repo, u'P195') #Add collection, isQualifier=True
                newqualifier.setTarget(vangoghmuseum)
                pywikibot.output('Adding new qualifier claim to %s' % paintingItem)
                newclaim.addQualifier(newqualifier)

                collectionclaim = pywikibot.Claim(self.repo, u'P195')
                collectionclaim.setTarget(vangoghmuseum)
                pywikibot.output('Adding collection claim to %s' % paintingItem)
                paintingItem.addClaim(collectionclaim)

                self.addReference(paintingItem, collectionclaim, painting[u'url'])
                
            
            if paintingItem and paintingItem.exists():
                painting['wikidata'] = paintingItem.title()
                
                data = paintingItem.get()
                claims = data.get('claims')
                #print claims

                # located in
                if u'P276' not in claims:
                    newclaim = pywikibot.Claim(self.repo, u'P276')
                    newclaim.setTarget(vangoghmuseum)
                    pywikibot.output('Adding located in claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)

                    self.addReference(paintingItem, newclaim, painting['url'])
                    

                # instance of always painting while working on the painting collection
                if u'P31' not in claims:
                    
                    dcformatItem = pywikibot.ItemPage(self.repo, title='Q3305213')

                    newclaim = pywikibot.Claim(self.repo, u'P31')
                    newclaim.setTarget(dcformatItem)
                    pywikibot.output('Adding instance claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)

                    self.addReference(paintingItem, newclaim, painting['url'])


                # creator        
                if u'P170' not in claims and painting.get(u'creator'):
                    # Just some hardcoded mappings for now

                    painters = { u'Vincent van Gogh' : u'Q5582',
                                 u'Claude Monet' : u'Q296',
                                 u'Paul Gauguin' : u'Q37693',
                                 }
                    if painting.get(u'creator') in painters.keys():
                        creatoritem = pywikibot.ItemPage(self.repo, painters.get(painting.get(u'creator')))
                        newclaim = pywikibot.Claim(self.repo, u'P170')
                        newclaim.setTarget(creatoritem)
                        pywikibot.output('Adding new creator claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        self.addReference(paintingItem, newclaim, painting[u'url'])
                        

                    #print painting[u'creator']
                    #creategen = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataItemGenerator(pagegenerators.SearchPageGenerator(dcCreatorName, step=None, total=10, namespaces=[0], site=self.repo)))
                    
                    #newcreator = None

                    """
                    for creatoritem in creategen:
                        print creatoritem.title()
                        if creatoritem.get().get('labels').get('en') == dcCreatorName or creatoritem.get().get('labels').get('nl') == dcCreatorName:
                            print creatoritem.get().get('labels').get('en')
                            print creatoritem.get().get('labels').get('nl')
                            # Check occupation and country of citizinship
                            if u'P106' in creatoritem.get().get('claims') and (u'P21' in creatoritem.get().get('claims') or u'P800' in creatoritem.get().get('claims')):
                                newcreator = creatoritem
                                continue
                        elif (creatoritem.get().get('aliases').get('en') and dcCreatorName in creatoritem.get().get('aliases').get('en')) or (creatoritem.get().get('aliases').get('nl') and dcCreatorName in creatoritem.get().get('aliases').get('nl')):
                            if u'P106' in creatoritem.get().get('claims') and (u'P21' in creatoritem.get().get('claims') or u'P800' in creatoritem.get().get('claims')):
                                newcreator = creatoritem
                                continue

                    if newcreator:
                        pywikibot.output(newcreator.title())

                        newclaim = pywikibot.Claim(self.repo, u'P170')
                        newclaim.setTarget(newcreator)
                        pywikibot.output('Adding creator claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        self.addReference(paintingItem, newclaim, uri)

                        print creatoritem.title()
                        print creatoritem.get()
                    
                            
                            

                        

                    else:
                        pywikibot.output('No item found for %s' % (dcCreatorName, ))
                    """
                else:
                    print u'Already has a creator'

                
                # date of creation
                if u'P571' not in claims and painting.get(u'year'):
                    if len(painting[u'year'])==4: # It's a year
                        newdate = pywikibot.WbTime(year=painting[u'year'])
                        newclaim = pywikibot.Claim(self.repo, u'P571')
                        newclaim.setTarget(newdate)
                        pywikibot.output('Adding date of creation claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        self.addReference(paintingItem, newclaim, painting[u'url'])


                # material used
                if u'P186' not in claims and painting.get(u'materiaal'):
                    if painting.get(u'materiaal')==u'olieverf op doek':
                        olieverf = pywikibot.ItemPage(self.repo, u'Q296955')
                        doek = pywikibot.ItemPage(self.repo, u'Q4259259')
                        oppervlak = pywikibot.ItemPage(self.repo, u'Q861259')
                        
                        newclaim = pywikibot.Claim(self.repo, u'P186')
                        newclaim.setTarget(olieverf)
                        pywikibot.output('Adding new oil paint claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        self.addReference(paintingItem, newclaim, painting[u'url'])

                        newclaim = pywikibot.Claim(self.repo, u'P186')
                        newclaim.setTarget(doek)
                        pywikibot.output('Adding new canvas claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        self.addReference(paintingItem, newclaim, painting[u'url'])
                
                        newqualifier = pywikibot.Claim(self.repo, u'P518') #Applies to part
                        newqualifier.setTarget(oppervlak)
                        pywikibot.output('Adding new qualifier claim to %s' % paintingItem)
                        newclaim.addQualifier(newqualifier)
                        
                    
                    """
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
                    """
                
                # Described at url 
                if u'P973' not in claims:
                    newclaim = pywikibot.Claim(self.repo, u'P973')
                    newclaim.setTarget(painting[u'url'])
                    pywikibot.output('Adding described at claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)
                #    self.addReference(paintingItem, newclaim, uri)

                # The two catalogs
                if u'P528' not in claims:
                    if painting.get(u'fnummer'):
                        newclaim = pywikibot.Claim(self.repo, u'P528')
                        newclaim.setTarget(painting.get(u'fnummer'))
                        pywikibot.output('Adding new fnummer claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        self.addReference(paintingItem, newclaim, painting[u'url'])

                        fcatalog = pywikibot.ItemPage(self.repo, u'Q17280421')
                
                        newqualifier = pywikibot.Claim(self.repo, u'P972') #Add catalog
                        newqualifier.setTarget(fcatalog)
                        pywikibot.output('Adding new qualifier claim to %s' % paintingItem)
                        newclaim.addQualifier(newqualifier)

                    if painting.get(u'jhnummer'):
                        newclaim = pywikibot.Claim(self.repo, u'P528')
                        newclaim.setTarget(painting.get(u'jhnummer'))
                        pywikibot.output('Adding new jhnummer claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        self.addReference(paintingItem, newclaim, painting[u'url'])

                        jhcatalog = pywikibot.ItemPage(self.repo, u'Q19833315')
                
                        newqualifier = pywikibot.Claim(self.repo, u'P972') #Add catalog
                        newqualifier.setTarget(jhcatalog)
                        pywikibot.output('Adding new qualifier claim to %s' % paintingItem)
                        newclaim.addQualifier(newqualifier)

                # Height in cm https://www.wikidata.org/wiki/Q174728
                if u'P2048' not in claims:
                     if painting.get(u'height'):
                         print painting.get(u'height')
                         snak = {"mainsnak": {"snaktype":'value', "property": "P2048", "datavalue": {
                                    "value": {
                                        "amount": "+%s" % painting.get(u'height'),
                                        "unit": "http://www.wikidata.org/entity/Q174728",
                                        "upperBound": "+%s" % painting.get(u'height'),
                                        "lowerBound": "+%s" % painting.get(u'height'),
                                    },
                                    "type": "quantity"
                                },
                                "datatype": "quantity"}, "type":"statement","rank":"normal"}
                         print snak
                         paintingItem.editEntity(data={'claims':[snak]})
                         paintingItem.get(force=True)
                         self.addReference(paintingItem, paintingItem.claims['P2048'][0], painting[u'url'])

                # Width in cm
                if u'P2049' not in claims:
                     if painting.get(u'width'):
                         print painting.get(u'width')
                         snak = {"mainsnak": {"snaktype":'value', "property": "P2049", "datavalue": {
                                    "value": {
                                        "amount": "+%s" % painting.get(u'width'),
                                        "unit": "http://www.wikidata.org/entity/Q174728",
                                        "upperBound": "+%s" % painting.get(u'width'),
                                        "lowerBound": "+%s" % painting.get(u'width'),
                                    },
                                    "type": "quantity"
                                },
                                "datatype": "quantity"}, "type":"statement","rank":"normal"}
                         print snak
                         paintingItem.editEntity(data={'claims':[snak]})
                         paintingItem.get(force=True)
                         self.addReference(paintingItem, paintingItem.claims['P2049'][0], painting[u'url'])                         

                # Europeana ID
                #if u'P727' not in claims:
                #    europeanaID = painting['object']['about'].lstrip('/')
                #    newclaim = pywikibot.Claim(self.repo, u'P727')
                #    newclaim.setTarget(europeanaID)
                #    pywikibot.output('Adding Europeana ID claim to %s' % paintingItem)
                #    paintingItem.addClaim(newclaim)
                #    self.addReference(paintingItem, newclaim, uri)

                """
                # Upload an image baby!
                title = u''
                if painting.get(u'imageurl'):
                    commonssite = pywikibot.Site("commons", "commons")
                    photo = Photo(painting[u'imageurl'], painting)
                    titlefmt = u'%(titlenl)s - %(id)s - Van Gogh Museum.%(_ext)s'
                    pagefmt = u'User:Multichill/Van Gogh Museum'
                    
                    duplicates = photo.findDuplicateImages()
                    if duplicates:
                        pywikibot.output(u"Skipping duplicate of %r" % duplicates)
                        title=duplicates[0]
                        #return duplicates[0]
                    else:

                        title = photo.getTitle(titlefmt).replace(u':', u'')
                        print title
                        description = photo.getDescription(pagefmt)
                        print description


                        handle, tempname = tempfile.mkstemp()
                        with os.fdopen(handle, "wb") as t:
                            t.write(photo.downloadPhoto().getvalue())
                            t.close()
                        #tempname
                            
                        bot = upload.UploadRobot(url=tempname,
                                                 description=description,
                                                 useFilename=title,
                                                 keepFilename=True,
                                                 verifyDescription=False,
                                                 uploadByUrl=False,
                                                 targetSite=commonssite)
                        #bot._contents = photo.downloadPhoto().getvalue()

                        

                        
                        #bot._retrieved = True
                        bot.run()
                    
                
                if u'P18' not in claims and title:
                    newclaim = pywikibot.Claim(self.repo, u'P18')
                    imagelink = pywikibot.Link(title, source=commonssite, defaultNamespace=6)
                    image = pywikibot.ImagePage(imagelink)
                    if image.isRedirectPage():
                        image = pywikibot.ImagePage(image.getRedirectTarget())
                    newclaim.setTarget(image)
                    pywikibot.output('Adding %s --> %s' % (newclaim.getID(), newclaim.getTarget()))
                    paintingItem.addClaim(newclaim)
                """
                

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




class Photo(pywikibot.FilePage):

    """Represents a Photo (or other file), with metadata, to be uploaded."""

    def __init__(self, URL, metadata, site=None):
        """
        Constructor.

        @param URL: URL of photo
        @type URL: str
        @param metadata: metadata about the photo that can be referred to
            from the title & template
        @type metadata: dict
        @param site: target site
        @type site: APISite

        """
        self.URL = URL
        self.metadata = metadata
        self.metadata["_url"] = URL
        self.metadata["_filename"] = filename = posixpath.split(
            urlparse(URL)[2])[1]
        self.metadata["_ext"] = ext = filename.split(".")[-1]
        if ext == filename:
            self.metadata["_ext"] = ext = None
        self.contents = None

        if not site:
            site = pywikibot.Site(u'commons', u'commons')

        # default title
        super(Photo, self).__init__(site,
                                    self.getTitle('%(_filename)s.%(_ext)s'))

    def downloadPhoto(self):
        """
        Download the photo and store it in a io.BytesIO object.

        TODO: Add exception handling
        """
        if not self.contents:
            imageFile = urlopen(self.URL).read()
            self.contents = io.BytesIO(imageFile)
        return self.contents


    def findDuplicateImages(self):
        """
        Find duplicates of the photo.

        Calculates the SHA1 hash and asks the MediaWiki api
        for a list of duplicates.

        TODO: Add exception handling, fix site thing
        """
        hashObject = hashlib.sha1()
        hashObject.update(self.downloadPhoto().getvalue())
        return list(
            page.title(withNamespace=False) for page in
            self.site.allimages(sha1=base64.b16encode(hashObject.digest())))

    def getTitle(self, fmt):
        """
        Populate format string with %(name)s entries using metadata.

        Note: this does not clean the title, so it may be unusable as
        a MediaWiki page title, and cause an API exception when used.

        @param fmt: format string
        @type fmt: unicode
        @return: formatted string
        @rtype: unicode
        """
        # FIXME: normalise the title so it is usable as a MediaWiki title.
        return fmt % self.metadata

    def getDescription(self, template, extraparams={}):
        """Generate a description for a file."""
        params = {}
        params.update(self.metadata)
        params.update(extraparams)
        description = u'{{%s\n' % template
        for key in sorted(params.keys()):
            value = params[key]
            if not key.startswith("_"):
                description = description + (
                    u'|%s=%s' % (key, self._safeTemplateValue(value))) + "\n"
        description = description + u'}}'

        return description

    def _safeTemplateValue(self, value):
        """Replace pipe (|) with {{!}}."""
        return value.replace("|", "{{!}}")







def getPaintingGenerator(query=u''):
    '''
    Bla %02d
    ''' 
    searchurl = 'http://www.vangoghmuseum.nl/nl/zoeken/collectie?q=&type=schilderij'
    searchPage = urllib2.urlopen(searchurl)
    searchData = searchPage.read()

    itemnlurl = u'http://www.vangoghmuseum.nl/nl/collectie/%s'
    itemenurl = u'http://www.vangoghmuseum.nl/en/collection/%s'

    #print searchData

    itemregex = u'<a href="/nl/collectie/([^"]+)" class="link-overview">'

    titleregex = u'<meta property="og:title" content="([^"]+) - Van Gogh Museum" />'
    descriptionregex = u'<meta property="og:description" content="([^"]+)" />'
    creatoryearregex = u'^(.+), (\d+)$'

    fnummerregex = u'<dt class="text-theme">F-nummer</dt>\s*<dd class="">F([^<]+)</dd>\s*<dd></dd>'
    jhnummerregex = u'<dt class="text-theme">JH-nummer</dt>\s*<dd class="">JH([^<]+)</dd>\s*<dd></dd>'

    materialregex = u'(olieverf op doek),\s*(?P<height>\d+(\.\d+)?) cm x (?P<width>\d+(\.\d+)?) cm<br />'

    imageurlregex = u'<a data-role="download-art-object-href" href="([^"]+)" class="button neutral dark-hover icon-before icon-download" target="_blank">Download deze afbeelding</a>'

    htmlparser = HTMLParser.HTMLParser()

    foundit = True
   

    for match in re.finditer(itemregex, searchData):
        metadata = {}
        
        itemid =  match.group(1)
        metadata[u'id']=itemid

        if itemid==u's0353M1974':
            foundit=True

        if not foundit:
            continue
        metadata[u'url']=itemnlurl % (itemid,)
        
        itemnlPage = urllib2.urlopen(itemnlurl % (itemid,))
        itemnlData = itemnlPage.read()

        itemenPage = urllib2.urlopen(itemenurl % (itemid,))
        itemenData = itemenPage.read()

        titlenlmatch = re.search(titleregex, itemnlData)
        #print htmlparser.unescape(titlenlmatch.group(1))
        metadata[u'titlenl']=htmlparser.unescape(titlenlmatch.group(1))
        
        titleenmatch = re.search(titleregex, itemenData)
        #print htmlparser.unescape(titleenmatch.group(1))
        metadata[u'titleen']=htmlparser.unescape(titleenmatch.group(1))
        
        descriptionmatch = re.search(descriptionregex, itemnlData)
        #print descriptionmatch.group(1)
        metadata[u'description']= descriptionmatch.group(1)

        creatoryearmatch = re.search(creatoryearregex, descriptionmatch.group(1))
        if creatoryearmatch:
            #print creatoryearmatch.group(1)
            metadata[u'creator']=creatoryearmatch.group(1)
            #print creatoryearmatch.group(2)
            metadata[u'year']=creatoryearmatch.group(2)

        # Sometimes match, need to be multiline. Need to trim zeroes
        fnummermatch = re.search(fnummerregex, itemnlData, flags=re.DOTALL)

        if fnummermatch:
            #print u'F%s' % (fnummermatch.group(1).lstrip(u'0'),)
            metadata[u'fnummer'] = u'F%s' % (fnummermatch.group(1).lstrip(u'0'),)
            

        # Sometimes match, need to be multiline. Need to trim zeroes
        jhnummermatch = re.search(jhnummerregex, itemnlData, flags=re.DOTALL)

        if jhnummermatch:
            #print u'JH%s' % (jhnummermatch.group(1).lstrip(u'0'),)
            metadata[u'jhnummer'] = u'JH%s' % (jhnummermatch.group(1).lstrip(u'0'),)

        materialmatch = re.search(materialregex, itemnlData, flags=re.DOTALL)

        if materialmatch:
            #print materialmatch.group(1)
            metadata[u'materiaal'] = materialmatch.group(1)
            metadata[u'height'] = materialmatch.group(u'height')
            metadata[u'width'] = materialmatch.group('width')

        imageurlmatch = re.search(imageurlregex, itemnlData)
        if imageurlmatch:
            metadata[u'imageurl'] = u'http://www.vangoghmuseum.nl%s' % (imageurlmatch.group(1),)
            print metadata[u'imageurl']


            

      
        

        
        
        
        
        #jsonData = json.loads(apiData)
        #if jsonData.get('artObject'):
        #    yield jsonData
        #else:
        #    print jsonData
        
        yield metadata
    
    """
    for i in range(3445, 3447):
        
        apiPage = urllib.urlopen(url % (i,))
        apiData = apiPage.read()
        jsonData = json.loads(apiData)
        if jsonData.get('artObject'):
            yield jsonData
        else:
            print jsonData
    """

        




def main():
    paintingGen = getPaintingGenerator()

    #for painting in paintingGen:
    #    print painting
        
    paintingsBot = PaintingsBot(paintingGen, 217)
    paintingsBot.run()
    
    

if __name__ == "__main__":
    main()
