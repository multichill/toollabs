#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to fix sorting of imprecise dates which have an earliest and latest date.

Inception is usually set to precision of a year. Sometimes it's set larger

"""

import pywikibot
from pywikibot import pagegenerators, WikidataBot

class InceptionSortBot(WikidataBot):
    """
    A bot fix sorting of inception
    """
    def __init__(self):
        """
        No arguments, bot makes it's own generator based on the genres
        """
        super(InceptionSortBot, self).__init__()
        self.use_from_page = False
        self.generator = self.getGenerator()
        self.precisionYears = { 6 : 1000,
                                7 : 100,
                                8 : 10,
                                9 : 1,
                                10 : 1,
                                11 : 1,
                                }

    def getGenerator(self):
        """
        Get a generator of inceptions to be fixed.
        :return: A generator that yields ItemPages
        """
        query = u"""
SELECT ?item ?inception ?earliestinception ?latestinception WHERE {
  ?item wdt:P31 wd:Q3305213 .
  ?item p:P571 ?inceptionstatement .
  ?inceptionstatement ps:P571 ?inception .
  ?inceptionstatement pq:P1319 ?earliestinception .
  ?inceptionstatement pq:P1326 ?latestinception .
  FILTER(!(?earliestinception <= ?inception && ?inception  <= ?latestinception ))
  FILTER(?earliestinception < ?latestinception) .
  FILTER(YEAR(?inception) > 1200)
  } ORDER BY ?inception
  LIMIT 5000"""

        generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query,
                                                                                                      site=self.repo))
        return generator

    def treat_page_and_item(self, page, item):
        """Treat each item, page is probably None."""
        if not item.exists():
            return

        data = item.get()
        claims = data.get('claims')

        if not u'P571' in claims:
            return

        if len(claims.get(u'P571')) > 1:
            return

        inceptionclaim = claims.get(u'P571')[0]
        earliestqualifier = inceptionclaim.qualifiers.get('P1319')[0]
        latestqualifier = inceptionclaim.qualifiers.get('P1326')[0]

        inceptiondate = inceptionclaim.getTarget()
        earliestdate = earliestqualifier.getTarget()
        latestdate = latestqualifier.getTarget()

        claimjson = inceptionclaim.toJSON()
        #pywikibot.output(claimjson)

        if inceptiondate.precision < 6:
            pywikibot.output(u'Precision shouldn\'t be smaller than millenia, skipping')
            return

        if not inceptiondate.precision < 9:
            pywikibot.output(u'Precision should be smaller than year, skipping')
            return

        if not earliestdate.precision > inceptiondate.precision or not latestdate.precision > inceptiondate.precision or \
                not earliestdate.precision==latestdate.precision:
            print (earliestdate.precision)
            print (latestdate.precision)
            print (inceptiondate.precision)
            pywikibot.output(u'Precision mismatch, skpping')
            return

        inceptionPrecisionYears = self.precisionYears.get(inceptiondate.precision)
        inceptionCurrentYear = inceptiondate.year
        inceptionStartYear = abs(inceptiondate.year/inceptionPrecisionYears) * inceptionPrecisionYears
        inceptionEndYear = inceptionStartYear + inceptionPrecisionYears

        earliestPrecisionYears = self.precisionYears.get(earliestdate.precision)
        if earliestPrecisionYears==1:
            earliestStartYear = earliestdate.year
            earliestEndYear = earliestdate.year
        else:
            earliestStartYear = abs(earliestdate.year/earliestPrecisionYears) * earliestPrecisionYears
            earliestEndYear = earliestStartYear + earliestPrecisionYears

        latestPrecisionYears = self.precisionYears.get(latestdate.precision)
        if latestPrecisionYears==1:
            latestStartYear = latestdate.year
            latestEndYear = latestdate.year
        else:
            latestStartYear = abs(latestdate.year/latestPrecisionYears) * latestPrecisionYears
            latestEndYear = latestStartYear + latestPrecisionYears

        if earliestStartYear < inceptionStartYear or inceptionEndYear < latestEndYear:
            pywikibot.output(u'%s < %s < %s' % (earliestStartYear, inceptionEndYear, latestEndYear , ))
            pywikibot.output(u'Qualifiers don\'t add up with the main inception. Skipping.')
            return

        pywikibot.output(u'Inception %s - %s (%s)' % (inceptionStartYear, inceptionEndYear, inceptionPrecisionYears))
        pywikibot.output(u'Earliest %s - %s (%s)' % (earliestStartYear, earliestEndYear, earliestPrecisionYears))
        pywikibot.output(u'Latest %s - %s (%s)' % (latestStartYear, latestEndYear, latestPrecisionYears))

        averageYear = int(abs((earliestStartYear + earliestEndYear + latestStartYear + latestEndYear)/4))

        if inceptionCurrentYear==averageYear:
            pywikibot.output(u'Looks like this one is already fixed, skipping')
            return

        summary = u'Updating sorting of inception from %s to %s' % (inceptionCurrentYear, averageYear)
        inceptiondate.year = averageYear
        pywikibot.output(summary)
        inceptionclaim.changeTarget(inceptiondate, summary=summary)


def main(*args):
    """
    """
    paintingBot = InceptionSortBot()
    paintingBot.run()

if __name__ == "__main__":
    main()
