#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape paintings from the MET website


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

        #self.paintingIds[u'1910.1.72']=u'17442480'
        
    def fillCache(self, propertyId, queryoverride=u'', cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        if queryoverride:
            query = queryoverride
        else:
            query = u'CLAIM[195:160236] AND CLAIM[%s]' % (propertyId,)
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
        met = pywikibot.ItemPage(self.repo, u'Q160236')
        for painting in self.generator:
            # Buh, for this one I know for sure it's in there
            
            #print painting[u'id']
            print painting[u'url']


            
            paintingItem = None
            newclaims = []
            if painting[u'id'] in self.paintingIds:
                paintingItemTitle = u'Q%s' % (self.paintingIds.get(painting[u'id']),)
                print paintingItemTitle
                paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

            else:
                #Break for now
                print u'Let us create stuff'
                #continue
                #print u'WTFTFTFTFT???'
                
                #print 'bla'


                data = {'labels': {},
                        'descriptions': {},
                        }

                data['labels']['en'] = {'language': 'en', 'value': painting[u'title']}
 
                data['descriptions']['en'] = {'language': u'en', 'value' : u'painting by %s' % (painting[u'creator'],)}
                data['descriptions']['nl'] = {'language': u'nl', 'value' : u'schilderij van %s' % (painting[u'creator'],)}
                
                print data
                
                identification = {}
                summary = u'Creating new item with data from %s ' % (painting[u'url'],)
                pywikibot.output(summary)
                #monumentItem.editEntity(data, summary=summary)
                try:
                    result = self.repo.editEntity(identification, data, summary=summary)
                except pywikibot.data.api.APIError:
                    # We got ourselves a duplicate label and description, let's correct that
                    pywikibot.output(u'Oops, already had that one. Trying again')
                    data['descriptions']['en'] = {'language': u'en', 'value' : u'painting by %s (MET, %s)' % (painting[u'creator'], painting[u'id'])}
                    result = self.repo.editEntity(identification, data, summary=summary)
                    pass
                    
                    
                #print result
                paintingItemTitle = result.get(u'entity').get('id')
                paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

                # Add to self.paintingIds so that we don't create dupes
                self.paintingIds[painting[u'id']]=paintingItemTitle.replace(u'Q', u'')

                newclaim = pywikibot.Claim(self.repo, u'P%s' % (self.paintingIdProperty,))
                newclaim.setTarget(painting[u'id'])
                pywikibot.output('Adding new id claim to %s' % paintingItem)
                paintingItem.addClaim(newclaim)

                self.addReference(paintingItem, newclaim, painting[u'url'])
                
                newqualifier = pywikibot.Claim(self.repo, u'P195') #Add collection, isQualifier=True
                newqualifier.setTarget(met)
                pywikibot.output('Adding new qualifier claim to %s' % paintingItem)
                newclaim.addQualifier(newqualifier)

                collectionclaim = pywikibot.Claim(self.repo, u'P195')
                collectionclaim.setTarget(met)
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
                    newclaim.setTarget(met)
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
                    #print painting[u'creator']
                    creategen = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataItemGenerator(pagegenerators.SearchPageGenerator(painting[u'creator'], step=None, total=10, namespaces=[0], site=self.repo)))
                    
                    newcreator = None

                    
                    for creatoritem in creategen:
                        print creatoritem.title()
                        if creatoritem.get().get('labels').get('en') == painting[u'creator'] or creatoritem.get().get('labels').get('nl') == painting[u'creator']:
                            #print creatoritem.get().get('labels').get('en')
                            #print creatoritem.get().get('labels').get('nl')
                            # Check occupation and country of citizinship
                            if u'P106' in creatoritem.get().get('claims') and (u'P21' in creatoritem.get().get('claims') or u'P800' in creatoritem.get().get('claims')):
                                newcreator = creatoritem
                                continue
                        elif (creatoritem.get().get('aliases').get('en') and painting[u'creator'] in creatoritem.get().get('aliases').get('en')) or (creatoritem.get().get('aliases').get('nl') and painting[u'creator'] in creatoritem.get().get('aliases').get('nl')):
                            if u'P106' in creatoritem.get().get('claims') and (u'P21' in creatoritem.get().get('claims') or u'P800' in creatoritem.get().get('claims')):
                                newcreator = creatoritem
                                continue

                    if newcreator:
                        pywikibot.output(newcreator.title())

                        newclaim = pywikibot.Claim(self.repo, u'P170')
                        newclaim.setTarget(newcreator)
                        pywikibot.output('Adding creator claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        self.addReference(paintingItem, newclaim, painting[u'url'])

                        #print creatoritem.title()
                        #print creatoritem.get()

                    else:
                        pywikibot.output('No item found for %s' % (painting[u'creator'], ))
                    
                else:
                    print u'Already has a creator'
                
                
                # date of creation
                if u'P571' not in claims and painting.get(u'datetext'):
                    if len(painting[u'datetext'])==4 and painting[u'datetext'].isnumeric(): # It's a year
                        newdate = pywikibot.WbTime(year=painting[u'datetext'])
                        newclaim = pywikibot.Claim(self.repo, u'P571')
                        newclaim.setTarget(newdate)
                        pywikibot.output('Adding date of creation claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)
                
                        self.addReference(paintingItem, newclaim, painting[u'url'])

                
                # material used
                if u'P186' not in claims and painting.get(u'medium'):
                    if painting.get(u'medium')==u'Oil on canvas':
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

                
                # Described at url 
                if u'P973' not in claims:
                    newclaim = pywikibot.Claim(self.repo, u'P973')
                    newclaim.setTarget(painting[u'url'])
                    pywikibot.output('Adding described at claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)
                #    self.addReference(paintingItem, newclaim, uri)
                

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
    Get paintings from the met from scrapi.org and their website. http://www.metmuseum.org/collection/the-collection-online/search?pg=1&what=Paintings&ft=*&noqs=true
    Different departments. Keep track of what have been done:
     * American Decorative Arts (193)
     * American Paintings and Sculpture (2,152) - id 2 - Done 205-06-20
     * Ancient Near Eastern Art (17)
     * Arms and Armor (22)
     * Arts of Africa, Oceania, and the Americas (363)
     * Asian Art (3,716)
     * Brooklyn Museum Costume Collection (39)
     * The Cloisters (91) - id 7 - Done 2015-06-22
     * Costume Institute (40)
     * Drawings and Prints (43)
     * Egyptian Art (75)
     * European Paintings (2,480) - id 11 - Done 2015-06-20. Could upload images
     * European Sculpture and Decorative Arts (228)
     * Greek and Roman Art (74)
     * Islamic Art (61)
     * Medieval Art (289)
     * Modern and Contemporary Art (2,370) - id 21 - Done 2015-06-22
     * Musical Instruments (13)
     * Photographs (33)
     * Provenance Research Project (745) - id 52 - All dupes
     * Robert Lehman Collection (364) - id 15 - Done 205-06-21
    '''
    
    searchurl = u'http://scrapi.org/search/painting&deptids=7?page=1' 
    #searchurl = u'http://scrapi.org/search/*&what=Paintings&deptids=21?page=22'
    #searchurl = u'http://scrapi.org/search/*&what=Paintings&deptids=2?page=1'

    htmlparser = HTMLParser.HTMLParser()

    while searchurl:
        print searchurl
        searchPage = urllib2.urlopen(searchurl)
        searchData = searchPage.read()
        searchDataObject = json.loads(searchData)

        for item in searchDataObject.get('collection').get('items'):
            metadata = {}
            metadata['metid'] = item.get('id')
            metadata['scrapiurl'] = item.get('href')
            metadata['url'] = item.get('website_href')
            # We have other fields, but these seem to be broken in the search
            print metadata['url']

            itemPage = urllib2.urlopen(metadata['scrapiurl'])
            itemData = itemPage.read()
            itemDataObject = json.loads(itemData)

            if itemDataObject.get('head'):
                # Cached problem
                print u'Ran into a cached problem, skipping. Should do this one later'
                continue

            metPage = urllib2.urlopen(metadata['url'])
            metData = metPage.read()
            
            # Not the inv number
            objectidregex = u'<div><strong>Accession Number:</strong>\s*([^<]+)</div>'
            objectidmatch = re.search(objectidregex, metData, flags=re.DOTALL)
            
            if not objectidmatch:
                # See for example http://www.metmuseum.org/collection/the-collection-online/search/435614
                print u'No id found, something fishy going on!!!! Skipping it'
                continue

            metadata['id'] = unicode(objectidmatch.group(1), "utf-8")

            # Always need this
            if itemDataObject.get('primaryArtistNameOnly'):
                metadata['creator'] = htmlparser.unescape(itemDataObject.get('primaryArtistNameOnly'))
            else:
                metadata['creator'] = u'anonymous'
                
            metadata['title'] = htmlparser.unescape(unicode(itemDataObject.get('title')))
            
            #Might have this
            metadata['medium'] = itemDataObject.get('medium')
            if itemDataObject.get('dateText'):
                if type(itemDataObject.get('dateText')) is int:
                    metadata['datetext'] = unicode(itemDataObject.get('dateText'))
                else:
                    metadata['datetext'] = itemDataObject.get('dateText')
            
            yield metadata

        # Done with this search page. Set the next page or break
        if searchDataObject.get('_links').get('next'):
            searchurl = searchDataObject.get('_links').get('next').get('href')
        else:
            searchurl = None
            break
        
        
            
        

def main():
    paintingGen = getPaintingGenerator()

    #for painting in paintingGen:
    #    print painting
        
    paintingsBot = PaintingsBot(paintingGen, 217)
    paintingsBot.run()
    
    

if __name__ == "__main__":
    main()
