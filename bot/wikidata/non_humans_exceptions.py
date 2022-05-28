#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add non-human exceptions to properties

See for example https://www.wikidata.org/wiki/Property:P650
It's a pain to manually maintain these exceptions

"""

import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql

class AddExceptionsBot:
    """
    A bot to add gender to people
    """
    def __init__(self, wdprop):
        """
        Arguments:
            * wdprop    - The Wikidata property to work on
        """
        self.wdprop = wdprop
        self.repo = pywikibot.Site().data_repository()
        self.property = pywikibot.PropertyPage(self.repo, self.wdprop)
        self.nonHumans = self.getNonHumans(self.wdprop)
        self.humanProps = [ u'P19', # place of birth (P19)
                            u'P21', # sex or gender (P21)
                            u'P106', # occupation (P106)
                            u'P569' #  date of birth (P569)
                            ]

    def getNonHumans(self, wdprop):
        '''
        Get a generator with items using wdprop and have P31 (instance of) set, but it's not-human
        '''
        query = """SELECT ?item WHERE {
  ?item wdt:%s [] .
  ?item wdt:P31/wdt:P279 wd:Q16334295 .
  FILTER NOT EXISTS { ?item wdt:P31 wd:Q5 } .
  }""" % (wdprop,)
        query = """SELECT ?item WHERE {
  ?item wdt:%s [] .
  ?item wdt:P31 [] .
  FILTER NOT EXISTS { ?item wdt:P31 wd:Q5 } .
  }""" % (wdprop,)
        generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query,
                                                                                                      site=self.repo))
        result = list(generator)
        pywikibot.output(u'Found %s non-human items for %s' % (len(result), wdprop))
        return result

    def run(self):
        """
        Starts the robot.
        """
        data = self.property.get()
        claims = data.get('claims')

        if len(self.nonHumans) > 200:
            pywikibot.output(u'More than 100 non-humans, not working on this one')
            return

        if not u'P2302' in claims:
            # Something went wrong
            return

        for claim in claims.get(u'P2302'):
            if not claim.getTarget().title()==u'Q21503247':
                # Not item requires statement constraint
                continue
            foundHumanProp = None
            for humanProp in self.humanProps:
                if claim.has_qualifier(u'P2306', humanProp):
                    foundHumanProp = humanProp
            if not foundHumanProp:
                continue
            for nonHuman in self.nonHumans:
                if claim.has_qualifier(u'P2303', nonHuman.title()):
                    pywikibot.output(u'The item %s is already listed as exception for %s' % (nonHuman.title(),
                                                                                             foundHumanProp,))
                else:
                    pywikibot.output(u'Going to add %s as exception to %s' % (nonHuman.title(),
                                                                              foundHumanProp,))
                    newqualifier = pywikibot.Claim(self.repo, u'P2303')
                    newqualifier.setTarget(nonHuman)
                    summary = u'not a human, adding as exception to [[Property:%s]]' % (foundHumanProp,)
                    claim.addQualifier(newqualifier, summary=summary)

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
    # This is the query to get the complete list. For now hard coded list
    query = u"""SELECT ?property WHERE {
  ?property wikibase:propertyType wikibase:ExternalId .
  ?property p:P2302 ?constraint .
  ?constraint ps:P2302 wd:Q21503250 . # Has type constraint
  ?constraint pq:P2308 wd:Q5 . # Human
  ?constraint pq:P2308 wd:Q16334295 .  # group of humans
  ?property p:P2302 ?constraint2 .
  ?constraint2 ps:P2302 wd:Q21503247 .
  ?constraint2 pq:P2306 wd:P21 .
}"""
    properties_to_clean = [ u'P650', #  RKDartists ID (P650)
                            u'P2843' #  Benezit ID (P2843)
                            ]

    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    #repo = pywikibot.Site().data_repository()
    #generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))
    #generator = pagegenerators.WikidataSPARQLPageGenerator(query, site=repo)

    #for page in generator:
    #    print page.title()
    #for resultitem in queryresult:
    #    wdprop = resultitem.get('property').replace(u'http://www.wikidata.org/entity/', u'')
    #    print wdprop
    for wdprop in properties_to_clean:
        addExceptionsBot = AddExceptionsBot(wdprop)
        addExceptionsBot.run()

if __name__ == "__main__":
    main()
