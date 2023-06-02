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


def get_art_uk_generator(start_year, start_search_page):
    """
    The generator to get the art uk works
    :return:
    """
    art_uk_artists = get_lookup_table('P1367')
    art_uk_collections = get_lookup_table('P1751')
    art_uk_venues = get_lookup_table('P1602')

    # Period buckets that stay under 10.000 paintings
    periods = [(1, 1501),
               (1500, 1601),
               (1600, 1651),
               (1650, 1701),
               (1700, 1751),
               (1750, 1801),
               (1800, 1826),
               (1825, 1851),
               (1850, 1876),
               (1875, 1891),
               (1890, 1901),
               (1900, 1911),
               (1910, 1921),
               (1920, 1931),
               (1930, 1941),
               (1940, 1951),
               (1950, 1961),
               (1960, 1971),
               (1970, 1981),
               (1980, 1991),
               (1990, 2001),
               (2000, 3000),
               ]
    for (start_period, end_period) in periods:
        if start_year > end_period:
            continue
        # base_search_url = 'https://artuk.org/discover/artworks/search/work_type:painting/page/%s/sort_by/date_earliest/order/asc?_ajax=1'
        load_more = True
        i = start_search_page
        base_search_url = 'https://artuk.org/discover/artworks/search/date-from:%s--date-to:%s--work_type:painting/page/%s?_ajax=1'
        while load_more:
            search_url = base_search_url % (start_period, end_period, i, )
            pywikibot.output('WORKING ON PERIOD %s TO %s SEARCH PAGE %s with url %s' % (start_period, end_period, i, search_url))
            search_page = requests.get(search_url, headers={'X-Requested-With': 'XMLHttpRequest',} )
            search_json = search_page.json()
            load_more = search_json.get('load_more')
            i += 1
            search_text = search_json.get('html')

            ids = set()
            id_regex = '\"https\:\/\/artuk\.org\/discover\/artworks\/([^\/]+)/([^\"]+)?search([^\"]+)\"'
            for match in re.finditer(id_regex, search_text):
                art_uk_id = match.group(1)
                ids.add(art_uk_id)

            for art_uk_id in ids:
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

                creator_regex = '<h2 class="artist">[\s\t\r\n]+<a href="https://artuk.org/discover/artists/([^"]+\d+)">[\s\t\r\n]+([^<]+)[\s\t\r\n]+</a>'
                creator_match = re.search(creator_regex, item_page.text)

                name = None
                artist_id = None
                if creator_match:
                    artist_id = html.unescape(creator_match.group(1))
                    # TODO: How to deal with different types of attributions? Just sort out later?
                    # maybe add object named as as qualifier/reference?
                    if artist_id in art_uk_artists:
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
                    else:
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
        start_search_page = 1  # Reset the start search page for the next period

def main(*args):
    dryrun = False
    create = False
    start_year = 1
    start_search_page = 1

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True
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

    painting_generator = get_art_uk_generator(start_year, start_search_page)

    if dryrun:
        for painting in painting_generator:
            print(painting)
    else:
        artDataBot = artdatabot.ArtDataIdentifierBot(painting_generator, id_property='P1679', create=create)
        artDataBot.run()


if __name__ == "__main__":
    main()
