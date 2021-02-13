#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to touch files that are in collections listed at https://commons.wikimedia.org/wiki/Data:Completely_indexed_painting_collections.tab ,
but  not in https://commons.wikimedia.org/wiki/Category:Paintings_from_completely_indexed_collections

The bot will do a search per collection and do a touch every returned file.

"""

import pywikibot
import time
import json
import pywikibot.data.sparql
from pywikibot import pagegenerators

class TouchPaintingBot:
    """
    Bot to add structured data statements on Commons
    """
    def __init__(self):
        """
        Grab generator based on search to work on.
        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.generator = self.getGenerator()

    def getGenerator(self):
        """
        Get the generator to work on.
        """
        coldatapage = pywikibot.Page(self.site, 'Data:Completely_indexed_painting_collections.tab')
        collectionjson = json.loads(coldatapage.text)
        colquery = 'SELECT ?item ?institution WHERE { VALUES ?item {'

        for collectioninfo in collectionjson.get('data'):
            colquery += ' wd:%s' % (collectioninfo[0],)
        colquery +=' }  ?item wdt:P1612 ?institution }'
        colsq = pywikibot.data.sparql.SparqlQuery()
        colqueryresult = colsq.select(colquery)

        for resultitem in colqueryresult:
            institution = resultitem.get('institution').replace(' ', '_')
            query = 'file: hastemplate:Institution:%s incategory:Paintings_without_Wikidata_item -incategory:Paintings_from_completely_indexed_collections' % (institution,)
            gen = pagegenerators.SearchPageGenerator(query, total=1000, namespaces=6, site=self.site)
            for filepage in gen:
                yield filepage

        creatordatapage = pywikibot.Page(self.site, 'Data:Completely_indexed_painters.tab')
        creatorjson = json.loads(creatordatapage.text)
        creatorquery = 'SELECT ?item ?creator WHERE { VALUES ?item {'

        for creatorinfo in creatorjson.get('data'):
            creatorquery += ' wd:%s' % (creatorinfo[0],)
        creatorquery +=' }  ?item wdt:P1472 ?creator }'
        creatorsq = pywikibot.data.sparql.SparqlQuery()
        creatorqueryresult = creatorsq.select(creatorquery)

        for resultitem in creatorqueryresult:
            creator = resultitem.get('creator').replace(' ', '_')
            query = 'file: hastemplate:Creator:%s incategory:Paintings_without_Wikidata_item -incategory:Paintings_by_completely_indexed_painters' % (creator,)
            gen = pagegenerators.SearchPageGenerator(query, total=1000, namespaces=6, site=self.site)
            for filepage in gen:
                yield filepage



    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            print (filepage)
            filepage.touch()


def main(*args):
    touchPaintingBot = TouchPaintingBot()
    touchPaintingBot.run()

if __name__ == "__main__":
    main()
