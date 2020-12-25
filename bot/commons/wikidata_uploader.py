#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to upload public domain paintings.

Bot uses files that have https://www.wikidata.org/wiki/Property:P4765

The bot will decide if it's publid domain because:
* Painter is known and died more than 95 years ago
* Painter is anonymous or low on metadata, but painting is dated before 1890
* Painting is by a known painter who died between 70-95 years ago and the painting was produced more than 95 years ago
* Painting is marked as public domain with the qualifiers that the creator died at least 100 years ago
That should be a safe enough margin.

"""

import pywikibot
import re
import pywikibot.data.sparql
from pywikibot.comms import http
import datetime
import hashlib
import io
import base64
import tempfile
import os
import time
import requests
import json

class WikidataUploaderBot:
    """
    A bot to enrich and create paintings on Wikidata
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.generatorDied95Creators = self.getGeneratorDied95Creators()
        self.generatorPre1890AnonymousWorks = self.getGeneratorPre1890AnonymousWorks()
        self.generatorDied70Produced95Works = self.getGeneratorDied70Produced95Works()
        self.generatorPublicDomain100pma = self.getGeneratorPublicDomain100pma()
        self.site = pywikibot.Site('commons', 'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()
        self.duplicates = []
        self.processeditems = []

    def getGeneratorDied95Creators(self):
        """
        Get the generator of items with known painter died more than 95 years ago
        """
        query = """
SELECT ?item ?itemdate ?inv ?downloadurl ?format ?sourceurl ?title ?creatorname ?license ?operator ?collectionLabel ?collectioncategory ?creator ?creatordate ?deathyear ?creatorcategory WHERE {
  ?item p:P4765 ?image .
  ?item schema:dateModified ?itemdate .
  ?item wdt:P31 wd:Q3305213 .
  ?item wdt:P217 ?inv .
  ?image ps:P4765 ?downloadurl .
  ?image pq:P2701 ?format .
  ?image pq:P2699 ?sourceurl .
  ?image pq:P1476 ?title .
  ?image pq:P2093 ?creatorname .
  OPTIONAL { ?image pq:P275 ?license } .
  OPTIONAL { ?image pq:P137 ?operator } .
  ?item wdt:P195 ?collection .
  ?collection rdfs:label ?collectionLabel. FILTER(LANG(?collectionLabel) = "en").
  ?collection wdt:P373 ?collectioncategory .
  ?item wdt:P170 ?creator .
  ?creator wdt:P570 ?dod . BIND(YEAR(?dod) AS ?deathyear)
  FILTER(?deathyear < (YEAR(NOW())-95)) .
  ?creator schema:dateModified ?creatordate .
  OPTIONAL { ?creator wdt:P373 ?creatorcategory } .
  } ORDER BY DESC(?itemdate)
  LIMIT 15000"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            resultitem['item'] = resultitem.get('item').replace('http://www.wikidata.org/entity/', '')
            resultitem['format'] = resultitem.get('format').replace('http://www.wikidata.org/entity/', '')
            if resultitem.get('license'):
                resultitem['license'] = resultitem.get('license').replace('http://www.wikidata.org/entity/', '')
            if resultitem.get('operator'):
                resultitem['operator'] = resultitem.get('operator').replace('http://www.wikidata.org/entity/', '')
            resultitem['creator'] = resultitem.get('creator').replace('http://www.wikidata.org/entity/', '')
            yield resultitem

    def getGeneratorPre1890AnonymousWorks(self):
        """
        Get the generator of items which were made before 1890 to consider
        """
        query = """
SELECT ?item ?itemdate ?inv ?downloadurl ?format ?sourceurl ?title ?creatorname ?license ?operator ?collectionLabel ?collectioncategory WHERE {
  ?item p:P4765 ?image .
  ?item schema:dateModified ?itemdate .
  ?item wdt:P31 wd:Q3305213 .
  ?item wdt:P217 ?inv .
  ?image ps:P4765 ?downloadurl .
  ?image pq:P2701 ?format .
  ?image pq:P2699 ?sourceurl .
  ?image pq:P1476 ?title .
  OPTIONAL { ?image pq:P2093 ?creatorname }.
  ?item wdt:P170 wd:Q4233718 .
  OPTIONAL { ?image pq:P275 ?license } .
  OPTIONAL { ?image pq:P137 ?operator } .
  ?item wdt:P195 ?collection .
  ?collection rdfs:label ?collectionLabel. FILTER(LANG(?collectionLabel) = "en").
  ?collection wdt:P373 ?collectioncategory .
  ?item wdt:P571 ?inception . BIND(YEAR(?inception) AS ?inceptionyear)
  FILTER(?inceptionyear < 1890) .
  } ORDER BY DESC(?itemdate)
  LIMIT 15000"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            resultitem['item'] = resultitem.get('item').replace('http://www.wikidata.org/entity/', '')
            resultitem['format'] = resultitem.get('format').replace('http://www.wikidata.org/entity/', '')
            if resultitem.get('license'):
                resultitem['license'] = resultitem.get('license').replace('http://www.wikidata.org/entity/', '')
            if resultitem.get('operator'):
                resultitem['operator'] = resultitem.get('operator').replace('http://www.wikidata.org/entity/', '')
            resultitem['creator'] = 'Q4233718' # Item for anonymous
            if not resultitem.get('creatorname'):
                resultitem['creatorname'] = 'anonymous'
            yield resultitem

    def getGeneratorDied70Produced95Works(self):
        """
        Get the generator of items with known painter who died between 70 and 95 years ago and painting was made
        more than 95 years ago.
        """
        query = """
SELECT ?item ?itemdate ?inv ?downloadurl ?format ?sourceurl ?title ?creatorname ?license ?operator ?collectionLabel ?collectioncategory ?creator ?creatordate ?deathyear ?creatorcategory WHERE {
  ?item p:P4765 ?image .
  ?item schema:dateModified ?itemdate .
  ?item wdt:P31 wd:Q3305213 .
  ?item wdt:P217 ?inv .
  ?image ps:P4765 ?downloadurl .
  ?image pq:P2701 ?format .
  ?image pq:P2699 ?sourceurl .
  ?image pq:P1476 ?title .
  ?image pq:P2093 ?creatorname .
  OPTIONAL { ?image pq:P275 ?license } .
  OPTIONAL { ?image pq:P137 ?operator } .
  ?item wdt:P195 ?collection .
  ?collection rdfs:label ?collectionLabel. FILTER(LANG(?collectionLabel) = "en").
  ?collection wdt:P373 ?collectioncategory .
  ?item wdt:P170 ?creator .
  ?creator wdt:P570 ?dod . BIND(YEAR(?dod) AS ?deathyear)
  FILTER(?deathyear >= (YEAR(NOW())-95) && ?deathyear < (YEAR(NOW())-70)) .
  ?creator wdt:P569 ?dob .
  ?item wdt:P571 ?inception .
  FILTER(YEAR(?inception) < (YEAR(NOW())-95) && ?dob < ?inception ) .
  ?creator schema:dateModified ?creatordate .
  OPTIONAL { ?creator wdt:P373 ?creatorcategory } .
  } ORDER BY DESC(?itemdate)
  LIMIT 15000"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            resultitem['item'] = resultitem.get('item').replace('http://www.wikidata.org/entity/', '')
            resultitem['format'] = resultitem.get('format').replace('http://www.wikidata.org/entity/', '')
            if resultitem.get('license'):
                resultitem['license'] = resultitem.get('license').replace('http://www.wikidata.org/entity/', '')
            if resultitem.get('operator'):
                resultitem['operator'] = resultitem.get('operator').replace('http://www.wikidata.org/entity/', '')
            resultitem['creator'] = resultitem.get('creator').replace('http://www.wikidata.org/entity/', '')
            yield resultitem

    def getGeneratorPublicDomain100pma(self):
        """
        Get the generator of items which are marked as being in the public domain because creator died 100+ years ago
        """
        query = """
SELECT ?item ?itemdate ?inv ?downloadurl ?format ?sourceurl ?title ?creatorname ?license ?operator ?collectionLabel ?collectioncategory WHERE {
  ?item p:P4765 ?image .
  ?item schema:dateModified ?itemdate .
  ?item wdt:P31 wd:Q3305213 .
  ?item wdt:P217 ?inv .
  ?image ps:P4765 ?downloadurl .
  ?image pq:P2701 ?format .
  ?image pq:P2699 ?sourceurl .
  ?image pq:P1476 ?title .
  ?image pq:P2093 ?creatorname .
  OPTIONAL { ?image pq:P275 ?license } .
  OPTIONAL { ?image pq:P137 ?operator } .
  ?item wdt:P195 ?collection .
  ?collection rdfs:label ?collectionLabel. FILTER(LANG(?collectionLabel) = "en").
  ?collection wdt:P373 ?collectioncategory .
  ?item p:P6216 ?copyrightstatement .
  ?copyrightstatement ps:P6216 wd:Q19652 .
  ?copyrightstatement pq:P1001 wd:Q60332278 .
  ?copyrightstatement pq:P459 wd:Q29940705
  } ORDER BY DESC(?itemdate)
  LIMIT 15000"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            resultitem['item'] = resultitem.get('item').replace('http://www.wikidata.org/entity/', '')
            resultitem['format'] = resultitem.get('format').replace('http://www.wikidata.org/entity/', '')
            if resultitem.get('license'):
                resultitem['license'] = resultitem.get('license').replace('http://www.wikidata.org/entity/', '')
            if resultitem.get('operator'):
                resultitem['operator'] = resultitem.get('operator').replace('http://www.wikidata.org/entity/', '')
            yield resultitem

    def run(self):
        """
        Starts the robot.
        """
        for metadata in self.generatorDied95Creators:
            if self.isReadyToUpload(metadata):
                self.uploadPainting(metadata)
        for metadata in self.generatorPre1890AnonymousWorks:
            if self.isReadyToUpload(metadata):
                self.uploadPainting(metadata)
        for metadata in self.generatorDied70Produced95Works:
            if self.isReadyToUpload(metadata):
                self.uploadPainting(metadata)
        for metadata in self.generatorPublicDomain100pma:
            if self.isReadyToUpload(metadata):
                self.uploadPainting(metadata)
        self.reportDuplicates()

    def isReadyToUpload(self, metadata):
        """
        Just wait two days to spread it out a bit
        """
        format = u'%Y-%m-%dT%H:%M:%SZ'
        now = datetime.datetime.utcnow()
        itemdelta = now - datetime.datetime.strptime(metadata.get('itemdate'), format)
        if metadata.get('creatordate'):
            creatordelta = now - datetime.datetime.strptime(metadata.get('creatordate'), format)
        else:
            creatordelta = datetime.timedelta(days=999) # Just something high for if it isn't set.

        # Both item and creator should at least be 2 days old
        if itemdelta.days > 2 and creatordelta.days > 2:
            return True
        return False

    def uploadPainting(self, metadata):
        """
        Process the metadata and if suitable, upload the painting
        """
        pywikibot.output(metadata)
        if metadata.get('item') in self.processeditems:
            pywikibot.output('Already worked on %s, skipping' % (metadata.get('item'),))
            return
        description = self.getDescription(metadata)
        title = self.cleanUpTitle(self.getTitle(metadata))
        if not description or not title:
            return
        pywikibot.output(title)
        pywikibot.output(description)

        # To prevent processing the same item twice:
        self.processeditems.append(metadata.get('item'))
        try:
            response = requests.get(metadata.get('downloadurl'), verify=False) # Museums and valid SSL.....
        except requests.exceptions.ConnectionError:
            pywikibot.output('Got a connection error for Wikidata item [[:d:%(item)s]] with url %(downloadurl)s' % metadata)
            return False

        if response.status_code == 200:
            hashObject = hashlib.sha1()
            hashObject.update(response.content)
            sha1base64 = base64.b16encode(hashObject.digest())
            duplicates = list(self.site.allimages(sha1=sha1base64))
            if duplicates:
                pywikibot.output('Found a duplicate, trying to add it')
                imagefile = duplicates[0]
                self.addImageToWikidata(metadata, imagefile, summary = 'Adding already uploaded image')
                duplicate = { 'title' : title,
                              'qid' : metadata.get('item'),
                              'downloadurl' : metadata.get('downloadurl'),
                              'sourceurl' : metadata.get('sourceurl'),
                              'duplicate' : imagefile.title(withNamespace=False),
                              'description' : description,
                              }
                self.duplicates.append(duplicate)
                return

            # This part is commented out because only sysop users can do this :-(
            ## self.site.filearchive does not exist, have to dig deeper
            ## deleted = list(self.site.filearchive(sha1=sha1base64))
            #deleted_url = u'https://commons.wikimedia.org/w/api.php?action=query&list=filearchive&faprop=sha1&fasha1=%s&format=json'
            #fa_response = http.fetch(deleted_url % (sha1base64,))
            #fa_data = json.loads(fa_response.text)
            #print (fa_data)
            #if fa_data.get(u'query').get(u'filearchive'):
            #    fa_title = fa_data.get(u'query').get(u'filearchive')[0].get(u'title')
            #    pywikibot.output(u'Found a deleted file %s with the same hash %s, skipping it' % (fa_title, sha1base64))
            #    return

            with tempfile.NamedTemporaryFile() as t:
                t.write(response.content)
                t.flush()
                filesize = len(response.content)
                chunkedfilesize = 80000000

                imagefile = pywikibot.FilePage(self.site, title=title)
                # For some reason sometimes the duplicate detection doesn't work
                if imagefile.exists():
                    pywikibot.output('The file with the name "%s" already exists, skipping' % (title,))
                    return
                imagefile.text=description

                comment = 'Uploading based on Wikidata item [[d:Special:EntityPage/%(item)s]] from %(downloadurl)s' % metadata
                try:
                    if filesize > chunkedfilesize:
                        pywikibot.output('File size %s is larger than %s so trying chunked uploading' % (filesize, chunkedfilesize))
                        uploadsuccess = self.site.upload(imagefile, source_filename=t.name, ignore_warnings=True, comment=comment, chunk_size=10000000)
                    else:
                        pywikibot.output('File size %s is smaller than %s so no using chunked uploading' % (filesize, chunkedfilesize))
                        uploadsuccess = self.site.upload(imagefile, source_filename=t.name, ignore_warnings=True, comment=comment)
                except pywikibot.data.api.APIError:
                    pywikibot.output('Failed to upload image for Wikidata item [[:d:%(item)s]] from %(downloadurl)s' % metadata)
                    uploadsuccess = False

            if uploadsuccess:
                pywikibot.output('Uploaded a file, sleeping a bit so I don\'t run into lagging databases')
                time.sleep(15)
                self.addImageToWikidata(metadata, imagefile, summary = 'Uploaded the image')
                imagefile.clear_cache() # Clear the cache otherwise the pageid is 0.
                mediaid = 'M%s' % (imagefile.pageid,)
                itemdata = self.getStructuredData(metadata)
                summary = 'this newly uploaded file depicts and is a digital representation of [[d:Special:EntityPage/%s]]' % (metadata.get('item'),)

                token = self.site.tokens['csrf']
                postdata = {'action' : 'wbeditentity',
                            'format' : 'json',
                            'id' : mediaid,
                            'data' : json.dumps(itemdata),
                            'token' : token,
                            'summary' : summary,
                            'bot' : True,
                            }
                #print (json.dumps(postdata, sort_keys=True, indent=4))
                request = self.site._simple_request(**postdata)
                data = request.submit()
                imagefile.touch()

    def addImageToWikidata(self, metadata, imagefile, summary='Added the image'):
        """
        Add the image to the Wikidata item. This might add an extra image if the item already has one
        """
        artworkItem = pywikibot.ItemPage(self.repo, title=metadata.get(u'item'))
        data = artworkItem.get()
        claims = data.get('claims')

        newclaim = pywikibot.Claim(self.repo, u'P18')
        newclaim.setTarget(imagefile)

        foundimage = False
        replacedimage = False
        if u'P18' in claims:
            for claim in claims.get(u'P18'):
                if claim.getTarget().title()==newclaim.getTarget().title():
                    pywikibot.output(u'The image is already on the item')
                    foundimage = True
            if not foundimage and len(claims.get(u'P18'))==1:
                claim = claims.get(u'P18')[0]
                newimagesize = imagefile.latest_file_info.size
                currentsize = claim.getTarget().latest_file_info.size
                # Only replace if new one is at least 4 times larger
                if currentsize * 4 < newimagesize:
                    summary = u'replacing with much larger image'
                    claim.changeTarget(imagefile, summary=summary)
                    replacedimage = True

        if not foundimage and not replacedimage:
            pywikibot.output('Adding %s --> %s' % (newclaim.getID(), newclaim.getTarget()))
            artworkItem.addClaim(newclaim, summary=summary)
        # Only remove if we had one suggestion. Might improve the logic in the future here
        if u'P4765' in claims and len(claims.get(u'P4765'))==1:
            artworkItem.removeClaims(claims.get(u'P4765')[0], summary=summary)

    def getDescription(self, metadata):
        """
        Construct the description for the file to be uploaded
        """
        artworkinfo = '{{Artwork}}\n' # All structured data on Commons!
        licenseinfo = self.getLicenseTemplate(metadata)
        categoryinfo =  self.getCategories(metadata)
        if artworkinfo and licenseinfo and categoryinfo:
            description = '== {{int:filedesc}} ==\n'
            description = description + artworkinfo
            description = description + '\n=={{int:license-header}}==\n'
            description = description + licenseinfo + '\n' + categoryinfo
            return description

    def getLicenseTemplate(self, metadata):
        """
        Construct the license template to be used

        https://w.wiki/rok gives a quick overview
        """
        # FIXME: Add more or different implementation
        licenses = { 'Q6938433' : 'cc-zero',
                     'Q20007257' : 'cc-by-4.0',
                     'Q18199165' : 'cc-by-sa-4.0'}

        if metadata.get('license'):
            result = '{{Licensed-PD-Art'
        else:
            result = '{{PD-Art'

        if metadata.get('deathyear'):
            result += '|PD-old-auto-expired'
        else:
            result += '|PD-old-100-expired'

        if metadata.get('license'):
            if metadata.get('license') not in licenses:
                pywikibot.output('Found a license I do not understand: %(license)s' % metadata)
                return False
            licensetemplate = licenses.get(metadata.get('license'))
            result += '|%s' % (licensetemplate,)

        if metadata.get('deathyear'):
            result += '|deathyear=%s' % (metadata.get('deathyear'),)

        result += '}}\n'
        return result

    def getCategories(self, metadata):
        """
        Add categories for the collection and creator if available.

        For the collection the fallback tree is:
        1. Category:Paintings in the <collectioncategory>
        2. Category:Paintings in <collectioncategory>
        3. Category:<collectioncategory>

        Only add a creatorcategory if it's available (not the case for anonymous works)
        """
        result = '{{subst:#ifexist:Category:Paintings in the %(collectioncategory)s|[[Category:Paintings in the %(collectioncategory)s]]|{{subst:#ifexist:Category:Paintings in %(collectioncategory)s|[[Category:Paintings in %(collectioncategory)s]]|[[Category:%(collectioncategory)s]]}}}}\n' % metadata
        if metadata.get('creatorcategory'):
            result = result + '{{subst:#ifexist:Category:Paintings by %(creatorcategory)s|[[Category:Paintings by %(creatorcategory)s]]|[[Category:%(creatorcategory)s]]}}' % metadata
        return result

    def getTitle(self, metadata):
        """
        Construct the title to be used for the upload
        """
        formats = { 'Q2195' : u'jpg',
                    #'Q215106' : u'tiff',
                    }
        if not metadata.get('format') or metadata.get('format') not in formats:
            return ''

        metadata['ext'] = formats.get(metadata.get('format'))

        fmt = '%(creatorname)s - %(title)s - %(inv)s - %(collectionLabel)s.%(ext)s'
        title = fmt % metadata
        if len(title) < 200:
            return title
        else:
            title = '%(creatorname)s - ' % metadata
            title = title + metadata.get('title')[0:100].strip()
            title = title + ' - %(inv)s - %(collectionLabel)s.jpg' % metadata
            return title

    def cleanUpTitle(self, title):
        """
        Clean up the title of a potential mediawiki page. Otherwise the title of
        the page might not be allowed by the software.
        """
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

    def getStructuredData(self, metadata):
        """
        Just like getting the description, but now in structured form
        :param metadata:
        :return:
        """
        claims = []

        itemid = metadata.get('item').replace('Q', '')
        # digital representation of -> item
        toclaim = {'mainsnak': { 'snaktype': 'value',
                                 'property': 'P6243',
                                 'datavalue': { 'value': { 'numeric-id': itemid,
                                                           'id' : metadata.get('item'),
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        claims.append(toclaim)
        # depicts -> item
        toclaim = {'mainsnak': { 'snaktype': 'value',
                                 'property': 'P180',
                                 'datavalue': { 'value': { 'numeric-id': itemid,
                                                           'id' : metadata.get('item'),
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        claims.append(toclaim)
        # Source
        toclaim = {'mainsnak': { 'snaktype': 'value',
                                 'property': 'P7482',
                                 'datavalue': { 'value': { 'numeric-id': 74228490,
                                                           'id' : 'Q74228490',
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   'qualifiers' : {'P973' : [ {'snaktype': 'value',
                                               'property': 'P973',
                                               'datavalue': { 'value': metadata.get('sourceurl'),
                                                              'type' : 'string',
                                                              },
                                               } ],
                                   },
                   }
        if metadata.get('operator'):
            operatorid = metadata.get('operator').replace('Q', '')
            toclaim['qualifiers']['P137'] = [ {'snaktype': 'value',
                                               'property': 'P137',
                                               'datavalue': { 'value': { 'numeric-id': operatorid,
                                                                         'id' : metadata.get('operator'),
                                                                         },
                                                              'type' : 'wikibase-entityid',
                                                              },
                                               } ]
        claims.append(toclaim)
        return {'claims' : claims}

    def reportDuplicates(self):
        """
        We might have encountered some duplicates. Publish these so they can be sorted out

        https://commons.wikimedia.org/wiki/Commons:WikiProject_sum_of_all_paintings/To_upload/Duplicates

        :return:
        """
        print (u'Duplicates:')
        print (json.dumps(self.duplicates, indent=4, sort_keys=True))

        pageTitle = u'Commons:WikiProject sum of all paintings/To upload/Duplicates'
        page = pywikibot.Page(self.site, title=pageTitle)

        text = u'{{Commons:WikiProject sum of all paintings/To upload/Duplicates/header}}\n'
        text = text + u'{| class="wikitable sortable"\n'
        text = text + u'! Existing file !! Wikidata item !! Url !! Description\n'
        for duplicate in self.duplicates:
            text = text + u'|-\n'
            text = text + u'| [[File:%(duplicate)s|150px]]\n' % duplicate
            text = text + u'| [[:d:%(qid)s|%(qid)s]]\n' % duplicate
            text = text + u'| [%(sourceurl)s]\n' % duplicate
            text = text + u'|\n<small><nowiki>\n%(description)s\n</nowiki></small>\n' % duplicate
        text = text + u'|}\n'

        summary = u'Found %s duplicates in this bot run' % (len(self.duplicates), )
        pywikibot.output(summary)
        page.put(text, summary)


def main():
    wikidataUploaderBot = WikidataUploaderBot()
    wikidataUploaderBot.run()

if __name__ == "__main__":
    main()
