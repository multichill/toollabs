#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to replace direct usage of anonymous (Q4233718) in creator (P170) for paintings

See https://www.wikidata.org/wiki/Wikidata:WikiProject_sum_of_all_paintings/Anonymous_creator for more information
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
    anonymous = pywikibot.ItemPage(repo, 'Q4233718')

    if broadrfc:
        query = """SELECT DISTINCT ?item WHERE {
  ?item wdt:P170 wd:Q4233718 .  
  } LIMIT 10000"""
        qualifier_summary = '[[Wikidata:Requests for comment/Cleaning up the ontology of anonymous|Cleaning up the ontology of anonymous]], move to qualifier'
        somevalue_summary = '[[Wikidata:Requests for comment/Cleaning up the ontology of anonymous|Cleaning up the ontology of anonymous]], set to somevalue'
    else:
        query = """SELECT ?item WHERE {
      ?item p:P170/ps:P170 wd:Q4233718 ;
            wdt:P31 wd:Q3305213 .
    } LIMIT 10000"""
        qualifier_summary = '[[Wikidata:WikiProject sum of all paintings/Anonymous creator#Normalization|Anonymous creator normalization for paintings]], move to qualifier'
        somevalue_summary = '[[Wikidata:WikiProject sum of all paintings/Anonymous creator#Normalization|Anonymous creator normalization for paintings]], set to somevalue'
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    for item in generator:
        data = item.get()
        claims = data.get('claims')

        if 'P170' in claims:
            for creatorclaim in claims.get('P170'):
                if creatorclaim.getTarget()==anonymous:
                    if not creatorclaim.has_qualifier('P3831', 'Q4233718'):
                        pywikibot.output('Adding object has role anonymous on %s' % (item.title(),))
                        newqualifier = pywikibot.Claim(repo, 'P3831')
                        newqualifier.setTarget(anonymous)
                        creatorclaim.addQualifier(newqualifier, summary=qualifier_summary)
                    pywikibot.output('Changing target from anonymous to somevalue on %s' % (item.title(),))
                    creatorclaim.changeTarget(value=None, snaktype='somevalue', summary=somevalue_summary)

if __name__ == "__main__":
    main()
