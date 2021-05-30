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
    repo = pywikibot.Site().data_repository()
    anonymous = pywikibot.ItemPage(repo, 'Q4233718')

    query = """SELECT ?item WHERE {
  ?item p:P170/ps:P170 wd:Q4233718 ;
        wdt:P31 wd:Q3305213 .
} LIMIT 10000"""
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    for item in generator:
        data = item.get()
        claims = data.get('claims')

        if 'P170' in claims:
            for creatorclaim in claims.get('P170'):
                if creatorclaim.getTarget()==anonymous:
                    if not creatorclaim.has_qualifier('P3831', 'Q4233718'):
                        pywikibot.output('Adding object has role anonymous on %s' % (item.title(),))
                        summary = '[[Wikidata:WikiProject sum of all paintings/Anonymous creator#Normalization|Anonymous creator normalization for paintings]], move to qualifier'
                        newqualifier = pywikibot.Claim(repo, 'P3831')
                        newqualifier.setTarget(anonymous)
                        creatorclaim.addQualifier(newqualifier, summary=summary)
                    pywikibot.output('Changing target from anonymous to somevalue on %s' % (item.title(),))
                    summary = '[[Wikidata:WikiProject sum of all paintings/Anonymous creator#Normalization|Anonymous creator normalization for paintings]], set to somevalue'
                    creatorclaim.changeTarget(value=None, snaktype='somevalue', summary=summary)

if __name__ == "__main__":
    main()
