#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add full provenance for paintings that started in Stichting Nederlands Kunstbezit and ended up in the RCE:
*  Stichting Nederlands Kunstbezit (Q28045665)
*  Dienst Verspreide Rijkscollecties (Q28045660)
*  Rijksdienst Beeldende Kunst (Q28045674)
*  Instituut Collectie Nederland (Q2066737)
*  Cultural Heritage Agency of the Netherlands Art Collection (Q18600731)

Not all works that started in Stichting Nederlands Kunstbezit ended up at the RCE, Some of them actually got returned
to the rightful owners. If a work is in SNK (Q28045665) and RCE Art (Q18600731) with the same inventory number and
not in the other collections. Add the misssing collections.

"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql

class ProvenanceBot:
    """
    A bot to enrich and create paintings on Wikidata
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
        self.snkitem = pywikibot.ItemPage(self.repo, u'Q28045665')
        self.dvritem = pywikibot.ItemPage(self.repo, u'Q28045660')
        self.rbkitem = pywikibot.ItemPage(self.repo, u'Q28045674')
        self.icnitem = pywikibot.ItemPage(self.repo, u'Q2066737')
        self.rceitem = pywikibot.ItemPage(self.repo, u'Q18600731')

    def run(self):
        """
        Starts the robot.
        """
        for item in self.generator:
            self.treat(item)

    def treat(self, item):

        data = item.get()
        claims = data.get('claims')

        snkinvnumber = u''
        dvrinvnumber = u''
        rbkinvnumber = u''
        icninvnumber = u''
        rceinvnumber = u''
        for invnumberclaim in claims.get(u'P217'):
            if invnumberclaim.has_qualifier(u'P195', self.snkitem):
                snkinvnumber = invnumberclaim.getTarget()
            elif invnumberclaim.has_qualifier(u'P195', self.dvritem):
                dvrinvnumber = invnumberclaim.getTarget()
            elif invnumberclaim.has_qualifier(u'P195', self.rbkitem):
                rbkinvnumber = invnumberclaim.getTarget()
            elif invnumberclaim.has_qualifier(u'P195', self.icnitem):
                icninvnumber = invnumberclaim.getTarget()
            elif invnumberclaim.has_qualifier(u'P195', self.rceitem):
                rceinvnumber = invnumberclaim.getTarget()

        if not snkinvnumber or not rceinvnumber or not snkinvnumber==rceinvnumber:
            print u'Something went wrong, skipping'
            return

        if not dvrinvnumber:
            self.addInventoryNumber(item, snkinvnumber, self.dvritem)
        if not rbkinvnumber:
            self.addInventoryNumber(item, snkinvnumber, self.rbkitem)
        if not icninvnumber:
            self.addInventoryNumber(item, snkinvnumber, self.icnitem)

        collectiontargets = []
        for collectionclaim in claims.get(u'P195'):
            collectiontargets.append(collectionclaim.getTarget())

        if self.dvritem not in collectiontargets:
            self.addCollection(item, self.dvritem)
        if self.rbkitem not in collectiontargets:
            self.addCollection(item, self.rbkitem)
        if self.icnitem not in collectiontargets:
            self.addCollection(item, self.icnitem)

    def addInventoryNumber(self, item, invnumber, collectionitem):
        summary = u'Add missing inventory number for full [[Q28045665]] --> [[Q18600731]] provenance'
        newclaim = pywikibot.Claim(self.repo, u'P217')
        newclaim.setTarget(invnumber)
        pywikibot.output('Adding new id claim to %s' % item)
        item.addClaim(newclaim, summary=summary)

        newqualifier = pywikibot.Claim(self.repo, u'P195')
        newqualifier.setTarget(collectionitem)
        pywikibot.output('Adding new qualifier claim to %s' % item)
        newclaim.addQualifier(newqualifier)

    def addCollection(self, item, collectionitem):
        summary = u'Add missing collection for full  [[Q28045665]] --> [[Q18600731]] provenance'
        newclaim = pywikibot.Claim(self.repo, u'P195')
        newclaim.setTarget(collectionitem)
        pywikibot.output('Adding new collection claim to %s' % item)
        item.addClaim(newclaim, summary=summary)


def main():
    query=u"""SELECT DISTINCT ?item WHERE {
  ?item wdt:P31 wd:Q3305213 .
  ?item wdt:P195 wd:Q28045665 .
  ?item wdt:P195 wd:Q18600731 .
  ?item p:P217 ?inv1statement .
  ?inv1statement ps:P217 ?inv .
  ?inv1statement pq:P195 wd:Q28045665 .
  ?item p:P217 ?inv2statement .
  ?inv2statement ps:P217 ?inv .
  ?inv2statement pq:P195 wd:Q18600731 .
  MINUS {
      ?item wdt:P195 wd:Q28045660 .
      ?item wdt:P195 wd:Q28045674 .
      ?item wdt:P195 wd:Q2066737 .
      ?item p:P217 ?inv3statement .
      ?inv3statement ps:P217 ?inv .
      ?inv3statement pq:P195 wd:Q28045660 .
      ?item p:P217 ?inv4statement .
      ?inv4statement ps:P217 ?inv .
      ?inv4statement pq:P195 wd:Q28045674 .
      ?item p:P217 ?inv5statement .
      ?inv5statement ps:P217 ?inv .
      ?inv5statement pq:P195 wd:Q2066737 .
    }
}"""
    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    provenanceBot = ProvenanceBot(generator)
    provenanceBot.run()

if __name__ == "__main__":
    main()
