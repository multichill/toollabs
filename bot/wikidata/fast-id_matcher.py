#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import VIAF ID (P214) and LCAuth ID (P244) statements from FAST-ID (P2163).
Might be more links in there that can be added later on.

"""
import pywikibot
from pywikibot import pagegenerators
import re
import datetime
import requests

class FastImportBot:
    """
    
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields wikidata item objects.

        """
        self.repo = pywikibot.Site().data_repository()
        self.generator = pagegenerators.PreloadingEntityGenerator(generator)
        self.fastitem = pywikibot.ItemPage(self.repo, u'Q3294867')
    
    def run(self):
        '''
        Work on all items
        '''

        for item in self.generator:
            if not item.exists():
                continue

            if item.isRedirectPage():
                item = item.getRedirectTarget()

            data = item.get()
            claims = data.get('claims')

            if not u'P2163' in claims:
                print u'No FAST-ID found, skipping'
                continue

            if u'P214' in claims and u'P244' in claims:
                # Already has both, great!
                continue

            fastid = claims.get(u'P2163')[0].getTarget()

            if not fastid:
                print u'FAST-ID is set to novalue, skipping'
                continue

            fasturl = u'http://id.worldcat.org/fast/%s'  % (fastid,)
            fasturlrdf = u'http://experimental.worldcat.org/fast/%s/rdf.xml' % (fastid,)
            fastPage = requests.get(fasturlrdf)

            # I hate XML so I just use a stupid regex
            linkregex = u'\<schema\:sameAs\>\s*\n\s*\<rdf\:Description rdf\:about\=\"([^\"]+)\"\>'

            for match in re.finditer(linkregex, fastPage.text):
                url = match.group(1)
                if url.startswith(u'http://id.loc.gov/authorities/names/'):
                    if u'P244' not in claims:
                        lcauthid = url.replace(u'http://id.loc.gov/authorities/names/', u'')
                        newclaim = pywikibot.Claim(self.repo, u'P244')
                        newclaim.setTarget(lcauthid)
                        pywikibot.output('Adding LCAuth ID %s claim to %s' % (lcauthid, item.title(),) )

                        # Default text is "‎Created claim: LCAuth ID (P244): 123, "
                        summary = u'based on FAST-ID %s' % (fastid,)

                        item.addClaim(newclaim, summary=summary)
                        self.addFastReference(item, newclaim, fasturl)

                elif url.startswith(u'https://viaf.org/viaf/'):
                    if u'P214' not in claims:
                        viafid = url.replace(u'https://viaf.org/viaf/', u'')

                        newclaim = pywikibot.Claim(self.repo, u'P214')
                        newclaim.setTarget(viafid)
                        pywikibot.output('Adding VIAF ID %s claim to %s' % (viafid, item.title(),) )

                        # Default text is "‎Created claim: VIAF ID (P214): 123, "
                        summary = u'based on FAST-ID %s' % (fastid,)

                        item.addClaim(newclaim, summary=summary)
                        self.addFastReference(item, newclaim, fasturl)

    def addFastReference(self, item, newclaim, fasturl):

        pywikibot.output('Adding new reference claim to %s' % item)

        refsource = pywikibot.Claim(self.repo, u'P248')
        refsource.setTarget(self.fastitem)

        refurl = pywikibot.Claim(self.repo, u'P854')
        refurl.setTarget(fasturl)

        refdate = pywikibot.Claim(self.repo, u'P813')
        today = datetime.datetime.today()
        date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
        refdate.setTarget(date)

        newclaim.addSources([refsource,refurl, refdate])

def main():
    """
    Do a query for items that do have  FAST-ID (P2163), but not and VIAF ID (P214) or LCAuth ID (P244)
    """
    query = u"""SELECT DISTINCT ?item WHERE {
  ?item wdt:P2163 [] .
  MINUS { ?item wdt:P214 []  . ?item wdt:P244 [] } .
}"""
    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))
    
    fastImportBot = FastImportBot(generator)
    fastImportBot.run()

if __name__ == "__main__":
    main()
