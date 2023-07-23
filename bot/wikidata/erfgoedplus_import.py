#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from erfgoedplus.be

looping over https://www.erfgoedplus.be/zoeken?sort=modifieddate&sort-order=desc&filters=1&object=schilderijen

This bot uses artdatabot to upload it to Wikidata.
"""
import artdatabot
import pywikibot
import requests
import re
import json


def get_erfgoedplus_generator(collectionname, collectionid):
    """
    The generator to get the erfgoedplus works
    :return:
    """
    total = 100000
    step = 12
    for i in range(0, total, step):
        es_query = {
            "type": "query",
            "from": i,
            "size": step,
            "countonly": False,
            "highlight": False,
            "queries": [],
            "filter": [],
            "filters": [
                {
                    "field": "object",
                    "values": [
                        "schilderijen"
                    ]
                },
                {
                    "field": "collection",
                    "values": [
                        collectionname
                    ]
                }
            ],
            "navigator_limits": {
                "object": { "size": 0 },
                "collection": { "size": 0 },
                "maker": { "size": 0 },
                "productionplace": { "size": 0 },
                "depictedplace": { "size": 0 },
                "period": { "size": 0 },
                "productioncentury": { "size": 0 },
                "location_structure": { "size": 0 },
                "location_road": { "size": 0 },
                "location_borough": { "size": 0 },
                "location_province": { "size": 0 },
                "location_municipality": { "size": 0 },
                "location_lookupaddress": { "size": 0 },
                "material": { "size": 0 },
                "resources": { "size": 0 }
            },
            "sort": { "modifieddate": { "order": "desc" } }
        }
        #print(es_query)

        search_page = requests.post('https://www.erfgoedplus.be/es',
                                    data={'d': json.dumps(es_query)},
                                    headers={'Origin': 'https://www.erfgoedplus.be',
                                             'Accept': 'application/json',
                                             'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                             'Referer': 'https://www.erfgoedplus.be/zoeken?sort=modifieddate&sort-order=desc&filters=1&object=schilderijen&collection=Collectie%20van%20M%20Leuven&page=2',
                                             'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
                                             'X-Requested-With': 'XMLHttpRequest', })
        #print(search_page.text)
        search_json = search_page.json()
        hits = search_json.get('hits').get('hits')
        if not hits:
            break
        for hit in hits:
            #print(json.dumps(hit, indent=4))
            erfgoedplus_id = hit.get('_id')
            item = hit.get('_source')

            metadata = {}

            print(erfgoedplus_id)

            #metadata['artworkidpid'] = 'Pxxxx'  # If we ever create the id
            #metadata['artworkid'] = erfgoedplus_id

            # Only want to trigger this sometimes
            if item.get('othernumber') and not isinstance(item.get('othernumber'), list) and False:
                kik_regex = '^<a href=&quot;http://balat\.kikirpa\.be/object/(\d+)&quot;.+$'
                kik_match = re.match(kik_regex, item.get('othernumber'))
                if kik_match:
                    metadata['artworkidpid'] = 'P3293'  # BALaT object ID (P3293)
                    metadata['artworkid'] = kik_match.group(1)

            url = 'https://www.erfgoedplus.be/details/%s' % (erfgoedplus_id,)
            #item_page = requests.get(url)
            pywikibot.output(url)
            metadata['url'] = url

            if item.get('object') == 'schilderijen':
                metadata['instanceofqid'] = 'Q3305213'
            elif isinstance(item.get('object'), list) and 'schilderijen' in item.get('object'):
                metadata['instanceofqid'] = 'Q3305213'
                if 'portretten' in item.get('object'):
                    metadata['genreqid'] = 'Q134307'  # portrait (Q134307)
            else:
                print(item.get('object'))
                continue

            metadata['idpid'] = 'P217'
            metadata['id'] = item.get('inventorynumber')

            metadata['collectionshort'] = collectionname

            if collectionid:
                metadata['collectionqid'] = collectionid
                metadata['locationqid'] = collectionid

            if item.get('title'):
                metadata['title'] = {'nl': item.get('title'), }  # Only doing Dutch. Mix of French & Dutch

            if item.get('maker'):
                creatorname = item.get('maker')
                if not isinstance(creatorname, list):
                    creator_regex = '^([^,]+), ([^,]+)$'
                    creator_match = re.match(creator_regex, creatorname)
                    if creator_match:
                        creatorname = '%s %s' % (creator_match.group(2), creator_match.group(1))
                    metadata['creatorname'] = creatorname

                    metadata['description'] = {'nl': '%s van %s' % ('schilderij', creatorname,),}

            date = item.get('productiondate')

            if date:
                # TODO: Implement date logic
                year_regex = '^(\d\d\d\d)$'
                period_regex = '^(\d\d\d\d) - (\d\d\d\d)$'
                #year_circa_regex = '^(\d\d\d\d) \(ca\) - (\d\d\d\d) \(ca\)$'

                year_match = re.match(year_regex, date)
                period_match = re.match(period_regex, date)

                if year_match:
                    metadata['inception'] = int(year_match.group(1))
                elif period_match:
                    metadata['inceptionstart'] = int(period_match.group(1))
                    metadata['inceptionend'] = int(period_match.group(2))
                else:
                    print('Could not parse date: "%s"' % (date,))

            # Materal
            if item.get('material'):
                found_materials = set()
                for material in item.get('material'):
                    found_materials.add(material)

                if found_materials:
                    if found_materials == {'olieverf', 'canvas'}:
                        metadata['medium'] = 'oil on canvas'
                    #elif found_materials == {"peinture à l'huile", 'toile à peindre'}:
                    #    metadata['medium'] = 'oil on canvas'
                    #elif found_materials == {'verf', 'schilderdoek'}:
                    #    metadata['medium'] = 'paint on canvas'
                    elif found_materials == {'olieverf', 'paneel (hout)'}:
                        metadata['medium'] = 'oil on panel'
                    #elif found_materials == {"peinture à l'huile", 'bois'}:
                    #    metadata['medium'] = 'oil on panel'
                    #elif found_materials == {'paneel[drager]', 'eik', 'olieverf'}:
                    #    metadata['medium'] = 'oil on oak panel'
                    elif found_materials == {'olieverf', 'papier (vezelproduct)'}:
                        metadata['medium'] = 'oil on paper'
                    else:
                        print(found_materials)

            # Movement
            # See https://balat.kikirpa.be/object/20024607

            # Technique

            # Dimensions
            ##dimensions_regex = '<strong>Creator</strong>:\s*</div><div class=\'three-fifth last\'><a class="lite1" href="results\.php\?[^"]+">([^<]+)</a>\s*\([^\)]+\)\s*<a href="people\.php\?[^"]+" title="People & institutions">\s*<i class="icon-user-1"></i></a><br/>Date:\s*([^<]+)</div>'
            #dimensions_regex = '<strong>Dimensions</strong>:\s*<br/>\s*</div><div class\=\'three-fifth last\'><i>hoogte</i>:\s*(?P<height>\d+(\.\d+)?)\s*cm<br/>\s*<i>breedte</i>:\s*(?P<width>\d+(\.\d+)?)\s*cm</div><div class="clear">'
            ##dimensions_regex = '<h5>Measurements</h5>[\s\t\r\n]+<p>H\s*(?P<height>\d+(\.\d+)?)\s*x\s*W\s*(?P<width>\d+(\.\d+)?)\s*cm</p>'
            #dimensions_match = re.search(dimensions_regex, item_page.text)
            #if dimensions_match:
            #    metadata['heightcm'] = dimensions_match.group('height')
            #    metadata['widthcm'] = dimensions_match.group('width')
            yield metadata


def main(*args):
    dryrun = False
    #createjson = False
    create = False
    collectionid = None
    collectionname = None
    start_search_page = 1

    collections = {'Q2362660': 'Collectie van M Leuven',  # M Leuven (Q2362660)
                   }

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True
        elif arg.startswith('-collectionid:'):
            if len(arg) == len('-collectionid:'):
                collectionid = pywikibot.input(
                    u'Please enter the collectionid you want to work on:')
            else:
                collectionid = arg[len('-collectionid:'):]
            if collectionid not in collections:
                pywikibot.output('Unknown collection')
                return
            collectionname = collections.get(collectionid)

    painting_generator = get_erfgoedplus_generator(collectionname, collectionid)

    if dryrun:
        for painting in painting_generator:
            print(painting)

    else:
        artDataBot = artdatabot.ArtDataBot(painting_generator, create=create)
        artDataBot.run()
    #else:
    #    artDataBot = artdatabot.ArtDataIdentifierBot(painting_generator, id_property='P3293', create=create)
    #    artDataBot.run()


if __name__ == "__main__":
    main()
