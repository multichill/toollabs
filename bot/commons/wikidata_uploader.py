#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape paintings from the Getty website
http://www.getty.edu/art/collection/search/?view=grid&query=YToxOntzOjEzOiJkZXBhcnRtZW50LmlkIjthOjE6e2k6MDtpOjE7fX0%3D&options=YToxOntzOjk6ImJlaGF2aW91ciI7czo2OiJ2aXN1YWwiO30%3D


"""
#import json
import pywikibot
#from pywikibot import pagegenerators
#import urllib2
import re
import pywikibot.data.sparql
import datetime
#import HTMLParser
#import posixpath
#from urlparse import urlparse
#from urllib import urlopen
import hashlib
import io
import base64
import tempfile
import os
import time
import requests

class WikidataUploaderBot:
    """
    A bot to enrich and create paintings on Wikidata
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.generator = self.getGenerator()
        self.repo = pywikibot.Site().data_repository()
        self.site = pywikibot.Site(u'commons', u'commons')

    def getGenerator(self):
        """
        Get the generator of items to consider
        """
        query = u"""
SELECT ?item ?itemdate ?inv ?downloadurl ?sourceurl ?title ?creatorname ?license ?institutiontemplate ?collectionLabel ?collectioncategory ?creator ?creatordate ?deathyear ?creatortemplate ?creatorcategory WHERE {
  ?item p:P4765 ?image .
  MINUS { ?item wdt:P18 [] } .
  ?item schema:dateModified ?itemdate .
  ?item wdt:P31 wd:Q3305213 .
  ?item wdt:P217 ?inv .
  ?image ps:P4765 ?downloadurl .
  ?image pq:P2701 wd:Q2195 .
  ?image pq:P2699 ?sourceurl .
  ?image pq:P1476 ?title .
  ?image pq:P2093 ?creatorname .
  OPTIONAL { ?image pq:P275 ?license } .
  ?item wdt:P195 ?collection . ?collection wdt:P1612 ?institutiontemplate .
  ?collection rdfs:label ?collectionLabel. FILTER(LANG(?collectionLabel) = "en").
  ?collection wdt:P373 ?collectioncategory .
  ?item wdt:P170 ?creator .
  ?creator wdt:P570 ?dod . BIND(YEAR(?dod) AS ?deathyear)
  FILTER(?deathyear < 1923) .
  ?creator schema:dateModified ?creatordate .
  OPTIONAL { ?creator wdt:P1472 ?creatortemplate } .
  OPTIONAL { ?creator wdt:P373 ?creatorcategory } .
  } LIMIT 15000"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            resultitem['item'] = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            if resultitem.get('license'):
                resultitem['license'] = resultitem.get('license').replace(u'http://www.wikidata.org/entity/', u'')
            resultitem['creator'] = resultitem.get('creator').replace(u'http://www.wikidata.org/entity/', u'')
            yield resultitem

    def run(self):
        """
        Starts the robot.
        """

        for metadata in self.generator:
            if self.isReadyToUpload(metadata):
                self.uploadPainting(metadata)

    def isReadyToUpload(self, metadata):
        """
        :param metadata:
        :return:
        """
        format = u'%Y-%m-%dT%H:%M:%SZ'
        now = datetime.datetime.utcnow()
        itemdelta = now - datetime.datetime.strptime(metadata.get(u'itemdate'), format)
        creatordelta = now - datetime.datetime.strptime(metadata.get(u'creatordate'), format)

        # Both item and creator should at least be 7 days old
        if itemdelta.days > 7 and metadata.get(u'creatortemplate') and metadata.get(u'creatorcategory') and creatordelta.days > 7:
            return True
        # If no creator template at least 14 days old
        if itemdelta.days > 14 and not metadata.get(u'creatortemplate') and metadata.get(u'creatorcategory') and creatordelta.days > 14:
            return True
        # If no creator category at least 21 days old
        if itemdelta.days > 21 and not metadata.get(u'creatortemplate') and metadata.get(u'creatorcategory') and creatordelta.days > 21:
            return True
        return False

    def uploadPainting(self, metadata):
        """
        Process the metadata and if suitable, upload the painting
        :param metadata:
        :return:
        """
        print (metadata)
        description = self.getDescription(metadata)
        title = self.cleanUpTitle(self.getTitle(metadata))
        print (title)
        print (description)
        response = requests.get(metadata.get(u'downloadurl'), verify=False) # Museums and valid SSL.....
        if response.status_code == 200:
            hashObject = hashlib.sha1()
            hashObject.update(response.content)
            duplicates = list(page.title(withNamespace=False) for page in self.site.allimages(sha1=base64.b16encode(hashObject.digest())))
            if duplicates:
                pywikibot.output(u'Found a duplicate, skipping')
                return
            handle, tempname = tempfile.mkstemp()
            with os.fdopen(handle, "wb") as t:
                t.write(response.content)
                t.close()


            imagefile = pywikibot.FilePage(self.site, title=title)
            imagefile.text=description

            comment = u'Uploading based on Wikidata item [[:d:%(item)s]] from %(downloadurl)s' % metadata
            try:
                uploadsuccess = self.site.upload(imagefile, source_filename=tempname, ignore_warnings=True, comment=comment) # chunk_size=1000000)
            except pywikibot.data.api.APIError:
                pywikibot.output(u'Failed to upload image for Wikidata item [[:d:%(item)s]] from %(downloadurl)s' % metadata)
                uploadsuccess = False

            if uploadsuccess:
                pywikibot.output('Uploaded a file, sleeping a bit so I don\'t run into lagging databases')
                time.sleep(15)
                artworkItem = pywikibot.ItemPage(self.repo, title=metadata.get(u'item'))
                data = artworkItem.get()
                claims = data.get('claims')
                if u'P18' not in claims:
                    newclaim = pywikibot.Claim(self.repo, u'P18')
                    newclaim.setTarget(imagefile)
                    pywikibot.output('Adding %s --> %s' % (newclaim.getID(), newclaim.getTarget()))
                    artworkItem.addClaim(newclaim)
                    if u'P4765' in claims and len(claims.get(u'P4765'))==1:
                        summary = u'Uploaded the image'
                        artworkItem.removeClaims(claims.get(u'P4765')[0], summary=summary)
                    imagefile.touch()


    def getDescription(self, metadata):
        """

        :param metadata:
        :return:
        """
        artworkinfo = self.getArtworkTemplate(metadata)
        licenseinfo = self.getLicenseTemplate(metadata)
        categoryinfo =  self.getCategories(metadata)
        if artworkinfo and licenseinfo and categoryinfo:
            description = u'== {{int:filedesc}} ==\n'
            description = description + artworkinfo
            description = description + u'\n=={{int:license-header}}==\n'
            description = description + licenseinfo + u'\n' + categoryinfo
            return description

    def getArtworkTemplate(self, metadata):
        """

        :param metadata:
        :return:
        """
        result = u'{{subst:Artwork/subst|subst=subst:\n'
        if metadata.get(u'creatortemplate'):
            result = result + u'|artist={{Creator:%(creatortemplate)s}}\n' % metadata
        else:
            result = result + u'|artist=%(creatorname)s\n' % metadata
        result = result + u'|title=%(title)s\n' % metadata
        result = result + u'|institution={{Institution:%(institutiontemplate)s}}\n' % metadata
        result = result + u'|accession number=%(inv)s\n' % metadata
        result = result + u'|source=%(sourceurl)s\n' % metadata
        result = result + u'|wikidata=%(item)s\n' % metadata
        result = result + u'}}\n' % metadata
        return result

    def getLicenseTemplate(self, metadata):
        """

        :param metadata:
        :return:
        """
        # FIXME: Add more or different implementation
        licenses = {u'Q6938433' : u'Cc-zero',
                    u'Q18199165' : u'cc-by-sa-4.0'}
        if metadata.get(u'license'):
            if metadata.get(u'license') not in licenses:
                pywikibot.output(u'Found a license I do not understand: %(license)s' % metadata)
                return False
            licensetemplate = licenses.get(metadata.get(u'license'))
            deathyear = metadata.get(u'deathyear')
            return u'{{Licensed-PD-Art|PD-old-auto-1923|%s|deathyear=%s}}\n' % (licensetemplate, deathyear)
        return u'{{PD-Art|PD-old-auto-1923|deathyear=%(deathyear)s}}\n' % metadata

    def getCategories(self, metadata):
        """

        :param metadata:
        :return:
        """
        result = u'{{subst:#ifexist:Category:Paintings in the %(collectioncategory)s]]|[[Category:Paintings in the %(collectioncategory)s]]|[[Category:%(collectioncategory)s]]}}\n' % metadata
        if metadata.get(u'creatorcategory'):
            result = result + u'{{subst:#ifexist:Category:Paintings by %(creatorcategory)s]]|[[Category:Paintings by %(creatorcategory)s]]|[[Category:%(creatorcategory)s]]}}' % metadata
        return result

    def getTitle(self, metadata):
        """

        :param metadata:
        :return:
        """
        fmt = u'%(creatorname)s - %(title)s - %(inv)s - %(collectionLabel)s.jpg'
        return fmt % metadata

    def cleanUpTitle(self, title):
        '''
        Clean up the title of a potential mediawiki page. Otherwise the title of
        the page might not be allowed by the software.

        '''
        title = title.strip()
        title = re.sub(u"[<{\\[]", u"(", title)
        title = re.sub(u"[>}\\]]", u")", title)
        title = re.sub(u"[ _]?\\(!\\)", u"", title)
        title = re.sub(u",:[ _]", u", ", title)
        title = re.sub(u"[;:][ _]", u", ", title)
        title = re.sub(u"[\t\n ]+", u" ", title)
        title = re.sub(u"[\r\n ]+", u" ", title)
        title = re.sub(u"[\n]+", u"", title)
        title = re.sub(u"[?!]([.\"]|$)", u"\\1", title)
        title = re.sub(u"[&#%?!]", u"^", title)
        title = re.sub(u"[;]", u",", title)
        title = re.sub(u"[/+\\\\:]", u"-", title)
        title = re.sub(u"--+", u"-", title)
        title = re.sub(u",,+", u",", title)
        title = re.sub(u"[-,^]([.]|$)", u"\\1", title)
        title = re.sub(u"^- ", u"", title)
        title = title.replace(u" ", u"_")
        return title
        """

                if painting.get(u'imageurl'):
                    #A free file is available, let's see how big the current file is
                    if u'P18' in claims:
                        imagefile = claims.get('P18')[0].getTarget()
                        size = imagefile.latest_file_info.size
                    if u'P18' not in claims or size < 1000000:
                        commonssite = pywikibot.Site("commons", "commons")
                        photo = Photo(painting[u'imageurl'], painting)
                        titlefmt = u'%(creator)s - %(title)s - %(id)s - J. Paul Getty Museum.%(_ext)s'
                        pagefmt = u'User:Multichill/J. Paul Getty Museum'
                        
                        duplicates = photo.findDuplicateImages()
                        if duplicates:
                            pywikibot.output(u"Skipping duplicate of %r" % duplicates)
                            imagetitle=duplicates[0]
                            #return duplicates[0]
                        else:

                            imagetitle = self.cleanUpTitle(photo.getTitle(titlefmt))
                            imagefile = pywikibot.FilePage(commonssite, title=imagetitle)
                            imagetitle = imagefile.title()
                            pywikibot.output(imagetitle)
                            description = photo.getDescription(pagefmt)
                            pywikibot.output(description)
                            imagefile.text=description


                            handle, tempname = tempfile.mkstemp()
                            with os.fdopen(handle, "wb") as t:
                                t.write(photo.downloadPhoto().getvalue())
                                t.close()
                            #tempname
                            commonssite.upload(imagefile,
                                               source_filename=tempname,
                                               ignore_warnings=True,
                                               chunk_size=1000000)

                            #bot = upload.UploadRobot(url=tempname,
                            #                         description=description,
                            #                         useFilename=imagetitle,
                            #                         keepFilename=True,
                            #                         verifyDescription=False,
                            #                         uploadByUrl=False,
                            #                         targetSite=commonssite)
                            #bot._contents = photo.downloadPhoto().getvalue()
                            pywikibot.output('Uploaded a file, sleeping a bit so I don\it run into lagging databases')
                            time.sleep(15)

                            #bot._retrieved = True
                            #bot.run()
                    
                
                if u'P18' not in claims and imagetitle:
                    newclaim = pywikibot.Claim(self.repo, u'P18')
                    imagelink = pywikibot.Link(imagetitle, source=commonssite, defaultNamespace=6)
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








        

def main():
    #paintingGen = getPaintingGenerator()

    #for painting in paintingGen:
    #    print painting

    wikidataUploaderBot = WikidataUploaderBot()
    wikidataUploaderBot.run()
    
    

if __name__ == "__main__":
    main()
