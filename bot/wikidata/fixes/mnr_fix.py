#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add the missing inventory numbers to MNR paintings


"""
import artdatabot
import pywikibot

def get_mnr_generator():
    """
    Search for paintings and loop over it.
    """
    query = """SELECT ?item ?inv ?mnrid WHERE {
  ?item wdt:P10039 [] ; 
        wdt:P31 wd:Q3305213 ;
        wdt:P10039 ?mnrid ;
        p:P217 ?invstatement .
  ?invstatement ps:P217 ?inv ;
                pq:P195 wd:Q3044768 .         
  #FILTER(REGEX(STR(?inv), \"^MNR \\d+\"))
  MINUS {?item p:P217/pq:P195 wd:Q19013512 }
  } LIMIT 500"""

    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

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
    dict_gen = get_mnr_generator()
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True

    if dryrun:
        for painting in dict_gen:
            print (painting)
    else:
        art_data_bot = artdatabot.ArtDataBot(dict_gen, create=create)
        art_data_bot.run()

if __name__ == "__main__":
    main()
