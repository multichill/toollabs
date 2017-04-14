#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to find and add missing imdb links. It works per series by looking at the next and previous items

"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import requests
import re
import datetime
import time

class IMDBFinderBot:
    """
    A bot to add missing links based on Biografisch portaal van Nederland
    """
    def __init__(self, generator, seriesid):
        """
        Arguments:
        :param generator     - A generator of Wikidata items to work on
        :param series        - Qidof the series

        """
        self.repo = pywikibot.Site().data_repository()
        self.generator = generator
        self.series = pywikibot.ItemPage(self.repo, title=seriesid)
        self.imdbcache = self.buildImdbCache(self.series)
        # To prevent big loops or double edits
        self.processeditems = []

    def buildImdbCache(self, series):
        result ={}
        data = series.get()
        claims = data.get('claims')
        if not u'P345' in claims:
            pywikibot.output(u'Error: No IMDB id found')
            return result

        seriesimdb = claims.get(u'P345')[0].getTarget()

        mainurl = u'http://www.omdbapi.com/?i=%s'
        seasonurl = u'http://www.omdbapi.com/?i=%s&Season=%s'

        mainSeriesPage = requests.get(mainurl % (seriesimdb,))
        seasons = mainSeriesPage.json().get(u'totalSeasons')

        previous = u''
        previousTitle = u''
        previousReleased = u''
        current = u''
        currentTitle = u''
        currentReleased = u''
        next = u''
        nextTitle = u''
        nextReleased = u''

        try:
            for i in range(1, int(seasons)+1):
                seasonpage = requests.get(seasonurl % (seriesimdb,i))
                episodes = seasonpage.json().get('Episodes')
                if episodes:
                    for episode in episodes:
                        if not previous:
                            previous = episode.get('imdbID')
                            previousTitle = episode.get('Title')
                            previousReleased  = episode.get('Released')
                        elif not current:
                            current = episode.get('imdbID')
                            currentTitle = episode.get('Title')
                            currentReleased = episode.get('Released')
                        else:
                            next = episode.get('imdbID')
                            nextTitle = episode.get('Title')
                            nextReleased = episode.get('Released')

                            if not result:
                                # Result is empty, we need to add the first item
                                result[previous] = {u'previous' : u'',
                                                    u'previoustitle' : u'',
                                                    u'previousReleased' : u'',
                                                    u'title' : previousTitle,
                                                    u'released' : previousReleased,
                                                    u'next' : next,
                                                    u'nexttitle' : nextTitle,
                                                    u'nextReleased' : nextReleased}
                            result[current] = {u'previous' : previous,
                                               u'previoustitle' : previousTitle,
                                               u'previousReleased' : previousReleased,
                                               u'title' : currentTitle,
                                               u'released' :currentReleased,
                                               u'next' : next,
                                               u'nexttitle' : nextTitle,
                                               u'nextReleased' : nextReleased}
                            previous = current
                            previousTitle = currentTitle
                            previousReleased = currentReleased
                            current = next
                            currentTitle = nextTitle
                            currentReleased = nextReleased
                            next = u''
                            nextTitle = u''
                            nextReleased = u''
                time.sleep(1)

            result[current] = {u'previous' : previous,
                               u'previoustitle' : previousTitle,
                               u'previousReleased' : previousReleased,
                               u'title' : currentTitle,
                               u'released' :currentReleased,
                               u'next' : next,
                               u'nexttitle' : nextTitle,
                               u'nextReleased' : nextReleased}
        except ValueError:
            pywikibot.output(u'Ran into a value error while working on %s' % (mainurl % (seriesimdb,),))

        return result

    def run(self):

        if not self.imdbcache:
            pywikibot.output(u'The cache is empty, no point in running on %s' % (self.series,))

        for item in self.generator:
            pywikibot.output(u'Working on %s' % (item.title(),))
            self.addImdb(item)

    def addImdb(self, item):
        if item.title() in self.processeditems:
            pywikibot.output(u'Already processed %s, skipping it' % (item.title(),))
            return

        self.processeditems.append(item.title())
        data = item.get()
        claims = data.get('claims')
        if u'P345' in claims:
            self.addReleased(item, claims.get(u'P345')[0].getTarget())
            return True

        langs = [u'en', u'es', u'fr', u'de', u'nl']
        label = u''
        for lang in langs:
            if data.get('labels').get(lang):
                label = data.get('labels').get(lang)
                break

        if not label:
            #FIXME: Implement
            # label = data.get('labels').get(u'en')
            pywikibot.output(u'Did not find a label for %s' % (item.title(),))

        previousitem = None
        nextitem = None

        if u'P155' in claims:
            previousitem =  claims.get(u'P155')[0].getTarget()
        if u'P156' in claims:
            nextitem =  claims.get(u'P156')[0].getTarget()


        imdbid_from_previous = u''
        imdbtitle_from_previous = u''

        if previousitem:
            previousclaims = previousitem.get().get('claims')
            if u'P345' in previousclaims:
                previousimdb = previousclaims.get(u'P345')[0].getTarget()
                if previousimdb in self.imdbcache:
                    imdbid_from_previous = self.imdbcache[previousimdb].get(u'next')
                    imdbtitle_from_previous = self.imdbcache[previousimdb].get(u'nexttitle')

        imdbid_from_next = u''
        imdbtitle_from_next = u''

        if nextitem:
            nextclaims = nextitem.get().get('claims')
            if u'P345' in nextclaims:
                nextimdb = nextclaims.get(u'P345')[0].getTarget()
                if nextimdb in self.imdbcache:
                    imdbid_from_next = self.imdbcache[nextimdb].get(u'previous')
                    imdbtitle_from_next = self.imdbcache[nextimdb].get(u'previoustitle')

        if imdbid_from_previous and imdbid_from_next:
            if imdbid_from_previous==imdbid_from_next:
                if label==imdbtitle_from_previous:
                    newclaim = pywikibot.Claim(self.repo, u'P345')
                    newclaim.setTarget(imdbid_from_previous)
                    summary = u'Adding link based on same label and link from [[%s|previous]] and [[%s|next item]]' % (previousitem.title(), nextitem.title())
                    pywikibot.output(summary)
                    item.addClaim(newclaim, summary=summary)
                    self.addReleased(item, imdbid_from_previous)
                    return True
                else:
                    pywikibot.output(u'The label "%s" is not the same as imdb "%s", skipping' % (label,
                                                                                                 imdbtitle_from_previous))
                    return False
            else:
                pywikibot.output(u'We have a mix up, found "%s" & "%s", skipping' % (imdbid_from_previous,
                                                                                     imdbid_from_next))
                return False
        elif imdbid_from_previous:
            if label==imdbtitle_from_previous:
                newclaim = pywikibot.Claim(self.repo, u'P345')
                newclaim.setTarget(imdbid_from_previous)
                summary = u'Adding link based on same label and link from [[%s|previous item]]' % (previousitem.title(),)
                pywikibot.output(summary)
                item.addClaim(newclaim, summary=summary)
                self.addReleased(item, imdbid_from_previous)
                if nextitem:
                    self.addImdb(nextitem)
                return True
            else:
                pywikibot.output(u'The label "%s" is not the same as imdb "%s", skipping' % (label,
                                                                                             imdbtitle_from_previous))
                # This will make the bot iterate the linked list.
                if nextitem:
                    self.addImdb(nextitem)
        elif imdbid_from_next:
            if label==imdbtitle_from_next:
                newclaim = pywikibot.Claim(self.repo, u'P345')
                newclaim.setTarget(imdbid_from_next)
                summary = u'Adding link based on same label and link from [[%s|next item]]' % (nextitem.title(),)
                pywikibot.output(summary)
                item.addClaim(newclaim, summary=summary)
                self.addReleased(item, imdbid_from_next)
                if previousitem:
                    self.addImdb(previousitem)
                return True
            else:
                pywikibot.output(u'The label "%s" is not the same as imdb "%s", skipping' % (label,
                                                                                             imdbtitle_from_next))
                # This will make the bot iterate the linked list.
                if previousitem:
                    self.addImdb(previousitem)
        pywikibot.output(u'Something went wrong. Couldn\'t add anything to %s' % (item.title(),))

    def addReleased(self, item, imdbid):
        '''
        Add the first airdate to the item based on the imdbid
        '''
        pywikibot.output(u'Trying to add date to %s based on %s' % (item, imdbid))
        data = item.get()
        claims = data.get('claims')
        if u'P1191' in claims:
            return True
        if imdbid not in self.imdbcache:
            return False
        releasedate = self.imdbcache[imdbid].get('released')
        regex = u'^(\d\d\d\d)-(\d\d)-(\d\d)$'
        match = re.match(regex, releasedate)
        if not match:
            return False

        newdate = pywikibot.WbTime(year=int(match.group(1)),
                                    month=int(match.group(2)),
                                    day=int(match.group(3)),)

        newclaim = pywikibot.Claim(self.repo, u'P1191')
        newclaim.setTarget(newdate)
        pywikibot.output('Adding release date claim %s to %s' % (releasedate, item))
        item.addClaim(newclaim)
        refurl = pywikibot.Claim(self.repo, u'P854')
        refurl.setTarget(u'http://www.omdbapi.com/?i=%s' % (imdbid,))
        refdate = pywikibot.Claim(self.repo, u'P813')
        today = datetime.datetime.today()
        date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
        refdate.setTarget(date)
        newclaim.addSources([refurl, refdate])


