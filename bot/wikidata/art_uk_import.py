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


def get_art_uk_generator():
    """
    The generator to get the art uk works
    :return:
    """
    art_uk_artists = get_lookup_table('P1367')
    art_uk_collections = get_lookup_table('P1751')
    art_uk_venues = get_lookup_table('P1602')

    i = 1
    load_more = True
    base_search_url = u'http://artuk.org/discover/artworks/search/work_type:painting/page/%s?_ajax=1'
    while load_more:
        search_url = base_search_url % (i, )
        pywikibot.output(search_url)
        search_page = requests.get(search_url, headers={'X-Requested-With': 'XMLHttpRequest',} )
        search_json = search_page.json()
        load_more = search_json.get('load_more')
        i += 1
        search_text = search_json.get('html')
        #print (search_text)

        id_regex = '\"https\:\/\/artuk\.org\/discover\/artworks\/([^\/]+)/search\/.+/page/\d+\"'
        for match in re.finditer(id_regex, search_text):
            metadata = {}

            art_uk_id = match.group(1)
            url = u'http://artuk.org/discover/artworks/%s' % (art_uk_id,)
            metadata['artworkidpid'] = 'P1679'
            metadata['artworkid'] = art_uk_id
            metadata['instanceofqid'] = 'Q3305213'

            item_page = requests.get(url)
            pywikibot.output(url)
            metadata['url'] = url

            # Sends ISO-8859-1, but is actually utf-8
            item_page.encoding = item_page.apparent_encoding

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
                print(artist_id)
                if artist_id in art_uk_artists:
                    metadata['creatorqid'] = art_uk_artists.get(artist_id)
                name = html.unescape(creator_match.group(2)).replace('\t', '').replace('\n', '').strip()
                metadata['creatorname'] = name

            venue_regex = '<h3 class="venue">[\s\t\r\n]+<a href="https://artuk.org/visit/(collection|venues)/([^"]+\d+)">[\s\t\r\n]+([^<]+)[\s\t\r\n]+</a>'
            venue_match = re.search(venue_regex, item_page.text)

            venue = None
            if venue_match:
                venue_type = html.unescape(venue_match.group(1))
                venue_id = html.unescape(venue_match.group(2))

                print(venue_type)
                print(venue_id)

                if venue_type == 'collection':
                    if venue_id in art_uk_collections:
                        metadata['collectionqid'] = art_uk_collections.get(venue_id)
                elif venue_type == 'venues':
                    if venue_id in art_uk_venues:
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

            # Only years at the moment. Is more info available?
            date_regex = '<h5>Date</h5>[\s\t\r\n]+<p>\s*(\d\d\d\d)\s*</p>'
            date_match = re.search(date_regex, item_page.text)
            if date_match:
                metadata['inception'] = int(date_match.group(1))

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
    painting_generator = get_art_uk_generator()
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True

    if dryrun:
        for painting in painting_generator:
            print (painting)
    else:
        artDataBot = artdatabot.ArtDataIdentifierBot(painting_generator, id_property='P1679', create=create)
        artDataBot.run()


if __name__ == "__main__":
    main()
