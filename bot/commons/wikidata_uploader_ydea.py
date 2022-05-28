#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Dedicated bot to upload Yale Digital Dura-Europos Archive (YDEA) images that are all CC0

https://ydea.yale.edu/about-ydea/rights-and-reproductions
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
    A bot to upload YDEA images
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.generatorArtifacts = self.getArtifactGenerator()
        self.site = pywikibot.Site('commons', 'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()
        self.duplicates = []
        self.processeditems = []

    def getArtifactGenerator(self):
        """
        Get the generator of items to upload
        """
        query = """
SELECT ?item ?yaleid ?invnum ?downloadurl ?title ?format WHERE {
  ?item wdt:P8583 ?yaleid ;
        wdt:P195 wd:Q1568434 ;
        wdt:P189 wd:Q464266 ;
        wdt:P6216 wd:Q19652;
        wdt:P217 ?invnum ;
        p:P4765 ?imagestatement .
  ?imagestatement ps:P4765 ?downloadurl ;
                  pq:P1476 ?title ;
                  pq:P2701 ?format ;
                  pq:P275 wd:Q6938433 .                
  }"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        # Just hardcode some of the things here so downstream doesn't change that much

        for resultitem in queryresult:
            resultitem['item'] = resultitem.get('item').replace('http://www.wikidata.org/entity/', '')
            resultitem['format'] = resultitem.get('format').replace('http://www.wikidata.org/entity/', '')
            resultitem['license'] = 'Q6938433' # Everything CC0
            resultitem['operator'] = 'Q1568434' # Yale University Art Gallery
            resultitem['sourceurl'] = 'https://artgallery.yale.edu/collections/objects/%s' % (resultitem.get('yaleid'),)
            yield resultitem

    def run(self):
        """
        Starts the robot.
        """
        for metadata in self.generatorArtifacts:
            self.uploadArtifact(metadata)
        #self.reportDuplicates()

    def uploadArtifact(self, metadata):
        """
        Process the metadata and if suitable, upload the artifact
        """
        pywikibot.output(metadata)
        if metadata.get('item') in self.processeditems:
            pywikibot.output('Already worked on %s, skipping' % (metadata.get('item'),))
            return
        description = self.getDescription(metadata)
        print (description)
        title = self.cleanUpTitle(self.getTitle(metadata))
        print (title)
        if not description or not title:
            return
        pywikibot.output(title)
        pywikibot.output(description)

        # To prevent processing the same item twice:
        self.processeditems.append(metadata.get('item'))
        try:
            response = requests.get(metadata.get('downloadurl'), verify=False) # Museums and valid SSL.....
        except requests.exceptions.ConnectionError:
            pywikibot.output('ERROR: Got a connection error for Wikidata item [[:d:%(item)s]] with url %(downloadurl)s' % metadata)
            return False
        except requests.exceptions.ChunkedEncodingError:
            pywikibot.output('ERROR: Got a chunked encoding error for Wikidata item [[:d:%(item)s]] with url %(downloadurl)s' % metadata)
            return False
        except requests.exceptions.RequestException:
            pywikibot.output('ERROR: Got a requests error for Wikidata item [[:d:%(item)s]] with url %(downloadurl)s' % metadata)
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

                comment = 'Uploading Yale Digital Dura-Europos Archive (YDEA) image based on Wikidata item [[d:Special:EntityPage/%(item)s]] from %(downloadurl)s' % metadata
                try:
                    if filesize > chunkedfilesize:
                        pywikibot.output('File size %s is larger than %s so trying chunked uploading' % (filesize, chunkedfilesize))
                        uploadsuccess = self.site.upload(imagefile, source_filename=t.name, ignore_warnings=True, comment=comment, chunk_size=10000000)
                    else:
                        pywikibot.output('File size %s is smaller than %s so not using chunked uploading' % (filesize, chunkedfilesize))
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
                summary = 'this newly uploaded YDEA file depicts [[d:Special:EntityPage/%s]]' % (metadata.get('item'),)

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
        description = '== {{int:filedesc}} ==\n'
        description += '{{Artwork|wikidata=%(item)s}}\n' % metadata
        description += '\n=={{int:license-header}}==\n'
        description += '{{Yale Digital Dura-Europos Archive}}\n'
        description += '{{Cc-zero}}\n'
        description += '[[Category:Objects from Dura Europos in the Yale University Art Gallery]]\n'
        return description

    def getTitle(self, metadata):
        """
        Construct the title to be used for the upload
        """
        formats = { 'Q2195' : u'jpg',
                    'Q215106' : u'jpg', # They added the wrong qualifier
                    }
        if not metadata.get('format') or metadata.get('format') not in formats:
            return ''

        metadata['ext'] = formats.get(metadata.get('format'))
        fmt = '%(title)s - YDEA - %(yaleid)s.%(ext)s'
        title = fmt % metadata
        if len(title) < 200:
            return title
        else:
            title = metadata.get('title')[0:100].strip()
            title += ' - YDEA - %(yaleid)s.%(ext)s' % metadata
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
        # digital representation of -> item. Also 3D so dropped that part

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

        # copyright status -> dedicated to the public domain
        toclaim = {'mainsnak': { 'snaktype': 'value',
                                 'property': 'P6216',
                                 'datavalue': { 'value': { 'numeric-id': 88088423,
                                                           'id' : 'Q88088423',
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        claims.append(toclaim)

        # copyright license -> CC0
        toclaim = {'mainsnak': { 'snaktype': 'value',
                                 'property': 'P275',
                                 'datavalue': { 'value': { 'numeric-id': 6938433,
                                                           'id' : 'Q6938433',
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
                                   'P8583' : [ {'snaktype': 'value',
                                                'property': 'P8583',
                                                'datavalue': { 'value': metadata.get('yaleid'),
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