def main(*args):
    """
    Main function. Grab a generator and pass it to the bot to work on
    """
    series = None
    report = None
    for arg in pywikibot.handle_args(args):
        if arg.startswith('-series:'):
            if len(arg) == 8:
                series = pywikibot.input(
                        u'Please enter the Q id of the series to work on:')
            else:
                series = arg[8:]
        elif arg.startswith('-report:'):
            if len(arg) == 8:
                report = pywikibot.input(
                        u'Please enter the name of the page to report on:')
            else:
                report = arg[8:]


    basequery = u"""SELECT DISTINCT ?item WHERE {
  ?item wdt:P31 wd:Q21191270 .
  ?item wdt:P179 wd:%s .
  MINUS { ?item wdt:P345 [] . ?item wdt:P1191 []}
  #{ ?item wdt:P155 ?otheritem } UNION { ?item wdt:P156 ?otheritem }
  #?otheritem wdt:P345 [] .
  }"""

    repo = pywikibot.Site().data_repository()
    if series:
        query = basequery % (series,)
        generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query,
                                                                                                      site=repo))
        imdbFinderBot = IMDBFinderBot(generator, series)
        imdbFinderBot.run()
    else:
        seriesquery = u"""SELECT DISTINCT ?item WHERE {
  ?episode wdt:P31 wd:Q21191270 .
  ?episode wdt:P179 ?item .
  MINUS { ?episode wdt:P345 [] . ?item wdt:P1191 []}
  { ?episode wdt:P155 ?otheritem } UNION { ?episode wdt:P156 ?otheritem }
  ?otheritem wdt:P345 [] .
  ?otheritem wdt:P179 ?item .
  }"""
        seriesgen = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(seriesquery,
                                                                                                      site=repo))
        for seriespage in seriesgen:
            series = seriespage.title()
            query = basequery % (series,)
            generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query,
                                                                                                          site=repo))
            imdbFinderBot = IMDBFinderBot(generator, series)
            imdbFinderBot.run()

if __name__ == "__main__":
    main()
