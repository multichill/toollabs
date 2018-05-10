#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add sitelinks to Commons categories based on Commons category (P373).

This bot is a pragmatic approach to the Wikidata and Commons modelling.
On https://commons.wikimedia.org/wiki/File:Commons-Wikidata_links_-_2015.svg you can see an example of a topic where
all different aspects are complete. This is often not the case.
Often we only have an item for the topic, maybe an article and a Commons Category. These might as well be linked up
and links can always be moved if the topic gets expanded. This fits well with the Wikidata approach of split up when
needed or the Wikipedia approach of disambiguate when needed.

The bots does a sparql query for items which do have Commons category (P373), but no sitelink to Commons

For each item:
1. If the item contains topic's main category (P910), skip it
2. If the item already has a Commons sitelink, skip it
3. Check if the item has Commons category (P373), if that is not the case, skip it
4. Check if the category on Commons exists, if that is not the case, skip it
5. Check if the category on Commons is not a redirect, if that is the case, skip it
6. Check if the category on Commons is not a disambiguation category, if that is the case, skip it
7. Try to add the sitelink, if Wikidata throws a already linked error, report and skip

"""

import pywikibot
from pywikibot import pagegenerators
import re
import datetime
import requests

class MissingCommonsSitelinkBot:
    """
    A bot to Commons Category sitelinks
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields ItemPage objects.
        """
        self.generator = generator
        self.commons = pywikibot.Site('commons', 'commons')
        self.repo = pywikibot.Site().data_repository()

    def run(self):
        """
        Starts the robot.
        """
            
        for itempage in self.generator:
            pywikibot.output(u'Working on %s' % (itempage.title(),))
            if not itempage.exists():
                pywikibot.output(u'Item does not exist, skipping')
                continue

            if itempage.isRedirectPage():
                itempage = itempage.getRedirectTarget()
                
            data = itempage.get()
            claims = data.get('claims')
            sitelinks = data.get('sitelinks')

            if u'P910' in claims:
                pywikibot.output(u'Item has topic\'s main category (P910), skipping')
                continue

            if u'commonswiki' in sitelinks:
                pywikibot.output(u'Item already has a sitelink to Commons, skipping')
                continue

            if u'P373' not in claims:
                pywikibot.output(u'Item seems to be missing Commons category (P373), skipping')
                continue

            commonscategorytitle = claims.get('P373')[0].getTarget()
            commonscategory = pywikibot.Category(self.commons, title=commonscategorytitle)
            if not commonscategory.exists():
                pywikibot.output(u'Commons category %s does not exist, skipping' % (commonscategory.title(),))
                continue

            # Check if the category on Commons is not a redirect, if that is the case, skip it
            #if not commonscategory.isRedirectPage():
            #    pywikibot.output(u'Commons category %s does not exist, skipping' % (commonscategory.title(),)
            #    continue


            # Check if the category on Commons is not a disambiguation category, if that is the case, skip it


            summary = 'Add sitelink to %s based on Commons category (P373)' % (commonscategory.title(asLink=True,
                                                                                                     insite=self.repo))
            pywikibot.output(summary)
            try:
                itempage.setSitelink(commonscategory, summary=summary)
            except pywikibot.exceptions.OtherPageSaveError:
                pywikibot.output(u'Item save failed, probably a conflicting sitelink, skipping')


def main():
    query = u"""SELECT ?item ?commonscat WHERE {
  ?item wdt:P1435 wd:Q916333 .
  ?item wdt:P373 ?commonscat .
  MINUS { ?item wdt:P910 [] } .
  FILTER NOT EXISTS {
    ?article schema:about ?item .
    ?article schema:isPartOf <https://commons.wikimedia.org/>
  }
}"""

    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    missingCommonsSitelinkBot = MissingCommonsSitelinkBot(generator)
    missingCommonsSitelinkBot.run()

if __name__ == "__main__":
    main()
