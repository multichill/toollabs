#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the  Joods Museum to Wikidata.

They have a collection api:
https://data.jck.nl/search/?q=&qf[]=nave_collectionPart%3AMuseumcollectie&qf[]=nave_objectSoort%3Aschilderij&page=2&format=json

This bot uses artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re


def get_joods_museum_generator():
    """
    Generator to return Joods Museum paintings
    """
    basesearchurl = 'https://data.jck.nl/search/?q=&qf[]=nave_collectionPart%%3AMuseumcollectie&qf[]=nave_objectSoort%%3Aschilderij&format=json&start=%s&rows=%s'
    start = 1
    rows = 50
    hasNext = True

    while hasNext:
        searchUrl = basesearchurl % (start, rows)
        print (searchUrl)
        searchPage = requests.get(searchUrl)
        searchJson = searchPage.json()
        #print (searchJson)

        start = searchJson.get('result').get('pagination').get('nextPage')
        hasNext = searchJson.get('result').get('pagination').get('hasNext')

        for item in searchJson.get('result').get('items'):
            itemfields = item.get('item').get('fields')
            #print (itemfields)
            metadata = {}

            if itemfields.get('edm_dataProvider')[0].get('value') == 'Joods Historisch Museum':
                metadata['collectionqid'] = 'Q702726'
                metadata['collectionshort'] = 'Joods Museum'
                metadata['locationqid'] = 'Q702726'
            else:
                #Another collection, skip
                continue

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = 'Q3305213'

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = itemfields.get('dc_identifier')[0].get('value')
            metadata['idpid'] = u'P217'

            if itemfields.get('dc_title'):
                title = itemfields.get('dc_title')[0].get('value').lstrip('[').rstrip(']')
                metadata['title'] = {'nl': title, }

            metadata['url'] = itemfields.get('entryURI')

            name = 'onbekend'

            if itemfields.get('dc_creator'):
                name = itemfields.get('dc_creator')[0].get('value')
                name_regex = '^([^,]+), ([^\(]+) (\([^\)]+\))$'
                name_match = re.match(name_regex, name)
                if name_match:
                    name = '%s %s %s' % (name_match.group(2), name_match.group(1), name_match.group(3))
                elif u',' in name:
                    (surname, sep, firstname) = name.partition(u',')
                    name = '%s %s' % (firstname.strip(), surname.strip(),)
            metadata['creatorname'] = name

            if metadata['creatorname'] == 'onbekend':
                metadata['creatorname'] = 'anonymous'
                metadata['description'] = {'nl': 'schilderij van anonieme schilder',
                                           'en': 'painting by anonymous painter',
                                           }
                metadata['creatorqid'] = 'Q4233718'
            else:
                metadata['description'] = {'nl': '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                           'en': '%s by %s' % ('painting', metadata.get('creatorname'),),
                                           }


            paints = {'olieverf': 'oil',
                      'waterverf': 'watercolor',
                      'aquarelverf': 'watercolor',
                      'acrylverf': 'acrylic',

                      }
            surfaces = {'doek': 'canvas',
                        'textiel': 'canvas',
                        'textiel (linnen of katoen?)': 'canvas',
                        'linnen': 'canvas',
                        'doek (linnen)': 'canvas',
                        'paneel': 'panel',
                        'panel': 'panel',
                        'hout': 'panel',
                        'naaldhout': 'panel',
                        'papier': 'paper',
                        'karton': 'cardboard',
                        }
            paint = None
            surface = None

            if itemfields.get('nave_material') and len(itemfields.get('nave_material')) == 2:
                material_1 = itemfields.get('nave_material')[0].get('value').strip()
                material_2 = itemfields.get('nave_material')[1].get('value').strip()

                for material in (material_1, material_2):
                    if material in paints:
                        paint = paints.get(material)
                    elif material in surfaces:
                        surface = surfaces.get(material)
                    else:
                        print('Unknown material %s' % (material,))
            elif itemfields.get('nave_material') and len(itemfields.get('nave_material')) > 2:
                print('More than 2 materials')
                print(itemfields.get('nave_material'))

            if paint and surface:
                metadata['medium'] = '%s on %s' % (paint, surface)

            if itemfields.get('dc_date'):
                date = itemfields.get('dc_date')[0].get('value')
                year_regex = '^(\d\d\d\d)$'
                date_circa_regex = '^ca?\.\s*(\d\d\d\d)$'
                period_regex = '^(\d\d\d\d)\s*[--\/]\s*(\d\d\d\d)$'
                circa_period_regex = '^ca?\.\s*(\d\d\d\d)\s*[--\/]\s*(\d\d\d\d)$'
                short_period_regex = '^(\d\d)(\d\d)[--\/](\d\d)$'
                circa_short_period_regex = '^ca?\.\s*(\d\d)(\d\d)[-–/](\d\d)$'

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

            if itemfields.get('edm_isShownBy'):
                recentinception = False
                if metadata.get('inception') and metadata.get('inception') > 1925:  # Europe so stayin on save side
                    recentinception = True
                if metadata.get('inceptionend') and metadata.get('inceptionend') > 1925:
                    recentinception = True
                if not recentinception:
                    metadata['imageurl'] = '%s000' % (itemfields.get('edm_isShownBy')[0].get('value'))
                    metadata['imageurlformat'] = 'Q2195'  # JPEG
                    metadata['imageoperatedby'] = 'Q702726'  # Jewish Museum

            yield metadata

    return
    
def main(*args):
    dictGen = get_joods_museum_generator()
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True

    if dryrun:
        for painting in dictGen:
            print(painting)
    else:
        artDataBot = artdatabot.ArtDataBot(dictGen, create=create)
        artDataBot.run()

if __name__ == "__main__":
    main()
