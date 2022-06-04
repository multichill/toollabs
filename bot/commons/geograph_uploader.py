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
import csv
from contextlib import closing
from html.parser import HTMLParser
#from pyproj import Proj, transform

class GeographUploaderBot:
    """
    A bot to upload images
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.site = pywikibot.Site('commons', 'commons')
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
        pywikibot.debug(metadata, 'bot')
        description = self.getDescription(metadata)
        title = self.cleanUpTitle(self.getTitle(metadata))

        #pywikibot.output(title)
        #pywikibot.output(description)

        try:
            response = requests.get(metadata.get('imageurl'))
        except requests.exceptions.ConnectionError:
            pywikibot.output('Got a connection error for %(imageurl)s' % metadata)
            return False

        pywikibot.output ('Ready to upload %s' % (title,))
        #print (json.dumps(metadata, sort_keys=True, indent=4))
        #print (description)
        #print (json.dumps(self.getStructuredData(metadata), sort_keys=True, indent=4))

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

                comment = 'Uploading geograph.org.uk image from %(sourceurl)s' % metadata
                pywikibot.output(comment)
                try:
                    uploadsuccess = self.site.upload(imagefile, source_filename=t.name, ignore_warnings=True, comment=comment) # chunk_size=1000000)
                except pywikibot.exceptions.APIError:
                    # Sometimes we have a time out, but file was uploaded. Bot will get an API error on retry
                    try:
                        # Check if the file exists or not
                        imagefile.get(force=True)
                        uploadsuccess = True
                        pywikibot.output('Got an API error, but looks like uploading worked for %(imageurl)s' % metadata)
                    except pywikibot.exceptions.NoPage:
                        # The upload really failed
                        pywikibot.output('Failed to upload image %(imageurl)s' % metadata)
                        uploadsuccess = False
                        # Grab a new token
                        time.sleep(30)
                        self. site.tokens.load_tokens(['csrf'])
            if uploadsuccess:
                pywikibot.output('Uploaded a file, now grabbing structured data')
                itemdata = self.getStructuredData(metadata)
                # Also add the title
                #if metadata.get('title'):
                #    itemdata['labels']
                #pywikibot.output(json.dumps(itemdata, indent=2))
                time.sleep(5)
                imagefile.get(force=True)
                mediaid = 'M%s' % (imagefile.pageid,)
                pywikibot.debug(mediaid, 'bot')
                summary = 'Adding structured data to this newly uploaded geograph.org.uk image'
                token = self.site.tokens['csrf']
                postdata = {'action' : 'wbeditentity',
                            'format' : 'json',
                            'id' : mediaid,
                            'data' : json.dumps(itemdata),
                            'token' : token,
                            'summary' : summary,
                            'bot' : True,
                            }
                pywikibot.debug(json.dumps(postdata, sort_keys=True, indent=4), 'bot')
                request = self.site.simple_request(**postdata)
                try:
                    data = request.submit()
                    pywikibot.debug(data,  'bot')
                    # A gentle touch to show the structured data we just added
                    #imagefile.touch() # Keeps getting broken
                    imagefile.put(imagefile.text)
                except (pywikibot.exceptions.APIError, pywikibot.exceptions.OtherPageSaveError):
                    pywikibot.output('Got an API error while saving page. Sleeping, getting a new token and retrying')
                    time.sleep(30)
                    self. site.tokens.load_tokens(['csrf'])
                    postdata['token'] = self.site.tokens['csrf']
                    request = self.site.simple_request(**postdata)
                    data = request.submit()
                    imagefile.put(imagefile.text)

    def getDescription(self, metadata):
        """
        Construct the description for the file to be uploaded
        """
        desc  = '{{Geograph from structured data}}\n'
        if metadata.get('commonscat'):
            desc += '[[Category:%s]]\n' % (metadata.get('commonscat'),)
            if metadata.get('objectcommonscat') and metadata.get('objectcommonscat')!=metadata.get('commonscat'):
                desc += '[[Category:%s]]\n' % (metadata.get('objectcommonscat'),)
        elif metadata.get('objectcommonscat'):
            desc += '[[Category:%s]]\n' % (metadata.get('objectcommonscat'),)
        else:
            desc += '{{Uncategorized-Geograph|year={{subst:CURRENTYEAR}}|month={{subst:CURRENTMONTHNAME}}|day={{subst:CURRENTDAY}}|gridref=%s}}\n' % (metadata.get('grid_reference'))
        return desc

    def getTitle(self, metadata):
        """
        Construct the title to be used for the upload
        """
        fmt = '%(title)s - geograph.org.uk - %(id)s.jpg'
        title = fmt % metadata
        if len(title) < 200:
            return title
        else:
            title = metadata.get('title')[0:100].strip()
            title = title + ' - geograph.org.uk - %(id)s.jpg' % metadata
            return title

    def cleanUpTitle(self, title):
        """
        Clean up the title of a potential mediawiki page. Otherwise the title of
        the page might not be allowed by the software.
        """
        title = title.strip()
        title = re.sub("[<{\\[]", "(", title)
        title = re.sub("[>}\\]]", ")", title)
        title = re.sub("[ _]?\\(!\\)", "", title)
        title = re.sub(",:[ _]", ", ", title)
        title = re.sub("[;:][ _]", ", ", title)
        title = re.sub("[\t\n ]+", " ", title)
        title = re.sub("[\r\n ]+", " ", title)
        title = re.sub("[\n]+", "", title)
        title = re.sub("[?!]([.\"]|$)", "\\1", title)
        title = re.sub("[&#%?!]", "^", title)
        title = re.sub("[\|]", "^", title)
        title = re.sub("[;]", ",", title)
        title = re.sub("[/+\\\\:]", "-", title)
        title = re.sub("--+", "-", title)
        title = re.sub(",,+", ",", title)
        title = re.sub("''+", "\"", title)
        title = re.sub("[-,^]([.]|$)", "\\1", title)
        title = re.sub("^- ", "", title)
        title = title.replace(" ", "_")
        return title

    def getStructuredData(self, metadata):
        """
        Just like getting the description, but now in structured form
        :param metadata:
        :return:
        """
        result = {}
        if metadata.get('title'):
            result['labels'] = {'en' : { 'language' : 'en',
                                         'value' : metadata.get('title').strip(),
                                         }
                                }
        claims = []
        # Instance of -> photograph
        toclaim = {'mainsnak': { 'snaktype': 'value',
                                 'property': 'P31',
                                 'datavalue': { 'value': { 'numeric-id': 125191,
                                                           'id' : 'Q125191',
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        claims.append(toclaim)
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
        claims.append(toclaim)
        toclaim = self.getLicense(metadata)
        if toclaim:
            claims.append(toclaim)
        toclaim = self.getSource(metadata)
        if toclaim:
            claims.append(toclaim)
        toclaim = self.getAuthor(metadata)
        if toclaim:
            claims.append(toclaim)
        toclaim = self.getDate(metadata)
        if toclaim:
            claims.append(toclaim)
        toclaim = self.getPhotographerCoordinates(metadata)
        if toclaim:
            claims.append(toclaim)
        toclaim = self.getObjectCoordinates(metadata)
        if toclaim:
            claims.append(toclaim)
        toclaims = self.getDepicts(metadata)
        if toclaims:
            claims.extend(toclaims)
        toclaim = self.getLocation(metadata)
        if toclaim:
            claims.append(toclaim)
        result['claims'] = claims
        return result

    def getLicense(self, metadata):
        """
        Get the license (cc-by-2.0) with the title and author name qualifiers
        :param metadata:
        :return:
        """
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
                   'qualifiers' : {'P1476' : [ {'snaktype': 'value',
                                                'property': 'P1476',
                                                'datavalue': { 'value': { 'text': metadata.get('title').strip(),
                                                                          'language' : 'en',
                                                                          },
                                                               'type' : 'monolingualtext',
                                                               },
                                                } ],
                                   'P2093' : [ {'snaktype': 'value',
                                                'property': 'P2093',
                                                'datavalue': { 'value': metadata.get('realname').strip(),
                                                               'type' : 'string',
                                                               },
                                                } ],

                                   },
                   }
        return toclaim

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
                                               'datavalue': { 'value': { 'numeric-id': '1503119',
                                                                         'id' : 'Q1503119',
                                                                         },
                                                              'type' : 'wikibase-entityid',
                                                              },
                                               } ],
                                   'P7384' : [ {'snaktype': 'value',
                                                'property': 'P7384',
                                                'datavalue': { 'value': metadata.get('id'),
                                                               'type' : 'string',
                                                               },
                                                } ],
                                   'P973' : [ {'snaktype': 'value',
                                               'property': 'P973',
                                               'datavalue': { 'value': metadata.get('sourceurl'),
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
                                                'datavalue': { 'value': metadata.get('realname').strip(),
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

        request = self.site.simple_request(action='wbparsevalue', datatype='time', values=date)
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
        if not metadata.get('photographer_lat') or not metadata.get('photographer_lon') or not metadata.get('photographer_precision'):
            return False

        toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': 'P1259',
                                 'datavalue': { 'value': { 'latitude': metadata.get('photographer_lat'),
                                                           'longitude':metadata.get('photographer_lon'),
                                                           'altitude': None,
                                                           'precision': metadata.get('photographer_precision'),
                                                           'globe':'http://www.wikidata.org/entity/Q2'},
                                                'type' : 'globecoordinate',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        if metadata.get('direction') and not metadata.get('direction')=='Unknown' and not metadata.get('direction')=='0':
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
        if not metadata.get('object_lat') or not metadata.get('object_lon') or not metadata.get('object_precision'):
            return False

        toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': 'P9149',
                                 'datavalue': { 'value': { 'latitude': metadata.get('object_lat'),
                                                           'longitude':metadata.get('object_lon'),
                                                           'altitude': None,
                                                           'precision': metadata.get('object_precision'),
                                                           'globe':'http://www.wikidata.org/entity/Q2'},
                                                'type' : 'globecoordinate',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        return toclaim

    def getDepicts(self, metadata):
        """

        :param metadata:
        :return:
        """
        if not metadata.get('depictsqids'):
            return False

        result = []
        for depictsqid in metadata.get('depictsqids'):
            toclaim = {'mainsnak': { 'snaktype': 'value',
                                     'property': 'P180',
                                     'datavalue': { 'value': { 'numeric-id': depictsqid.replace('Q', ''),
                                                               'id' : depictsqid,
                                                               },
                                                    'type' : 'wikibase-entityid',
                                                    }

                                     },
                       'type': 'statement',
                       'rank': 'normal',
                       }
            result.append(toclaim)
        return result

    def getLocation(self, metadata):
        """

        :param metadata:
        :return:
        """
        if not metadata.get('locationqid'):
            return False

        toclaim = {'mainsnak': { 'snaktype': 'value',
                                 'property': 'P1071',
                                 'datavalue': { 'value': { 'numeric-id': metadata.get('locationqid').replace('Q', ''),
                                                           'id' : metadata.get('locationqid'),
                                                           },
                                                'type' : 'wikibase-entityid',
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
    commonsgenerator = getCommonsGeographIdGenerator(startid, endid)
    geographgenerator = getGeographGenerator(startid, endid)

    toskiplist = []
    for toskip in commonsgenerator:
        toskiplist.append(toskip)

    for metadata in geographgenerator:
        if int(metadata.get('id')) not in toskiplist:
            # Reverse geocoding is slow so only do it on images likely to be uploaded
            yield addReverseGeocodingMetadata(metadata)
    return

def addReverseGeocodingMetadata(metadata):
    """
    Do reverse geocoding on the metadata and return the result
    :param metadata: Geograph metadata
    :return: Metadata expanded with the reverse geocoding
    """
    if metadata.get('photographer_lat') and metadata.get('photographer_lon'):
        (locationqid, locationcc) = reverseGeocode(metadata.get('photographer_lat'), metadata.get('photographer_lon'), )
        if locationqid:
            metadata['locationqid'] = locationqid
        if locationcc:
            metadata['commonscat'] = locationcc

    if metadata.get('object_lat') and metadata.get('object_lon'):
        (objectqid, objectcc) = reverseGeocode(metadata.get('object_lat'), metadata.get('object_lon'), )
        if objectqid:
            if not metadata.get('locationqid'):
                metadata['locationqid'] = objectqid
            metadata['depictsqids'].append(objectqid)
        if objectcc:
            metadata['objectcommonscat'] = objectcc
    return metadata

def reverseGeocode(lat, lon, tries=3):
    """
    Do reverse geocoding based on latitude & longitude and return Wikidata item and Commons category
    :param lat: The latitude
    :parim lon: The longitude
    :return: Tuple of Wikidata item and Commons category
    """
    qid = None
    commonscat = None

    url = 'http://edwardbetts.com/geocode/?lat=%s&lon=%s' % (lat, lon)
    try:
        page = requests.get(url)
        jsondata = page.json()
    except ValueError:
        # Either json.decoder.JSONDecodeError or simplejson.scanner.JSONDecodeError, both subclass of ValueError
        pywikibot.output('Got invalid json at %s' % (url,))
        time.sleep(60)
        if tries > 0:
            return reverseGeocode(lat, lon, tries=tries-1)
        return (qid, commonscat)
    except IOError:
        # RequestExceptions was thrown
        pywikibot.output('Got an IOError at %s' % (url,))
        time.sleep(60)
        if tries > 0:
            return reverseGeocode(lat, lon, tries=tries-1)
        return (qid, commonscat)

    if not jsondata.get('missing'):
        if jsondata.get('wikidata'):
            qid = jsondata.get('wikidata')
        if jsondata.get('commons_cat') and jsondata.get('commons_cat').get('title'):
            commonscat = jsondata.get('commons_cat').get('title')
    return (qid, commonscat)

def getGeographResumeGenerator(resumephoto=None, backphotos=1000, newphotos=10000):
    """
    Resume the upload
    :param resumephoto: The id of the last uploaded photo. If set to None, the latest upload is used
    :param backphotos: The number of photos to look back for resuming
    :param newphotos: The number of new photos to upload

    :return: The generator that can be used by GeographUploaderBot
    """
    if not resumephoto:
        site = pywikibot.Site('commons', 'commons')
        user = pywikibot.User(site, 'GeographBot')
        (lastfile, lasttimestamp, lastcomment, lastexists) = list((user.uploadedImages(total=1)))[0]
        idregex = u'^File\:.+ - geograph\.org\.uk - (\d+)\.jpg$'
        titlematch = re.match(idregex, lastfile.title())
        if titlematch:
            resumephoto = int(titlematch.group(1))
    # Should have it now
    if resumephoto:
        return getFilteredGeographGenerator(int(resumephoto)-int(backphotos), int(resumephoto)+int(newphotos),)

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
    idregex = u'^File\:.+ - geograph\.org\.uk - (\d+)\.jpg$'
    sloppyidregex =u'^File:[^\d]*(\d+)[^\d]*\.jpg'
    for filepage in category.articles(content=False, namespaces=6, startprefix=startprefix):
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
    tags = getGeographTags()
    pywikibot.debug(tags, 'bot')
    limit = 100

    for i in range(startid, endid, limit):
        searchurl = 'http://api.geograph.org.uk/api-facetql.php?select=*&limit=%s&where=id+between+%s+and+%s&utf=2' % (limit, i, min(i+limit,endid))
        try:
            searchpage = requests.get(searchurl)
        except requests.exceptions.ConnectionError:
            pywikibot.output(u'Got a connection error on %s. Sleeping 5 minutes' % (searchurl,))
            time.sleep(300)
            searchpage = requests.get(searchurl)
        for row in searchpage.json().get('rows'):
            metadata = row
            metadata['imageurl'] = u'https://www.geograph.org.uk/reuse.php?id=%s&download=%s&size=largest' % (row.get('id'), row.get('hash'))
            metadata['sourceurl'] = u'https://www.geograph.org.uk/photo/%s' % (row.get('id'), )

            if row.get('takenday'):
                dateregex = '^(\d\d\d\d)(\d\d)(\d\d)$'
                datematch = re.match(dateregex, row.get('takenday'))
                if datematch:
                    row['date'] = '%s-%s-%s' % (datematch.group(1), datematch.group(2), datematch.group(3), )

            if row.get('vlat'):
                metadata['photographer_lat'] = math.degrees(float(row.get('vlat')))
            if row.get('vlong'):
                metadata['photographer_lon'] = math.degrees(float(row.get('vlong')))
            if row.get('vgrlen'):
                if int(row.get('vgrlen')) == 0:
                    metadata['photographer_precision'] = None
                elif int(row.get('vgrlen')) <= 4:
                    metadata['photographer_precision'] = 0.01
                elif int(row.get('vgrlen')) <= 6:
                    metadata['photographer_precision'] = 0.001
                elif int(row.get('vgrlen')) <= 8:
                    metadata['photographer_precision'] = 0.0001
                elif int(row.get('vgrlen')) > 8:
                    metadata['photographer_precision'] = 0.00001
            if row.get('wgs84_lat'):
                metadata['object_lat'] = math.degrees(float(row.get('wgs84_lat')))
            if row.get('wgs84_long'):
                metadata['object_lon'] = math.degrees(float(row.get('wgs84_long')))
            if row.get('natgrlen'):
                if int(row.get('natgrlen')) == 0:
                    metadata['object_precision'] = None
                elif int(row.get('natgrlen')) <= 4:
                    metadata['object_precision'] = 0.01
                elif int(row.get('natgrlen')) <= 6:
                    metadata['object_precision'] = 0.001
                elif int(row.get('natgrlen')) <= 8:
                    metadata['object_precision'] = 0.0001
                elif int(row.get('natgrlen')) > 8:
                    metadata['object_precision'] = 0.00001
            metadata['depictsqids'] = []
            if row.get('contexts'):
                for tag in row.get('contexts').replace('_SEP_', '|').split('|'):
                    tag = tag.strip().lower()
                    if tag:
                        tag = 'top:%s' % (tag,)
                        pywikibot.debug('Tag found:"%s"' % (tag,), 'bot')
                        if tag in tags:
                            depictsqid = tags.get(tag)
                            if depictsqid not in metadata.get('depictsqids'):
                                metadata['depictsqids'].append(depictsqid)
            if row.get('subjects'):
                for tag in row.get('subjects').replace('_SEP_', '|').split('|'):
                    tag = tag.strip().lower()
                    if tag:
                        pywikibot.debug('Tag found:"%s"' % (tag,), 'bot')
                        if tag in tags:
                            depictsqid = tags.get(tag)
                            if depictsqid not in metadata.get('depictsqids'):
                                metadata['depictsqids'].append(depictsqid)
            if row.get('tags'):
                for tag in row.get('tags').replace('_SEP_', '|').split('|'):
                    tag = tag.strip().lower()
                    if tag:
                        pywikibot.debug('Tag found:"%s"' % (tag,), 'bot')
                        if tag in tags:
                            depictsqid = tags.get(tag)
                            if depictsqid not in metadata.get('depictsqids'):
                                metadata['depictsqids'].append(depictsqid)
            yield row
    return

def getGeographTags():
    """
    Get the Geograph tags and subjects. Just merge them into one.
    :return:
    """
    page = pywikibot.Page(pywikibot.Site('commons', 'commons'), title='User:GeographBot/Tags')
    text = page.get()
    regex = u'^\*\s*https\:\/\/www\.geograph\.org\.uk\/tagged\/(?P<tag>[^\s]+)\s*-\s*(?P<text>(\{\{Q\|(?P<qid>Q\d+)\}\})?.*)$'
    result = {}
    skipped = {}

    for match in re.finditer(regex, text, flags=re.M):
        tag = match.group('tag').replace('+', ' ').replace('%28', '(').replace('%29', ')').replace('%2C', ',').lower()
        if match.group('tag').startswith('subject:'):
            tag = tag.replace('subject:', '')
        if match.group('qid'):
            result[tag] = match.group('qid')
        else:
            skipped[tag] = match.group('text')

    pywikibot.debug('Loaded %s and skipped %s tags from %s' % (len(result), len(skipped), 'https://commons.wikimedia.org/wiki/User:GeographBot/Tags'), 'bot')

    pywikibot.debug (skipped, 'bot')

    subjectsurl = 'https://www.geograph.org.uk/tags/prefix.php?prefix=subject&output=csv'
    subjectsmin = 99
    #subjectpage = requests.get(subjectsurl)
    #csvreader = csv.DictReader(subjectpage.iter_lines())
    #for subject in csvreader:
    #    if subject.get('tag') not in result and subject.get('tag') not in skipped:
    #        print (subject)
    newsubjects = []

    pywikibot.debug('Subjects from %s that are missing and are used at lest %s times' % (subjectsurl, subjectsmin,), 'bot')
    with closing(requests.get(subjectsurl, stream=True)) as r:
        lines = (line.decode('utf-8') for line in r.iter_lines())
        for subject in csv.DictReader(lines):
            tag = subject.get('tag').lower().replace('subject:', '')
            if tag not in result and tag not in skipped and int(subject.get('images')) > subjectsmin:
                newsubject = '* https://www.geograph.org.uk/tagged/subject:%s - <to do %s hits>' % (tag.replace(' ', '+'), subject.get('images'))
                newsubjects.append(newsubject)
                pywikibot.debug(newsubject, 'bot')

    topurl = 'https://multichill.toolforge.org/queries/commons/tag_stat_top.tsv'
    topmin = 499
    pywikibot.debug('Top tags from %s that are missing and are used at least %s times' % (topurl, topmin), 'bot')
    with closing(requests.get(topurl, stream=True)) as r:
        lines = (line.decode('utf-8') for line in r.iter_lines())
        for subject in csv.DictReader(lines, delimiter='\t'):
            tag = subject.get('tagtext').lower().replace('subject:', '')
            if tag.startswith('place:') or tag.startswith('county:') or tag.startswith('camera:'):
                continue
            elif tag not in result and tag not in skipped and int(subject.get('count')) > topmin:
                newsubject = '* https://www.geograph.org.uk/tagged/%s -  <to do %s hits>' % (tag.replace(' ', '+'), subject.get('count'))
                newsubjects.append(newsubject)
                pywikibot.debug(newsubject, 'bot')

    # Don't want to trigger updates too often
    if len(newsubjects) > 10:
        talkpage = pywikibot.Page(pywikibot.Site('commons', 'commons'), title='User talk:GeographBot/Tags')
        newtext = talkpage.get()
        newtext += '\n\n== New tags ~~~~~ ==\n'
        for newsubject in sorted(newsubjects):
            newtext += '%s\n' % (newsubject,)
        summary = 'Added %s new Geograph tags to match' % (len(newsubjects),)
        talkpage.put(newtext, summary=summary)
    return result


def main(*args):
    startid = None
    endid = None
    resumeupload = False
    dryrun = False
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
        elif arg.startswith('-resumeupload'):
            resumeupload = True
        elif arg.startswith('-dry'):
            dryrun = True
        #elif genFactory.handleArg(arg):
        #    continue
    generator = None
    if resumeupload and startid:
        generator = getGeographResumeGenerator(resumephoto=startid)
    elif resumeupload:
        generator = getGeographResumeGenerator()
    elif startid and endid:
        generator = getFilteredGeographGenerator(int(startid), int(endid),)

    if not generator:
        pywikibot.output('No generator found')
        pywikibot.output('Add -resumeupload to resume where GeographBot left off')
        pywikibot.output('Add -startid:<id> -endid:<id> to work on a specific set of Geograph files')
        return

    if dryrun:
        for page in generator:
            print (json.dumps(page, sort_keys=True, indent=4))
    else:
        geographUploaderBot = GeographUploaderBot(generator)
        geographUploaderBot.run()

if __name__ == "__main__":
    main()
