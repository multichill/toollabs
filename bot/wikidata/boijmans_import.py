#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape paintings from the Boijmans website. Uses artdatabot to do the actual work.

Their search engine provides json these days, see https://www.algolia.com/doc/api-reference/api-methods/search/
Maximum 1000 results so I have to play around a bit to find all.
"""
import artdatabot
import pywikibot
import requests
import json
import time

def get_Boijmans_painting_generator():
    """
    The Boijmans painting generator
    """
    departments = ['', 'Oude Kunst', 'Moderne Kunst']
    index_names = ['production_collection_artworks',
                   'production_collection_artworks_date_asc',
                   'production_collection_artworks_date_desc',
                   'production_collection_artworks_title_asc',
                   'production_collection_artworks_title_desc',
                   'production_collection_artworks_artist_asc',
                   'production_collection_artworks_artist_desc',
                   ]


    found_ids = [] # To keep track what we have already seen
    #boijmans_artists = boijmans_artists_on_wikidata()
    session = requests.Session()
    referer = 'https://www.boijmans.nl/'

    searchurl = 'https://s1zzm36i7l-dsn.algolia.net/1/indexes/*/queries?x-algolia-agent=Algolia%20for%20JavaScript%20(3.33.0)%3B%20Browser%20(lite)%3B%20instantsearch.js%20(3.6.0)%3B%20Vue%20(2.6.10)%3B%20Vue%20InstantSearch%20(2.3.0)%3B%20JS%20Helper%202.26.1&x-algolia-application-id=S1ZZM36I7L&x-algolia-api-key=c5a5dbed3cdf3ee64bc109c7e15f15cf'

    for department in departments:
        for index_name in index_names:
            nbPages = 50
            page = 0
            while page < nbPages:
                if department:
                    params = "query=&facetFilters=%5B%5B%22department%3A" + department + "%22%5D%2C%5B%22objectname.tree.name%3Aschilderij%22%5D%5D&page=" + str(page)
                else:
                    params = "query=&facetFilters=objectname.tree.name:schilderij&page=" + str(page)
                searchrequest = { "requests": [ {"indexName": index_name, "params": params } ], }
                search_page = session.post(searchurl,
                                           data=json.dumps(searchrequest),
                                           headers={'X-Requested-With' : 'XMLHttpRequest',
                                                    'referer' : referer,
                                                    u'Content-Type' : u'application/json; charset=utf-8',
                                                    }
                                           )
                page += 1
                nbPages = search_page.json().get('results')[0].get('nbPages')
                for iteminfo in search_page.json().get('results')[0].get('hits'):
                    tms_id = '%s' % (iteminfo.get('tms_id'),)  # Has to be a string
                    if tms_id in found_ids:
                        # Already been here, go to the next
                        continue
                    found_ids.append(tms_id)

                    #print(json.dumps(iteminfo, indent=4, sort_keys=True))

                    metadata = {}
                    metadata['url'] = iteminfo.get('url')

                    metadata['collectionqid'] = u'Q679527'
                    metadata['collectionshort'] = u'Boijmans'
                    metadata['locationqid'] = u'Q679527'

                    #No need to check, I'm actually searching for paintings.
                    metadata['instanceofqid'] = u'Q3305213'

                    metadata['id'] = iteminfo.get('identifier')
                    metadata['idpid'] = u'P217'

                    metadata['artworkidpid'] = u'P5499'
                    metadata['artworkid'] = tms_id

                    # API returns the Dutch title

                    metadata['title'] = {'nl': iteminfo.get('title').strip(),}
                    metadata['creatorname'] = iteminfo.get('main_artist')
                    if iteminfo.get('artists'):
                        if len(iteminfo.get('artists')) == 1:
                            # TO DO: Add more languages
                            metadata['description'] = {'nl': '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                                       'en': '%s by %s' % ('painting', metadata.get('creatorname'),),
                                                       'de': '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                                       'fr': '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                                        }
                            # DISABLED: The returned ID is different than what we're using
                            #if artistid in boijmans_artists:
                            #    pywikibot.output (u'Found Boijmans id %s on %s' % (artistid, boijmans_artists.get(artistid)))
                            #    metadata['creatorqid'] = boijmans_artists.get(artistid)
                        elif len(iteminfo.get('artists'))>1:
                            metadata['description'] = {'nl': 'schilderij van %s' % (metadata.get('creatorname'), ),}

                    if iteminfo.get('aquisitiondate_year'):
                        metadata['acquisitiondate'] = iteminfo.get('aquisitiondate_year')

                    if iteminfo.get('dating_start') and iteminfo.get('dating_end'):
                        dating_average = int((iteminfo.get('dating_start') + iteminfo.get('dating_end')) /2)
                        if iteminfo.get('dating_indication') == str(iteminfo.get('dating_start')) and \
                            iteminfo.get('dating_indication') == iteminfo.get('dating_end'):
                            metadata['inception'] = iteminfo.get('dating_indication')
                        elif iteminfo.get('dating_indication') == 'circa %s' % (dating_average,):
                            metadata['inception'] = dating_average
                            metadata['inceptioncirca'] = True
                        elif iteminfo.get('dating_start') > 1200 and iteminfo.get('dating_end') > 1200:
                            metadata['inceptionstart'] = iteminfo.get('dating_start')
                            metadata['inceptionend'] = iteminfo.get('dating_end')

                    if iteminfo.get('material'):
                        materials = set()
                        for material in iteminfo.get('material'):
                            materials.add(material.get('name'))

                        if materials == {'olieverf', 'doek'} or materials == {'olieverf', 'canvas'} :
                            metadata['medium'] = 'oil on canvas'
                        elif materials == {'olieverf', 'paneel'}:
                            metadata['medium'] = 'oil on panel'
                        elif materials == {'olieverf', 'koper'}:
                            metadata['medium'] = 'oil on copper'
                        #elif (material1 == 'papier' and material2 == 'olieverf') or (material1 == 'olieverf' and material2 == 'papier'):
                        #    metadata['medium'] = 'oil on paper'
                        #elif (material1 == 'doek' and material2 == 'tempera') or (material1 == 'tempera' and material2 == 'doek'):
                        #    metadata['medium'] = 'tempera on canvas'
                        #elif (material1 == 'paneel' and material2 == 'tempera') or (material1 == 'tempera' and material2 == 'paneel'):
                        #    metadata['medium'] = 'tempera on panel'
                        #elif (material1 == 'doek' and material2 == 'acrylverf') or (material1 == 'acrylverf' and material2 == 'doek'):
                        #    metadata['medium'] = 'acrylic paint on canvas'
                        elif materials == {'acryl', 'doek'}:
                            metadata['medium'] = 'acrylic paint on canvas'
                        #elif (material1 == 'paneel' and material2 == 'acrylverf') or (material1 == 'acrylverf' and material2 == 'paneel'):
                        #    metadata['medium'] = 'acrylic paint on panel'
                        #elif (material1 == 'papier' and material2 == 'aquarel') or (material1 == 'aquarel' and material2 == 'papier'):
                        #    metadata['medium'] = 'watercolor on paper'
                        #else:
                        #    print('Unable to match %s & %s' % (material1, material2,))
                        elif materials == {'olieverf', 'doek', 'paneel'}:
                            metadata['medium'] = 'oil on canvas on panel'
                        elif materials == {'olieverf', 'papier', 'paneel'}:
                            metadata['medium'] = 'oil on paper on panel'
                        elif materials == {'olieverf', 'karton', 'paneel'}:
                            metadata['medium'] = 'oil on cardboard on panel'
                        elif materials == {'olieverf', 'koper', 'paneel'}:
                            metadata['medium'] = 'oil on copper on panel'
                        elif materials == {'olieverf', 'doek', 'karton'}:
                            metadata['medium'] = 'oil on canvas on cardboard'
                        elif materials == {'olieverf', 'papier', 'karton'}:
                            metadata['medium'] = 'oil on paper on cardboard'
                        else:
                            print('Unable to match %s' % (materials,))
                    if iteminfo.get('dating_end') and iteminfo.get('dating_end') < 1925 and \
                        iteminfo.get('modal_data_url'):
                        try:
                            time.sleep(10)
                            modal_page = requests.get(iteminfo.get('modal_data_url'))
                            metadata['imageurl'] = modal_page.json().get('image')
                            metadata['imagesourceurl'] = modal_page.json().get('url')
                            metadata['imageurlformat'] = 'Q2195'  # JPEG
                            metadata['imageurlforce'] = False  # Really shitty quality
                            metadata['imageoperatedby'] = 'Q679527'
                        except ValueError:
                            pywikibot.output('url %s failed, retrying' % (iteminfo.get('modal_data_url'),))
                            time.sleep(120)
                            try:
                                modal_page = requests.get(iteminfo.get('modal_data_url'))
                                metadata['imageurl'] = modal_page.json().get('image')
                                metadata['imagesourceurl'] = modal_page.json().get('url')
                                metadata['imageurlformat'] = 'Q2195'  # JPEG
                                metadata['imageurlforce'] = False  # Really shitty quality
                                metadata['imageoperatedby'] = 'Q679527'
                            except ValueError:
                                pywikibot.output('url %s completely failed' % (iteminfo.get('modal_data_url'),))
                    yield metadata
    pywikibot.output('Found %s paintings in this run ' % (len(found_ids),))


def boijmans_artists_on_wikidata():
    """
    Just return all the Boijmans people as a dict
    :return: Dict
    """
    result = {}
    query = u'SELECT ?item ?id WHERE { ?item wdt:P3888 ?id . ?item wdt:P31 wd:Q5 }'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = qid
    return result


def main(*args):
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        if arg.startswith('-create'):
            create = True

    paintingGen = get_Boijmans_painting_generator()

    if dryrun:
        for painting in paintingGen:
            print(painting)
    else:
        artDataBot = artdatabot.ArtDataBot(paintingGen, create=create)
        artDataBot.run()

if __name__ == "__main__":
    main()
