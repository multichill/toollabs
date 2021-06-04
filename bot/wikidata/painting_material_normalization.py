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

def replace_paint(repo, wrongqid, rightqid):
    """
    Replace the wrongqid with rightqid for paint

    :param repo: The repo to work on
    :param wrongqid: Qid of the wrong material to replace
    :param rightqid: Qid of the right material to add instead
    :return: Edit in place
    """
    wrongmaterial = pywikibot.ItemPage(repo, wrongqid)
    rightmaterial = pywikibot.ItemPage(repo, rightqid)

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
                    summary = '[[Wikidata:WikiProject sum of all paintings/Made from material#Normalization|Made from material normalization for paintings]]'
                    pywikibot.output('Replacing %s with %s on %s' % (wrongqid, rightqid, item.title()))
                    madeclaim.changeTarget(rightmaterial, summary=summary)

def main(*args):
    """
    Main function does all the work.
    """
    repo = pywikibot.Site().data_repository()
    # canvas (Q4259259) -> canvas (Q12321255)
    replace_painting_surface(repo, 'Q4259259', 'Q12321255', strict=False, add_missing=True)
    add_painting_surface_qualifier(repo, 'Q12321255')
    # panel (Q1348059) -> panel (Q106857709)
    replace_painting_surface(repo, 'Q1348059', 'Q106857709', strict=False, add_missing=True)
    add_painting_surface_qualifier(repo, 'Q106857709')
    # wood (Q287) -> panel (Q106857709)
    replace_painting_surface(repo, 'Q287', 'Q106857709', strict=True, add_missing=False)
    # oak (Q2075708) -> oak panel (Q106857823)
    replace_painting_surface(repo, 'Q2075708', 'Q106857823', strict=True, add_missing=False)
    add_painting_surface_qualifier(repo, 'Q106857823')
    # poplar wood (Q291034) -> poplar panel (Q106857865)
    replace_painting_surface(repo, 'Q291034', 'Q106857865', strict=True, add_missing=False)
    add_painting_surface_qualifier(repo, 'Q106857865')
    # fir wood (Q746026) -> fir panel (Q107103505)
    replace_painting_surface(repo, 'Q746026', 'Q107103505', strict=True, add_missing=False)
    add_painting_surface_qualifier(repo, 'Q107103505')
    # lime (Q575018) -> lime panel (Q107103548)
    replace_painting_surface(repo, 'Q575018', 'Q107103548', strict=True, add_missing=False)
    add_painting_surface_qualifier(repo, 'Q107103548')
    # walnut wood (Q2288038) -> walnut panel (Q107103575)
    replace_painting_surface(repo, 'Q2288038', 'Q107103575', strict=True, add_missing=False)
    add_painting_surface_qualifier(repo, 'Q107103575')
    # gouache painting (Q21281546) -> gouache paint (Q204330)
    replace_paint(repo, 'Q21281546', 'Q204330')
    # watercolor painting (Q18761202) -> watercolor paint (Q22915256)
    replace_paint(repo, 'Q18761202', 'Q22915256')
    # watercolor (Q50030) -> watercolor paint (Q22915256)
    replace_paint(repo, 'Q50030', 'Q22915256')
    # oil painting (Q56676227) -> oil paint (Q296955)
    replace_paint(repo, 'Q56676227', 'Q296955')
    # oil painting (Q174705) -> oil paint (Q296955)
    replace_paint(repo, 'Q174705', 'Q296955')

if __name__ == "__main__":
    main()
