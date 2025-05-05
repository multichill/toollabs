#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add copyright status (P6216) -> public domain (Q19652) to paintings
where the painter died more than 100 years ago.
"""
import pywikibot
from pywikibot import pagegenerators

class PublicDomainPaintingsBot:
    """
    A bot to add copyright status to paintings on Wikidata
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields Wikidata items objects.

        """
        self.cutoff_year = 1900
        self.repo = pywikibot.Site().data_repository()
        self.generator = self.get_generator()
        self.public_domain = pywikibot.ItemPage(self.repo, 'Q19652')
        self.author_death = pywikibot.ItemPage(self.repo, 'Q29940705')
        self.countries_pma = pywikibot.ItemPage(self.repo, 'Q60332278')

    def get_generator(self):
        """
        Get items that creator who died before 1900 and no copyright status
        :return:
        """
        query = """SELECT DISTINCT ?item WHERE {
  ?item wdt:P31 wd:Q3305213 ;
        wdt:P170 ?creator .
  MINUS { ?item wdt:P6216 [] } .
  ?creator wdt:P570 ?dod .
  FILTER(YEAR(?dod) < %s) . 
}""" % (self.cutoff_year, )
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

        if 'P6216' in claims:
            pywikibot.output('Already has a copyright status, done')
            return

        if 'P170' not in claims:
            pywikibot.output('No creator, skipping')
            return

        # Currently only able to handle paintings with one painter
        if len(claims.get('P170')) != 1:
            pywikibot.output('Multiple creators found, skipping')
            return

        rank = claims.get('P170')[0].getRank()
        if rank != 'normal':
            pywikibot.output('Statement has rank %s, expected normal, skipping' % (rank,) )
            return

        creator = claims.get('P170')[0].getTarget()
        year_of_death = self.get_year_of_death_for_creator(creator)

        if not year_of_death:
            pywikibot.output('Unable to get a valid year of death from %s, skipping' % (creator.title(),))
            return

        new_claim = pywikibot.Claim(self.repo, 'P6216')
        new_claim.setTarget(self.public_domain)

        # determination method or standard (P459) → 100 years or more after author(s) death
        new_qualifier = pywikibot.Claim(self.repo, 'P459', is_qualifier=True)
        new_qualifier.setTarget(self.author_death)
        new_claim.qualifiers['P459'] = [new_qualifier]

        # applies to jurisdiction (P1001) → countries with 100 years pma or shorter (Q60332278)
        new_qualifier = pywikibot.Claim(self.repo, 'P1001', is_qualifier=True)
        new_qualifier.setTarget(self.countries_pma)
        new_claim.qualifiers['P1001'] = [new_qualifier]

        summary = 'based on [[Property:P170]] → [[%s]] (died %s)' % (creator.title(), year_of_death)
        pywikibot.output('Adding copyright claim to %s %s' % (item.title(), summary))
        item.addClaim(new_claim, summary=summary)

    def get_year_of_death_for_creator(self, creator):
        """
        Check if the creator died before 1900 so we know it's public domain
        If multiple dates exist: Check all

        Return the year of death.

        #TODO: Expand later to also be able to handle century

        :return: boolean
        """
        if not creator:
            # We might have encountered an item with unknown value (changed after query)
            return False
        data = creator.get()
        claims = data.get('claims')
        if 'P570' not in claims:
            return False

        # Check if all the dates are good
        year_of_death = False
        for claim in claims.get('P570'):
            if not claim:
                # Novalue? Not sure
                return False
            dod = claim.getTarget()
            if not dod:
                # Unknown value
                return False
            if dod.precision < 9:
                # Precision is worst than a year, can probably change that to century later
                return False
            if dod.year >= self.cutoff_year:
                return False
            # Looks good, let's get the date
            if not year_of_death:
                year_of_death = dod.year
            elif year_of_death == dod.year:
                # Found the same year of death in the other statement
                pass
            else:
                # It's different so skipping this one
                return False

        # Return the year of death we found
        return year_of_death


def main():
    """
    Just a main function to start the robot
    """
    public_domain_paintings_bot = PublicDomainPaintingsBot()
    public_domain_paintings_bot.run()

if __name__ == "__main__":
    main()
