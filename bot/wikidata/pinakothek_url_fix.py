#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Fix download links for the pinakothek.de
* Old: https://media.static.onlinesammlung.thenetexperts.info/unsafe/5179.jpg
* New: https://media.static.sammlung.pinakothek.de/unsafe/5179.jpg
"""
#import json
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
#import requests


def main(*args):
    """
    Run the bot.
    """
    query = u"""SELECT ?item ?url WHERE {
  ?item wdt:P4765 ?url .
  FILTER(REGEX(STR(?url), "media.static.onlinesammlung.thenetexperts.info/unsafe/"))
} LIMIT 2000"""

    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    summary = u'Fixing pinakothek.de download url'

    for item in generator:
        data = item.get()
        claims = data.get('claims')

        if not u'P4765' in claims:
            pywikibot.output(u'No url found')
            continue

        if not len(claims.get('P4765'))==1:
            pywikibot.output(u'Not two urls')
            continue

        for claim in claims.get('P4765'):
            oldurl = claim.getTarget()
            if oldurl.startswith(u'https://media.static.onlinesammlung.thenetexperts.info/unsafe/'):
                newurl = oldurl.replace(u'https://media.static.onlinesammlung.thenetexperts.info/unsafe/', u'https://media.static.sammlung.pinakothek.de/unsafe/')
                pywikibot.output(summary)
                claim.changeTarget(newurl, summary=summary)


if __name__ == "__main__":
    main()
