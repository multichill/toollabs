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
    item.get()
    wikibasejson = json.dumps(item.toJSON())
    #print wikibasejson
    newjsontext = wikibasejson.replace(searchstring, replacestring)
    #print newjson
    pywikibot.showDiff(wikibasejson, newjsontext)
    newjson = json.loads(newjsontext)
    summary = u'Fixing collectienederland urls'
    item.editEntity(newjson, summary=summary)
    data = item.get(force=True)
    claims = data.get('claims')
    if u'P973' in claims and len(claims.get(u'P973'))==2 and claims.get(u'P973')[0].getTarget()==replacestring:
        if claims.get(u'P973')[0].getTarget()==claims.get(u'P973')[1].getTarget():
            summary = u'Removing duplicate URL claim'
            item.removeClaims(claims.get(u'P973')[1], summary=summary)

def replaceGenerator():
    query = u"""
SELECT ?item ?itemLabel ?inventory_no ?wrongurl ?righturl WHERE {
  ?item wdt:P31 wd:Q3305213 .
  ?item wdt:P195 wd:Q18600731 .
  ?item wdt:P973 ?wrongurl .
  ?item wdt:P973 ?righturl .
  ?item p:P217 ?invstatement .
  ?invstatement ps:P217 ?inventory_no .
  ?invstatement pq:P195 wd:Q18600731 .
  BIND(IRI(CONCAT("http://data.collectienederland.nl/resource/aggregation/rce-kunstcollectie/", ?inventory_no)) AS ?newurl)  .
  FILTER(CONTAINS(str(?wrongurl), "http://data.collectienederland.nl/resource/aggregation/rce-kunstcollectie/") ) .
  FILTER(?righturl=?newurl && ?wrongurl!=?newurl)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],nl". }
}"""
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    repo = pywikibot.Site().data_repository()

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        item = pywikibot.ItemPage(repo, title=qid)
        wrongurl = resultitem.get('wrongurl')
        righturl = resultitem.get('righturl')
        yield (item, wrongurl, righturl)

def main(*args):
    """
    Main function. Grab a generator and pass it to the bot to work on
    """
    generator = replaceGenerator()

    for (item, wrongurl, righturl) in generator:
        print item
        print wrongurl
        print righturl
        itemReplace(item, wrongurl, righturl)

if __name__ == "__main__":
    main()
