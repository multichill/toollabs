#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add genre is portrait to paintings based on the label

Configure what to look for at https://www.wikidata.org/wiki/User:BotMultichillT/portrait_paintings.js

"""
import json
import pywikibot
from pywikibot import pagegenerators

class PortraitPaintingsBot:
    """
    A bot to add genre to paintings on Wikidata
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields Wikidata items objects.

        """
        self.repo = pywikibot.Site().data_repository()
        self.langlabelpairs = self.getConfiguration()
        self.generator = self.getGeneratorSearch()

    def getConfiguration(self):
        """
        Grab the configuration of tuples to work on
        :return: List of tuples
        """
        result = []
        configpage = pywikibot.Page(self.repo, title=u'User:BotMultichillT/portrait paintings.js')
        (comments, sep, jsondata) = configpage.get().partition(u'[')
        jsondata = u'[' + jsondata
        configjson = json.loads(jsondata)
        for workitem in configjson:
            langlabelpair = (workitem.get('lang'), workitem.get('labelstart'))
            result.append(langlabelpair)
        return result

    def getGeneratorSparql(self):
        """
        Build a SPARQL query based on the langlabelpairs of items to work on
        :return: A generator that yields items
        """
        firstfilter = True
        query = """SELECT ?item ?label WHERE {
  ?item wdt:P31 wd:Q3305213 .
  MINUS { ?item wdt:P136 ?genre } .
  ?item rdfs:label ?label .
  FILTER("""
        for (lang, labelstart) in self.langlabelpairs:
            if not firstfilter:
                query = query + """\n||"""
            firstfilter = False
            query = query + """(LANG(?label)="%s" && REGEX(STR(?label), "^%s.*$"))""" % (lang, labelstart)
        query = query + """)\n} LIMIT 5000"""
        return pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=self.repo))

    def getGeneratorSearch(self):
        """
        Do searches and return the results
        :return: A generator that yields items
        """
        for (lang, labelstart) in self.langlabelpairs:
            search = f'inlabel:"{labelstart}"@{lang} haswbstatement:P31=Q3305213 -haswbstatement:P136'
            gen = pagegenerators.PreloadingEntityGenerator(pagegenerators.SearchPageGenerator(search, site=self.repo))
            for item in gen:
                yield item

    def run(self):
        """
        Starts the robot.
        """
        for item in self.generator:
            self.processPainting(item)

    def processPainting(self, item):
        """
        Work on a individual painting. Add the genre if a label is found
        """
        data = item.get()
        claims = data.get('claims')

        if u'P136' in claims:
            # Already done
            return

        gotmatch = self.findLabelMatch(item)

        if not gotmatch:
            return

        summary = u'based on (%s)"%s" ' % gotmatch

        genreclaim = pywikibot.Claim(self.repo, u'P136')
        genreclaim.setTarget(pywikibot.ItemPage(self.repo, title=u'Q134307'))
        pywikibot.output('Adding genre claim to %s %s' % (item.title(), summary))
        item.addClaim(genreclaim, summary=summary)

    def findLabelMatch(self, item):
        """
        Try to find a match in the item.
        :param item: The paiting ItemPage
        :return: Tuple (lang, labelstart) if match is found
        """
        labels = item.get().get('labels')
        for (itemlang, itemlabel) in labels.items():
            for (lang, labelstart) in self.langlabelpairs:
                if itemlang==lang:
                    if itemlabel.startswith(labelstart):
                        gotmatch = (lang, labelstart)
                        return gotmatch
        return None


def main():
    """
    Just a main function to start the robot
    """
    portraitPaintingsBot = PortraitPaintingsBot()
    portraitPaintingsBot.run()

if __name__ == "__main__":
    main()
