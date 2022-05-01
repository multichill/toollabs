#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Now redundant bot to fix some MET links. Replaced with a property now.
"""
#import json
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
#import requests


def main(*args):
    """
    Run the bot. By default it only runs on the items changed in the last 14 days.
    """
    query = u"""SELECT ?item ?urlold ?url WHERE {
?item wdt:P195 wd:Q160236 .
?item wdt:P973 ?urlold .
?item wdt:P973 ?url .
FILTER REGEX(STR(?urlold), "http://www.metmuseum.org/collection/the-collection-online/search/.+") .
FILTER REGEX(STR(?url), "http://www.metmuseum.org/art/collection/search/.+") .
}"""

    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    summary = u'Removing redundant MET url'

    for item in generator:
        data = item.get()
        claims = data.get('claims')

        if not u'P973' in claims:
            pywikibot.output(u'No url found')
            continue

        if not len(claims.get('P973'))>=2:
            pywikibot.output(u'Not two urls')
            continue

        for claim in claims.get('P973'):
            if claim.getTarget().startswith(u'http://www.metmuseum.org/collection/the-collection-online/search/'):
                pywikibot.output(summary)
                item.removeClaims(claim, summary=summary)
    


if __name__ == "__main__":
    main()
