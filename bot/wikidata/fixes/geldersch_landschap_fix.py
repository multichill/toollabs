#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
I mixed up  Geldersch Landschap (Q1856245) and Geldersch Landschap en Kasteelen (Q98904445)

"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import re
import json
import time

def main(*args):
    repo = pywikibot.Site().data_repository()
    query = """SELECT ?item WHERE {
  ?item p:P195/ps:P195 wd:Q1856245 ;
        wdt:P31 wd:Q3305213 .  
}
LIMIT 2000"""
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    for item in generator:
        pywikibot.output('Working on %s' % (item.title()),)
        current_json = item.toJSON()
        new_json = json.loads(json.dumps(current_json).replace('1856245', '98904445'))
        summary = 'Replace [[Q1856245]] with [[Q98904445]]'
        item.editEntity(data=new_json, summary=summary)

    site = pywikibot.Site('commons', 'commons')
    search_string = 'file: haswbstatement:P7482=Q74228490[P137=Q1856245]'
    generator = pagegenerators.SearchPageGenerator(search_string, total=500, namespaces=6, site=site)

    for filepage in generator:
        item = filepage.data_item()
        item.get()
        print (item.id)
        pywikibot.output('Working on %s' % (filepage.title()),)
        current_json = item._content # item.toJSON() returns empty dict
        #print(json.dumps(current_json, indent = 2, separators=(',', ': ')))
        # AAAARGH, "statements" and "claims" mixed up
        new_json = json.loads(json.dumps(current_json).replace('1856245', '98904445').replace('"statements": {', '"claims": {'))
        summary = 'Replace [[d:Special:EntityPage/Q1856245]] with [[d:Special:EntityPage/Q98904445]]'

        #print(json.dumps(new_json, indent = 2, separators=(',', ': ')))

        token = site.tokens['csrf']

        postdata = {'action' : 'wbeditentity',
                    'format' : 'json',
                    'id' : item.id,
                    'data' : json.dumps(new_json),
                    'token' : token,
                    'summary' : summary,
                    'bot' : True,
                    }

        request = site._simple_request(**postdata)
        data = request.submit()

        #site.editEntity(item, data=new_json, summary=summary)


if __name__ == "__main__":
    main()

