#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape https://beckmann-gemaelde.org/gemaelde?page=0

"""
import artdatabot
import pywikibot
import requests
import re


def get_beckmann_generator():
    """
    Search for paintings and loop over it. Did I mention that old emuseum sucks?
    """
    base_search_url = 'https://beckmann-gemaelde.org/gemaelde?page=%s'

    locations = { 'Amsterdam': 'Q727',
                  'Bad Nenndorf': 'Q543342',
                  'Berlin': 'Q64',
                  'Davos': 'Q68097',
                  'Florenz': 'Q2044',
                  'Frankfurt am Main': 'Q1794',
                  'Hamburg': 'Q1055',
                  'Jütland': 'Q25389',
                  'New York': 'Q60',
                  'Niebusch (Schlesien)': 'Q11792426',
                  'Ohlstadt': 'Q432528',
                  'Paris': 'Q90',
                  'Saint Louis': 'Q38022',
                  'Thuner See': 'Q14426',
                  'Vietzkerstrand': 'Q1465604',
                  'Wangerooge': 'Q25135',
                  'Weimar': 'Q3955',
                  'Wervik': 'Q318532',
                  }
    unknown_locations = {}

    collections = {}

    unknown_collections = {}

    session = requests.Session()

    # 109589 is the first one giving content
    # 130586 and above nothing (might be lower)

    for i in range(0, 22):
        search_url = base_search_url % (i,)

        print (search_url)
        search_page = requests.get(search_url)

        item_regex = '<span class="field-content"><a href="/(\d+[^"]+)">(\d+[^\s]*) ([^<]+)</a><'
        item_matches = re.finditer(item_regex, search_page.text)

        for item_match in item_matches:
            metadata = {}
            url = 'https://beckmann-gemaelde.org/%s' % (item_match.group(1),)
            metadata['url'] = url
            # Only paintings on this website
            metadata['instanceofqid'] = 'Q3305213'
            metadata['catalog_code'] = item_match.group(2)
            metadata['catalog'] = 'Q111366312'
            metadata['title'] = {'de' : item_match.group(3)}
            metadata['description'] = { 'de' : 'Gemälde von Max Beckmann',
                                        'nl' : 'schilderij van Max Beckmann',
                                        'en' : 'painting by Max Beckmann',
                                        }
            # Only paintings by Max Beckmann
            metadata['creatorqid'] = 'Q164683'
            #print(item_match.group(1))
            #print(item_match.group(2))
            #print(item_match.group(3))
            item_page = requests.get(url)

            en_title_regex = '<div class="group-en-title field-group-div"><h3><span>Englische Titel</span></h3><p><span>([^<]+)</span>'
            en_title_match = re.search(en_title_regex, item_page.text)

            if en_title_match:
                metadata['title']['en'] = en_title_match.group(1)

            date_regex = '<div class="field-date-frontend font-size-16">[\s\t\r\n]*(\d\d\d\d)[\s\t\r\n]*</div>'
            date_matches = re.finditer(date_regex, item_page.text)

            if date_matches:
                date_matches = list(date_matches)
                if len(date_matches) == 1:
                    metadata['inception'] = int(date_matches[0].group(1))
                else:
                    print(f'Looking for date returned {len(date_matches)} matches')

            location_regex = '<div class="field-ort-frontend font-size-16">[\s\t\r\n]*([^<]+)[\s\t\r\n]*</div>'
            location_matches = re.finditer(location_regex, item_page.text)

            if location_matches:
                location_matches = list(location_matches)
                if len(location_matches) == 1:
                    location = location_matches[0].group(1).rstrip(' ')
                    #location = location
                    if location in locations:
                        metadata['madeinqid'] = locations.get(location)
                    else:
                        if location not in unknown_locations:
                            unknown_locations[location] = 0
                        unknown_locations[location] += 1
                        print(unknown_locations)
                else:
                    print(f'Looking for location returned {len(location_matches)} matches')

            private_regex = '<div style="margin-top: 15px">In privater Hand</div>'
            private_match = re.search(private_regex, item_page.text)
            if private_match:
                metadata['extracollectionqid'] = 'Q768717'

            medium_regex = '/div><span>Öl auf Leinwand</span>'
            medium_match = re.search(medium_regex, item_page.text)
            if medium_match:
                metadata['medium'] = 'oil on canvas'
            yield metadata


def main(*args):
    dict_gen = get_beckmann_generator()
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
        art_data_bot = artdatabot.ArtDataCatelogBot(dict_gen, create=create)
        art_data_bot.run()

if __name__ == "__main__":
    main()
