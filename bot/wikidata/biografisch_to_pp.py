#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
OBSOLETE Bot to import missing Parlement & Politiek ID ( http://www.parlement.com/ ) links based on
Biografisch portaal van Nederland ( http://www.biografischportaal.nl )

The bot does a SPARQL query to find a list of potential candidates and loops over these.

OBSOLETE, use biografisch_finder.py

"""
import pywikibot
from pywikibot import pagegenerators
import requests
import re
import datetime

class PPImporterBot:
    """
    A bot to enrich humans on Wikidata
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields ItemPage objects.

        """
        self.generator = generator
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

            data = itempage.get()
            claims = data.get('claims')

            # Do some checks so we are sure we found exactly one inventory number and one collection
            if u'P651' not in claims:
                pywikibot.output(u'No Biografisch portaal found, skipping')
                continue

            if u'P1749' in claims:
                pywikibot.output(u'Already has Parlement & Politiek ID, skipping')
                continue

            bioid = claims.get(u'P651')[0].getTarget()
            biourl = u'http://www.biografischportaal.nl/persoon/%s?' % (bioid,)
            refurl = biourl

            # Do some checking if it actually exists?
            bioPage = requests.get(biourl, verify=False)

            ppregex = u'href=\"http:\/\/www\.parlementairdocumentatiecentrum\.nl\/id\/([^\"]+)\"\>'

            ppmatch = re.search(ppregex, bioPage.text)
            if ppmatch:
                ppid = ppmatch.group(1)
                # Add the P&P id to the item
                newclaim = pywikibot.Claim(self.repo, u'P1749')
                newclaim.setTarget(ppid)
                summary = u'Adding link to Parlement & Politiek based on link on Biografisch Portaal number %s' % (bioid,)
                pywikibot.output(summary)
                itempage.addClaim(newclaim, summary=summary)
                self.addReference(itempage, newclaim, refurl)

    def addItemStatement(self, item, pid, qid):
        '''
        Helper function to add a statement
        '''
        if not qid:
            return False

        claims = item.get().get('claims')
        if pid in claims:
            return

        newclaim = pywikibot.Claim(self.repo, pid)
        destitem = pywikibot.ItemPage(self.repo, qid)
        newclaim.setTarget(destitem)
        pywikibot.output(u'Adding %s->%s to %s' % (pid, qid, item))
        item.addClaim(newclaim)
        return newclaim
        #self.addReference(item, newclaim, url)

    def addReference(self, item, newclaim, url):
        """
        Add a reference with a retrieval url and todays date
        """
        pywikibot.output('Adding new reference claim to %s' % item)
        refurl = pywikibot.Claim(self.repo, u'P854') # Add url, isReference=True
        refurl.setTarget(url)
        refdate = pywikibot.Claim(self.repo, u'P813')
        today = datetime.datetime.today()
        date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
        refdate.setTarget(date)
        newclaim.addSources([refurl, refdate])


def main():
    """
    Main function. Grab a generator and pass it to the bot to work on
    """
    # Does have biografisch portaal, but no Parlement & Politiek ID
    query = u"""SELECT DISTINCT ?item WHERE {
  ?item wdt:P651 [] .
  MINUS { ?item wdt:P1749 [] }
}"""
    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    ppImporterBot = PPImporterBot(generator)
    ppImporterBot.run()

if __name__ == "__main__":
    main()
