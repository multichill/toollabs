#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Wikidata had an RFC to replace brother (P7) and sister (P9) with  sibling (P3373)
see https://www.wikidata.org/wiki/Wikidata:Requests_for_comment/Make_family_member_properties_gender_neutral

This bot moves the statements.

First it does a (SPARQL) query to find wikidata items that need work and loop over them.

TODO: Currently only works on rank normal, no sources, no qualifiers. Should expand to include this.

"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql

def main(*args):
    """
    Main function. Grab a generator and work on it
    """
    repo = pywikibot.Site().data_repository()

    query = u"""SELECT DISTINCT ?item WHERE {
  { ?item wdt:P7 [] . } UNION
  { ?item wdt:P9 [] } .
  ?item wdt:P31 wd:Q5
  }"""

    summarybrother = u'Moved from [[Property:P7]] per [[Wikidata:Requests for comment/Make family member properties gender neutral|RFC]]'
    summarysister = u'Moved from [[Property:P9]] per [[Wikidata:Requests for comment/Make family member properties gender neutral|RFC]]'
    summaryremove = u'per [[Wikidata:Requests for comment/Make family member properties gender neutral|RFC]]'

    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    for item in generator:
        pywikibot.output(u'Working on %s' % (item.title(),))
        data = item.get()
        claims = data.get('claims')
        toremove = []

        if claims.get('P7'):
            for brother in claims.get('P7'):
                if brother.rank==u'normal' and not brother.sources and not brother.qualifiers:
                    brotherjson = brother.toJSON()
                    brotherjson[u'mainsnak'][u'property']=u'P3373'
                    sibling = brother.fromJSON(repo, brotherjson)
                    item.addClaim(sibling, summary=summarybrother)
                    toremove.append(brother)
        if claims.get('P9'):
            for sister in claims.get('P9'):
                if sister.rank==u'normal' and not sister.sources and not sister.qualifiers:
                    sisterjson = sister.toJSON()
                    sisterjson[u'mainsnak'][u'property']=u'P3373'
                    sibling = sister.fromJSON(repo, sisterjson)
                    item.addClaim(sibling, summary=summarysister)
                    toremove.append(sister)
        if toremove:
            item.removeClaims(toremove, summary=summaryremove)

if __name__ == "__main__":
    main()
