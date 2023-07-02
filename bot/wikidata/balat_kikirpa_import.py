#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from BALaT (Belgian Art Links and Tools) from Kikirpa

looping over https://balat.kikirpa.be/results.php?linkthrough=OB&linkval=schilderij
Have to keep an session open for the search so we can iterate.

This bot uses artdatabot to upload it to Wikidata.
"""
import artdatabot
import pywikibot
import requests
import re
import html
import json


# TODO: Check if I still need this here
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


def get_balat_generator(balat_search_string, collectionid=None):
    """
    The generator to get the BALat works
    :return:
    """
    # FXIME: Am I going to use this or not?
    #balat_artists = get_lookup_table('P1901')

    session = requests.Session()
    start_search_url = 'https://balat.kikirpa.be/results.php?%s' % (balat_search_string, )
    session.get(start_search_url)
    session.get('https://balat.kikirpa.be/results.php?startfrom=1&refine-add=object_name&value=schilderij')

    total = 100000
    for i in range(1, total):
        #session.get(start_search_url)
        #session.get('https://balat.kikirpa.be/results.php?startfrom=1&refine-add=object_name&value=schilderij')
        search_url = 'https://balat.kikirpa.be/results.php?startfrom=%s' % (i,)
        print(search_url)
        search_page = session.get(search_url)

        photo_regex = '<h5><a href="photo\.php\?path=[^"]+&objnr=(\d+)&nr=\d+">'
        matches = list(re.finditer(photo_regex, search_page.text))
        if not matches:
            break
        for match in matches:
            balat_id = match.group(1)
            print(balat_id)
            metadata = {}

            url = 'https://balat.kikirpa.be/object/%s' % (balat_id,)
            item_page = requests.get(url)
            pywikibot.output(url)

            # Object number
            object_number_regex = '<strong>Object number</strong>:\s*</div><div class="three-fifth last">([^<]+)</div>'
            object_number_match = re.search(object_number_regex, item_page.text)
            if not object_number_match or object_number_match.group(1).strip() != balat_id:
                # Something weird going on
                continue
            metadata['artworkidpid'] = 'P3293'
            metadata['artworkid'] = balat_id

            # Permalink
            permalink_regex = '<strong>Permalink</strong>:\s*</div><div class="three-fifth last"><a href=\'([^\']+)\'>'
            permalink_match = re.search(permalink_regex, item_page.text)
            if not permalink_match or permalink_match.group(1) != url:
                # Something weird going on
                continue
            metadata['url'] = url

            # Title
            title_regex = '<meta property="og:title"\s*content="([^"]+)" />'
            title_match = re.search(title_regex, item_page.text)

            if title_match:
                title = html.unescape(title_match.group(1)).strip()

                # Chop chop, might have long titles
                if len(title) > 220:
                    title = title[0:200]
                title = title.replace('\t', '').replace('\n', '').strip()
                # We never know what language it is in
                metadata['orginal_title'] = title
                metadata['title'] = {'nl': title, }  # Only doing Dutch. Mix of French & Dutch

            # Type of object
            work_types = {'schilderij': 'Q3305213',
                          'tableau[peinture]': 'Q3305213',
                          'portret[schildering]': 'Q3305213',
                          }

            work_type_regex = '<strong>Type of object</strong>:\s*</div><div class=\'three-fifth last\'><a class="lite1" href="results.php\?[^"]+">([^<]+)</a>'
            work_type_match = re.search(work_type_regex, item_page.text)
            if not work_type_match:
                # Just skip it
                print('Work type not found')
                continue
            work_type = html.unescape(work_type_match.group(1)).strip().lower()
            if work_type in work_types:
                metadata['instanceofqid'] = work_types.get(work_type)
            else:
                print(work_type)
                #continue

            if work_type == 'portret[schildering]':
                metadata['genreqid'] = 'Q134307'  # portrait (Q134307)

            # Inventory number
            inv_regex = '<strong>Inventory number</strong>:\s*</div><div class=\'three-fifth last\'>([^<]+)</div>'
            inv_match = re.search(inv_regex, item_page.text)
            if inv_match:
                metadata['idpid'] = 'P217'
                metadata['id'] = html.unescape(inv_match.group(1)).strip()

            if collectionid:
                metadata['collectionqid'] = collectionid

            # Institution place
            place_regex = '<strong>Institution place</strong>:\s*</div><div class=\'three-fifth last\'><a class=\'lite1\' href=\'results\.php\?[^\']+\'>([^<]+)</a>'
            place_match = re.search(place_regex, item_page.text)
            if place_match:
                metadata['location_name'] = html.unescape(place_match.group(1)).strip()

            # Institution
            # TODO: Also handle case where we have repository and that other thing
            # https://balat.kikirpa.be/object/153627
            institution_regex = '<strong>Institution</strong>:\s*</div><div class=\'three-fifth last\'><a class=\'lite1\' href=\'results\.php\?[^\']+\'>([^<]+)</a>'
            institution_match = re.search(institution_regex, item_page.text)
            if institution_match:
                metadata['collection_name'] = html.unescape(institution_match.group(1)).strip()

            # Creator
            # TODO: Handle attribution
            # TODO: Do something with multiple creators?
            creator_date_regex = '<strong>Creator</strong>:\s*</div><div class=\'three-fifth last\'><a class="lite1" href="results\.php\?[^"]+">([^<]+)</a>\s*\([^\)]+\)\s*<a href="people\.php\?[^"]+" title="People & institutions">\s*<i class="icon-user-1"></i></a><br/>Date:\s*([^<]+)</div>'
            creator_date_match = re.search(creator_date_regex, item_page.text)
            if creator_date_match:
                creatorname = html.unescape(creator_date_match.group(1)).strip()
                metadata['creatorname_raw'] = creatorname
                date = html.unescape(creator_date_match.group(2)).strip()
                metadata['date_raw'] = date

                creator_regex = '^([^,]+), ([^,]+)$'
                creator_match = re.match(creator_regex, creatorname)
                if creator_match:
                    creatorname = '%s %s' % (creator_match.group(2), creator_match.group(1))
                metadata['creatorname'] = creatorname
                if creatorname == 'onbekend' and metadata.get('collection_name'):
                    metadata['description'] = {'nl': 'schilderij van anonieme schilder, %s' % (metadata.get('collection_name',)),
                                               'en': 'painting by anonymous painter, %s' % (metadata.get('collection_name',)),
                                               }
                    metadata['creatorqid'] = 'Q4233718'
                elif metadata.get('collection_name'):
                    metadata['description'] = {'nl': '%s van %s, %s' % ('schilderij',
                                                                        metadata.get('creatorname'),
                                                                        metadata.get('collection_name')),
                                               'en': '%s by %s, %s' % ('painting',
                                                                       metadata.get('creatorname'),
                                                                       metadata.get('collection_name'),),
                                               'fr': '%s de %s, %s' % ('peinture',
                                                                       metadata.get('creatorname'),
                                                                       metadata.get('collection_name'),),
                                               }

                # TODO: Implement date logic
                year_regex = '^(\d\d\d\d) - (\d\d\d\d)$'
                year_circa_regex = '^(\d\d\d\d) \(ca\) - (\d\d\d\d) \(ca\)$'

                year_match = re.match(year_regex, date)
                year_circa_match = re.match(year_circa_regex, date)

                if year_match:
                    if year_match.group(1) == year_match.group(2):
                        metadata['inception'] = int(year_match.group(1))
                    else:
                        metadata['inceptionstart'] = int(year_match.group(1))
                        metadata['inceptionend'] = int(year_match.group(2))
                elif year_circa_match:
                    if year_circa_match.group(1) == year_circa_match.group(2):
                        metadata['inception'] = int(year_circa_match.group(1))
                    else:
                        metadata['inceptionstart'] = int(year_circa_match.group(1))
                        metadata['inceptionend'] = int(year_circa_match.group(2))
                    metadata['inceptioncirca'] = True
                else:
                    print('Could not parse date: "%s"' % (date,))
                    print('Could not parse date: "%s"' % (date,))
                    print('Could not parse date: "%s"' % (date,))
                    print('Could not parse date: "%s"' % (date,))
            # Materal

            # Technique

            # Dimensions

            yield metadata
            continue

            # Sends ISO-8859-1, but is actually utf-8
            #item_page.encoding = item_page.apparent_encoding

            work_typeregex = '<h5>Work type</h5>[\s\t\r\n]+<p>\s*([^<]+)\s*</p>'
            work_type_match = re.search(work_typeregex, item_page.text)



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


def main(*args):
    dryrun = False
    createjson = False
    create = False
    collectionid = None
    balat_search_string = 'linkthrough=OB&linkval=schilderij'
    start_search_page = 1

    collections = {'Q1471477': 'Koninklijk+Museum+voor+Schone+Kunsten+-+KMSKA',  # Royal Museum of Fine Arts Antwerp (Q1471477)
                   'Q2365880': 'Museum+voor+Schone+Kunsten+Gent+-+MSK',  # Museum of Fine Arts Ghent (MSK) (Q2365880)
                   'Q2362660': 'M+-+Museum+Leuven',  # M Leuven (Q2362660)
                   'Q1928672': 'Stedelijk+Museum+voor+Schone+Kunsten[Oostende]',  # Mu.ZEE - Kunstmuseum aan Zee (Q1928672)
                   'Q1948674': 'Groeningemuseum',  # Groeningemuseum (Q1948674)
                   'Q377500': 'Musées+Royaux+des+Beaux-Arts+de+Belgique',  # Royal Museums of Fine Arts of Belgium (Q377500)
                   'Q775644': 'Rubenshuis',  # Rubenshuis (Q775644)
                   'Q1699233': 'Museum+Mayer+van+den+Bergh',  # Museum Mayer van den Bergh (Q1699233)
                   'Q80784': 'Musée+des+Beaux-Arts+de+Liège',  # Musée des beaux-arts de Liège (Q80784)
                   'Q1778179': 'Musée+des+Beaux-Arts[Tournai]',  # Musée des Beaux-Arts Tournai (Q1778179)
                   'Q1378149': 'Kathedraal+Sint-Salvator',  # Sint-Salvatorskathedraal (Q1378149)
                   'Q1540707': 'SMAK+-+Stedelijk+Museum+voor+Actuele+Kunst',  # Stedelijk Museum voor Actuele Kunst (Q1540707)
                   'Q2893370': 'Musée+des+Beaux-Arts+de+Mons',  # Beaux-Arts Mons (Q2893370)
                   'Q5901': 'Kathedraal+Onze-Lieve-Vrouw+ten+Hemel+opgenomen',  # Onze-Lieve-Vrouwekathedraal (Q5901)
                   'Q2272511': 'Kerk+Sint-Paulus[Antwerpen]',  # St. Paul's Church (Q2272511)
                   'Q938154': 'Sint-Baafskathedraal[Gent]',  # Saint Bavo Cathedral (Q938154)
                   'Q2662909': 'Rockoxhuis',  # Museum Nicolaas Rockox - Het Rockoxhuis (Q2662909)
                   'Q49425918': 'Groot+Seminarie[Mechelen]',  # Grand Seminary Mechelen (Q49425918)
                   }

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-createjson'):
            createjson = True
        elif arg.startswith('-create'):
            create = True
        elif arg.startswith('-startsearchpage:'):
            if len(arg) == len('-startsearchpage:'):
                start_search_page = int(pywikibot.input(
                    'Please enter the start search page you want to work on:'))
            else:
                start_search_page = int(arg[len('-startsearchpage:'):])
        elif arg.startswith('-collectionid:'):
            if len(arg) == len('-collectionid:'):
                collectionid = pywikibot.input(
                    u'Please enter the collectionid you want to work on:')
            else:
                collectionid = arg[len('-collectionid:'):]
            if collectionid not in collections:
                pywikibot.output('Unknown collection')
                return
            balat_search_string = 'linkthrough=BA&linkval=%s' % (collections.get(collectionid,) )

    painting_generator = get_balat_generator(balat_search_string, collectionid=collectionid)

    if dryrun:
        for painting in painting_generator:
            print(painting)
    elif createjson:
        result = []
        for painting in painting_generator:
            result.append(painting)
            print(painting)

        with open('/tmp/balat_objects.json', 'w') as jsonfile:
            jsonfile.write(json.dumps(result, indent=4))


    #elif collectionid:
    #    artDataBot = artdatabot.ArtDataBot(painting_generator, create=create)
    #    artDataBot.run()
    else:
        artDataBot = artdatabot.ArtDataIdentifierBot(painting_generator, id_property='P3293', create=create)
        artDataBot.run()


if __name__ == "__main__":
    main()
