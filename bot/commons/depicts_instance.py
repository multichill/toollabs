#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to describe Geograph images using SDoC (structured data on Commons).

Bot will extract the id and retrieve the metadata from geograph. It will try to add:
*  depicts (P180) based on the mappings at https://commons.wikimedia.org/wiki/User:GeographBot/Tags
*  location of creation (P1071) based on reverse geocoding at http://edwardbetts.com/geocode/

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

class DepictsInstanceBot:
    """
    """
    def __init__(self, depictsclass, gen):
        """
        Grab generator based on search to work on.

        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()
        self.depictsclass = depictsclass
        self.generator = gen

    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            print (filepage.title())
            if not filepage.exists():
                continue
            # Probably want to get this all in a preloading generator to make it faster
            mediaid = u'M%s' % (filepage.pageid,)
            currentdata = self.getCurrentMediaInfo(mediaid)
            self.processFile(filepage, mediaid, currentdata)

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

    def processFile(self, filepage, mediaid, currentdata):
        """
        Handle a file.
        Extract the metadata, add the structured data

        :param filepage: The page of the file to work on.
        :param mediaid: The mediaid of the file (like M12345)
        :param currentdata: Dict with the current structured data
        :return: Nothing, edit in place
        """
        pywikibot.output(u'Working on %s' % (filepage.title(),))
        if not filepage.exists():
            return

        if not currentdata.get('statements'):
            return

        if not currentdata.get('statements').get('P180'):
            return

        # I need the id of the existing statement to replace it later on
        foundClassStatementId = False

        for statement in currentdata.get('statements').get('P180'):
            if statement.get('mainsnak').get('datavalue').get('value').get('id')==self.depictsclass:
                foundClassStatementId = statement.get('id')
                if statement.get('qualifiers'):
                    # I can't handle qualifiers, skip it.
                    return
                break

        instanceqid = self.getInstanceFromCategories(filepage)

        if not instanceqid:
            return

        # Check to make sure that the statement isn't already on the file
        for statement in currentdata.get('statements').get('P180'):
            if statement.get('mainsnak').get('datavalue').get('value').get('id')==instanceqid:
                return

        summary = 'adding specific instance for [[d:Special:EntityPage/%s]] based on category' % (self.depictsclass,)

        token = self.site.tokens['csrf']
        postdata = {u'action' : u'wbsetclaimvalue',
                    u'format' : u'json',
                    u'claim' : foundClassStatementId,
                    u'snaktype' : 'value',
                    u'value' : json.dumps({'entity-type' : 'item',
                                'numeric-id' : int(instanceqid.replace('Q', ''))}),
                    #u'id' : mediaid,
                    #u'data' : json.dumps(itemdata),
                    u'token' : token,
                    u'summary' : summary,
                    u'bot' : True,
                    }

        print (json.dumps(postdata))
        request = self.site._simple_request(**postdata)
        data = request.submit()

    def getInstanceFromCategories(self, filepage):
        """
        Get the specific instance based on the categories on the file
        :param filepage:
        :return:
        """
        for category in filepage.categories():
            if not category.isHiddenCategory():
                instance = self.getInstanceFromCategory(category)
                if instance:
                    return instance
        return None

    def getInstanceFromCategory(self, category):
        """
        Try to get the instance from one category
        :param category:
        :return:
        """
        try:
            item = category.data_item()
        except pywikibot.exceptions.NoPage:
            return None

        data = item.get()
        claims = data.get('claims')
        if not 'P31' in claims:
            return None

        foundcategory = False
        for claim in claims.get('P31'):
            if claim.getTarget().getID()==self.depictsclass:
                return item.getID()
            elif claim.getTarget().getID()=='Q4167836':
                foundcategory = True
                break

        # Handle category items
        if foundcategory and 'P301' in claims:
            item = claims.get('P301')[0].getTarget()
            data = item.get()
            claims = data.get('claims')
            if not 'P31' in claims:
                return None

            for claim in claims.get('P31'):
                if claim.getTarget().getID()==self.depictsclass:
                    return item.getID()
        return None

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
        return self.reverseGeocode(metadata)


    def reverseGeocode(self, metadata):
        """
        Do reverse geocoding based on the metadata and return the metadata with extra fields
        :param metadata:
        :return:
        """
        result = metadata
        # Based on the photographer
        if metadata.get('photographer_lat') and metadata.get('photographer_lon'):
            url = 'http://edwardbetts.com/geocode/?lat=%s&lon=%s' % (metadata.get('photographer_lat'),
                                                                     metadata.get('photographer_lon'))
            page = requests.get(url)
            json = page.json()
            if not json.get('missing'):
                if json.get('wikidata'):
                    result['locationqid'] = json.get('wikidata')
                if json.get('commons_cat') and json.get('commons_cat').get('title'):
                    result['commonscat'] = json.get('commons_cat').get('title')

        # Based on the object
        if metadata.get('object_lat') and metadata.get('object_lon'):
            url = 'http://edwardbetts.com/geocode/?lat=%s&lon=%s' % (metadata.get('object_lat'),
                                                                     metadata.get('object_lon'))
            page = requests.get(url)
            json = page.json()
            if not json.get('missing'):
                if json.get('wikidata'):
                    if not result.get('locationqid'):
                        result['locationqid'] = json.get('wikidata')
                    elif result.get('locationqid') != json.get('wikidata'):
                        result['depictslocationqid'] = json.get('wikidata')
                if json.get('commons_cat') and json.get('commons_cat').get('title'):
                    if not result.get('commonscat'):
                        result['commonscat'] = json.get('commons_cat').get('title')
                    elif result.get('commonscat') != json.get('commons_cat').get('title'):
                        result['objectcommonscat'] = json.get('commons_cat').get('title')
        else:
            return result
        print (url)
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
    depictsclass = 'Q16970'

    for arg in pywikibot.handle_args(args):
        if genFactory.handleArg(arg):
            continue
    gen = genFactory.getCombinedGenerator(gen, preload=True)

    depictsInstanceBot = DepictsInstanceBot(depictsclass, gen)
    depictsInstanceBot.run()

if __name__ == "__main__":
    main()
