#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Staatliche Museen zu Berlin to Wikidata based on their api

"""
import artdatabot
import pywikibot
import requests
import json
import pywikibot.data.sparql
import re

def get_smb_generator():
    """
    """

    post_json = {"q_advanced":[{"field":"technicalTerm","operator":"AND","q":"Gemälde"},{"field":"collectionKey","operator":"AND","q":"GG*"}]}

    headers = { "Accept" : "*/*",
                "origin" : "https://api.smb.museum",
                "Referer" : "https://recherche.smb.museum/",
                "Content-type": "application/json",
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0",
                }
    #base_search_url = 'https://api.smb.museum/v1/graphql'

    limit = 15
    base_search_url = 'https://api.smb.museum/search/?lang=de&limit=%s&offset=%s'

    painting_types = ['Gemälde', 'Malerei', 'Malerei/Gemälde']

    for i in range(0, 1500, 15):
        search_url = base_search_url % (limit, i)
        search_page = requests.post(search_url, data=json.dumps(post_json), headers=headers)
        for object_info in search_page.json().get('objects'):
            #print(json.dumps(object_info,  indent=4, sort_keys=True))

            metadata = {}
            #print (workinfo)
            # Check if it's a painting
            if object_info.get('technicalTerm') not in painting_types:
                print('PANIC, not a painting')
                continue
            metadata['instanceofqid'] = 'Q3305213'
            # And check if we're working on the right collection
            if object_info.get('collection') != 'Gemäldegalerie':
                print('PANIC, not the right collection')
                continue

            metadata['collectionqid'] = 'Q165631'
            metadata['collectionshort'] = 'GG'
            metadata['locationqid'] = 'Q165631'

            title = object_info.get('title').replace('\n', '').replace('\t', '').replace('   ', ' ').strip()

            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { 'de' : title,
                                  }
            if object_info.get('titles'):
                for title in object_info.get('titles'):
                    if title.startswith('Übersetzung engl.: '):
                        title = title.replace('Übersetzung engl.: ', '')
                        title = title.replace('\n', '').replace('\t', '').replace('   ', ' ').strip()
                        if len(title) > 220:
                            title = title[0:200]
                        metadata['title']['en'] = title

            # Get the SMB-digital ID (P8923)
            metadata['artworkid'] = object_info.get('@id')
            metadata['artworkidpid'] = 'P8923'
            metadata['url'] = object_info.get('permalink')

            # I had one item with missing identifier, wonder if it shows up here too
            metadata['idpid'] = 'P217'
            if not object_info.get('identNumber'):
                # Few rare items without an inventory number, just skip them
                print (object_info)
                print('The inventory number (identNumber) is missing on %s' % (metadata.get('url'),))
                #continue
            metadata['id'] = object_info.get('identNumber')

            if object_info.get('involvedParties') and len(object_info.get('involvedParties')) == 1:
                    name = object_info.get('involvedParties')[0]
                    if name.startswith('Herstellung: '):
                        name = name.replace('Herstellung: ', '').strip()
                    if name.endswith(', Maler*in'):
                        name = name.replace(', Maler*in', '').strip()
                    metadata['creatorname'] = name
                    if object_info.get('collectionKey') == 'GGVerlust':
                        metadata['description'] = { 'en' : '%s by %s' % ('lost painting', metadata.get('creatorname'),),
                                                    }
                    else:
                        metadata['description'] = { 'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'),),
                                                    'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                                    'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                                    }

            # Try to extract the date
            if object_info.get('dating') and len(object_info.get('dating')) == 1:
                date_string = object_info.get('dating')[0].strip().lower()
                if date_string.startswith('datierung: '):
                    date_string = date_string.replace('datierung: ', '')
                date_regex = '^(\d\d\d\d)$'
                date_circa_regex = '^um\s*(\d\d\d\d)$'
                period_regex = '^(\d\d\d\d)\s*[\/-]\s*(\d\d\d\d)$'
                circa_period_regex = '^um\s*(\d\d\d\d)\s*[\/-]\s*(\d\d\d\d)$'
                short_period_regex = '^(\d\d)(\d\d)\s*[\/-]\s*(\d\d)$'
                circa_short_period_regex = '^um\s*(\d\d)(\d\d)\s*[\/-]\s*(\d\d)$'

                date_match = re.match(date_regex, date_string)
                date_circa_match = re.search(date_circa_regex, date_string)
                period_match = re.search(period_regex, date_string)
                circa_period_match = re.search(circa_period_regex, date_string)
                short_period_match = re.search(short_period_regex, date_string)
                circa_short_period_match = re.search(circa_short_period_regex, date_string)

                if date_match:
                    metadata['inception'] = int(date_match.group(1).strip())
                elif date_circa_match:
                    metadata['inception'] = int(date_circa_match.group(1).strip())
                    metadata['inceptioncirca'] = True
                elif period_match:
                    metadata['inceptionstart'] = int(period_match.group(1))
                    metadata['inceptionend'] = int(period_match.group(2))
                elif circa_period_match:
                    metadata['inceptionstart'] = int(circa_period_match.group(1))
                    metadata['inceptionend'] = int(circa_period_match.group(2))
                    metadata['inceptioncirca'] = True
                elif short_period_match:
                    metadata['inceptionstart'] = int('%s%s' % (short_period_match.group(1),short_period_match.group(2),))
                    metadata['inceptionend'] = int('%s%s' % (short_period_match.group(1),short_period_match.group(3),))
                elif circa_short_period_match:
                    metadata['inceptionstart'] = int('%s%s' % (circa_short_period_match.group(1),circa_short_period_match.group(2),))
                    metadata['inceptionend'] = int('%s%s' % (circa_short_period_match.group(1),circa_short_period_match.group(3),))
                    metadata['inceptioncirca'] = True
                else:
                    print ('Could not parse date: "%s"' % (date_string,))

            # Medium seems to be incomplete like they're only showing first entry in the list

            if object_info.get('acquisition') and len(object_info.get('acquisition')) == 1:
                acquisition_regex = '^(\d\d\d\d) .+$'
                acquisition_match = re.match(acquisition_regex, object_info.get('acquisition')[0])
                if acquisition_match:
                    metadata['acquisitiondate'] = acquisition_match.group(1)

            if object_info.get('attachments') and \
                    object_info.get('assets'):
                #and \
                #metadata.get('creatorname'):
                # They put everything under public domain mark
                asset_id = object_info.get('assets')[0]
                image_url = 'https://recherche.smb.museum/images/%s_4000x4000.jpg' % (asset_id,)

                metadata['imageurl'] = image_url
                metadata['imageurlformat'] = 'Q2195' # JPEG
                metadata['imageoperatedby'] = 'Q700216'  # Staatliche Museen zu Berlin (Q700216)
                #metadata['imageurlforce'] = True  # A lot with crappy images
            yield metadata


def main(*args):
    painting_generator = get_smb_generator()
    dry_run = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dry_run = True
        elif arg.startswith('-create'):
            create = True

    if dry_run:
        for painting in painting_generator:
            print (painting)
    else:
        art_data_bot = artdatabot.ArtDataIdentifierBot(painting_generator, id_property='P8923', create=create)
        #art_data_bot = artdatabot.ArtDataBot(painting_generator, create=create)
        art_data_bot.run()


if __name__ == "__main__":
    main()
