#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add Commons category (P373) on paintings that do have a sitelink to a Commons category
"""
import pywikibot
from pywikibot import pagegenerators


class PaintingMissingCommonsCategoryBot:
    """
    A bot to Commons Category (P373) links
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
            
        for item_page in self.generator:
            pywikibot.output('Working on %s' % (item_page.title(),))
            if not item_page.exists():
                pywikibot.output(u'Item does not exist, skipping')
                continue

            if item_page.isRedirectPage():
                item_page = item_page.getRedirectTarget()
                
            data = item_page.get()
            claims = data.get('claims')

            if 'P373' in claims:
                pywikibot.output('Item already has Commons Category (P373), skipping')
                continue

            try:
                commons_category_title = item_page.getSitelink(self.commons)
                commons_category = pywikibot.Page(self.commons, title=commons_category_title)
            except pywikibot.exceptions.NoPageError:
                pywikibot.output('Item does not have a sitelink to Commons, skipping')
                continue

            if not commons_category.namespace() == 14:
                pywikibot.output('Linked page is not a category, skipping')

            new_claim = pywikibot.Claim(self.repo, 'P373')
            new_claim.setTarget(commons_category.title(underscore=False, with_ns=False))

            pywikibot.output('Adding %s --> %s' % (new_claim.getID(), new_claim.getTarget()))
            summary = 'Adding missing Commons Category link'
            item_page.addClaim(new_claim, summary=summary)


def main():
    general_query = """SELECT ?item WHERE {
  ?item wdt:P18 [] .
  ?category schema:about ?item ;
           schema:isPartOf <https://commons.wikimedia.org/>.
  MINUS { ?item wdt:P373 [] } .  
  } LIMIT 2000"""

    query = """SELECT ?item WHERE {
  ?item wdt:P31 wd:Q3305213 ;
        wdt:P18 [] .
  MINUS { ?item wdt:P373 [] } .
  ?article schema:about ?item ;
           schema:isPartOf <https://commons.wikimedia.org/>.
  } LIMIT 2000"""

    query = """SELECT ?item WHERE {
  ?comm schema:about ?item ; 
        schema:isPartOf <https://commons.wikimedia.org/> .
  MINUS { ?item wdt:P373 [] }
  ?item wdt:P31 wd:Q3305213
  } LIMIT 1000"""

    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    painting_missing_commons_category_bot = PaintingMissingCommonsCategoryBot(generator)
    painting_missing_commons_category_bot.run()


if __name__ == "__main__":
    main()
