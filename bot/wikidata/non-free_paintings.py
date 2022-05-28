#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to replace some Commons compatible image available at URL (P4765) with non-free artwork image URL (P6500)
* https://www.wikidata.org/wiki/Property:P4765
* https://www.wikidata.org/wiki/Property:P6500

Sometimes some obviously non-free images slip through the cracks. This bot moves the suggestions to a different property
so we don't end up accidentally uploading these images. It takes the existing claim and changes the P target.

US cases are complicated, see https://commons.wikimedia.org/wiki/Commons:Hirtle_chart .
Some of the US images might be free, but just clog up the queue and can still be uploaded based on the other property.

"""
import pywikibot
from pywikibot import pagegenerators, WikidataBot

class NonFreePaintingBot(WikidataBot):
    """
    A bot to move image URLs to different property.
    """
    def __init__(self):
        """
        No arguments, bot makes it's own generator based on the genres
        """
        super(NonFreePaintingBot, self).__init__()
        self.use_from_page = False
        self.generator = self.getGenerator()

    def getGenerator(self):
        """
        Get a generator of obviously non-free images based on (and go 3 years shorter for public domain days):
        * Inception more recent than 92 (95 minus 3) years ago (to cover US part)
        * Creator born more recent than 95 years ago
        * Creator died more recent than 68 (71 minus 3) years ago
        This should cover most of the unfree stuff and also the complicated US works.
        :return: A generator that yields ItemPages
        """
        query = """
SELECT DISTINCT ?item WHERE {
  ?item p:P4765 ?commonscompatible .
  ?item wdt:P31 wd:Q3305213 .
  { ?item wdt:P571 ?inception . FILTER(YEAR(?inception) > (YEAR(NOW())-92) ) } UNION
  { ?item wdt:P170 ?creator . ?creator wdt:P569 ?dob . FILTER(YEAR(?dob) > (YEAR(NOW())-95) ) } UNION
  { ?item wdt:P170 ?creator . ?creator wdt:P570 ?dod . FILTER(YEAR(?dod) > (YEAR(NOW())-68) ) } .
  }"""

        generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query,
                                                                                                      site=self.repo))
        return generator

    def treat_page_and_item(self, page, item):
        """Treat each item, page is probably None."""
        if not item.exists():
            return

        data = item.get()
        claims = data.get('claims')

        if not 'P4765' in claims:
            return

        currentclaim = claims.get('P4765')[0]
        claimjson = currentclaim.toJSON()
        claimjson['mainsnak']['property']='P6500'
        newclaim = pywikibot.Claim.fromJSON(self.repo, claimjson)

        summaryAdd = 'Adding [[Property:P6500]] because the image appears to be too recent to be Commons compatible'
        summaryRemove = 'Not a Commons compatible image, moved to [[Property:P6500]]'

        pywikibot.output('Moving the statement')

        item.addClaim(newclaim, summary=summaryAdd)
        item.removeClaims(currentclaim, summary=summaryRemove)


def main(*args):
    """
    """
    paintingBot = NonFreePaintingBot()
    paintingBot.run()

if __name__ == "__main__":
    main()
