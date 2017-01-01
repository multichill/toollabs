#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to normalize inventory numbers. Currently only for Frans Hals Museum (Q574961) , but could be more general

"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import re

class NormalizationBot:
    """
    A bot to normalize inventory number of paintings on Wikidata
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.
            The dict in this generator needs to contain 'idpid' and 'collectionqid'
            * create       - Boolean to say if you want to create new items or just update existing

        """
        self.generator = generator
        self.repo = pywikibot.Site().data_repository()
        self.collectionitem = pywikibot.ItemPage(self.repo, u'Q574961')

    def run(self):
        """
        Starts the robot.
        """
        for item in self.generator:
            self.treat(item, self.collectionitem, u'^OS[- ](.*)$', u'os \\1')

    def treat(self, item, collection, pattern, replacement):

        data = item.get()
        claims = data.get('claims')

        summary = u'Normaliz'

        for invnumberclaim in claims.get(u'P217'):
            if invnumberclaim.has_qualifier(u'P195', self.collectionitem):
                invnumber = invnumberclaim.getTarget()
                newinvnumber = re.sub(pattern, replacement, invnumber)
                if newinvnumber != invnumber:
                    summary = u'Normalization of inventory numbers in [[%s]] from "%s" to "%s"' % (collection.title(),
                                                                                               invnumber,
                                                                                               newinvnumber)
                    pywikibot.output(summary)
                    invnumberclaim.changeTarget(newinvnumber, summary=summary)


def main():
    query=u"""SELECT DISTINCT ?item WHERE {
  ?item wdt:P195 wd:Q574961 .
  ?item wdt:P31 wd:Q3305213 .
  ?item p:P217 ?invstatement .
  ?invstatement ps:P217 ?inv .
  ?invstatement pq:P195 wd:Q574961 .
  FILTER regex (?inv, "^OS[- ](.*)$").
  }
LIMIT 2500"""
    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    normalizationBot = NormalizationBot(generator)
    normalizationBot.run()

if __name__ == "__main__":
    main()
