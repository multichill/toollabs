#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape paintings from the Statens Museum for Kunst website.

http://www.smk.dk/en/explore-the-art/search-smk/#/category/collections/fq=object_type%3Amaleri&start=12

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
    def __init__(self, dictGenerator, paintingIdProperty, collectionid):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.generator = dictGenerator
        self.repo = pywikibot.Site().data_repository()
        
        self.paintingIdProperty = paintingIdProperty
        self.collectionid = collectionid
        self.collectionitem = pywikibot.ItemPage(self.repo, u'Q%s' % (self.collectionid,))
        self.paintingIds = self.fillCache(self.collectionid, self.paintingIdProperty)

        #self.paintingIds[u'1910.1.72']=u'17442480'
        
    def fillCache(self, collectionid, propertyId, queryoverride=u'', cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        if queryoverride:
            query = queryoverride
        else:
            query = u'CLAIM[195:%s] AND CLAIM[%s]' % (collectionid, propertyId,)

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
            else:
                pywikibot.output('I expected %s items, but I have %s items in cache' % (expectedItems, len(result),))

        return result
                        
    def run(self):
        """
        Starts the robot.
        """
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

                data['labels']['da'] = {'language': 'da', 'value': painting[u'titleda']}
                data['labels']['en'] = {'language': 'en', 'value': painting[u'titleen']}
 
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
                    data['descriptions']['en'] = {'language': u'en', 'value' : u'painting by %s (%s, %s)' % (painting[u'creator'], painting[u'collectionshort'], painting[u'id'])}
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
                newqualifier.setTarget(self.collectionitem)
                pywikibot.output('Adding new qualifier claim to %s' % paintingItem)
                newclaim.addQualifier(newqualifier)

                collectionclaim = pywikibot.Claim(self.repo, u'P195')
                collectionclaim.setTarget(self.collectionitem)
                pywikibot.output('Adding collection claim to %s' % paintingItem)
                paintingItem.addClaim(collectionclaim)

                # Add the date they got it as a qualifier to the collection
                if painting.get(u'acquisitiondate'):
                    colqualifier = pywikibot.Claim(self.repo, u'P580')
                    acdate = None
                    if len(painting[u'acquisitiondate'])==4 and painting[u'acquisitiondate'].isnumeric(): # It's a year
                        acdate = pywikibot.WbTime(year=painting[u'acquisitiondate'])
                    elif len(painting[u'acquisitiondate'].split(u'-', 2))==3:
                        (acday, acmonth, acyear) = painting[u'acquisitiondate'].split(u'-', 2)
                        acdate = pywikibot.WbTime(year=int(acyear), month=int(acmonth), day=int(acday))
                    if acdate:
                        colqualifier.setTarget(acdate)
                        pywikibot.output('Adding new acquisition date qualifier claim to collection on %s' % paintingItem)
                        collectionclaim.addQualifier(colqualifier)
                
                self.addReference(paintingItem, collectionclaim, painting[u'url'])
                
            
            if paintingItem and paintingItem.exists():
                painting['wikidata'] = paintingItem.title()
                
                data = paintingItem.get()
                claims = data.get('claims')
                #print claims

                # located in
                if u'P276' not in claims and painting.get(u'location'):
                    newclaim = pywikibot.Claim(self.repo, u'P276')
                    location = pywikibot.ItemPage(self.repo, painting.get(u'location'))
                    newclaim.setTarget(location)
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
                if u'P571' not in claims and painting.get(u'date'):
                    if len(painting[u'date'])==4 and painting[u'date'].isnumeric(): # It's a year
                        newdate = pywikibot.WbTime(year=painting[u'date'])
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

    Doing a two step approach here. Could do one, but would be complicated
    * Loop over http://www.artic.edu/aic/collections/artwork-search/results/painting?filters=object_type_s%3APainting&page=0 - 237 and grab paintings
    * Grab data from paintings
    '''

    start = 0
    end = 7000
    step = 100

    basestarturl = u'http://solr.smk.dk:8080/proxySolrPHP/proxy.php?wt=json&query=facet%3Dfalse%26facet.field%3Dartist_name_ss%26facet.field%3Dartist_natio%26facet.field%3Dobject_production_century_earliest%26facet.field%3Dobject_type%26facet.field%3D%7B!ex%3Dcategory%7Dcategory%26facet.limit%3D-1%26facet.mincount%3D1%26rows%3D' + unicode(step) + u'%26defType%3Dedismax%26json.nl%3Dmap%26q%3D-%28id_s%253A%28*%252F*%29%2520AND%2520category%253Acollections%29%2520-%28id_s%253A%28*verso%29%2520AND%2520category%253Acollections%29%26fq%3D%7B!tag%3Dcategory%7Dcategory%253Acollections%26fq%3Dobject_type%253Amaleri%26qf%3D%2520id%255E20%2520title_dk%255E5%2520title_eng%255E15%2520title_first%255E15%2520artist_name%255E15%2520page_content%255E10%2520page_title%255E15%2520description_note_dk%255E2%2520description_note_en%255E5%2520prod_technique_dk%255E2%2520prod_technique_en%255E5%2520object_type%255E10%26sort%3Dscore%2520desc%26start%3D'
    baseendurl = u'&prev_query=&solrUrl=http%3A%2F%2Fsolr.smk.dk%3A8080%2Fsolr%2Fprod_all_en%2F&language=en'

    htmlparser = HTMLParser.HTMLParser()

    for i in range (start, end, step):
        searchurl = basestarturl + unicode(i) + baseendurl
        
    
        searchPage = urllib2.urlopen(searchurl)
        searchData = searchPage.read()
        #print searchData[1:-1]
        searchDataObject = json.loads(searchData[1:-1])
        #print searchDataObject.get('response')
        for item in searchDataObject.get(u'response').get(u'docs'):
            metadata = {}
            metadata[u'id'] = item['id']
            metadata[u'url'] = u'http://www.smk.dk/en/explore-the-art/search-smk/#/detail/%s' % (item.get('id'),)
            print metadata[u'url']

            metadata[u'acquisitiondate'] = item.get('acq_date')
            metadata[u'creator'] = htmlparser.unescape(item.get('artist_name')[0])
            metadata[u'date'] = item.get('object_production_date_text_en')
            metadata[u'medium'] = item.get('prod_technique_en')

            if item.get('title_dk'):
                metadata[u'titleda'] = item['title_dk']
            else:
                metadata[u'titleda'] = item['title_first']
                
            if item.get('title_eng'):
                metadata[u'titleen'] = item['title_eng']
            else:
                metadata[u'titleen'] = item['title_first']

            metadata[u'location'] = u'Q671384'
            metadata[u'collectionshort'] = u'SMK'
            
            yield metadata

            #except TypeError:
            #    print u'EEEEEEEEEEEEEEEEEEEEEEEEEEERRROOOOR'
            #    print u'EEEEEEEEEEEEEEEEEEEEEEEEEEERRROOOOR'
            #    print u'EEEEEEEEEEEEEEEEEEEEEEEEEEERRROOOOR'
            #    print u'EEEEEEEEEEEEEEEEEEEEEEEEEEERRROOOOR'

                
            #   for key in sorted(item.keys()):
            #        print key
            #        print item.get(key)            
    """        
        playdata = [0]
        for key in sorted(playdata.keys()):
            
            print key
            print playdata.get(key)
        time.sleep(10)

        yield searchDataObject

    
    
    # LOL, these nerds start at zero :-)    
    baseurl = u'http://www.artic.edu/aic/collections/artwork-search/results/painting?filters=object_type_s%%3APainting&page=%s' 

    htmlparser = HTMLParser.HTMLParser()

    total = 0
    success = 0
    fail = 0
    problems = []

    # 0 - 237
    for i in range(0,237):
        searchurl = baseurl % (i,)
        pywikibot.output(searchurl)
        searchPage = urllib2.urlopen(searchurl)
        searchData = searchPage.read()
        # <span class="italic"><a href="/aic/collections/artwork/47149?search_no=

        itemregex = u'<span class="italic"><a href="(/aic/collections/artwork/\d+)\?search_no='

        for match in re.finditer(itemregex, searchData):
            url = u'http://www.artic.edu%s' % (match.group(1),)
            total = total + 1

            #pywikibot.output(url)
            
            itemPage = urllib2.urlopen(url)
            itemData = itemPage.read()

            metadata = {}
            metadata['url'] = url

            # "object_artist_culture_display": "Albert Besnard\x3cbr /\x3e\nFrench, 1849-1934", "object_title": "Woman\'s Head", "object_date_display": "c. 1890", "object_id": "81525"

            #Horrible encoding problems
            #creatorregex = u'"object_artist_culture_display"\s*:\s"([^"]+)"'
            creator2regex = u'<p><a href="/aic/collections/artwork/artist/[^"]+">([^<]+)<'
            #titleregex = u'"object_title"\s*:\s"([^"]+)"'
            #Horrible encoding problems
            title2regex = u'<img src="http://www.artic.edu/aic/collections/citi/images/standard/WebMedium/[^"]+" alt="([^"]+)"'
            title3regex = u'<title>([^\|]+) \| The Art Institute of Chicago</title>'
            #dateregex = u'"object_date_display"\s*:\s"([^"]+)"'
            #This is a PITA
            # idregex = u'<br/>[^<]+, (\d+\.\d+)</p>\s*<p id="dept-gallery">'
            idregex = u'<br\s*/>[^<]+, (\d\d\d\d\.\d+(\.[\d\-a-g]+)?)</p>'
            id2regex = u'<br\s*/>[^<]+, (RofO\d+\.\d+(\.[\d\-a-g]+)?)</p>'
            id3regex = u'<br\s*/>[^<]+, (\d+\.\d+)</p>'

            #creatormatch = re.search(creatorregex, itemData, flags=re.M)
            creator2match = re.search(creator2regex, itemData)
            #if creatormatch:
            #    metadata[u'creator']=htmlparser.unescape(unicode(creatormatch.group(1), "ascii"))
            if creator2match:
                metadata[u'creator']=htmlparser.unescape(unicode(creator2match.group(1), "utf-8"))
            else:
                print u'No creator found'
                fail = fail + 1
                problems.append(url)
                continue
                
            #else:
            #    # Creator not always available
            #    metadata[u'creator']=u'anonymous'

            #titlematch = re.search(titleregex, itemData)
            title2match = re.search(title2regex, itemData)
            title3match = re.search(title3regex, itemData)
            #if titlematch:
            #    metadata[u'title']=htmlparser.unescape(unicode(titlematch.group(1), "ascii"))
            if title2match:
                metadata[u'title']=htmlparser.unescape(unicode(title2match.group(1), "utf-8"))
            else:
                metadata[u'title']=htmlparser.unescape(unicode(title3match.group(1), "utf-8"))
            


                
            #datematch = re.search(dateregex, itemData)
            ## Not always available
            #if datematch:
            #    metadata[u'date']=htmlparser.unescape(unicode(datematch.group(1), "ascii"))

            #PITA, maybe later
            #mediummatch = re.search(mediumregex, itemData)
            ## Not always available
            #if mediummatch:
            #    metadata[u'medium']=htmlparser.unescape(unicode(mediummatch.group(1), "utf-8"))

            idmatch = re.search(idregex, itemData) #, flags=re.M)
            id2match = re.search(id2regex, itemData) 
            id3match = re.search(id3regex, itemData)
            if idmatch:
                metadata[u'id']=htmlparser.unescape(unicode(idmatch.group(1), "utf-8"))
            elif id2match:
                metadata[u'id']=htmlparser.unescape(unicode(id2match.group(1), "utf-8"))
            elif id3match:
                metadata[u'id']=htmlparser.unescape(unicode(id3match.group(1), "utf-8"))
            else:
                print u'No id found'
                fail = fail + 1
                problems.append(url)
                continue                
            #if u'?' in metadata[u'id']:
            #    continue

            success = success + 1
            yield metadata

        pywikibot.output(u'Current score after %s items: %s failed & %s success' % (total, fail, success))
        pywikibot.output(problems)  

            
    """
    '''
        
        objectidmatch = re.search(objectidregex, metData, flags=re.DOTALL)        
        # Get the urls here
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
                
            metadata['title'] = htmlparser.unescape(itemDataObject.get('title'))
            
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

        '''
        
            
        

def main():
    paintingGen = getPaintingGenerator()

    #for painting in paintingGen:
    #    print painting

    paintingsBot = PaintingsBot(paintingGen, 217, u'671384')
    paintingsBot.run()
    
    

if __name__ == "__main__":
    main()
