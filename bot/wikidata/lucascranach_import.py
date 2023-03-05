#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from Cranach Digital Archive to Wikidata

The website at https://lucascranach.org/en/search/?kind=PAINTING contains 2361 paintings

Use artdatabot to upload it to Wikidata
"""
import artdatabot
import pywikibot
import requests
import re

def get_cranach_generator():
    """
    Generator to return cranach paintings
    """
    session = requests.Session()

    lang = 'en'

    base_search_url = 'https://mivs02.gm.fh-koeln.de/?language=%s&entity_type:neq=DOCUMENT&size_height:gt=200&size=60&from=%s&dating_begin:gte=1470&entity_type:eq=PAINTING'

    headers = {'Origin': 'https://lucascranach.org',
               'Referer': 'https://lucascranach.org/',
               'authorization': 'Basic bHVjYXM6Y3I0bjRo',  # username lucas & password cr4n4h , very secure :-)
               }

    for i in range(0, 2400, 60):
        search_url = base_search_url % (lang, i,)
        print(search_url)
        search_page = session.get(search_url, headers=headers)

        for item_info in search_page.json().get('data').get('results'):
            metadata = {}
            metadata['artworkidpid'] = 'P5783'  #  Cranach Digital Archive artwork ID (P5783)
            metadata['artworkid'] = item_info.get('inventory_number')

            url = 'https://lucascranach.org/%s/%s' % (lang, item_info.get('inventory_number'),)
            metadata['url'] = url
            title = item_info.get('title').replace('\n', ' ').replace('\t', ' ').replace('  ', ' ').strip()
            metadata['title'] = {lang: title, }

            if item_info.get('entity_type') == 'PAINTING':
                metadata['instanceofqid'] = 'Q3305213'
            else:
                continue

            if item_info.get('involved_persons'):
                if len(item_info.get('involved_persons')) == 1:
                    person = item_info.get('involved_persons')[0]
                    if person.get('roleType') == 'ARTIST':
                        if person.get('name') and person.get('prefix') == '' and person.get('suffix') == '':
                            metadata['creatorname'] = person.get('name')
                            if person.get('name') == 'Lucas Cranach the Elder':
                                metadata['creatorqid'] = 'Q191748'
                            elif person.get('name') == 'Lucas Cranach the Younger':
                                metadata['creatorqid'] = 'Q170339'
                        elif person.get('name') and person.get('prefix') == '' and person.get('suffix'):
                            metadata['creatorname'] = '%s %s' % (person.get('name'), person.get('suffix'))
                        elif person.get('name') == '' and person.get('prefix') == '' and person.get('suffix'):
                            metadata['creatorname'] = person.get('suffix')
                if len(item_info.get('involved_persons')) == 2:
                    names = []
                    for person in item_info.get('involved_persons'):
                        if person.get('roleType') == 'ARTIST':
                            if person.get('name') and person.get('prefix') == '' and person.get('suffix') == '':
                                names.append(person.get('name'))
                            elif person.get('name') and person.get('prefix') == '' and person.get('suffix'):
                                names.append('%s %s' % (person.get('name'), person.get('suffix')))
                            elif person.get('name') == '' and person.get('prefix') == '' and person.get('suffix'):
                                names.append(person.get('suffix'))
                    if len(item_info.get('involved_persons')) == len(names):
                        metadata['creatorname'] = '%s or %s' % (names[0], names[1])

            if metadata.get('creatorname'):
                if lang == 'en' and item_info.get('classification') == 'Painting':
                    metadata['description'] = {lang: 'painting by %s (%s)' % (metadata.get('creatorname'),
                                                                              item_info.get('repository'),)
                                               }
                elif lang == 'de' and item_info.get('classification') == 'Malerei':
                    metadata['description'] = {lang: 'Gemälde von %s (%s)' % (metadata.get('creatorname'),
                                                                              item_info.get('repository'),)
                                               }
            if item_info.get('dating'):
                date = item_info.get('dating')
                year_regex = '^(\d\d\d\d)$'
                date_circa_regex = '^about\s*(\d\d\d\d)$'
                period_regex = '^(\d\d\d\d)\s*[--\/]\s*(\d\d\d\d)$'
                circa_period_regex = '^about\s*(\d\d\d\d)\s*[--\/]\s*(\d\d\d\d)$'
                short_period_regex = '^(\d\d)(\d\d)[--\/](\d\d)$'
                circa_short_period_regex = '^about\s*(\d\d)(\d\d)[-–/](\d\d)$'

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

            yield metadata


def main(*args):
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        if arg.startswith('-create'):
            create = True

    painting_generator = get_cranach_generator()

    if dryrun:
        for painting in painting_generator:
            print(painting)
    else:
        artDataBot = artdatabot.ArtDataIdentifierBot(painting_generator, id_property='P5783', create=create)
        artDataBot.run()

if __name__ == "__main__":
    main()
