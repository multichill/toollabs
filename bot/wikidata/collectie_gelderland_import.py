#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from multiple collections in Collectie Gelderland to Wikidata.

This bot uses artdatabot to upload it to Wikidata
"""
import artdatabot
import pywikibot
import requests
#import re
#import html

def get_collectie_gelderland_generator(objectcategorie, participant, prefix, collectionqid, collectionshort, locationqid):
    """
    Generator to return Collectie Gelderland paintings
    """
    apikey = '4c536e8a-6cdd-11e9-ab74-37871f3093e6'
    rows = 10
    base_search_url = 'https://webservices.picturae.com/mediabank/media?&apiKey=%s&q=&page=%s&rows=%s&fq[]=search_s_objectcategorie:%%22%s%%22&fq[]=search_s_participant:%%22%s%%22'

    search_url = base_search_url % (apikey, '1', rows, objectcategorie, participant)
    session = requests.Session()
    search_page = session.get(search_url)
    pages = search_page.json().get('metadata').get('pagination').get('pages')

    for current_page in range(1, pages+1):
        search_url = base_search_url % (apikey, current_page, rows, objectcategorie, participant)
        print(search_url)
        search_page = session.get(search_url)

        for item_info in search_page.json().get('media'):
            metadata = {}
            url = 'https://www.collectiegelderland.nl/%s/object/%s' % (prefix, item_info.get('id'),)

            pywikibot.output(url)
            metadata['url'] = url

            metadata['collectionqid'] = collectionqid
            metadata['collectionshort'] = collectionshort
            if locationqid:
                metadata['locationqid'] = locationqid

            # Searching for paintings
            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = 'P217'

            for fields in item_info.get('metadata'):
                field = fields.get('field')
                label = fields.get('label')
                value = fields.get('value')
                if field == 'spectrum_objectnummer' and label == 'Objectnummer':
                    metadata['id'] = value.strip()

                elif field == 'object_title' and label == 'Titel':
                    title = value
                    if len(title) > 220:
                        title = title[0:200]
                    title = title.replace('\r', '').replace('\t', '').replace('\n', '').replace('  ', ' ').strip()
                    metadata['title'] = {'nl': title, }

                elif field == 'dcterms_subject' and label == 'Onderwerp':
                    if bool(set(value) & {'Vrouwenportretten', 'Familieportretten', 'mansportret'}):
                        metadata['genreqid'] = 'Q134307'  # portrait

                elif field == 'creators' and label == 'Vervaardiger':
                    if len(value) == 1 and len(value[0]) == 1 and value[0][0].get('field') == 'creators.surname':
                        name = value[0][0].get('value')
                        if ',' in name:
                            (surname, sep, firstname) = name.partition(',')
                            name = '%s %s' % (firstname.strip(), surname.strip(),)
                        metadata['creatorname'] = name.strip()

                        if name in ['onbekend', 'anoniem', 'Anoniem']:
                            metadata['description'] = {'nl': 'schilderij van anonieme schilder',
                                                       'en': 'painting by anonymous painter',
                                                       }
                            metadata['creatorqid'] = 'Q4233718'
                        else:
                            metadata['description'] = { 'nl': '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                                        'en': '%s by %s' % ('painting', metadata.get('creatorname'),),
                                                        'de': '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                                        'fr': '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                                        }

                elif field == 'dcterms_temporal_start' and label == 'Datering van':
                    metadata['inceptionstart'] = int(value)

                elif field == 'dcterms_temporal_end' and label == 'Datering tot':
                    metadata['inceptionend'] = int(value)

                elif field == 'spectrum_materiaal' and label == 'Materiaal':
                    materials = set(value)

                    if materials == {'olieverf', 'doek'} or materials == {'olieverf op doek'} \
                            or materials == {'verf', 'doek', 'olieverf'} or materials == {'linnen', 'olieverf'}:
                        metadata['medium'] = 'oil on canvas'
                    elif materials == {'olieverf', 'paneel'} or materials == {'olieverf op paneel'} \
                            or materials == {'verf', 'paneel', 'olieverf'} or materials == {'olieverf', 'paneel', 'hout'}:
                        metadata['medium'] = 'oil on panel'
                    elif materials == {'paneel', 'olieverf', 'eikenhout'} or materials == {'eikenhout', 'olieverf'}:
                        metadata['medium'] = 'oil on oak panel'
                    elif materials == {'olieverf', 'koper'}:
                        metadata['medium'] = 'oil on copper'
                    elif materials == {'olieverf', 'papier'}:
                        metadata['medium'] = 'oil on paper'
                    elif materials == {'olieverf', 'karton'}:
                        metadata['medium'] = 'oil on cardboard'
                    elif materials == {'acryl', 'doek'} or materials == {'acrylverf', 'doek'}:
                        metadata['medium'] = 'acrylic paint on canvas'
                    elif materials == {'olieverf', 'doek', 'paneel'} or materials == {'hout [plantaardig materiaal]', 'stof [textiel]', 'olieverf'}:
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
                        print('Unable to match materials for %s' % (materials,))

                elif field == 'sizes' and label == 'Afmetingen':
                    if len(value) == 2 and len(value[0]) == 3 and len(value[1]) == 3:
                        hoogte = value[0]
                        if hoogte[0].get('field') == 'sizes.size_type' and hoogte[0].get('label') == 'Afmeting type' \
                            and hoogte[0].get('value') == 'hoogte' and hoogte[1].get('field') == 'sizes.value' \
                            and hoogte[1].get('label') == 'Waarde' and hoogte[2].get('field') == 'sizes.unit' \
                            and hoogte[2].get('label') == 'Eenheid' and hoogte[2].get('value') == 'cm':
                            metadata['heightcm'] = hoogte[1].get('value')
                        breedte = value[1]
                        if breedte[0].get('field') == 'sizes.size_type' and breedte[0].get('label') == 'Afmeting type' \
                                and breedte[0].get('value') == 'breedte' and breedte[1].get('field') == 'sizes.value' \
                                and breedte[1].get('label') == 'Waarde' and breedte[2].get('field') == 'sizes.unit' \
                                and breedte[2].get('label') == 'Eenheid' and breedte[2].get('value') == 'cm':
                            metadata['widthcm'] = breedte[1].get('value')

                elif field == 'reference_source' and label == 'Bronvermelding':
                    if value == 'Geldersch Landschap & Kasteelen, bruikleen Brantsen van de Zyp Stichting':
                        metadata['extracollectionqid'] = 'Q116311926'

                elif field == 'dcterms_rights_url' and label == 'Auteursrechten url':
                    if value == 'https://creativecommons.org/publicdomain/mark/1.0/' and item_info.get('asset'):
                        asset = item_info.get('asset')[0]
                        if asset.get('mimetype') == 'image/jpeg' and asset.get('download'):
                            metadata['imageurl'] = asset.get('download')
                            metadata['imageurlformat'] = 'Q2195'  # JPEG
                            #    metadata['imageurllicense'] = 'Q18199165' # cc-by-sa.40
                            metadata['imageoperatedby'] = metadata.get('collectionqid')
                            metadata['imageurlforce'] = False  # Used this to add suggestions everywhere

            yield metadata


def main(*args):
    collections = {'Q1856245': {'objectcategorie': 'schilderijen',
                                'participant': 'Geldersch%20Landschap%20%26%20Kasteelen',
                                'prefix': 'geldersch-landschap-en-kasteelen',
                                'collectionqid': 'Q1856245',
                                'collectionshort': 'GLK',
                                'locationqid': None,
                                },
                   }

    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        if arg.startswith('-create'):
            create = True

    for collectionqid in collections:
        collection_info = collections.get(collectionqid)
        generator = get_collectie_gelderland_generator(collection_info.get('objectcategorie'),
                                                       collection_info.get('participant'),
                                                       collection_info.get('prefix'),
                                                       collection_info.get('collectionqid'),
                                                       collection_info.get('collectionshort'),
                                                       collection_info.get('locationqid'),
                                                       )
        if dryrun:
            for painting in generator:
                print(painting)
        else:
            artDataBot = artdatabot.ArtDataBot(generator, create=create)
            artDataBot.run()

if __name__ == "__main__":
    main()
