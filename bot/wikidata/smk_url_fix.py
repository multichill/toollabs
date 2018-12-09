#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Our friends at SMK broke all their urls. Fun!

* Old format : http://www.smk.dk/en/explore-the-art/search-smk/#/detail/KMSst586
* New format: http://collection.smk.dk/#/en/detail/KMSst586

Grab all the items that have a described by url in the old format and replace the url in the raw json.
This also includes the references.

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
    item.get()
    wikibasejson = json.dumps(item.toJSON())
    #print wikibasejson
    newjsontext = wikibasejson.replace(searchstring, replacestring)
    #print newjson
    pywikibot.showDiff(wikibasejson, newjsontext)
    newjson = json.loads(newjsontext)
    summary = u'Fixing SMK collection urls'
    try:
        item.editEntity(newjson, summary=summary)
    except:
        return
    #data = item.get(force=True)

def replaceGenerator():
    query = u"""SELECT ?item ?oldurl WHERE {
  ?item wdt:P195 wd:Q671384 .
  ?item wdt:P31 wd:Q3305213 .
  ?item wdt:P973 ?oldurl .
  FILTER(REGEX(STR(?oldurl), "http://www.smk.dk/en/explore-the-art/search-smk/#/detail/.+"))
  } LIMIT 7000"""
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    repo = pywikibot.Site().data_repository()

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        item = pywikibot.ItemPage(repo, title=qid)
        wrongurl = resultitem.get('oldurl')
        righturl = resultitem.get('oldurl').replace(u'http://www.smk.dk/en/explore-the-art/search-smk/#/detail/', u'http://collection.smk.dk/#/en/detail/')
        yield (item, wrongurl, righturl)

def main(*args):
    """
    Main function. Grab a generator and pass it to the bot to work on
    """
    repo = pywikibot.Site().data_repository()

    generator = replaceGenerator()

    for (item, wrongurl, righturl) in generator:
        print item
        print wrongurl
        print righturl
        itemReplace(item, wrongurl, righturl)


if __name__ == "__main__":
    main()
