#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Berlinische Galerie to Wikidata.

They seems to use Emuseum with json output

This bot uses artdatabot to upload it to Wikidata.

First version used the Deutsche Digitale Bibliothek API

"""
import artdatabot
import pywikibot
import requests
import re

def get_berlinische_galerie_generator():
    """
    Generator to return Berlinische Galerie paintings
    """
    base_search_url = 'https://sammlung-online.berlinischegalerie.de/solr/published/select?&fq=type:Object&fq=loans_b:%%22false%%22&fq={!tag=et_classification_en_s}classification_en_s:(%%22Painting%%22)&q=*:*&rows=%s&sort=person_sort_en_s%%20asc&start=%s'

    start_url = base_search_url % (1, 0, )

    session = requests.Session()
    start_page = session.get(start_url)
    number_found = start_page.json().get('response').get('numFound')

    # Trying to hide the json with a build id that changes
    collection_page = session.get('https://sammlung-online.berlinischegalerie.de/en/collection/')
    build_id_regex = '<script id="__NEXT_DATA__" type="application/json">.+"buildId":"([^"]+)","isFallback":false,"gsp":true,"scriptLoader":\[\]}</script>'
    build_id_match = re.search(build_id_regex, collection_page.text)
    build_id = build_id_match.group(1)

    step = 10

    artists = get_berlinische_galerie_artists_wikidata()

    for i in range(0, number_found + step, step):
        search_url = base_search_url % (step, i,)

        print(search_url)
        search_page = session.get(search_url)

        for object_docs in search_page.json().get('response').get('docs'):
            metadata = {}
            object_id = object_docs.get('oid')

            url = 'https://sammlung-online.berlinischegalerie.de/en/collection/item/%s/' % (object_id, )
            json_url = 'https://sammlung-online.berlinischegalerie.de/_next/data/%s/en/collection/item/%s.json' % (build_id, object_id, )

            pywikibot.output(url)
            pywikibot.output(json_url)

            json_page = session.get(json_url)
            item_json = json_page.json().get('pageProps').get('data').get('item')
            metadata['url'] = url

           ## Add the identifier property
            metadata['artworkidpid'] = 'P13197'  # Berlinische Galerie object ID (P13197)
            metadata['artworkid'] = object_id

            # Only paintings
            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = 'P217'
            if item_json.get('ObjMainObjectNumberTxt'):
                metadata['id'] = item_json.get('ObjMainObjectNumberTxt')
            else:
                # Some items don't have an inventory number
                continue

            metadata['collectionqid'] = 'Q700222'
            metadata['collectionshort'] = 'BG'
            metadata['locationqid'] = 'Q700222'

            title = item_json.get('ObjTitleTxt').replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').replace('  ', ' ').strip()

            # Chop chop, might have long titles
            if len(title) > 220:
                title = title[0:200]
            title = title.replace('\t', '').replace('\n', '')
            metadata['title'] = {'de': title, }

            creator_name = item_json.get('ObjMainPersonTxt')

            if creator_name:
                if creator_name.lower() == 'unbekannt':
                    metadata['description'] = { 'de': '%s von %s' % ('Gemälde', creator_name, ),
                                                }
                else:
                    metadata['description'] = { 'nl': '%s van %s' % ('schilderij', creator_name,),
                                                'en': '%s by %s' % ('painting', creator_name,),
                                                'de': '%s von %s' % ('Gemälde', creator_name, ),
                                                'fr': '%s de %s' % ('peinture', creator_name, ),
                                                }
                metadata['creatorname'] = creator_name

            if len(item_json.get('ObjPersonRef').get('Items')) == 1:
                person_info = item_json.get('ObjPersonRef').get('Items')[0]
                if person_info.get('LinkLabelTxt').startswith(creator_name):
                    artist_id = int(person_info.get('ReferencedId'))
                    if artist_id and artist_id in artists:
                        metadata['creatorqid'] = artists.get(artist_id)

            date = item_json.get('ObjDateTxt')

            if date:
                year_regex = '^\s*(\d\d\d\d)\s*$'
                date_circa_regex = '^um\s*(\d\d\d\d)$'
                period_regex = '^(\d\d\d\d)\s*[\-\–\/]\s*(\d\d\d\d)$'
                circa_period_regex = '^ca?\.\s*(\d\d\d\d)\s*[\-\–\/]\s*(\d\d\d\d)$'
                short_period_regex = '^(\d\d)(\d\d)[\-\–\/](\d\d)$'
                circa_short_period_regex = '^ca?\.\s*(\d\d)(\d\d)[\-\–\/](\d\d)$'

                year_match = re.match(year_regex, date)
                date_circa_match = re.match(date_circa_regex, date)
                period_match = re.match(period_regex, date)
                circa_period_match = re.match(circa_period_regex, date)
                short_period_match = re.match(short_period_regex, date)
                circa_short_period_match = re.match(circa_short_period_regex, date)

                if year_match:
                    # Don't worry about cleaning up here.
                    metadata['inception'] = int(year_match.group(1))
                elif date_circa_match:
                    metadata['inception'] = int(date_circa_match.group(1))
                    metadata['inceptioncirca'] = True
                elif period_match:
                    metadata['inceptionstart'] = int(period_match.group(1),)
                    metadata['inceptionend'] = int(period_match.group(2),)
                elif circa_period_match:
                    metadata['inceptionstart'] = int(circa_period_match.group(1),)
                    metadata['inceptionend'] = int(circa_period_match.group(2),)
                    metadata['inceptioncirca'] = True
                elif short_period_match:
                    metadata['inceptionstart'] = int('%s%s' % (short_period_match.group(1), short_period_match.group(2), ))
                    metadata['inceptionend'] = int('%s%s' % (short_period_match.group(1), short_period_match.group(3), ))
                elif circa_short_period_match:
                    metadata['inceptionstart'] = int('%s%s' % (circa_short_period_match.group(1), circa_short_period_match.group(2), ))
                    metadata['inceptionend'] = int('%s%s' % (circa_short_period_match.group(1), circa_short_period_match.group(3), ))
                    metadata['inceptioncirca'] = True
                else:
                    print('Could not parse date: "%s"' % (date,))

            # acquisition year
            acquisition_year = item_json.get('ObjAcquisitionTxt')
            if acquisition_year:
                metadata['acquisitiondate'] = acquisition_year

            materials = item_json.get('ObjMaterialTxt_de')
            if materials:
                materials = materials.lower()
                material_lookup = {'acryl auf leinwand': 'oil on canvas' ,
                                   'öl auf leinwand': 'acrylic on canvas',}
                if materials in material_lookup:
                    metadata['medium'] = material_lookup.get(materials)
                else:
                    metadata['medium'] = materials.lower()

            owner = item_json.get('ObjOwnerTxt')
            if owner and owner == 'Berlinische Galerie, Landesmuseum für Moderne Kunst, Fotografie und Architektur, Berlin':
                metadata['ownerqid'] = 'Q700222'

            yield metadata

def get_berlinische_galerie_artists_wikidata():
    """
    Get the artists for which we have a link
    """
    pywikibot.output('Loading Berlinische Galerie artist ID lookup table')
    result = {}
    query = 'SELECT ?item ?id WHERE { ?item wdt:P4580 ?id  }'
    sq = pywikibot.data.sparql.SparqlQuery()
    query_result = sq.select(query)

    for result_item in query_result:
        qid = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
        result[int(result_item.get('id'))] = qid
    pywikibot.output('Loaded %s Wikidata items for Berlinische Galerie artist ID' % (len(result,)))
    return result


def main(*args):
    dict_gen = get_berlinische_galerie_generator()
    dry_run = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dry_run = True
        elif arg.startswith('-create'):
            create = True

    if dry_run:
        for painting in dict_gen:
            print (painting)
    else:
        art_data_bot = artdatabot.ArtDataBot(dict_gen, create=create)
        art_data_bot.run()


if __name__ == "__main__":
    main()
