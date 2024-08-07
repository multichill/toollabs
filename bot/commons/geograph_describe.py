#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to describe Geograph images using SDoC (structured data on Commons).

Bot will extract the id and retrieve the metadata from geograph. It will try to add:
* location of creation (P1071) based on reverse geocoding at http://edwardbetts.com/geocode/
* depicts (P180) based on the mappings at https://commons.wikimedia.org/wiki/User:GeographBot/Tags
* depicts (P180) based on the object location and reverse geocoding

Should be switched to a more general Pywikibot implementation.
"""

import pywikibot
import re
import pywikibot.data.sparql
import time
from pywikibot.comms import http
import requests
import json
import math
from pywikibot import pagegenerators

class GeographDescribeBot:
    """
    Bot to add structured data to Geograph uploads
    """
    def __init__(self, gen):
        """
        Grab generator based on search to work on.

        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()
        self.tags = self.getGeographTags()
        self.generator = gen

    def getGeographTags(self):
        """
        Get the Geograph tags and subjects. Just merge them into one.
        :return: Dict
        """
        page = pywikibot.Page(self.site , title='User:GeographBot/Tags')
        text = page.get()
        regex = u'^\*\s*https\:\/\/www\.geograph\.org\.uk\/tagged\/(?P<tag>[^\s]+)\s*-\s*\{\{Q\|(?P<qid>Q\d+)\}\}.*$'
        result = {}

        for match in re.finditer(regex, text, flags=re.M):
            tag = match.group('tag').replace('+', ' ').lower()
            if match.group('tag').startswith('subject:'):
                tag = tag.replace('subject:', u'')
            result[tag] = match.group('qid')
        return result

    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            if not filepage.exists():
                continue
            # Probably want to get this all in a preloading generator to make it faster
            mediaid = u'M%s' % (filepage.pageid,)
            currentdata = self.getCurrentMediaInfo(mediaid)
            self.describeGeographFile(filepage, mediaid, currentdata)

    def getCurrentMediaInfo(self, mediaid):
        """
        Check if the media info exists. If that's the case, return that so we can check against it
        Otherwise return an empty dict
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :return: dict
        """
        request = self.site._simple_request(action='wbgetentities',ids=mediaid)
        data = request.submit()
        if data.get(u'entities').get(mediaid).get(u'pageid'):
            return data.get(u'entities').get(mediaid)
        return {}

    def describeGeographFile(self, filepage, mediaid, currentdata):
        """
        Handle a Geograph file.
        Extract the metadata, add the structured data

        :param filepage: The page of the file to work on.
        :param mediaid: The mediaid of the file (like M12345)
        :param currentdata: Dict with the current structured data
        :return: Nothing, edit in place
        """
        pywikibot.output(u'Working on %s' % (filepage.title(),))
        if not filepage.exists():
            return

        # Check if the file is from Geograph
        geographid = self.getGeographId(filepage, currentdata)
        if not geographid:
            pywikibot.output(u'No Geograph ID found  on %s, skipping' % (filepage.title(),))
            return
        print (geographid)

        if currentdata.get('statements'):
            if currentdata.get('statements').get('P180') and currentdata.get('statements').get('P1071'):
                # Already done
                return

        try:
            metadata = self.getGeographMetadata(geographid)
        except json.decoder.JSONDecodeError:
            pywikibot.output('Got invalid JSON. Skipping this one')
            time.sleep(60)
            return

        if not metadata:
            return
        #print(json.dumps(metadata))

        depictsclaims = self.getDepicts(currentdata, metadata)
        locationclaim = self.getLocation(currentdata, metadata)

        currentcategory = False
        for category in filepage.categories():
            if metadata.get('commonscat') and category.title(with_ns=False)==metadata.get('commonscat'):
                currentcategory = True
            elif metadata.get('objectcommonscat') and category.title(with_ns=False)==metadata.get('objectcommonscat'):
                currentcategory = True

        claims = []
        if depictsclaims and locationclaim:
            summary = 'adding [[d:Special:EntityPage/P180]] and [[d:Special:EntityPage/P1071]] [[d:Special:EntityPage/%s]] based on Geograph' % metadata.get('locationqid')
            claims.extend(depictsclaims)
            claims.append(locationclaim)
        elif depictsclaims:
            summary = 'adding [[d:Special:EntityPage/P180]] based on Geograph'
            claims.extend(depictsclaims)
        elif locationclaim:
            summary = 'adding [[d:Special:EntityPage/P1071]] [[d:Special:EntityPage/%s]] based on Geograph' % metadata.get('locationqid')
            claims.append(locationclaim)
        else:
            return

        if locationclaim and currentcategory:
            summary = summary + ', linked to current [[:Category:%s]]' % metadata.get('commonscat')

        itemdata = dict()
        itemdata['claims'] = claims

        # Flush it
        pywikibot.output(summary)

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

    def getGeographId(self, filepage, currentdata):
        """
        Extract the geograph ID from the filepage

        :param filepage: The page of the file to work on.
        :param currentdata: The current structured data
        :return: The ID of the file (string)
        """
        templateFound = False
        for template in filepage.itertemplates():
            if template.title()==u'Template:Geograph':
                templateFound = True
            elif template.title()==u'Template:Also geograph':
                templateFound = True
        if not templateFound:
            return False

        regex = u'\{\{[gG]eograph\|(\d+)\|[^\}]+\}\}'

        match = re.search(regex, filepage.text)
        if match:
            return match.group(1)

        alsoregex = u'\{\{[aA]lso[ _]geograph\|(\d+)\}\}'
        alsomatch = re.search(alsoregex, filepage.text)
        if alsomatch:
            return alsomatch.group(1)

        # TODO: Try to extract it from structured data (currentdata)
        return False


    def getGeographMetadata(self, geographid):
        """
        Get the metadata for a single geograph file
        :param id: The id of the file
        :return: Dict with the metadata
        """
        searchurl = 'http://api.geograph.org.uk/api-facetql.php?select=*&limit=1&where=id=%s' % (geographid)
        try:
            searchpage = requests.get(searchurl)
        except requests.exceptions.ConnectionError:
            pywikibot.output(u'Got a connection error on %s. Sleeping 5 minutes' % (searchurl,))
            time.sleep(300)
            searchpage = requests.get(searchurl)
        if searchpage.json().get('rows'):
            row = searchpage.json().get('rows')[0]
        else:
            return False
        metadata = row

        # For the reverse geocoding
        if row.get('vlat'):
            metadata['photographer_lat'] = math.degrees(float(row.get('vlat')))
        if row.get('vlong'):
            metadata['photographer_lon'] = math.degrees(float(row.get('vlong')))

        # For the fallback reverse geocoding
        if row.get('wgs84_lat'):
            metadata['object_lat'] = math.degrees(float(row.get('wgs84_lat')))
        if row.get('wgs84_long'):
            metadata['object_lon'] = math.degrees(float(row.get('wgs84_long')))

        # And get the depicts info
        metadata['depictsqids'] = []
        if row.get('tags'):
            for tag in row.get('tags').split('_SEP_'):
                tag = tag.strip().lower()
                if tag in self.tags:
                    depictsqid = self.tags.get(tag)
                    if depictsqid not in metadata.get('depictsqids'):
                        metadata['depictsqids'].append(depictsqid)
        if row.get('subjects'):
            for tag in row.get('subjects').split('_SEP_'):
                tag = tag.strip().lower()
                if tag in self.tags:
                    depictsqid = self.tags.get(tag)
                    if depictsqid not in metadata.get('depictsqids'):
                        metadata['depictsqids'].append(depictsqid)

        if metadata.get('photographer_lat') and metadata.get('photographer_lon'):
            (locationqid, locationcc) = self.reverseGeocode(metadata.get('photographer_lat'),
                                                            metadata.get('photographer_lon'), )
            if locationqid:
                metadata['locationqid'] = locationqid
            if locationcc:
                metadata['commonscat'] = locationcc

        if metadata.get('object_lat') and metadata.get('object_lon'):
            (objectqid, objectcc) = self.reverseGeocode(metadata.get('object_lat'),
                                                        metadata.get('object_lon'), )
            if objectqid:
                if not metadata.get('locationqid'):
                    metadata['locationqid'] = objectqid
                metadata['depictsqids'].append(objectqid)
            if objectcc:
                metadata['objectcommonscat'] = objectcc

        return metadata

    def reverseGeocode(self, lat, lon):
        """
        Do reverse geocoding based on photographer and return Wikidata item and Commons category
        :param metadata: The Geograph metadata to work on
        :return: Tuple of Wikidata item and Commons category
        """
        qid = None
        commonscat = None

        url = 'http://edwardbetts.com/geocode/?lat=%s&lon=%s' % (lat, lon)
        page = requests.get(url)
        json = page.json()
        if not json.get('missing'):
            if json.get('wikidata'):
                qid = json.get('wikidata')
            if json.get('commons_cat') and json.get('commons_cat').get('title'):
                commonscat = json.get('commons_cat').get('title')
        return (qid, commonscat)

    def getDepicts(self, currentdata, metadata):
        """

        :param metadata:
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P180'):
            return False

        depictstoadd = []
        if metadata.get('depictsqids'):
            depictstoadd.extend(metadata.get('depictsqids'))
        if metadata.get('depictslocationqid'):
            depictstoadd.append(metadata.get('depictslocationqid'))
        if not depictstoadd:
            return False

        result = []
        for depictsqid in depictstoadd:
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

    def getLocation(self, currentdata, metadata):
        """

        :param metadata:
        :return:
        """
        if not metadata.get('locationqid'):
            return False
        if currentdata.get('statements') and currentdata.get('statements').get('P1071'):
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


def main(*args):
    gen = None
    genFactory = pagegenerators.GeneratorFactory()

    for arg in pywikibot.handle_args(args):
        if genFactory.handleArg(arg):
            continue
    gen = genFactory.getCombinedGenerator(gen, preload=True)

    geographDescribeBot = GeographDescribeBot(gen)
    geographDescribeBot.run()

if __name__ == "__main__":
    main()
