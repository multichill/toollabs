#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This bot adds the missing digital representation of link on files that are in use.
"""
import pywikibot
import requests
import re
import pywikibot.data.sparql
import json

class PaintingsMatchBot:
    """
    A bot to add missing links to Wikidata on Commons
    """
    def __init__(self):
        """
        Build all the lookup tables to work on
        """
        self.commons = pywikibot.Site(u'commons', u'commons')
        self.commons.login()
        self.commons.get_tokens('csrf')
        self.repo = self.commons.data_repository()

        self.commonsNoLink = self.getCommonsWithoutWikidataSimple()
        self.wikidataImages = self.getWikidataWithImages()

    def run(self):
        """
        Get the intersection of painting items with images and painting images without an item and add the links
        """
        missingCommonsLinks = set(self.wikidataImages.keys()) & set(self.commonsNoLink)
        pywikibot.output('Found %s files to add Wikidata link to' % (len(missingCommonsLinks),))
        for filename in missingCommonsLinks:
            wikidataitem = self.wikidataImages.get(filename)
            self.addMissingCommonsWikidataLink(filename, wikidataitem)

    def getCommonsWithoutWikidataSimple(self):
        """
        Get the list of painting images on Commons that don't have a Wikidata identifier.
        """
        result = []
        url = 'http://tools.wmflabs.org/multichill/queries2/commons/paintings_without_wikidata_simple.txt'
        regex = '^\* \[\[:File:(?P<image>[^\]]+)\]\]$'
        queryPage = requests.get(url)
        for match in re.finditer(regex, queryPage.text, flags=re.M):
            image = match.group("image")
            result.append(image)
        return result

    def getWikidataWithImages(self):
        """
        Query to get all the paintings on Wikidata that have an image.
        """
        result = {}
        query = u"""SELECT ?item ?image WHERE {
        ?item wdt:P31 wd:Q3305213 .
        ?item wdt:P18 ?image .
}"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            item = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            image = pywikibot.FilePage(pywikibot.Site('commons', 'commons'),resultitem.get('image').replace(u'http://commons.wikimedia.org/wiki/Special:FilePath/', u'')).title(underscore=True, with_ns=False)
            result[image] = item
        return result

    def addMissingCommonsWikidataLink(self, filename, wikidata_item):
        """
        Try to add a missing link to Commons.
        """
        imagefile = pywikibot.FilePage(self.commons, title=filename)

        imagefile.clear_cache() # Clear the cache otherwise the pageid is 0.
        mediaid = 'M%s' % (imagefile.pageid,)
        currentdata = self.getCurrentMediaInfo(mediaid)

        if currentdata.get('statements') and currentdata.get('statements').get('P6243'):
            # Already on the file
            return

        itemdata = self.getStructuredData(wikidata_item)
        summary = 'Adding link to [[d:Special:EntityPage/%s]] based on usage on that item' % (wikidata_item,)

        token = self.commons.tokens['csrf']
        postdata = {'action' : 'wbeditentity',
                    'format' : 'json',
                    'id' : mediaid,
                    'data' : json.dumps(itemdata),
                    'token' : token,
                    'summary' : summary,
                    'bot' : True,
                    }
        #print (json.dumps(postdata, sort_keys=True, indent=4))
        request = self.commons._simple_request(**postdata)
        data = request.submit()
        imagefile.touch()

    def getCurrentMediaInfo(self, mediaid):
        """
        Check if the media info exists. If that's the case, return that so we can expand it.
        Otherwise return an empty structure with just <s>claims</>statements in it to start
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :return: json
            """
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M52611909
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M10038
        request = self.commons._simple_request(action='wbgetentities',ids=mediaid)
        data = request.submit()
        if data.get(u'entities').get(mediaid).get(u'pageid'):
            return data.get(u'entities').get(mediaid)
        return {}

    def getStructuredData(self, wikidata_item):
        """
        Get the structured data to add to the file
        :param wikidata_item: The Qid o the Wikidata item about the painting
        :return: The claims to add
        """
        claims = []

        itemid = wikidata_item.replace('Q', '')
        # digital representation of -> item
        toclaim = {'mainsnak': { 'snaktype': 'value',
                                 'property': 'P6243',
                                 'datavalue': { 'value': { 'numeric-id': itemid,
                                                           'id' : wikidata_item,
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        claims.append(toclaim)

        # main subject -> item
        toclaim = {'mainsnak': { 'snaktype': 'value',
                                 'property': 'P921',
                                 'datavalue': { 'value': { 'numeric-id': itemid,
                                                           'id' : wikidata_item,
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
                                                           'id' : wikidata_item,
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        claims.append(toclaim)
        return {'claims' : claims}


def main():
    paintingsMatchBot = PaintingsMatchBot()
    paintingsMatchBot.run()

if __name__ == "__main__":
    main()
