#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to replace some Commons compatible image available at URL (P4765)  with  non-free artwork image URL (P6500)
* https://www.wikidata.org/wiki/Property:P4765
* https://www.wikidata.org/wiki/Property:P6500

Sometimes some obviously non-free images slip through the cracks. This bot moves the suggestions to a different property
so we don't end up accidentally uploading these images. It takes the existing claim and change the P target.

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
        Get a generator of obviously non-free images based on:
        * Inception more recent than 95 years ago (to cover US part)
        * Creator born more recent than 95 years ago
        * Creator died more recent than 70 years ago
        This should cover most of the unfree stuff and some false positives if run on US works.
        :return: A generator that yields ItemPages
        """
        query = u"""
SELECT DISTINCT ?item WHERE {
  ?item wdt:P195 wd:Q18600731 . # RCE for now, that's over 3800 suggestions. Be careful with other collections!
  ?item p:P4765 ?commonscompatible .
  ?item wdt:P31 wd:Q3305213 .
  { ?item wdt:P571 ?inception . FILTER(YEAR(?inception) > (YEAR(NOW())-95) ) } UNION
  { ?item wdt:P170 ?creator . ?creator wdt:P569 ?dob . FILTER(YEAR(?dob) > (YEAR(NOW())-95) ) } UNION
  { ?item wdt:P170 ?creator . ?creator wdt:P570 ?dod . FILTER(YEAR(?dod) > (YEAR(NOW())-70) ) } .
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

        if not u'P4765' in claims:
            return

        currentclaim = claims.get('P4765')[0]
        claimjson = currentclaim.toJSON()
        claimjson[u'mainsnak'][u'property']=u'P6500'
        newclaim = pywikibot.Claim.fromJSON(self.repo, claimjson)

        summaryAdd = u'Adding [[Property:P6500]] because the image doesn\'t appear to be Commons compatible'
        summaryRemove = u'Not a Commons compatible image, moved to [[Property:P6500]]'

        pywikibot.output(u'Moving the statement')

        item.addClaim(newclaim, summary=summaryAdd)
        item.removeClaims(currentclaim, summary=summaryRemove)


def main(*args):
    """
    """
    paintingBot = NonFreePaintingBot()
    paintingBot.run()

if __name__ == "__main__":
    main()
