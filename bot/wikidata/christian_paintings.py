#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add religion or worldview (P140) -> Christianity (Q5043) to Christian religious paintings

"""
import pywikibot
from pywikibot import pagegenerators

class ChristianPaintingsBot:
    """
    A bot to add genre to paintings on Wikidata
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields Wikidata items objects.

        """
        self.repo = pywikibot.Site().data_repository()
        self.generator = self.get_generator()
        self.religious_art = pywikibot.ItemPage(self.repo, 'Q2864737')
        self.christianity = pywikibot.ItemPage(self.repo, 'Q5043')

    def get_generator(self):
        """
        Get items that have genre religious are and main subject set, but no  religion or worldview (P140)

        :return:
        """
        query = """SELECT DISTINCT ?item WHERE {
  ?item wdt:P136 wd:Q2864737;
        wdt:P31 wd:Q3305213 ;
        wdt:P921 ?mainsubject .
  MINUS { ?item wdt:P140 [] } .
  { ?mainsubject wdt:P140 wd:Q5043 } UNION 
  { ?mainsubject wdt:P31 wd:Q20643955 }.
}"""
        return pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query,
                                                                                                   site=self.repo))

    def run(self):
        """
        Starts the robot.
        """
        for item in self.generator:
            self.process_painting(item)

    def process_painting(self, item):
        """
        Work on a individual painting.
        """
        data = item.get()
        claims = data.get('claims')

        pywikibot.output('Working on %s' % (item.title(),))

        if 'P140' in claims:
            pywikibot.output('Already has a religion or worldview, done')
            return

        if 'P136' not in claims:
            pywikibot.output('No genre, skipping')
            return

        found_religious_art = False
        for claim in claims.get('P136'):
            if claim.getTarget() == self.religious_art:
                found_religious_art = True
        if not found_religious_art:
            pywikibot.output('No religious art genre found, skipping')
            return

        if 'P921' not in claims:
            pywikibot.output('No main subject, skipping')
            return

        if len(claims.get('P921')) != 1:
            pywikibot.output('Multiple main subjects, skipping')
            return

        main_subject = claims.get('P921')[0].getTarget()
        christian_subject = self.check_main_subject(main_subject)

        if not christian_subject:
            pywikibot.output('Main subject %s does not look correct, skipping' % (main_subject.title(),))
            return

        new_claim = pywikibot.Claim(self.repo, 'P140')
        new_claim.setTarget(self.christianity)
        summary = 'based on [[Property:P136]] → [[Q2864737]] & [[Property:P921]] → [[%s]]' % (main_subject.title(),)
        pywikibot.output('Adding religion claim to %s %s' % (item.title(), summary))
        item.addClaim(new_claim, summary=summary)

    def check_main_subject(self, main_subject):
        """
        Check if based on the main subject, this is Christian art

        :return: boolean
        """
        data = main_subject.get()
        claims = data.get('claims')
        if 'P140' in claims:
            for claim in claims.get('P140'):
                if claim.getTarget() == self.christianity:
                    return True

        if 'P31' in claims:
            for claim in claims.get('P31'):
                if claim.getTarget().title() == 'Q20643955':  #  human biblical figure (Q20643955)
                    return True

        # Not sure how to handle saints yet

        return False


def main():
    """
    Just a main function to start the robot
    """
    christian_paintings_bot = ChristianPaintingsBot()
    christian_paintings_bot.run()

if __name__ == "__main__":
    main()
