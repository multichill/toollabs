#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to replace direct usage of private collection (Q768717) in creator (P195) for paintings

See https://www.wikidata.org/wiki/Wikidata:WikiProject_sum_of_all_paintings/Private_collection for more information
"""
import pywikibot
from pywikibot import pagegenerators

def main(*args):
    """
    Main function does all the work.
    """
    broadrfc = False
    for arg in pywikibot.handle_args(args):
        if arg.startswith('-broadrfc'):
            broadrfc = True

    repo = pywikibot.Site().data_repository()
    private_collection = pywikibot.ItemPage(repo, 'Q768717')

    if broadrfc:
        query = """SELECT DISTINCT ?item WHERE {
  ?item wdt:P195 wd:Q768717 .  
  } LIMIT 10000"""
        qualifier_summary = 'Private collection normalization, move to qualifier'
        somevalue_summary = 'Private collection normalization, set to somevalue'
    else:
        query = """SELECT ?item WHERE {
      ?item p:P195/ps:P195 wd:Q768717 ;
            wdt:P31 wd:Q3305213 .
    } LIMIT 10000"""
        qualifier_summary = '[[Wikidata:WikiProject sum of all paintings/Private collection|Private collection normalization for paintings]], move to qualifier'
        somevalue_summary = '[[Wikidata:WikiProject sum of all paintings/Private collection|Private collection normalization for paintings]], set to somevalue'
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    for item in generator:
        data = item.get()
        claims = data.get('claims')

        if 'P195' in claims:
            for collectionclaim in claims.get('P195'):
                if collectionclaim.getTarget()==private_collection:
                    if not collectionclaim.has_qualifier('P3831', 'Q768717'):
                        pywikibot.output('Adding object has role private collection on %s' % (item.title(),))
                        newqualifier = pywikibot.Claim(repo, 'P3831')
                        newqualifier.setTarget(private_collection)
                        collectionclaim.addQualifier(newqualifier, summary=qualifier_summary)
                    pywikibot.output('Changing target from private collection to somevalue on %s' % (item.title(),))
                    collectionclaim.changeTarget(value=None, snaktype='somevalue', summary=somevalue_summary)

if __name__ == "__main__":
    main()
