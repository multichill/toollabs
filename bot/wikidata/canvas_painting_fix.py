#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
We decided to change canvas (Q4259259) to canvas (Q12321255)
* canvas (Q4259259) - extremely heavy-duty plain-woven fabric
* canvas (Q12321255) - painting surface made of extremely heavy-duty plain-woven fabric
See https://www.wikidata.org/wiki/Wikidata_talk:WikiProject_Visual_arts#Canvasing_about_canvas

This bot is to update all usage.
"""
import pywikibot
from pywikibot import pagegenerators

def main(*args):
    """
    Main function does all the work.
    """
    repo = pywikibot.Site().data_repository()
    wrongcanvas = pywikibot.ItemPage(repo, 'Q4259259')
    rightcanvas = pywikibot.ItemPage(repo, 'Q12321255')
    summary = 'Change canvas per [[Wikidata_talk:WikiProject_Visual_arts#Canvasing_about_canvas|discussion]]'

    query = """SELECT ?item WHERE {
  ?item wdt:P186 wd:Q4259259 ;
        wdt:P31 wd:Q3305213 .
  MINUS { ?item wdt:P186 wd:Q12321255 } 
  } LIMIT 100000"""
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    for item in generator:
        data = item.get()
        claims = data.get('claims')

        if 'P186' in claims:
            for madeclaim in claims.get('P186'):
                if madeclaim.getTarget()==wrongcanvas:
                    madeclaim.changeTarget(rightcanvas, summary=summary)

if __name__ == "__main__":
    main()
