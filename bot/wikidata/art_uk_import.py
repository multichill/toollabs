#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from Art UK

Looping over https://artuk.org/discover/artworks/view_as/grid/search/work_type:painting/page/3

This bot uses artdatabot to upload it to Wikidata.
"""
import artdatabot
import pywikibot
import requests
import re
import html
import json


def get_lookup_table(pid):
    """
    Make a lookup table for the property
    :param pid:
    :return:
    """
    result = {}
    query = u"""SELECT ?item ?id WHERE {
  ?item wdt:%s ?id .
  }""" % (pid, )
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        identifier = resultitem.get('id')
        result[identifier] = qid
    return result


def get_search_page_generator(start_year, start_search_page, venue=None, collection=None):
    """
    Generaor that yields search pages
    :param start_year: The year to start in with the period buckets that stay under 10.000 paintings
    :param start_search_page: The page to start at for the first search
    :param venue: Only get paintings from a venue
    :param collection: Only get paintings from a collection
    :return: Generator yielding search pages
    """
    periods = [(1, 1501),
               (1500, 1601),
               (1600, 1651),
               (1650, 1701),
               (1700, 1751),
               (1750, 1776),
               (1775, 1801),
               (1800, 1826),
               (1825, 1841),
               (1840, 1851),
               (1850, 1861),
               (1860, 1871),
               (1870, 1881),
               (1880, 1886),
               (1885, 1891),
               (1890, 1896),
               (1895, 1901),
               (1900, 1906),
               (1905, 1911),
               (1910, 1916),
               (1915, 1921),
               (1920, 1926),
               (1925, 1931),
               (1930, 1936),
               (1935, 1941),
               (1940, 1946),
               (1945, 1951),
               (1950, 1956),
               (1955, 1961),
               (1960, 1966),
               (1965, 1971),
               (1970, 1976),
               (1975, 1981),
               (1980, 1986),
               (1985, 1991),
               (1990, 1996),
               (1995, 2001),
               (2000, 2006),
               (2005, 2011),
               (2010, 2016),
               (2015, 2021),
               (2020, 3000),
               ]
    if start_year:
        base_search_url = 'https://artuk.org/discover/artworks/search/date-from:%s--date-to:%s--work_type:painting/page/%s?_ajax=1'
        for (start_period, end_period) in periods:
            if start_year > end_period:
                continue
            load_more = True
            i = start_search_page
            while load_more:
                search_url = base_search_url % (start_period, end_period, i, )
                pywikibot.output('WORKING ON PERIOD %s TO %s SEARCH PAGE %s with url %s' % (start_period, end_period, i, search_url))
                search_page = requests.get(search_url, headers={'X-Requested-With': 'XMLHttpRequest', })
                search_json = search_page.json()
                load_more = search_json.get('load_more')
                i += 1
                yield search_page
            start_search_page = 1  # Reset the start search page for the next period
    elif venue:
        base_search_url = 'https://artuk.org/discover/artworks/search/work_type:painting--venue:%s/page/%s?_ajax=1'
        load_more = True
        i = start_search_page
        while load_more:
            search_url = base_search_url % (venue, i, )
            pywikibot.output('WORKING ON VENUE %s SEARCH PAGE %s with url %s' % (venue, i, search_url))
            search_page = requests.get(search_url, headers={'X-Requested-With': 'XMLHttpRequest', })
            search_json = search_page.json()
            load_more = search_json.get('load_more')
            i += 1
            yield search_page
    elif collection:
        base_search_url = 'https://artuk.org/discover/artworks/search/work_type:painting--collection:%s/page/%s?_ajax=1'
        load_more = True
        i = start_search_page
        while load_more:
            search_url = base_search_url % (collection, i, )
            pywikibot.output('WORKING ON COLLECTION %s SEARCH PAGE %s with url %s' % (collection, i, search_url))
            search_page = requests.get(search_url, headers={'X-Requested-With': 'XMLHttpRequest', })
            search_json = search_page.json()
            load_more = search_json.get('load_more')
            i += 1
            yield search_page

def get_all_generator(filter_type, all_list):
    for target in all_list:
        for id in get_art_uk_ids(filter_type, target):
            yield id


def get_art_uk_ids(filter_type, target):
    base_search_url = 'https://artuk.org/discover/artworks/search/work_type:painting--%s:%s/page/%s?_ajax=1'
    postdata = { 'work_type': 'Painting', filter_type: target}
    load_more = True
    i = 1
    requests.post('https://artuk.org/discover/artworks/search/work_type:painting', data=postdata)
    while load_more:
        search_url = base_search_url % (filter_type, target, i, )
        pywikibot.output('WORKING ON %s TARGET %s SEARCH PAGE %s with url %s' % (filter_type, target, i, search_url))
        search_page = requests.get(search_url, headers={'X-Requested-With': 'XMLHttpRequest', })
        search_json = search_page.json()
        load_more = search_json.get('load_more')
        i += 1
        search_json = search_page.json()
        search_text = search_json.get('html')

        ids = set()
        id_regex = '\"https\:\/\/artuk\.org\/discover\/artworks\/([^\/]+)/([^\"]+)?search([^\"]+)\"'
        for match in re.finditer(id_regex, search_text):
            art_uk_id = match.group(1)
            ids.add(art_uk_id)
        for art_uk_id in ids:
            yield art_uk_id

def get_incomplete_item_generator(pid):
    """
    Do a query on Wikidata to art uk id's for items missing a certain property
    :param pid:
    :return:
    """
    query = """SELECT ?item ?id WHERE {
  ?item wdt:P1679 ?id ;
        wdt:P31 wd:Q3305213 .
  MINUS { ?item wdt:%s [] }
  }""" % (pid, )
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        yield resultitem.get('id')


def get_art_uk_generator(generator_type, target=None, only_new=None):
    """
    The generator to get the art uk works
    :return:
    """
    anonymous_artists = ['british-school-5156',
                         'british-english-school-5157',
                         'british-scottish-school',
                         'chinese-school',
                         'dutch-school-5174',
                         'flemish-school-5175',
                         'french-school-5161',
                         'german-school-5186',
                         'italian-school-5182',
                         'italian-sienese-school',
                         'italian-tuscan-school',
                         'netherlandish-school-1245',
                         'northern-italian-school',
                         'roman',
                         'russian-school',
                         'southern-german-school',
                         'spanish-school-5163',
                         'students-from-the-bombay-school-of-art',
                         ]
    art_uk_artists = get_lookup_table('P1367')
    art_uk_collections = get_lookup_table('P1751')
    art_uk_venues = get_lookup_table('P1602')

    if only_new:
        art_uk_paintings = get_lookup_table('P1679')
    else:
        art_uk_paintings = {}
    generator = None

    if generator_type == 'all_artists':
        generator = get_all_generator('actor', art_uk_artists)
    elif generator_type == 'all_collections':
        generator = get_all_generator('collection', art_uk_collections)
    elif generator_type == 'all_venues':
        generator = get_all_generator('venue', art_uk_venues)
    elif generator_type == 'actor' and target:
        generator = get_art_uk_ids('artist', target)
    elif generator_type == 'collection' and target:
        generator = get_art_uk_ids('collection', target)
    elif generator_type == 'venue' and target:
        generator = get_art_uk_ids('venue', target)
    elif generator_type == 'incomplete' and target:
        generator = get_incomplete_item_generator(target)
    else:
        return

    """

    #search_page_generator = get_search_page_generator(start_year, start_search_page, venue, collection)

    for search_page in search_page_generator:
        search_json = search_page.json()
        search_text = search_json.get('html')

        ids = set()
        id_regex = '\"https\:\/\/artuk\.org\/discover\/artworks\/([^\/]+)/([^\"]+)?search([^\"]+)\"'
        for match in re.finditer(id_regex, search_text):
            art_uk_id = match.group(1)
            ids.add(art_uk_id)
    
    """

    for art_uk_id in generator:

        if only_new and art_uk_id in art_uk_paintings:
            continue
        metadata = {}

        url = 'https://artuk.org/discover/artworks/%s' % (art_uk_id,)
        metadata['artworkidpid'] = 'P1679'
        metadata['artworkid'] = art_uk_id

        item_page = requests.get(url)
        pywikibot.output(url)
        metadata['url'] = url

        # Sends ISO-8859-1, but is actually utf-8
        item_page.encoding = item_page.apparent_encoding

        work_typeregex = '<h5>Work type</h5>[\s\t\r\n]+<p>\s*([^<]+)\s*</p>'
        work_type_match = re.search(work_typeregex, item_page.text)

        if not work_type_match:
            # Just skip it
            continue
        work_type = html.unescape(work_type_match.group(1)).strip().lower()

        work_types = {'painting': 'Q3305213',
                      'miniature': 'Q3305213',  # Also just painting
                      }
        if work_type in work_types:
            metadata['instanceofqid'] = work_types.get(work_type)
        else:
            continue

        title_regex = '<h1 class="artwork-title">([^<]+)</h1>'
        title_match = re.search(title_regex, item_page.text)

        if title_match:
            title = html.unescape(title_match.group(1)).strip()

            # Chop chop, might have long titles
            if len(title) > 220:
                title = title[0:200]
            title = title.replace('\t', '').replace('\n', '').strip()
            metadata['title'] = {'en': title, }

        creator_regex = '<h2 class="artist">[\s\t\r\n]+<a href="https://artuk.org/discover/artists/([^"]+)">[\s\t\r\n]+([^<]+)[\s\t\r\n]+</a>'
        creator_match = re.search(creator_regex, item_page.text)

        name = None
        artist_id = None
        if creator_match:
            artist_id = html.unescape(creator_match.group(1))
            # TODO: How to deal with different types of attributions? Just sort out later?
            # maybe add object named as as qualifier/reference?
            if artist_id in anonymous_artists:
                metadata['creatorqid'] = 'Q4233718'
            elif artist_id in art_uk_artists:
                metadata['creatorqid'] = art_uk_artists.get(artist_id)
            # Make a static list of anonymous like english school
            name = html.unescape(creator_match.group(2)).replace('\t', '').replace('\n', '').strip()
            metadata['creatorname'] = name

        venue_regex = '<h3 class="venue">[\s\t\r\n]+<a href="https://artuk.org/visit/(collection|venues)/([^"]+\d+)">[\s\t\r\n]+([^<]+)[\s\t\r\n]+</a>'
        venue_match = re.search(venue_regex, item_page.text)

        venue = None
        if venue_match:
            venue_type = html.unescape(venue_match.group(1))
            venue_id = html.unescape(venue_match.group(2))

            if venue_type == 'collection':
                if venue_id in art_uk_collections:
                    metadata['collectionqid'] = art_uk_collections.get(venue_id)
            elif venue_type == 'venues':
                if venue_id in art_uk_venues:
                    # FIXME: Adding too many collections now
                    metadata['collectionqid'] = art_uk_venues.get(venue_id)
                    metadata['locationqid'] = art_uk_venues.get(venue_id)

            venue = html.unescape(venue_match.group(3)).replace('\t', '').replace('\n', '').strip()
            metadata['collectionshort'] = venue

        if name and venue:
            metadata['description'] = {'en': 'painting by %s, %s' % (name, venue,), }

        if metadata.get('collectionqid'):
            inv_regex = '<h5>Accession number</h5>[\s\t\r\n]+<p>([^\<]+)</p>'
            inv_match = re.search(inv_regex, item_page.text)
            if inv_match:
                metadata['idpid'] = 'P217'
                metadata['id'] = html.unescape(inv_match.group(1)).strip()
            acquisition_date_regex = '<h5>Acquisition method</h5>[\s\t\r\n]+<p>[^\<]+, (\d\d\d\d)</p>'
            acquisition_date_match = re.search(acquisition_date_regex, item_page.text)
            if acquisition_date_match:
                metadata['acquisitiondate'] = acquisition_date_match.group(1)

        date_regex = '<h5>Date</h5>[\s\t\r\n]+<p>\s*([^<]+)\s*</p>'
        date_match = re.search(date_regex, item_page.text)
        if date_match:
            date = html.unescape(date_match.group(1)).strip()

            year_regex = '^(\d\d\d\d)$'
            date_circa_regex = '^(about|[cC]\.)\s*(\d\d\d\d)$'
            period_regex = '^(\d\d\d\d)\s*[–\--\/]\s*(\d\d\d\d)$'
            circa_period_regex = '^(about|[cC]\.)\s*(\d\d\d\d)\s*[–\--\/]\s*(\d\d\d\d)$'
            short_period_regex = '^(\d\d)(\d\d)[–\--\/](\d\d)$'
            circa_short_period_regex = '^(about|[cC]\.)\s*(\d\d)(\d\d)[–\-–/](\d\d)$'
            century_regex = '^(\d\d)th C$'
            in_century_regex = '^(early |mid-|late )(\d\d)th C$'
            decade_regex = '^(\d\d\d\d)s$'
            in_decade_regex = '^([cC]\.|early |mid-|late )(\d\d\d\d)s$'

            year_match = re.match(year_regex, date)
            date_circa_match = re.match(date_circa_regex, date)
            period_match = re.match(period_regex, date)
            circa_period_match = re.match(circa_period_regex, date)
            short_period_match = re.match(short_period_regex, date)
            circa_short_period_match = re.match(circa_short_period_regex, date)
            century_match = re.match(century_regex, date)
            in_century_match = re.match(in_century_regex, date)
            decade_match = re.match(decade_regex, date)
            in_decade_match = re.match(in_decade_regex, date)

            if year_match:
                # Don't worry about cleaning up here.
                metadata['inception'] = int(year_match.group(1))
            elif date_circa_match:
                metadata['inception'] = int(date_circa_match.group(2))
                metadata['inceptioncirca'] = True
            elif period_match:
                metadata['inceptionstart'] = int(period_match.group(1),)
                metadata['inceptionend'] = int(period_match.group(2),)
            elif circa_period_match:
                metadata['inceptionstart'] = int(circa_period_match.group(2),)
                metadata['inceptionend'] = int(circa_period_match.group(3),)
                metadata['inceptioncirca'] = True
            elif short_period_match:
                metadata['inceptionstart'] = int('%s%s' % (short_period_match.group(1), short_period_match.group(2), ))
                metadata['inceptionend'] = int('%s%s' % (short_period_match.group(1), short_period_match.group(3), ))
            elif circa_short_period_match:
                metadata['inceptionstart'] = int('%s%s' % (circa_short_period_match.group(2), circa_short_period_match.group(3), ))
                metadata['inceptionend'] = int('%s%s' % (circa_short_period_match.group(2), circa_short_period_match.group(4), ))
                metadata['inceptioncirca'] = True
            elif century_match:
                metadata['inception'] = int('%s00' % (century_match.group(1),)) - 50  # Put it in the middle
                metadata['inceptionprecision'] = 'century'
                print(date)
                print(date)
                print(date)
                print(metadata['inception'])
                print(metadata['inception'])
                print(metadata['inception'])
            elif decade_match:
                metadata['inception'] = int(decade_match.group(1),) + 5  # Put it in the middle
                metadata['inceptionprecision'] = 'decade'
                print(date)
                print(date)
                print(date)
                print(metadata['inception'])
                print(metadata['inception'])
                print(metadata['inception'])
            else:
                print('Could not parse date: "%s"' % (date,))
                print('Could not parse date: "%s"' % (date,))
                print('Could not parse date: "%s"' % (date,))
                print('Could not parse date: "%s"' % (date,))

        medium_regex = '<h5>Medium</h5>[\s\t\r\n]+<p>([^\<]+)</p>'
        medium_match = re.search(medium_regex, item_page.text)
        if medium_match:
            metadata['medium'] = html.unescape(medium_match.group(1)).strip().lower()

        dimensions_regex = '<h5>Measurements</h5>[\s\t\r\n]+<p>H\s*(?P<height>\d+(\.\d+)?)\s*x\s*W\s*(?P<width>\d+(\.\d+)?)\s*cm</p>'
        dimensions_match = re.search(dimensions_regex, item_page.text)
        if dimensions_match:
            metadata['heightcm'] = dimensions_match.group('height')
            metadata['widthcm'] = dimensions_match.group('width')

        yield metadata


def main(*args):
    dryrun = False
    create = False
    start_year = None
    start_search_page = 1
    art_uk_venue = None
    art_uk_collection = None
    generator_type = None
    generator_target = None
    only_new = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True
        elif arg.startswith('-onlynew'):
            only_new = True
        elif arg.startswith('-generatortype:'):
            if len(arg) == len('-generatortype:'):
                generator_type = pywikibot.input(
                    'Please enter the generator type want to work on:')
            else:
                generator_type = arg[len('-generatortype:'):]
        elif arg.startswith('-generatortarget:'):
            if len(arg) == len('-generatortarget:'):
                generator_target = pywikibot.input(
                    'Please enter the generator target year want to work on:')
            else:
                generator_target = arg[len('-generatortarget:'):]
        elif arg.startswith('-startyear:'):
            if len(arg) == len('-startyear:'):
                start_year = int(pywikibot.input(
                    'Please enter the start year want to work on:'))
            else:
                start_year = int(arg[len('-startyear:'):])
        elif arg.startswith('-startsearchpage:'):
            if len(arg) == len('-startsearchpage:'):
                start_search_page = int(pywikibot.input(
                    'Please enter the start search page you want to work on:'))
            else:
                start_search_page = int(arg[len('-startsearchpage:'):])
        elif arg.startswith('-art_uk_venue:'):
            if len(arg) == len('-art_uk_venue:'):
                art_uk_venue = pywikibot.input(
                    'Please enter the art uk venue you want to work on:')
            else:
                art_uk_venue = arg[len('-art_uk_venue:'):]

    painting_generator = get_art_uk_generator(generator_type, target=generator_target, only_new=only_new)

    if dryrun:
        for painting in painting_generator:
            print(painting)
    else:
        artDataBot = artdatabot.ArtDataIdentifierBot(painting_generator, id_property='P1679', create=create)
        artDataBot.run()


if __name__ == "__main__":
    main()
