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
        datapage = pywikibot.Page(self.site, 'Data:Completely_indexed_painting_collections.tab')
        collectionjson = json.loads(datapage.text)
        query = 'SELECT ?item ?institution WHERE { VALUES ?item {'
        count = 0
        for collectioninfo in collectionjson.get('data'):
            query += ' wd:%s' % (collectioninfo[0],)
        query +=' }  ?item wdt:P1612 ?institution }'
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            institution = resultitem.get('institution').replace(' ', '_')
            query = 'file: hastemplate:Institution:%s incategory:Paintings_without_Wikidata_item -incategory:Paintings_from_completely_indexed_collections' % (institution,)
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
