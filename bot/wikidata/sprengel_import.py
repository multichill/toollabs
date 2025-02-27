#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Sprengel Museum to Wikidata.

They have some kind of API that outputs json, but haven't figured out how to link to one object.

This bot uses artdatabot to upload it to Wikidata.
"""
import artdatabot
import pywikibot
import requests
import re
#import json

def get_sprengel_generator():
    """
    Generator to return Sprengel paintings
    """
    search_url = 'https://sprengel.hannover-stadt.de/museumWeb2_backend/api/artwork/search'
    base_url = 'https://sprengel.hannover-stadt.de/results?inventoryNumber=%s&page=1&pageSize=12'
    post_data = {"page":0,
                 "pageSize": "12",
                 "artworkCriteria": {"freeSearch":[],
                                     "artistContributor":[],
                                     "artForm":"Malerei",
                                     "materialAndTechnique":[],
                                     "groupOfWork":[],
                                     "page":"1",
                                     "pageSize":"12"},
                 "bookmarkCriteria":{"artworkIds":[]}
                 }

    session = requests.Session()
    start_page = session.post(search_url, json = post_data)
    total_pages = start_page.json().get('totalPages')

    for i in range(0, total_pages +1):
        post_data['page'] = i

        search_page = session.post(search_url, json = post_data)

        for item_data in search_page.json().get('content'):
            metadata = {}
            #print(json.dumps(item_data, indent=4))

            if item_data.get('artform') == 'Malerei':
                metadata['instanceofqid'] = 'Q3305213'
            else:
                print('Not a painting')
                continue

            if item_data.get('inventorynumber'):
                metadata['idpid'] = 'P217'
                metadata['id'] = item_data.get('inventorynumber')
                url = base_url % (item_data.get('inventorynumber'), )
                metadata['url'] = url.replace(' ', '%20')
            else:
                print('No inventory number found')
                continue

            metadata['collectionqid'] = 'Q510144'
            metadata['collectionshort'] = 'Sprengel'
            metadata['locationqid'] = 'Q510144'

            if item_data.get('title'):
                title = item_data.get('title').replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').replace('  ', ' ').strip()

                # Chop chop, might have long titles
                if len(title) > 220:
                    title = title[0:200]
                metadata['title'] = {'de': title, }

            if item_data.get('titletranslations'):
                en_title = item_data.get('titletranslations')[0].get('titleTranslation')
                en_title = en_title.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').replace('  ', ' ').strip()

                # Chop chop, might have long titles
                if len(en_title) > 220:
                    en_title = en_title[0:200]
                metadata['title']['en'] = en_title

            # Add the artist
            name = None
            if item_data.get('roles'):
                if len(item_data.get('roles')) == 1:
                    name = item_data.get('roles')[0].get('person').get('name')
                elif len(item_data.get('roles')) == 2:
                    if item_data.get('roles')[0].get('functionOfPerson') == 'Hauptkuenstler' and item_data.get('roles')[1].get('functionOfPerson') == 'Dargestellte/r':
                        name = item_data.get('roles')[0].get('person').get('name')
                    elif item_data.get('roles')[0].get('functionOfPerson') == 'Dargestellte/r' and \
                            item_data.get('roles')[1].get('functionOfPerson') == 'Hauptkuenstler':
                        name = item_data.get('roles')[1].get('person').get('name')
            if name:
                if ',' in name:
                    (surname, sep, firstname) = name.partition(',')
                    name = '%s %s' % (firstname.strip(), surname.strip(),)
                metadata['description'] = { 'nl': '%s van %s' % ('schilderij', name,),
                                            'en': '%s by %s' % ('painting', name,),
                                            'de': '%s von %s' % ('Gemälde', name, ),
                                            'fr': '%s de %s' % ('peinture', name, ),
                                            }
                metadata['creatorname'] = name
            else:
                print('Unable to extract name from these roles')
                print(item_data.get('roles'))

            if item_data.get('date') and item_data.get('datestart') and item_data.get('dateend'):
                period_date_slash = '%s/%s' % (item_data.get('datestart'), item_data.get('dateend'))
                period_date_dash = '%s–%s' % (item_data.get('datestart'), item_data.get('dateend'))
                if item_data.get('date') == item_data.get('datestart') == item_data.get('dateend'):
                    metadata['inception'] = int(item_data.get('date'))
                elif item_data.get('date') == period_date_slash or item_data.get('date') == period_date_dash:
                    metadata['inceptionstart'] = int(item_data.get('datestart'))
                    metadata['inceptionend'] = int(item_data.get('dateend'))
                #else:
                #    print('"%s"' % item_data.get('datestart'),)
                #    print('"%s"' % item_data.get('date'),)
                #    print('"%s"' % item_data.get('dateend'),)

            # Dimensions
            if item_data.get('dimensions') and len(item_data.get('dimensions')) == 1:
                if item_data.get('dimensions')[0].get('type') == 'H\u00f6he x Breite':
                    dimension_regex = '(?P<height>\d+(,\d+)?)\s*x\s*(?P<width>\d+(,\d+)?)\s*cm'
                    value = item_data.get('dimensions')[0].get('value')
                    dimension_match = re.match(dimension_regex, value)
                    if dimension_match:
                        metadata['heightcm'] = dimension_match.group('height')
                        metadata['widthcm'] = dimension_match.group(u'width')

            # materialandtechniques
            if item_data.get('materialandtechniques') and len(item_data.get('materialandtechniques')) == 1:
                medium = item_data.get('materialandtechniques')[0].get('materialandtechnique')
                if medium == '\u00d6l auf Leinwand':
                    metadata['medium'] = 'oil on canvas'

            # Owner info
            owner_reasons = ['Geschenk des Künstlers',
                             'Vermächtnis Wolf und Ursula Hermann',
                             'Schenkung aus Privatbesitz']
            if item_data.get('ownerinfo') and item_data.get('proprietor'):
                if item_data.get('ownerinfo') == 'Sammlung Nieders\u00e4chsische Sparkassenstiftung':
                    metadata['ownerqid'] = 'Q19964586'
                    metadata['extracollectionqid'] = 'Q19964586'
                elif item_data.get('proprietor') == 'Sprengel Museum Hannover' and \
                        item_data.get('ownerinfo') in owner_reasons:
                    metadata['ownerqid'] = 'Q510144'

            yield metadata


def main(*args):
    dict_gen = get_sprengel_generator()
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
