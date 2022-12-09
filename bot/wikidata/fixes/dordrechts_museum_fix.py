#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Dordrechts Museum has a some link rot. Replace the links


"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import re

def get_mnr_generator():
    """
    Search for paintings and loop over it.
    """


    for resultitem in queryresult:
        print (resultitem)
        metadata = {}
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        url = 'https://www.pop.culture.gouv.fr/notice/mnr/%s' % (resultitem.get('mnrid'),)
        metadata['url'] = url
        metadata['idpid'] = 'P217'
        metadata['id'] = resultitem.get('inv')
        metadata['collectionqid'] = 'Q3044768'
        metadata['extraid'] = resultitem.get('inv')
        metadata['extracollectionqid'] = 'Q19013512'
        yield metadata





def main(*args):
    repo = pywikibot.Site().data_repository()
    query = """SELECT ?item ?doid ?url WHERE {
  ?item wdt:P5265 ?doid ;
        wdt:P973 ?url .
  }"""
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    for item in generator:
        claims = item.get().get('claims')
        if 'P5265' in claims and 'P973' in claims:
            url_regex = '^https://dordrecht\.adlibhosting\.com/ais6/Details/collect/(\d+)$'
            dordrecht_id = None
            summary = ''
            for url_claim in claims.get('P973'):
                url = url_claim.getTarget()
                url_match = re.match(url_regex, url)
                if url_match:
                    dordrecht_id = url_match.group(1)
                    summary = 'Update id based on %s' % (url)

            if dordrecht_id:
                claim = claims.get('P5265')[0]
                print(summary)
                claim.changeTarget(dordrecht_id, summary=summary)



if __name__ == "__main__":
    main()
