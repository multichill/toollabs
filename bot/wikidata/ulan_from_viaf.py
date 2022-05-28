#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import ULAN statements from viaf. Could be expanded later to something more general

"""
import json
import pywikibot
from pywikibot import pagegenerators
import re
import datetime
import requests

class ViafImportBot:
    """
    
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields wikidata item objects.

        """
        
        self.repo = pywikibot.Site().data_repository()
        self.generator = pagegenerators.PreloadingEntityGenerator(generator)
        self.viafitem = pywikibot.ItemPage(self.repo, u'Q54919')

    def run(self):
        """
        Work on all items
        """

        for item in self.generator:
            if not item.exists():
                continue

            if item.isRedirectPage():
                item = item.getRedirectTarget()

            data = item.get()
            claims = data.get('claims')

            if u'P214' not in claims:
                print u'No viaf found, skipping'
                continue

            if u'P245' in claims:
                # Already has ULAN, great!
                continue

            viafid = claims.get(u'P214')[0].getTarget()

            if not viafid:
                print u'Viaf is set to novalue, skipping'
                continue
            
            viafurl = u'http://www.viaf.org/viaf/%s/' % (viafid,)
            viafurljson = u'%sjustlinks.json' % (viafurl,)
            viafPage = requests.get(viafurljson)

            try:
                viafPageDataDataObject = viafPage.json()
            except ValueError:
                pywikibot.output('On %s the VIAF link %s returned this junk:\n %s' % (item.title(),
                                                                                      viafurljson,
                                                                                      viafPage.text))
                continue

            if isinstance(viafPageDataDataObject, dict) and viafPageDataDataObject.get(u'JPG'):
                ulanid = viafPageDataDataObject.get(u'JPG')[0]

                newclaim = pywikibot.Claim(self.repo, u'P245')
                newclaim.setTarget(ulanid)
                pywikibot.output('Adding ULAN %s claim to %s' % (ulanid, item.title(), ))

                # Default text is "‎Created claim: ULAN identifier (P245): 500204732, "
                summary = u'based on VIAF %s' % (viafid,)
                
                item.addClaim(newclaim, summary=summary)

                pywikibot.output('Adding new reference claim to %s' % item)

                refsource = pywikibot.Claim(self.repo, u'P248')
                refsource.setTarget(self.viafitem)
                
                refurl = pywikibot.Claim(self.repo, u'P854')
                refurl.setTarget(viafurl)
                
                refdate = pywikibot.Claim(self.repo, u'P813')
                today = datetime.datetime.today()
                date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
                refdate.setTarget(date)
                
                newclaim.addSources([refsource, refurl, refdate])


def main():
    """
    Do a query for items that do have RKDartists (P650) and VIAF (P214), but no ULAN (P245)
    :return:
    """

    query = u"""SELECT ?item WHERE {
  ?item wdt:P650 [] .
  ?item wdt:P214 [] .
  MINUS { ?item wdt:P245 [] }
}"""
    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))
    
    viafImportBot = ViafImportBot(generator)
    viafImportBot.run()

if __name__ == "__main__":
    main()
