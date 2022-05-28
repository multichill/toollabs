#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
In the past I messed up the collection for the Staatliche Museen zu Berlin (Q700216).
Turns out these are all separate collections. Have to do some clean up to sort that out.
"""
import pywikibot
from pywikibot import pagegenerators

def main(*args):
    """
    Main function does all the work.
    """
    repo = pywikibot.Site().data_repository()
    smb = pywikibot.ItemPage(repo, 'Q700216')
    alte_nationalgalerie = pywikibot.ItemPage(repo, 'Q162111')

    query = """SELECT ?item ?id ?inv WHERE {
  ?item wdt:P195 wd:Q700216 ;
        wdt:P31 wd:Q3305213 ;
        wdt:P8923 ?id ;
        wdt:P276 wd:Q162111 ;
        p:P217 ?invstatement .
  ?invstatement pq:P195 wd:Q700216 ;
                ps:P217 ?inv . 
  }"""
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    for item in generator:
        data = item.get()
        claims = data.get('claims')

        if 'P276' in claims and claims.get('P276')[0].getTarget()==alte_nationalgalerie:
            if 'P195' in claims and len(claims.get('P195'))==1:
                collectionclaim = claims.get('P195')[0]
                if collectionclaim.getTarget()==smb:
                    summary = 'Cleaning up Staatliche Museen zu Berlin collections'
                    pywikibot.output('Changing collection on %s' % (item.title(),))
                    collectionclaim.changeTarget(value=alte_nationalgalerie, summary=summary)
            if 'P217' in claims and len(claims.get('P217'))==1:
                inventoryclaim = claims.get('P217')[0]
                qualifier = inventoryclaim.qualifiers.get('P195')[0]
                if qualifier.getTarget()==smb:
                    summary = 'Cleaning up Staatliche Museen zu Berlin collections'
                    pywikibot.output('Changing collection qualifier on %s' % (item.title(),))
                    qualifier.setTarget(value=alte_nationalgalerie)
                    repo.editQualifier(inventoryclaim, qualifier, summary=summary)
                    #inventoryclaim.addQualifier(qualifier, summary=summary)

if __name__ == "__main__":
    main()
