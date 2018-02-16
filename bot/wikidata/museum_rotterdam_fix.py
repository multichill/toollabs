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

def fixRotterdamItem(item):
    """
    Replace a string in the raw Wikibase json
    :param item:
    :param searchstring:
    :param replacestring:
    :return:
    """
    pywikibot.output(u'Working on %s' % (item.title(),))
    data = item.get()
    claims = data.get('claims')
    if not u'P217' in claims:
        pywikibot.output(u'No inventory number found, skipping')
        return
    if not len(claims.get(u'P217'))==1:
        pywikibot.output(u'Multiple inventory numbers found, skipping')
        return
    invclaim = claims.get(u'P217')[0]
    inventorynumber = invclaim.getTarget()
    if not u'_' in inventorynumber:
        pywikibot.output(u'No _ found in inventory number, skipping')
        return
    newinventorynumber = inventorynumber.replace(u'_', u'-')

    if not u'P973' in claims:
        pywikibot.output(u'No url found, skipping')
        return
    if not len(claims.get(u'P973'))==1:
        pywikibot.output(u'Multiple urls found, skipping')
        return
    urlclaim = claims.get(u'P973')[0]
    url = urlclaim.getTarget()
    newurl = url

    if not u'collectie.museumrotterdam.nl/objecten/' in url:
        pywikibot.output(u'Invalid url: %s, skipping' % (url,))
        return
    if not url.endswith(newinventorynumber):
        pywikibot.output(u'Url %s and inventory number %s don\'t match, skipping' % (url,newinventorynumber))
        return

    museumpage = requests.get(url)
    if u'Pagina niet gevonden' in museumpage.text:
        newurl = newurl + u'-B'
        pywikibot.output(u'Current url %s broken, trying %s' % (url,newurl ))
        newinventorynumber =  newinventorynumber + u'-B'
        museumpage = requests.get(newurl)
        if not u'content="Museum Rotterdam - van de stad">' in museumpage.text:
            pywikibot.output(u'New url did not work, skipping')
            return

    summary = u'Fixing Rotterdam Museum'
    if inventorynumber!=newinventorynumber:
        invclaim.changeTarget(newinventorynumber, summary=summary)
    if url !=newurl:
        urlclaim.changeTarget(newurl, summary=summary)


def fixRotterdamImage(item):
    """
    Replace a string in the raw Wikibase json
    :param item:
    :param searchstring:
    :param replacestring:
    :return:
    """
    pywikibot.output(u'Working on %s' % (item.title(),))
    data = item.get()
    claims = data.get('claims')
    if not u'P217' in claims:
        pywikibot.output(u'No inventory number found, skipping')
        return
    if not len(claims.get(u'P217'))==1:
        pywikibot.output(u'Multiple inventory numbers found, skipping')
        return
    invclaim = claims.get(u'P217')[0]
    inventorynumber = invclaim.getTarget()

    if not u'P4765' in claims:
        pywikibot.output(u'No image url found, skipping')
        return
    if not len(claims.get(u'P4765'))==1:
        pywikibot.output(u'Multiple urls found, skipping')
        return

    urlclaim = claims.get(u'P4765')[0]
    url = urlclaim.getTarget()
    newurl = url

    if not u'collectie.museumrotterdam.nl/beeld/' in url:
        pywikibot.output(u'Invalid url: %s, skipping' % (url,))
        return

    if inventorynumber in url:
        return
    newurl = u'http://collectie.museumrotterdam.nl/beeld/%s_1.jpg' % (inventorynumber,)
    summary = u'Fixing Rotterdam Museum'
    urlclaim.changeTarget(newurl, summary=summary)

def main(*args):
    """
    Main function. Grab a generator and pass it to the bot to work on
    """
    repo = pywikibot.Site().data_repository()

    query = u"""
    SELECT DISTINCT ?item ?inv ?url WHERE {
  ?item wdt:P195 wd:Q2130225 .
  ?item wdt:P31 wd:Q3305213 .
  ?item p:P217 ?invstatement .
  ?invstatement ps:P217 ?inv .
  ?invstatement pq:P195 wd:Q2130225 .
  FILTER regex(?inv, "^.+_.+$") .
  ?item wdt:P973 ?url .
  }
 LIMIT 500
    """
    #generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))
    #for item in generator:
    #    fixRotterdamItem(item)

    query = u"""
SELECT DISTINCT ?item WHERE {
  ?item wdt:P195 wd:Q2130225 .
  ?item wdt:P31 wd:Q3305213 .
  ?item p:P217 ?invstatement .
  ?invstatement ps:P217 ?inv .
  ?invstatement pq:P195 wd:Q2130225 .
  FILTER regex(?inv, "^.+A-B$") .
  ?item wdt:P4765 ?url .
  #FILTER regex(STR(?url), "^.+-A_1\\.jpg$") .
  }
 LIMIT 2200"""
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))
    for item in generator:
        fixRotterdamImage(item)


if __name__ == "__main__":
    main()
