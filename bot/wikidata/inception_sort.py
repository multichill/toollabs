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
        self.repo = pywikibot.Site().data_repository()
        self.sort_generator = self.get_sort_generator()
        self.somevalue_generator = self.get_somevalue_generator()
        self.precisionYears = { 6 : 1000,
                                7 : 100,
                                8 : 10,
                                9 : 1,
                                10 : 1,
                                11 : 1,
                                }

    def get_sort_generator(self):
        """
        Get a generator of inceptions to be fixed.
        :return: A generator that yields ItemPages
        """
        query = u"""SELECT ?item ?inception ?earliestinception ?latestinception WHERE {
  ?item wdt:P31 wd:Q3305213 ;
        p:P571 [ ps:P571 ?inception ; pq:P1319 ?earliestinception ; pq:P1326 ?latestinception ].
  FILTER(YEAR(?inception) > 1200 && (!(?earliestinception <= ?inception && ?inception  <= ?latestinception )) && ?earliestinception < ?latestinception) .  
  } 
  LIMIT 1000"""
        generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query,
                                                                                                      site=self.repo))
        return generator

    def get_somevalue_generator(self):
        """
        Get a generator of inceptions to be fixed.
        :return: A generator that yields ItemPages
        """
        query = """SELECT ?item ?inception ?earliestinception ?latestinception WHERE {
  ?item wdt:P31 wd:Q3305213 ;
        p:P571 [ ps:P571 ?inception ; pq:P1319 ?earliestinception ; pq:P1326 ?latestinception ].
  FILTER(wikibase:isSomeValue(?inception) && ?earliestinception < ?latestinception && YEAR(?earliestinception) > 1200 && YEAR(?latestinception) > 1200)
  } LIMIT 1000"""
        generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query,
                                                                                                        site=self.repo))
        return generator

    def run(self):
        """
        Starts the robot.
        """
        for item in self.sort_generator:
            self.fix_inception_sort(item)

        for item in self.somevalue_generator:
            self.fix_inception_somevalue(item)


    def fix_inception_sort(self, item):
        """Treat each item."""
        if not item.exists():
            return

        data = item.get()
        claims = data.get('claims')

        if 'P571' not in claims:
            return

        if len(claims.get('P571')) > 1:
            return

        inceptionclaim = claims.get('P571')[0]
        earliestqualifier = inceptionclaim.qualifiers.get('P1319')[0]
        latestqualifier = inceptionclaim.qualifiers.get('P1326')[0]

        inceptiondate = inceptionclaim.getTarget()
        earliestdate = earliestqualifier.getTarget()
        latestdate = latestqualifier.getTarget()

        if inceptiondate.precision < 6:
            pywikibot.output(u'Precision should at least be millenia, skipping')
            return

        if not inceptiondate.precision < 9:
            pywikibot.output('Precision should be less precise than year, skipping')
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
        inceptionStartYear = inceptiondate.year - inceptionPrecisionYears
        inceptionEndYear = inceptiondate.year + inceptionPrecisionYears

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

    def fix_inception_somevalue(self, item):
        """Treat each item."""
        if not item.exists():
            return

        data = item.get()
        claims = data.get('claims')

        if 'P571' not in claims:
            return

        if len(claims.get('P571')) > 1:
            return

        inceptionclaim = claims.get('P571')[0]
        if inceptionclaim.getTarget() or inceptionclaim.getSnakType()!='somevalue':
            pywikibot.output('I expected somevalue, but I got something else')
            return
        earliestqualifier = inceptionclaim.qualifiers.get('P1319')[0]
        latestqualifier = inceptionclaim.qualifiers.get('P1326')[0]

        # Just use the year and don't look at precision here
        earliestyear = earliestqualifier.getTarget().year
        latestyear = latestqualifier.getTarget().year
        averageYear = int(abs((earliestyear + latestyear)/2))

        # For things like 1901-2000 I want to end with century
        incstart = str(earliestyear)
        normalend = str(latestyear)
        lowerend = str(latestyear-1)

        if len(incstart) != 4 or len(normalend) != 4:
            return
        precision = 5 # 10 millenia

        # The normal loop
        if incstart[0] == normalend[0]:
            precision = 6  # millenium
            if incstart[1] == normalend[1]:
                precision = 7  # century
                if incstart[2] == normalend[2]:
                    precision = 8  # decade
        # The one lower loop. Can't mix them, will give funky results with things like 1701 and 1800
        if incstart[0] == lowerend[0]:
            if precision < 6:
                precision = 6  # millenium
            if incstart[1] == lowerend[1]:
                if precision < 7:
                    precision = 7  # century
                # Don't do it for decade

        newdate = pywikibot.WbTime(year=averageYear, precision=precision)
        summary = 'Replacing somevalue with a date %s based on earliest %s and latest %s' % (averageYear, earliestyear, latestyear)
        pywikibot.output(summary)
        inceptionclaim.changeTarget(newdate, summary=summary)


def main(*args):
    """
    """
    paintingBot = InceptionSortBot()
    paintingBot.run()

if __name__ == "__main__":
    main()
