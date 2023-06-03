#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add missing depicted by (P1299) backlinks

If a painting:
1. Links to a person using main subject (P921)
2. Links to the same person using depicts (P180)
3. Has an image (P18)
4. Person uses the same image (P18)
5. Genre is portrait (Q134307) or self-portrait (Q192110)
Add the missing depicted by (P1299) backlink
"""
import pywikibot
from pywikibot import pagegenerators


class DepictedByPaintingBot:
    """
    A bot to add depicted by (P1299) links
    """
    def __init__(self):
        """
        """
        self.repo = pywikibot.Site().data_repository()
        self.generator = self.get_generator()

    def get_generator(self):
        """
        Get a generator of paintings
        :return: A generator that yields ItemPages
        """
        query = """
        SELECT DISTINCT ?item ?person ?image WHERE {
  ?item wdt:P31 wd:Q3305213 ;
        wdt:P921 ?person ;
        wdt:P180 ?person ;
        wdt:P18 ?image .
  ?person wdt:P31 wd:Q5 ;
          wdt:P18 ?image .
  MINUS { ?person wdt:P1299 [] } .
  { ?item wdt:P136 wd:Q134307 } UNION { ?item wdt:P136 wd:Q192110 } 
  } LIMIT 1000"""

        generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query,
                                                                                                        site=self.repo))
        return generator

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

            self.process_painting(item_page)

    def process_painting(self, item_page):
        """
        Process a single painting
        :param item_page: Pywikibot.ItemPage
        :return: Edit in plage
        """
        data = item_page.get()
        claims = data.get('claims')

        if 'P921' not in claims or 'P180' not in claims or 'P180' not in claims or 'P18' not in claims:
            pywikibot.output('Item missing one of he properties (P921/P180/P18), skipping')
            return

        # Do some basic sanity checking to prevent weird results
        if len(claims.get('P921')) > 1:
            pywikibot.output('Multiple main subject (P921) claims, skipping')
            return
        person = claims.get('P921')[0].getTarget()

        image2 = None
        if len(claims.get('P18')) == 2:
            # Also handle it if the painting has two images
            image2 = claims.get('P18')[1].getTarget()
        elif len(claims.get('P18')) > 2:
            pywikibot.output('Multiple image (P18) claims, skipping')
            return
        image = claims.get('P18')[0].getTarget()

        depicts_person = False
        for depicts_claim in claims.get('P180'):
            if depicts_claim.getTarget() == person:
                depicts_person = True
        if not depicts_person:
            pywikibot.output('Main subject (P921) claims doesn\'t match a depicts (P180) claim, skipping')
            return

        person_data = person.get()
        person_claims = person_data.get('claims')

        if 'P1299' in person_claims:
            pywikibot.output('Person already has depicted by (P1299) claim, all done')
            return

        same_image = False
        for image_claim in person_claims.get('P18'):
            if image_claim.getTarget() == image:
                same_image = True
            elif image2 and image_claim.getTarget() == image2:
                same_image = True
        if not same_image:
            pywikibot.output('Same image (P18) not found on person, skipping')
            return

        new_claim = pywikibot.Claim(self.repo, 'P1299')
        new_claim.setTarget(item_page)

        pywikibot.output('Adding %s --> %s' % (new_claim.getID(), new_claim.getTarget()))
        summary = 'linked [[Property:P921]], [[Property:P180]] and same [[Property:P18]]'
        person.addClaim(new_claim, summary=summary)


def main():

    depicted_by_painting_bot = DepictedByPaintingBot()
    depicted_by_painting_bot.run()


if __name__ == "__main__":
    main()
