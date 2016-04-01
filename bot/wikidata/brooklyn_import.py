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

        self.paintingIds[u'1910.1.72']=u'17442480'
        
    def fillCache(self, propertyId, queryoverride=u'', cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        if queryoverride:
            query = queryoverride
        else:
            query = u'CLAIM[195:632682] AND CLAIM[%s]' % (propertyId,)
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
        brooklynmuseum = pywikibot.ItemPage(self.repo, u'Q632682')

        imported = pywikibot.Claim(self.repo, u'P143')
        imported.setTarget(pywikibot.ItemPage(self.repo, u'Q565'))
        
        for painting in self.generator:
            # Buh, for this one I know for sure it's in there
            
            

            print painting[u'id']
            print painting[u'url']


            
            paintingItem = None
            newclaims = []
            if painting.get('wikidata'):
                paintingItem = pywikibot.ItemPage(self.repo, title= painting.get('wikidata'))
                
            elif painting[u'id'] in self.paintingIds:
                paintingItemTitle = u'Q%s' % (self.paintingIds.get(painting[u'id']),)
                print paintingItemTitle
                paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

                self.addWikidataBacklink(painting.get('imagepage'), paintingItemTitle, summary=u'Adding missing Wikidata link')

            else:
                #Break for now
                print u'Let us create stuff'
                #continue
                #print u'WTFTFTFTFT???'
                
                #print 'bla'


                data = {'labels': {},
                        'descriptions': {},
                        }

                data['labels']['en'] = {'language': 'en', 'value': painting[u'titleen']}

                if painting.get(u'titlefr'):
                    data['labels']['fr'] = {'language': 'fr', 'value': painting[u'titlefr']}
                    
 
                data['descriptions']['en'] = {'language': u'en', 'value' : u'%s by %s (Brooklyn Museum, %s)' % (painting[u'medium'], painting[u'creator'], painting[u'id'])}
                #if painting[u'medium']==u'painting
                #data['descriptions']['nl'] = {'language': u'nl', 'value' : u'schilderij van %s' % (painting[u'creator'],)}
                
                print data
                
                identification = {}
                summary = u'Creating new item with data from [[:Commons:%s]]' % (painting[u'image'],)
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
                newqualifier.setTarget(brooklynmuseum)
                pywikibot.output('Adding new qualifier claim to %s' % paintingItem)
                newclaim.addQualifier(newqualifier)

                collectionclaim = pywikibot.Claim(self.repo, u'P195')
                collectionclaim.setTarget(brooklynmuseum)
                pywikibot.output('Adding collection claim to %s' % paintingItem)
                paintingItem.addClaim(collectionclaim)

                self.addReference(paintingItem, collectionclaim, painting[u'url'])

                self.addWikidataBacklink(painting.get('imagepage'), paintingItemTitle, summary=u'Adding missing Wikidata link')
                
            
            if paintingItem and paintingItem.exists():
                painting['wikidata'] = paintingItem.title()
                
                data = paintingItem.get()
                claims = data.get('claims')
                #print claims

                # located in
                if u'P276' not in claims:
                    newclaim = pywikibot.Claim(self.repo, u'P276')
                    newclaim.setTarget(brooklynmuseum)
                    pywikibot.output('Adding located in claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)

                    self.addReference(paintingItem, newclaim, painting['url'])
                    

                # instance of always painting while working on the painting collection
                if u'P31' not in claims:
                    dcformatItem=None
                    if painting[u'medium']==u'painting':
                        dcformatItem = pywikibot.ItemPage(self.repo, title='Q3305213')
                    elif painting[u'medium']==u'watercolor':
                        dcformatItem = pywikibot.ItemPage(self.repo, title='Q18761202')

                    if dcformatItem:
                        newclaim = pywikibot.Claim(self.repo, u'P31')
                        newclaim.setTarget(dcformatItem)
                        pywikibot.output('Adding instance claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        self.addReference(paintingItem, newclaim, painting['url'])


                # creator        
                if u'P170' not in claims and painting.get('creator'):
                    # We're going to take the creator template and see if it contains a link to Wikidata
                    creatorItem = self.getCreatorItem(painting.get('creator'))
                    if creatorItem:
                        print u'yah, found a creator item'

                        newclaim = pywikibot.Claim(self.repo, u'P170')
                        newclaim.setTarget(creatorItem)
                        pywikibot.output('Adding creator claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)
                        newclaim.addSource(imported)
                else:
                    print u'Already has a creator'

                
                # date of creation
                #if u'P571' not in claims and painting.get(u'year'):
                #    if len(painting[u'year'])==4: # It's a year
                #        newdate = pywikibot.WbTime(year=painting[u'year'])
                #        newclaim = pywikibot.Claim(self.repo, u'P571')
                #        newclaim.setTarget(newdate)
                #        pywikibot.output('Adding date of creation claim to %s' % paintingItem)
                #        paintingItem.addClaim(newclaim)
                #
                #        self.addReference(paintingItem, newclaim, painting[u'url'])

                """
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

                if u'P18' not in claims:
                    newclaim = pywikibot.Claim(self.repo, u'P18')
                    newclaim.setTarget(painting.get('imagepage'))
                    paintingItem.addClaim(newclaim)
                    #newclaim.addSource(imported)
                
    def addWikidataBacklink(self, painting, paintingItemTitle, summary=u''):
        '''
        Add a Wikidata link to painting based on paintingItem
        '''

        artworkRegex = u'\{\{Artwork'
        text = painting.get()
        if not summary:
            summary = u'Created a new item [[:d:%s|%s]] on Wikidata, adding link' % (paintingItemTitle, paintingItemTitle)

        newtext = re.sub(artworkRegex, u'{{Artwork\n | wikidata = %s' % (paintingItemTitle,), text, count=1)
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
    Loop over everything in https://commons.wikimedia.org/w/index.php?title=Special:WhatLinksHere/Category:European_Art_in_the_Brooklyn_Museum&limit=500
    Need an identifier
    Need an url
    Need to be a painting or watercolor
    File needs to start with File:Brooklyn Museum - 
    '''
    site = pywikibot.Site(u'commons', u'commons')
    searchpage = pywikibot.Page(site, u'Category:European_Art_in_the_Brooklyn_Museum')
    gen = pagegenerators.PreloadingGenerator(pagegenerators.NamespaceFilterPageGenerator(pagegenerators.ReferringPageGenerator(searchpage, withTemplateInclusion=False), [6]))

    validFields = [u'artist',
                   u'title',
                   u'year',
                   u'technique',
                   u'dimensions',
                   u'gallery',
                   u'location',
                   u'credit_line',
                   u'notes',
                   u'source',
                   u'id',
                   u'accession number',
                   u'permission',
                   u'other_versions',
                   u'wikidata',
                   ]

    foundit = False

    for page in gen:
        if page.title()==u'File:Brooklyn Museum - The Magnificat (Le magnificat) - James Tissot - overall .jpg':
            foundit=True

        if not foundit:
            continue
            
        metadata = {}
        if not page.title().startswith(u'File:Brooklyn Museum -'):
            continue

        foundPainting = False
        #skipthis = False
        metadata['medium'] = u''
        for cat in page.categories():
            if cat.title()==u'Category:The Life of Jesus Christ by James Tissot':
                foundPainting = True
                #skipthis = True
            elif u'painting' in cat.title().lower():
                foundPainting = True
                if not metadata['medium']:
                    metadata['medium']=u'painting'
            elif u'watercolor' in cat.title().lower():
                foundPainting = True
                if not metadata['medium']:
                    metadata['medium']=u'watercolor'
                elif metadata['medium']==u'painting':
                    metadata['medium']=u'watercolor'
        #if skipthis:
        #    continue
        if not foundPainting:
            print u'No painting found for %s!!!!!!!!!!!' % (page.title(),)
            continue

        if not metadata['medium']:
            metadata['medium']=u'work'
            

        print page.title()
        rawdata = {}

        for (templatePage, templateParams) in page.templatesWithParams():
            if templatePage.title()==u'Template:Artwork':
                for param in templateParams:
                    if len(param.split(u'=', 1))==2:
                        (fieldname, field) = param.split(u'=', 1)
                        if fieldname.lower() in validFields:
                            if field.strip():
                                rawdata[fieldname.lower()] = field.strip()
                        else:
                            pywikibot.output(u'Found unknown field %s with contents %s' % (fieldname.lower(), field))

        

        if rawdata.get('accession number'):
            metadata['id'] = rawdata['accession number']
        else:
            metadata['id'] = rawdata['id']

        if not metadata['id']:
            continue
        metadata['image']=page.title()
        #print rawdata

        urlregex = u'\[(http://www.brooklynmuseum.org/opencollection/objects/\d+/[^\s]+)+\sOnline Collection\]'
        urlmatch = re.search(urlregex, rawdata['source'])
        metadata[u'url']=urlmatch.group(1)

        if rawdata.get('artist'):
            creatorRegex = u'^\{\{[cC]reator:(.+)\}\}$'
            creatorMatch = re.match(creatorRegex, rawdata.get('artist'))

            if creatorMatch:
                metadata['creator']=creatorMatch.group(1)
            elif rawdata.get('artist').lower().startswith(u'{{anonymous') or rawdata.get('artist').lower().startswith(u'{{unknown'):
                metadata['creator']=u'anonymous'
            elif not u'{' in rawdata.get('artist'):
                metadata['creator']=rawdata.get('artist')
            else:
                metadata['creator'] = rawdata.get('artist')
                # crash
                #print rawdata.get('artist')
                #print creatorMatch.group(0)
        else:
            metadata['creator'] = u'anonymous'

        titleenRegex = u'\{\{en\|([^\}]+)\}\}'
        titleenMatch = re.search(titleenRegex, rawdata.get('title'))

        if titleenMatch:
            metadata[u'titleen']=titleenMatch.group(1)

        titlefrRegex = u'\{\{fr\|([^\}]+)\}\}'
        titlefrMatch = re.search(titlefrRegex, rawdata.get('title'))

        if titlefrMatch:
            metadata[u'titlefr']=titlefrMatch.group(1)

        if not metadata.get(u'titleen'):
            titleRegex = u'\{\{[tT]itle\|([^\}]+)\}\}'
            titleMatch = re.search(titleRegex, rawdata.get('title'))

            if titleMatch:
                metadata[u'titleen']=titleMatch.group(1)
            elif not u'{' in rawdata.get('title'):
                metadata['titleen']=rawdata.get('title')
            else:
                metadata['titleen']=rawdata.get('title')
                #crash
                print rawdata.get('title')
                print titleMatch
                
        if rawdata.get('wikidata'):
            metadata['wikidata']=rawdata['wikidata']

        metadata['imagepage']=page
            
                
            
            
        
            
            

        yield metadata

        
        

    return
    
    #Category:European_Art_in_the_Brooklyn_Museum
    searchurl = u'http://collections.frick.org/view/objects/asitem/152/%s/primaryMaker-asc/title-asc'
    # collections.frick.org/view/objects/asitem/152/188/primaryMaker-asc/title-asc
    
    for i in range(63, 189):
        tempurl = searchurl % (i, )
        itemPage = urllib2.urlopen(tempurl)
        itemData = itemPage.read()
        print tempurl

        metadata = {}
        
        # <meta content="The Cavalry Camp" name="title">
        # <span class="artistName">Philips Wouwerman</span>
        # Accession number: 1901.1.136<br/>
        # <a class="permalink" href="http://collections.frick.org/view/objects/asitem/items$0040:361">Permalink</a>


        titleregex = u'<meta content="([^"]+)" name="title">'
        creatorregex = u'<span class="artistName">([^<]+)</span>'
        idregex = u'Accession number:\xc2\xa0(\d+\.\d+\.\d+(\.[A-Z])?)<br/>'
        #idregex = u'Accession number:\s*(.+)<br/>'
        urlregex = u'<a class="permalink" href="([^"]+)">Permalink</a>'

        #materialregex = u'(olieverf op doek),\s*\d+(\.\d+)? cm x \d+(\.\d+)? cm<br />'
        #imageurlregex = u'<a data-role="download-art-object-href" href="([^"]+)" class="button neutral dark-hover icon-before icon-download" target="_blank">Download deze afbeelding</a>'
        #htmlparser = HTMLParser.HTMLParser()

        titlematch = re.search(titleregex, itemData)
        metadata[u'title']=unicode(titlematch.group(1), "utf-8")

        creatormatch = re.search(creatorregex, itemData)
        metadata[u'creator']=unicode(creatormatch.group(1), "utf-8")

        idmatch = re.search(idregex, itemData)
        metadata[u'id']=idmatch.group(1)

        urlmatch = re.search(urlregex, itemData)
        metadata[u'url']=urlmatch.group(1)


        
        yield metadata


def main():
    paintingGen = getPaintingGenerator()

    #for painting in paintingGen:
    #    print painting
        
    paintingsBot = PaintingsBot(paintingGen, 217)
    paintingsBot.run()
    
    

if __name__ == "__main__":
    main()
