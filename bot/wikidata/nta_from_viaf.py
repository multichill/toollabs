#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import  National Thesaurus for Author Names ID (P1006) statements from viaf.

See https://www.wikidata.org/wiki/Property:P1006

Viaf contains some broken links so check that the entry at http://data.bibliotheken.nl/ actually exists
and links back to the same viaf item.

"""
import pywikibot
from pywikibot import pagegenerators
import requests
import datetime

class ViafImportBot:
    """
    Bot to import NTA links from VIAF
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields wikidata item objects.
        """
        self.repo = pywikibot.Site().data_repository()
        self.generator = pagegenerators.PreloadingItemGenerator(generator)
        self.viafitem = pywikibot.ItemPage(self.repo, u'Q54919')
    
    def run (self):
        '''
        Work on all items
        '''
        validlinks = 0
        brokenlinks = 0

        for item in self.generator:
            if not item.exists():
                continue

            if item.isRedirectPage():
                item = item.getRedirectTarget()

            data = item.get()
            claims = data.get('claims')

            if not u'P214' in claims:
                pywikibot.output(u'No viaf found, skipping')
                continue

            if u'P1006' in claims:
                # Already has National Thesaurus for Author Names ID, great!
                continue

            viafid = claims.get(u'P214')[0].getTarget()

            if not viafid:
                pywikibot.output(u'Viaf is set to novalue, skipping')
                continue
            
            viafurl = u'http://viaf.org/viaf/%s' % (viafid,)
            viafurljson = u'%s/justlinks.json' % (viafurl,)
            try:
                viafPage = requests.get(viafurljson)
            except requests.HTTPError as e:
                pywikibot.output('On %s the VIAF link %s returned this HTTPError %s: %s' % (item.title(), viafurljson, e.errno, e.strerror))
            except requests.exceptions.ConnectionError as e:
                pywikibot.output('On %s the VIAF link %s returned this HTTPError %s: %s' % (item.title(), viafurljson, e.errno, e.strerror))

            try:
                viafPageDataDataObject = viafPage.json()
            except ValueError:
                pywikibot.output('On %s the VIAF link %s returned this junk:\n %s' % (item.title(), viafurljson, viafPage.text))
                continue

            if not isinstance(viafPageDataDataObject, dict):
                pywikibot.output('On %s the VIAF link %s did not return a dict:\n %s' % (item.title(), viafurljson, viafPage.text))
                continue

            if viafPageDataDataObject.get(u'NTA'):
                ntaid = viafPageDataDataObject.get(u'NTA')[0]

                ntaurl = u'http://data.bibliotheken.nl/id/thes/p%s' % (ntaid,)
                ntapage = requests.get(ntaurl)
                if not ntapage.status_code==200:
                    pywikibot.output(u'Viaf %s points to broken NTA url: %s' % (viafurljson, ntaurl,))
                    brokenlinks = brokenlinks + 1
                    continue

                if not viafurl in ntapage.text:
                    pywikibot.output(u'No backlink found on %s to viaf %s' % (ntaurl, viafurl, ))
                    continue

                newclaim = pywikibot.Claim(self.repo, u'P1006')
                newclaim.setTarget(ntaid)
                pywikibot.output('Adding National Thesaurus for Author Names ID %s claim to %s (based on bidirectional viaf<->nta links)' % (ntaid, item.title(),) )

                summary = u'based on VIAF %s (with bidirectional viaf<->nta links)' % (viafid,)
                
                item.addClaim(newclaim, summary=summary)

                pywikibot.output('Adding new reference claim to %s' % item)

                refurl = pywikibot.Claim(self.repo, u'P214')
                refurl.setTarget(viafid)

                refsource = pywikibot.Claim(self.repo, u'P248')
                refsource.setTarget(self.viafitem)

                refdate = pywikibot.Claim(self.repo, u'P813')
                today = datetime.datetime.today()
                date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
                refdate.setTarget(date)
                
                newclaim.addSources([refurl, refsource, refdate])
                validlinks = validlinks + 1

        pywikibot.output(u'I found %s valid links and %s broken links' % (validlinks, brokenlinks,))


def main():
    repo = pywikibot.Site().data_repository()
    query = u"""SELECT ?item WHERE {
  ?item wdt:P214 ?viafid .
  ?item wdt:P31 wd:Q5 .
  MINUS { ?item wdt:P1006 [] } .
  } LIMIT 400000"""
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    viafImportBot = ViafImportBot(generator)
    viafImportBot.run()

if __name__ == "__main__":
    main()
