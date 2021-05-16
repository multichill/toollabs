#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to do a bit of made from material (P186) clean up for paintings

See https://www.wikidata.org/wiki/Wikidata:WikiProject_sum_of_all_paintings/Made_from_material for more information

This bot will do the needed changes.
"""
import pywikibot
from pywikibot import pagegenerators

def replace_painting_surface(repo, wrongqid, rightqid, strict=True, add_missing=False):
    """
    Replace the wrongqid with rightqid for a painting surface

    :param repo: The repo to work on
    :param wrongqid: Qid of the wrong material to replace
    :param rightqid: Qid of the right material to add instead
    :param strict: If set, the wrongqid needs to have the painting surface qualifier
    :param add_missing: If set, add the missing painting surface
    :return: Edit in place
    """
    wrongmaterial = pywikibot.ItemPage(repo, wrongqid)
    rightmaterial = pywikibot.ItemPage(repo, rightqid)
    paintingsurface = pywikibot.ItemPage(repo, 'Q861259')

    if strict:
        query = """SELECT ?item WHERE {
  ?item p:P186 ?madestatement .
  ?madestatement ps:P186 wd:%s .
  ?madestatement pq:P518 wd:Q861259 .  
  ?item wdt:P31 wd:Q3305213 .
  } LIMIT 10000""" % (wrongqid, )
    else:
        query = """SELECT ?item WHERE {
      ?item p:P186 ?madestatement .
      ?madestatement ps:P186 wd:%s .      
      ?item wdt:P31 wd:Q3305213 .
      } LIMIT 10000""" % (wrongqid, )
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    for item in generator:
        data = item.get()
        claims = data.get('claims')

        if 'P186' in claims:
            for madeclaim in claims.get('P186'):
                if madeclaim.getTarget()==wrongmaterial:
                    if madeclaim.has_qualifier('P518', 'Q861259'):
                        summary = '[[Wikidata:WikiProject sum of all paintings/Made from material#Normalization|Made from material normalization for paintings]] for painting surface (qualifier [[Property:P518]] is set to [[Q861259]])'
                        pywikibot.output('Strict replacing %s with %s on %s' % (wrongqid, rightqid, item.title()))
                        madeclaim.changeTarget(rightmaterial, summary=summary)
                    elif not strict:
                        summary = '[[Wikidata:WikiProject sum of all paintings/Made from material#Normalization|Made from material normalization for paintings]] for painting surface'
                        pywikibot.output('Replacing %s with %s on %s' % (wrongqid, rightqid, item.title()))
                        madeclaim.changeTarget(rightmaterial, summary=summary)
                        if add_missing:
                            summary = 'Also adding missing painting surface'
                            pywikibot.output('Also adding missing painting surface on %s' % (item.title(),))
                            newqualifier = pywikibot.Claim(repo, 'P518')
                            newqualifier.setTarget(paintingsurface)
                            madeclaim.addQualifier(newqualifier, summary=summary)

def add_painting_surface_qualifier(repo, materialqid):
    """
    Add the missing painting surface qualifier

    :param repo: The repo to work on
    :param materialqid: Qid of material to work on
    :return: Edit in place
    """
    material = pywikibot.ItemPage(repo, materialqid)
    paintingsurface = pywikibot.ItemPage(repo, 'Q861259')

    query = """SELECT ?item WHERE {
  ?item p:P186 ?madestatement .
  ?madestatement ps:P186 wd:%s .
  MINUS { ?madestatement pq:P518 wd:Q861259 }
  ?item wdt:P31 wd:Q3305213 .
  } LIMIT 10000""" % (materialqid, )
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    for item in generator:
        data = item.get()
        claims = data.get('claims')

        if 'P186' in claims:
            for madeclaim in claims.get('P186'):
                # Only work on the material claim if it doesn't have any qualifiers
                if madeclaim.getTarget()==material and not madeclaim.qualifiers:
                    summary = '[[Wikidata:WikiProject sum of all paintings/Made from material#Normalization|Made from material normalization for paintings]]: Add missing painting surface qualifier'
                    pywikibot.output('Add missing painting surface qualifier on %s' % (item.title(),))
                    newqualifier = pywikibot.Claim(repo, 'P518')
                    newqualifier.setTarget(paintingsurface)
                    madeclaim.addQualifier(newqualifier, summary=summary)

def main(*args):
    """
    Main function does all the work.
    """
    repo = pywikibot.Site().data_repository()
    # canvas -> canvas
    replace_painting_surface(repo, 'Q4259259', 'Q12321255', strict=False, add_missing=True)
    add_painting_surface_qualifier(repo, 'Q12321255')
    # panel -> panel
    replace_painting_surface(repo, 'Q1348059', 'Q106857709', strict=False, add_missing=True)
    add_painting_surface_qualifier(repo, 'Q106857709')
    # wood -> panel
    replace_painting_surface(repo, 'Q287', 'Q106857709', strict=True, add_missing=False)
    # oak -> oak panel
    replace_painting_surface(repo, 'Q2075708', 'Q106857823', strict=True, add_missing=False)
    # poplar wood -> poplar panel
    replace_painting_surface(repo, 'Q291034', 'Q106857865', strict=True, add_missing=False)

if __name__ == "__main__":
    main()
