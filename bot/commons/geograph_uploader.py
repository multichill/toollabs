#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to upload https://www.geograph.org.uk/ images.

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
import math
from html.parser import HTMLParser
from pyproj import Proj, transform

class GeographUploaderBot:
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
        metadata = self.reverseGeocode(metadata)
        description = self.getDescription(metadata)
        title = self.cleanUpTitle(self.getTitle(metadata))

        #pywikibot.output(title)
        #pywikibot.output(description)

        try:
            response = requests.get(metadata.get(u'imageurl'))
        except requests.exceptions.ConnectionError:
            pywikibot.output(u'Got a connection error for [[:d:%(item)s]] with url %(imageurl)s' % metadata)
            return False

        print (title)
        print (json.dumps(metadata, sort_keys=True, indent=4))
        print (description)
        print (json.dumps(self.getStructuredData(metadata), sort_keys=True, indent=4))



        if response.status_code == 200:
            hashObject = hashlib.sha1()
            hashObject.update(response.content)
            sha1base64 = base64.b16encode(hashObject.digest())
            duplicates = list(self.site.allimages(sha1=sha1base64))
            if duplicates:
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
                if imagefile.exists():
                    # If it exists, it already got uploaded
                    return
                imagefile.text=description

                comment = u'Uploading geograph.org.uk image from %(imageurl)s' % metadata
                try:
                    uploadsuccess = self.site.upload(imagefile, source_filename=t.name, ignore_warnings=True, comment=comment) # chunk_size=1000000)
                except pywikibot.data.api.APIError:
                    pywikibot.output(u'Failed to upload image %(imageurl)s' % metadata)
                    uploadsuccess = False
            if uploadsuccess:
                pywikibot.output('Uploaded a file, now grabbing structured data')
                itemdata = {u'claims' : self.getStructuredData(metadata) }
                # Also add the title
                #if metadata.get('title'):
                #    itemdata['labels']
                #pywikibot.output(json.dumps(itemdata, indent=2))
                time.sleep(5)
                imagefile.get(force=True)
                mediaid = u'M%s' % (imagefile.pageid,)
                print (mediaid)
                summary = u'Adding structured data to this newly uploaded geograph.org.uk image'
                token = self.site.tokens['csrf']
                postdata = {u'action' : u'wbeditentity',
                            u'format' : u'json',
                            u'id' : mediaid,
                            u'data' : json.dumps(itemdata),
                            u'token' : token,
                            u'summary' : summary,
                            u'bot' : True,
                            }
                print (json.dumps(postdata, sort_keys=True, indent=4))
                request = self.site._simple_request(**postdata)
                data = request.submit()
                pywikibot.output(data)

    def reverseGeocode(self, metadata):
        """
        Do reverse geocoding based on the metadata and return the metadata with extra fields
        :param metadata:
        :return:
        """
        result = metadata
        url = 'http://edwardbetts.com/geocode/?lat=%s&lon=%s' % (metadata.get('object_lat'), metadata.get('object_lon'))
        page = requests.get(url)
        json = page.json()
        print (json)
        if json.get('missing'):
            return result
        if json.get('wikidata'):
            result['locationqid'] = json.get('wikidata')
        if json.get('commons_cat') and json.get('commons_cat').get('title'):
            result['commonscat'] = json.get('commons_cat').get('title')
        return result

    def getDescription(self, metadata):
        """
        Construct the description for the file to be uploaded
        """
        desc  = '{{Geograph from structured data}}\n'
        if metadata.get('commonscat'):
            desc += '[[Category:%s]]\n' % (metadata.get('commonscat'),)
        else:
            desc += '{{Subst:Unc}}\n'
        return desc

    def getTitle(self, metadata):
        """
        Construct the title to be used for the upload
        """
        fmt = u'%(title)s - geograph.org.uk - %(id)s.jpg'
        title = fmt % metadata
        if len(title) < 200:
            return title
        else:
            title = metadata.get(u'title')[0:100].strip()
            title = title + u' - geograph.org.uk - %(id)s.jpg' % metadata
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
        # License -> cc-by-2.0
        toclaim = {'mainsnak': { 'snaktype': 'value',
                                 'property': 'P275',
                                 'datavalue': { 'value': { 'numeric-id': 19068220,
                                                           'id' : 'Q19068220',
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
        toclaim = self.getAuthor(metadata)
        if toclaim:
            result.append(toclaim)
        toclaim = self.getDate(metadata)
        if toclaim:
            result.append(toclaim)
        toclaim = self.getPhotographerCoordinates(metadata)
        if toclaim:
            result.append(toclaim)
        toclaim = self.getObjectCoordinates(metadata)
        if toclaim:
            result.append(toclaim)
        # TODO: Add depicts and location
        return result

    def getSource(self, metadata):
        """

        :param metadata:
        :return:
        """
        geographid = metadata.get('id')
        geographUrl = u'https://www.geograph.org.uk/photo/%s' % (geographid, )
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
                                               'datavalue': { 'value': { 'numeric-id': '1503119',
                                                                         'id' : 'Q1503119',
                                                                         },
                                                              'type' : 'wikibase-entityid',
                                                              },
                                               } ],
                                   'P7384' : [ {'snaktype': 'value',
                                                'property': 'P7384',
                                                'datavalue': { 'value': geographid,
                                                               'type' : 'string',
                                                               },
                                                } ],
                                   'P973' : [ {'snaktype': 'value',
                                               'property': 'P973',
                                               'datavalue': { 'value': geographUrl,
                                                              'type' : 'string',
                                                              },
                                               } ],
                                   },
                   }
        return toclaim

    def getAuthor(self, metadata):
        """
        Construct the structured author to add if it isn't in the currentdata
        :param authorUrl: The url pointing to the author on Geograph
        :param authorName: The name of the author
        :return: List of dicts
        """
        authorUrl = 'https://www.geograph.org.uk/profile/%s' % (metadata.get('user_id'))

        toclaim = {'mainsnak': { 'snaktype':'somevalue',
                                 'property': 'P170',
                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   'qualifiers' : {'P3831' : [ {'snaktype': 'value',
                                                'property': 'P3831',
                                                'datavalue': { 'value': { 'numeric-id': '33231',
                                                                          'id' : 'Q33231',
                                                                          },
                                                               'type' : 'wikibase-entityid',
                                                               },
                                                } ],
                                   'P2093' : [ {'snaktype': 'value',
                                                'property': 'P2093',
                                                'datavalue': { 'value': metadata.get('realname'),
                                                               'type' : 'string',
                                                               },
                                                } ],
                                   'P2699' : [ {'snaktype': 'value',
                                                'property': 'P2699',
                                                'datavalue': { 'value': authorUrl,
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

        dateregex = '(\d\d\d\d-\d\d-\d\d)'
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

    def getPhotographerCoordinates(self, metadata):
        """

        :param metadata:
        :return:
        """
        if not metadata.get('photographer_lat') or not metadata.get('photographer_lon'):
            return False

        toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': 'P1259',
                                 'datavalue': { 'value': { 'latitude': metadata.get('photographer_lat'),
                                                           'longitude':metadata.get('photographer_lon'),
                                                           'altitude': None,
                                                           'precision':1.0e-6,
                                                           'globe':'http://www.wikidata.org/entity/Q2'},
                                                'type' : 'globecoordinate',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        if metadata.get('direction') and not metadata.get('direction')=='0':
            toclaim['qualifiers'] = {'P7787' : [ {'snaktype': 'value',
                                                  'property': 'P7787',
                                                  'datavalue': { 'value': { 'amount': '+%s' % (metadata.get('direction'),),
                                                                            'unit' : 'http://www.wikidata.org/entity/Q28390',
                                                                            },
                                                                 'type' : 'quantity',
                                                                 },
                                                  },
                                                 ],
                                     }
        return toclaim

    def getObjectCoordinates(self, metadata):
        """

        :param metadata:
        :return:
        """
        if not metadata.get('object_lat') or not metadata.get('object_lon'):
            return False

        toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': 'P625',
                                 'datavalue': { 'value': { 'latitude': metadata.get('object_lat'),
                                                           'longitude':metadata.get('object_lon'),
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

def getFilteredGeographGenerator(startid, endid):
    """
    Get files from Geograph, but filtered to only return id's we don't already have on Commons
    :param startid: Integer to start with
    :param endid: Integer to end with
    :return: Yields metadata
    """
    toskiplist = []
    lastmetadata = None
    commonsgenerator = getCommonsGeographIdGenerator(startid, endid)
    for toskip in commonsgenerator:
        toskiplist.append(toskip)
    #return
    geographgenerator = getGeographGenerator(startid, endid)
    for metadata in geographgenerator:
        if int(metadata.get('id')) not in toskiplist:
            yield metadata
    return
    """
    # Could probably do something with two generators running together
    for toskip in commonsgenerator:
        toskiplist.append(toskip)
        print (toskip)
        #print (toskiplist)
        if lastmetadata:
            if int(lastmetadata.get('id')) > toskip:
                continue
            elif int(lastmetadata.get('id'))==toskip:
                lastmetadata = None
                continue
            elif int(metadata.get('id')) not in toskiplist:
                print (u'To skip %s, to return %s' % (toskip, metadata.get('id')))
                yield metadata
                lastmetadata = None
        else:
            for metadata in geographgenerator:
                if int(metadata.get('id')) > toskip:
                    lastmetadata = metadata
                    break
                elif int(metadata.get('id'))==toskip:
                    lastmetadata = None
                    break
                elif int(metadata.get('id')) not in toskiplist:
                    print (u'To skip %s, to return %s' % (toskip, metadata.get('id')))
                    yield metadata
                    lastmetadata = None
    print (toskiplist)
    """

def getCommonsGeographIdGenerator(startid, endid):
    """
    Get a generator giving the id's of Geograph files currently on Commons
    :param startid: Id to start at
    :param endid: Id to end at
    :return:
    """
    site = pywikibot.Site(u'commons', u'commons')
    category = pywikibot.Category(site, title='Images_from_Geograph_Britain_and_Ireland')
    startprefix = ' %s' % (str(startid).zfill(8),)
    endprefix = ' %s' % (str(endid).zfill(8),)
    idregex = u'^File\:.+ - geograph\.org\.uk - (\d+)\.jpg$'
    sloppyidregex =u'^File:[^\d]*(\d+)[^\d]*\.jpg'
    for filepage in category.articles(content=False, namespaces=6, startprefix=startprefix): #, endprefix=endprefix):
        titlematch = re.match(idregex, filepage.title())
        sloppytitlematch = re.match(sloppyidregex, filepage.title())
        if titlematch:
            identifier = int(titlematch.group(1))
            yield identifier
        elif sloppytitlematch and startid < int(sloppytitlematch.group(1)) < endid:
            identifier = int(sloppytitlematch.group(1))
            yield identifier
        else:
            templateregex = u'\{\{[gG]eograph\|(\d+)\|[^\}]+\}\}'
            alsotemplateregex = u'\{\{[aA]lso[ _]geograph\|(\d+)\}\}'
            templatematch = re.search(templateregex, filepage.text)
            alsotemplatematch = re.search(alsotemplateregex, filepage.text)
            if templatematch:
                identifier = int(templatematch.group(1))
                yield identifier
            elif alsotemplatematch:
                identifier = int(alsotemplatematch.group(1))
                yield identifier

        # Break out when identifier is higher than what we're looking for
        if identifier > endid:
            return

def getGeographGenerator(startid, endid):
    """
    :param startpage:
    :return:
    """
    htmlparser = HTMLParser()
    limit = 100

    for i in range(startid, endid, limit):
        searchurl = 'http://api.geograph.org.uk/api-facetql.php?select=*&limit=%s&where=id+between+%s+and+%s' % (limit, i, min(i+limit,endid))
        try:
            searchpage = requests.get(searchurl)
        except requests.exceptions.ConnectionError:
            pywikibot.output(u'Got a connection error on %s. Sleeping 5 minutes' (searchurl,))
            time.sleep(300)
            searchpage = requests.get(searchurl)
        for row in searchpage.json().get('rows'):
            metadata = row
            metadata['imageurl'] = u'https://www.geograph.org.uk/reuse.php?id=%s&download=%s&size=largest' % (row.get('id'), row.get('hash'))

            if row.get('takenday'):
                dateregex = '^(\d\d\d\d)(\d\d)(\d\d)$'
                datematch = re.match(dateregex, row.get('takenday'))
                if datematch:
                    row['date'] = '%s-%s-%s' % (datematch.group(1), datematch.group(2), datematch.group(3), )

            if row.get('vlat'):
                metadata['photographer_lat'] = math.degrees(float(row.get('vlat')))
            if row.get('vlong'):
                metadata['photographer_lon'] = math.degrees(float(row.get('vlong')))
            if row.get('wgs84_lat'):
                metadata['object_lat'] = math.degrees(float(row.get('wgs84_lat')))
            if row.get('wgs84_long'):
                metadata['object_lon'] = math.degrees(float(row.get('wgs84_long')))

            yield row
    return

def main(*args):
    startid = None
    endid = None
    for arg in pywikibot.handle_args(args):
        if arg.startswith('-startid:'):
            if len(arg) == 9:
                startid = pywikibot.input(
                    u'Please enter the start identifier you want to work on:')
            else:
                startid = arg[9:]
        elif arg.startswith('-endid:'):
            if len(arg) == 7:
                endid = pywikibot.input(
                    u'Please enter the start identifier you want to work on:')
            else:
                endid = arg[7:]
        #elif genFactory.handleArg(arg):
        #    continue

    if not startid or not endid:
        pywikibot.output('Need startid and endid')
        return
    generator = getFilteredGeographGenerator(int(startid), int(endid),)
    #for page in generator:
    #    print (json.dumps(page, sort_keys=True, indent=4))
    geographUploaderBot = GeographUploaderBot(generator)
    geographUploaderBot.run()

if __name__ == "__main__":
    main()
