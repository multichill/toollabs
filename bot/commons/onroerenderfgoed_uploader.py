#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to upload onroerenderfgoed.be images.

"""

import pywikibot
import re
import pywikibot.data.sparql
import datetime
import hashlib
import io
import base64
import tempfile
import os
import time
import requests
import json
from html.parser import HTMLParser
from pyproj import Proj, transform

class OnroerendUploaderBot:
    """
    A bot to upload images
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()
        self.generator = generator

    def run(self):
        """
        Starts the robot.
        """
        for metadata in self.generator:
            self.uploadImage(metadata)

    def uploadImage(self, metadata):
        """
        Process the metadata and if suitable, upload the painting
        """
        pywikibot.output(metadata)
        description = self.getDescription(metadata)
        title = self.cleanUpTitle(self.getTitle(metadata))

        pywikibot.output(title)
        pywikibot.output(description)

        try:
            response = requests.get(metadata.get(u'imageurl')) #, verify=False) # Museums and valid SSL.....
        except requests.exceptions.ConnectionError:
            pywikibot.output(u'Got a connection error for [[:d:%(item)s]] with url %(imageurl)s' % metadata)
            return False

        if response.status_code == 200:
            hashObject = hashlib.sha1()
            hashObject.update(response.content)
            sha1base64 = base64.b16encode(hashObject.digest())
            duplicates = list(self.site.allimages(sha1=sha1base64))
            if duplicates:
                return
                pywikibot.output(u'Found a duplicate, trying to add it')
                imagefile = duplicates[0]
                self.addImageToWikidata(metadata, imagefile, summary = u'Adding already uploaded image')
                duplicate = { u'title' : title,
                              u'qid' : metadata.get(u'item'),
                              u'downloadurl' : metadata.get(u'downloadurl'),
                              u'sourceurl' : metadata.get(u'sourceurl'),
                              u'duplicate' : imagefile.title(withNamespace=False),
                              u'description' : description,
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

                imagefile = pywikibot.FilePage(self.site, title=title)
                imagefile.text=description

                comment = u'Uploading onroerenderfboed.be image from %(imageurl)s' % metadata
                try:
                    uploadsuccess = self.site.upload(imagefile, source_filename=t.name, ignore_warnings=True, comment=comment) # chunk_size=1000000)
                except pywikibot.data.api.APIError:
                    pywikibot.output(u'Failed to upload image %(imageurl)s' % metadata)
                    uploadsuccess = False
            if uploadsuccess:
                pywikibot.output('Uploaded a file, now grabbing structured data')
                itemdata = {u'claims' : self.getStructuredData(metadata) }
                #pywikibot.output(json.dumps(itemdata, indent=2))
                #time.sleep(15)
                mediaid = u'M%s' % (imagefile.pageid,)
                summary = u'Adding structured data to this newly uploaded beeldbank.onroerenderfgoed.be image'
                token = self.site.tokens['csrf']
                postdata = {u'action' : u'wbeditentity',
                            u'format' : u'json',
                            u'id' : mediaid,
                            u'data' : json.dumps(itemdata),
                            u'token' : token,
                            u'summary' : summary,
                            u'bot' : True,
                            }

                request = self.site._simple_request(**postdata)
                data = request.submit()
                pywikibot.output(data)

    def getDescription(self, metadata):
        """
        Construct the description for the file to be uploaded
        """
        desc  = '=={{int:filedesc}}==\n'
        desc += '{{Information\n'
        desc += '|description={{nl|%(title)s}}\n' % metadata
        if metadata.get('erfgoedobject'):
            for erfgoedid in metadata.get('erfgoedobject'):
                desc += '{{Onroerend erfgoed|%s}}\n' % (erfgoedid,)
        else:
            desc += '{{Possible onroerend erfgoed'
            if metadata.get('street') and metadata.get('housenumber'):
                desc += '\n| adres = %(street)s %(housenumber)s' % metadata
            if metadata.get('municipality'):
                desc += '\n| plaats = %(municipality)s' % metadata
            if metadata.get('province'):
                desc += '\n| provincie = %(province)s\n' % metadata
            desc += '}}\n'
        if metadata.get('street'):
            desc += '{{Building address\n'
            desc += ' | Street name = %(street)s\n' % metadata
            if metadata.get('housenumber'):
                desc += ' | House number = %(housenumber)s\n' % metadata
            desc += ' | Postal code = \n'
            desc += ' | City = %(municipality)s \n' % metadata
            desc += ' | State = %(province)s \n' % metadata
            desc += ' | Country = BE\n'
            desc += '}}\n'
        if metadata.get('date'):
            desc += '|date=%(date)s\n' % metadata
        else:
            desc += '|date=\n'
        desc += '|source=%(url)s\n' % metadata
        if metadata.get('author'):
            desc += '|author=%(author)s\n' % metadata
        else:
            desc += '|author=\n'
        desc += '|permission=\n'
        desc += '|other_versions=\n'
        desc += '|other_fields=\n'
        desc += '}}\n'
        if metadata.get('coordinatessource'):
            desc += '{{Object location|%(lat)s|%(lon)s|source:%(coordinatessource)s}}\n' % metadata
        desc += '\n=={{int:license-header}}==\n'
        desc += '{{%(license)s}}\n\n' % metadata
        if metadata.get('erfgoedobject'):
            if metadata.get('municipality'):
                desc += '[[Category:Onroerend erfgoed in %(municipality)s]]\n' % metadata
            else:
                desc += '[[Category:Onroerend erfgoed in Flanders]]\n'
        else:
            if metadata.get('municipality'):
                desc += '[[Category:%(municipality)s]]\n' % metadata
            elif metadata.get('province'):
                desc += '[[Category:%(province)s]]\n' % metadata
            else:
                desc += '[[Category:Buildings in Flanders]]\n'
        return desc

    def getTitle(self, metadata):
        """
        Construct the title to be used for the upload
        """
        fmt = u'%(title)s - %(imageid)s - onroerenderfgoed.jpg'
        title = fmt % metadata
        if len(title) < 200:
            return title
        else:
            title = metadata.get(u'title')[0:100].strip()
            title = title + u' - %(imageid)s - onroerenderfgoed.jpg' % metadata
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
        result = []
        # Copyright status -> copyrighted
        toclaim = {'mainsnak': { 'snaktype': 'value',
                                 'property': 'P6216',
                                 'datavalue': { 'value': { 'numeric-id': 50423863,
                                                           'id' : 'Q50423863',
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        result.append(toclaim)
        # License -> cc-by-4.0
        toclaim = {'mainsnak': { 'snaktype': 'value',
                                 'property': 'P275',
                                 'datavalue': { 'value': { 'numeric-id': 20007257,
                                                           'id' : 'Q20007257',
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        result.append(toclaim)
        toclaim = self.getSource(metadata)
        if toclaim:
            result.append(toclaim)
        toclaim = self.getDate(metadata)
        if toclaim:
            result.append(toclaim)
        toclaim = self.getCoordinates(metadata)
        if toclaim:
            result.append(toclaim)
        return result

    def getSource(self, metadata):
        """

        :param metadata:
        :return:
        """

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
                   'qualifiers' : {'P137' : [ {'snaktype': 'value',
                                                'property': 'P137',
                                                'datavalue': { 'value': { 'numeric-id': '3262326',
                                                                          'id' : 'Q3262326',
                                                                          },
                                                               'type' : 'wikibase-entityid',
                                                               },
                                                } ],
                                   'P973' : [ {'snaktype': 'value',
                                                'property': 'P973',
                                                'datavalue': { 'value': metadata.get('url'),
                                                               'type' : 'string',
                                                               },
                                                } ],
                                   },
                   }
        return toclaim

    def getDate(self, metadata):
        """

        :param metadata:
        :return:
        """
        if not metadata.get('date'):
            return False

        dateregex = '(\d\d\d\d-\d\d-\d\d) \d\d:\d\d'
        datematch = re.search(dateregex, metadata.get('date'))
        if datematch:
            date = datematch.group(1)
        else:
            date = metadata.get('date')

        request = self.site._simple_request(action='wbparsevalue', datatype='time', values=date)
        data = request.submit()
        # Not sure if this works or that I get an exception.
        if data.get('error'):
            return False
        postvalue = data.get(u'results')[0].get('value')

        toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': 'P571',
                                 'datavalue': { 'value': postvalue,
                                                'type' : 'time',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        return toclaim

    def getCoordinates(self, metadata):
        """

        :param metadata:
        :return:
        """
        if not metadata.get('coordinatessource'):
            return False

        toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': 'P9149',
                                 'datavalue': { 'value': { 'latitude': metadata.get('lat'),
                                                           'longitude':metadata.get('lon'),
                                                           'altitude': None,
                                                           'precision':1.0e-6,
                                                           'globe':'http://www.wikidata.org/entity/Q2'},
                                                'type' : 'globecoordinate',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        return toclaim

def getOnroerenderfgoedGenerator(startpage=1):
    """
    You can force it to spit out JSON:
curl 'https://beeldb2F4.0%2F&page=1629' -H 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:72.0) Gecko/20100101 Firefox/72.0' -H 'Accept: application/json' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'Referer: https://inventaris.onroerenderfgoed.be/erfgoedobjecten/56629' -H 'Content-Type: application/json' -H 'Cache-Control: no-cache,no-store, max-age=0' -H 'Origin: https://inventaris.onroerenderfgoed.be' -H 'Connection: keep-alive'
curl 'https://beeldbank.onroerenderfgoed.be/images/27869' -H 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:72.0) Gecko/20100101 Firefox/72.0' -H 'Accept: application/json' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'Referer: https://inventaris.onroerenderfgoed.be/erfgoedobjecten/56629' -H 'Content-Type: application/json' -H 'Cache-Control: no-cache,no-store, max-age=0' -H 'Origin: https://inventaris.onroerenderfgoed.be' -H 'Connection: keep-alive'

    :param startpage:
    :return:
    """
    htmlparser = HTMLParser()
    endpage = 19643
    for i in range(startpage, endpage):
        searchurl = 'https://beeldbank.onroerenderfgoed.be/images?license=https%%3A%%2F%%2Fcreativecommons.org%%2Flicenses%%2Fby%%2F4.0%%2F&page=%s' % (i,)
        try:
            searchpage = requests.get(searchurl)
        except requests.exceptions.ConnectionError:
            pywikibot.output(u'Got a connection error on %s. Sleeping 5 minutes' (searchurl,))
            time.sleep(300)
            searchpage = requests.get(searchurl)
        itemidregex = '\<img src\=\"[\s\t\r\n]*\/images\/(\d+)[\s\t\r\n]*\/content\/square\"\>'
        matches = re.finditer(itemidregex, searchpage.text)
        for match in matches:
            metadata = {}
            metadata['license'] = 'Cc-by-4.0'
            metadata['licenseqid'] = 'Q20007257'

            imageid = match.group(1)
            url = 'https://beeldbank.onroerenderfgoed.be/images/%s' % (imageid,)

            pywikibot.output (searchurl)
            pywikibot.output (url)
            metadata['imageid'] = imageid
            metadata['url'] = 'https://id.erfgoed.net/afbeeldingen/%s' % (imageid,)
            metadata['imageurl'] = 'https://beeldbank.onroerenderfgoed.be/images/%s/content/original' % (imageid,)

            try:
                itempage = requests.get(url)
            except requests.exceptions.ConnectionError:
                pywikibot.output(u'Got a connection error on %s. Sleeping 5 minutes' % (url,))
                time.sleep(300)
                itempage = requests.get(url)

            titleregex = '\<dl class\=\"caption-info\"\>[\s\t\r\n]*\\<dd\>Titel\<\/dd\>[\s\t\r\n]*\<dt\>([^\<]+)\<\/dt\>'

            titlematch = re.search(titleregex, itempage.text)
            # Sometimes we get a weird page
            if not titlematch:
                pywikibot.output(u'Title did not match on %s. Sleeping 5 minutes' % (url,))
                time.sleep(300)
                itempage = requests.get(url)
                titlematch = re.search(titleregex, itempage.text)

            metadata['title'] = htmlparser.unescape(titlematch.group(1)).strip()

            dateregex = '\<dd\>Datum opname\<\/dd\>[\s\t\r\n]*\<dt\>[\s\t\r\n]*(?P<day>\d\d)-(?P<month>\d\d)-(?P<year>\d\d\d\d)\s*(?P<hour>\d\d)\:(?P<minute>\d\d)[\s\t\r\n]*\<\/dt\>'
            datematch = re.search(dateregex, itempage.text)

            if datematch:
                if datematch.group('minute')=='00' and datematch.group('hour')=='00' and datematch.group('day')=='01' and datematch.group('month')=='01':
                    metadata['date'] = datematch.group('year')
                elif datematch.group('minute')=='00' and datematch.group('hour')=='00' and datematch.group('day')=='01':
                    metadata['date'] = '%s-%s' % (datematch.group('year'), datematch.group('month'))
                else:
                    metadata['date'] = '%s-%s-%s %s:%s' % (datematch.group('year'), datematch.group('month'), datematch.group('day'), datematch.group('hour'), datematch.group('minute'))

            authorregex = '\<dd\>Fotograaf\<\/dd\>[\s\t\r\n]*\<dt\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/dt\>'
            authormatch = re.search(authorregex, itempage.text)
            if authormatch:
                metadata['author'] = htmlparser.unescape(authormatch.group(1)).strip()

            addressregex = '\<dd\>Adres\<\/dd\>[\s\t\r\n]*\<dt\>[\s\t\r\n]*\<ul class\=\"nodisk\"\>[\s\t\r\n]*\<li\>[\s\t\r\n]*Provincie\:[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/li\>[\s\t\r\n]*\<li\>[\s\t\r\n]*Gemeente\:[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/li\>[\s\t\r\n]*\<li\>[\s\t\r\n]*Straat\:[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/li\>[\s\t\r\n]*\<li\>[\s\t\r\n]*Nummer\:[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/li\>[\s\t\r\n]*\<\/ul\>[\s\t\r\n]*\<\/dt\>'
            addressmatch = re.search(addressregex, itempage.text)
            if addressmatch:
                metadata['province'] = htmlparser.unescape(addressmatch.group(1).strip())
                metadata['municipality'] = htmlparser.unescape(addressmatch.group(2).strip())
                if addressmatch.group(3).strip()!='/':
                    metadata['street'] = htmlparser.unescape(addressmatch.group(3).strip())
                #print (addressmatch.group(2).strip())
                #print (addressmatch.group(3).strip())
                if addressmatch.group(4).strip()!='/':
                    metadata['housenumber'] = addressmatch.group(4).strip()

            erfgoedobjectregex = '\{\"uri\"\:\s*\"https\:\/\/id\.erfgoed\.net\/erfgoedobjecten\/(\d+)\"\}'
            erfgoedobjectmatches = re.finditer(erfgoedobjectregex, itempage.text)

            metadata['erfgoedobject'] = []
            for erfgoedobjectmatch in erfgoedobjectmatches:
                metadata['erfgoedobject'].append(erfgoedobjectmatch.group(1))



                print (erfgoedobjectmatch.group(1))


            pointregex = 'var point\s*\=\s*JSON\.parse\(\'\{\"coordinates\"\:\s*\[(?P<x>\d+(\.\d+)?), (?P<y>\d+(\.\d+)?)\], \"crs\"\:\s*\{\"properties\"\: \{\"name\"\: \"urn\:ogc\:def\:crs\:EPSG\:\:31370\"\}, \"type\"\: \"name\"\}\, \"type\"\: \"Point\"\}\'\)'
            pointmatch = re.search(pointregex, itempage.text)
            if pointmatch:
                print ('%s %s' % (pointmatch.group('x'), pointmatch.group('y')))
                metadata['coordinatessource'] = 'epsg:31370 %s, %s' % (pointmatch.group('x'), pointmatch.group('y'))
                sourceProj = Proj('epsg:31370')
                outputProj = Proj('epsg:4326')
                lat,lon = transform(sourceProj,outputProj,float(pointmatch.group('x')),float(pointmatch.group('y')))
                print ('https://www.openstreetmap.org/#map=15/%s/%s' % (lat, lon,))
                metadata['lat'] = lat
                metadata['lon'] = lon

            yield metadata


def main():
    generator = getOnroerenderfgoedGenerator()
    #for page in generator:
    #    print (page)
    onroerendUploaderBot = OnroerendUploaderBot(generator)
    onroerendUploaderBot.run()

if __name__ == "__main__":
    main()
