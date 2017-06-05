#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to replace some broken dimcon urls.

This one was hacked up quickly to just fix this case. Could be use as basis for a more general approach.

"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import requests
import re
import datetime
import time
import json

def itemReplace(item, searchstring, replacestring):
    """
    Replace a string in the raw Wikibase json
    :param item:
    :param searchstring:
    :param replacestring:
    :return:
    """
    wikibasejson = json.dumps(item.toJSON())
    #print wikibasejson
    newjsontext = wikibasejson.replace(searchstring, replacestring)
    #print newjson
    pywikibot.showDiff(wikibasejson, newjsontext)
    newjson = json.loads(newjsontext)
    summary = u'Fixing dimcon/collectienederland urls'
    item.editEntity(newjson, summary=summary)



def main(*args):
    """
    Main function. Grab a generator and pass it to the bot to work on
    """

    query = u"""SELECT DISTINCT ?item  WHERE {
  ?item wdt:P31 wd:Q3305213 .
  ?item wdt:P195 wd:Q1051928 .
  } LIMIT 1000"""
    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    for item in generator:
        itemReplace(item, u'http://dimcon.nl/dimcon/kroller-muller/', u'http://data.collectienederland.nl/page/aggregation/kroller-muller/')

if __name__ == "__main__":
    main()
