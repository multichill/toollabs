#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to sync depicts (P18) and main subject (P921) for portrait paintings
"""
import pywikibot
from pywikibot import pagegenerators

class PortraitPaintingsSyncHumanBot:
    """
    A bot to sync portrait paintings on Wikidata
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields Wikidata items objects.

        """
        self.repo = pywikibot.Site().data_repository()
        self.portrait = pywikibot.ItemPage(self.repo, 'Q134307')
        self.human = pywikibot.ItemPage(self.repo, 'Q5')
        self.generator = self.get_generator_sparql()

    def get_generator_sparql(self):
        """
        Do the two SPARQL queries to give the items to work on.
        First query gets the paintings without main subject, but with human depicts
        Second query gets the paintings without depicts, but with human main subject
        :return: A generator that yields items
        """
        queries = ["""SELECT DISTINCT ?item WHERE {
  ?item wdt:P31 wd:Q3305213 ;
        wdt:P136 wd:Q134307 .
  MINUS { ?item wdt:P921 [] } .
  MINUS { ?item wdt:P136 ?genre. FILTER(?genre!=wd:Q134307) } .
  ?item wdt:P180 ?human .
  ?human wdt:P31 wd:Q5 ;
         wdt:P569 ?dob ;
  FILTER(YEAR(?dob) > 1000 && YEAR(?dob) < 2050)
  FILTER NOT EXISTS { ?human wdt:P31 wd:Q20643955 }
  FILTER NOT EXISTS { ?human wdt:P411 [] } 
  } ORDER BY DESC(?sitelinks) LIMIT 5000""",
                   """SELECT DISTINCT ?item WHERE {
  ?item wdt:P31 wd:Q3305213 ;
        wdt:P136 wd:Q134307 .
  MINUS { ?item wdt:P180 [] } .
  MINUS { ?item wdt:P136 ?genre. FILTER(?genre!=wd:Q134307) } .
  ?item wdt:P921 ?human .
  ?human wdt:P31 wd:Q5 ;
         wdt:P569 ?dob ;
  FILTER(YEAR(?dob) > 1000 && YEAR(?dob) < 2050)
  FILTER NOT EXISTS { ?human wdt:P31 wd:Q20643955 }
  FILTER NOT EXISTS { ?human wdt:P411 [] } 
  } ORDER BY DESC(?sitelinks) LIMIT 500"""
                   ]
        for query in queries:
            gen = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query,
                                                                                                      site=self.repo))
            for item in gen:
                yield item

    def run(self):
        """
        Starts the robot.
        """
        for item in self.generator:
            self.process_painting(item)

    def process_painting(self, item):
        """
        Work on a individual painting. Add the missing depicts or main subject
        """
        pywikibot.output('Working on %s' % (item.title()))
        data = item.get()
        claims = data.get('claims')

        if 'P136' not in claims:
            pywikibot.output('No genre statement, skipping.')
            return

        if len(claims.get('P136')) != 1:
            pywikibot.output('Multiple genre statement founds, skipping.')
            return

        if claims.get('P136')[0].getTarget() != self.portrait:
            pywikibot.output('Genre is not portrait, skipping.')
            return

        if 'P180' in claims and 'P921' in claims:
            pywikibot.output('Depicts (P180) and main subject (P921) both found, done.')
            return

        elif 'P180' in claims and 'P921' not in claims:
            # Working on depicts to main subject
            if len(claims.get('P180')) != 1:
                human_item = self.get_single_human(claims.get('P180'))
                if not human_item:
                    pywikibot.output('Multiple depicts statement founds and not able to extract single, skipping.')
                    return
            else:
                human_item = claims.get('P180')[0].getTarget()
            self.add_human(item, human_item, 'P180', 'P921')

        elif 'P921' in claims and 'P180' not in claims:
            # Working on main subject to depicts
            if len(claims.get('P921')) != 1:
                pywikibot.output('Multiple main subject statement founds, skipping.')
                return
            human_item = claims.get('P921')[0].getTarget()
            self.add_human(item, human_item, 'P921', 'P180')

    def get_single_human(self, claims):
        """
        Try to extra single human from a list of claims

        :param claims: List of claims to extract it from
        :return: ItemPage or False
        """
        human_item = None
        humans_found = 0

        for claim in claims:
            check_item = claim.getTarget()
            if check_item.isRedirectPage():
                check_item = check_item.getRedirectTarget()
            data = check_item.get()
            item_claims = data.get('claims')
            if item_claims.get('P31') and len(item_claims.get('P31')) == 1 and \
                    item_claims.get('P31')[0].getTarget() == self.human:
                human_item = check_item
                humans_found +=1

        if human_item and humans_found == 1:
            return human_item
        else:
            pywikibot.output(f'Multiple ({humans_found}) human depicts statement founds, skipping.')
            return False

    def add_human(self, painting_item, human_item, source_property, target_property):
        """
        Add the human statement. We don't actually check if it's a human because that's in the SPARQL queries

        :param painting_item: Item of the portrait painting
        :param human_item: Item of the human to add
        :param source_property: Statement from which we got it
        :param target_property: Statement to put it in
        :return: Nothing, edit in place
        """
        summary = f'copied from [[Property:{source_property}]]'

        claim = pywikibot.Claim(self.repo, target_property)
        claim.setTarget(human_item)
        pywikibot.output(f'Adding {target_property} claim {summary}')
        painting_item.addClaim(claim, summary=summary)


def main():
    """
    Just a main function to start the robot
    """
    portrait_paintings_bot = PortraitPaintingsSyncHumanBot()
    portrait_paintings_bot.run()

if __name__ == "__main__":
    main()
