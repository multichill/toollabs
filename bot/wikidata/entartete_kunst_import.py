#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape "entartete" ("degenerate") paintings (the stuff I love)

Takes it from the http://emuseum.campus.fu-berlin.de/eMuseumPlus?service=ExternalInterface&moduleFunction=search
It's horrible old emuseum so I just loop over a bunch of integers in hope to find a painting
"""
import artdatabot
import pywikibot
import urllib3
import requests
import re
import html


def get_entarte_generator():
    """
    Search for paintings and loop over it. Did I mention that old emuseum sucks?
    """
    #urllib3.disable_warnings()
    #htmlparser = HTMLParser()

    # Inventory can be found at https://www.vam.ac.uk/articles/explore-entartete-kunst-the-nazis-inventory-of-degenerate-art
    # This also lists the number of works per collection
    # https://www.geschkult.fu-berlin.de/en/e/db_entart_kunst/datenbank/aktueller_stand/index.html


    """
    Berlin, National Galerie / Crown Prince’s Palace (October 2010)
    Dresden, City Museum (January 2011)
    Düsseldorf, Kunstsammlungen der Stadt (sculptures, June 2013)
    Erfurt, Angermuseum (November 2010) <--- also ge
    Essen, Museum Folkwang (excluding prints, July 2010)
    Frankfurt/Main, Städel Art Institute and Municipal Gallery (paintings and sculptures, December 2010)
    Freiburg im Breisgau, Municipial Art Collections (March 2016)
    Halle/Salle, Museum for Arts and Crafts (April 2010)
    Hamm, Gustav Lübcke Museum (January 2012)
    Jena, Kunstverein (January 2011)
    Munich, Bavarian State Painting Collections (November 2010)
    Oldenburg, Landesmuseum (November 2010)
    Rostock, Municipal Museum (April 2010)
    Schwerin, Staatliches Museum Schwerin (April 2010)
    Stuttgart, State Gallery (March 2016)
    Ulm, Municipial Museum (March 2016)
    """
    collections = { 'Berlin, Nationalgalerie (Kronprinzen-Palais)': 'Q162111',
                    'Dresden, Stadtmuseum': 'Q2327655',
                    'Düsseldorf, Kunstsammlungen der Stadt': 'Q131748853',
                    'Erfurt, Angermuseum': 'Q538183',
                    # Erfurt, Museen der Stadt (Museum für Kunst und Heimatgeschichte) ?????
                    'Essen, Museum Folkwang': 'Q125634',
                    'Frankfurt/M, Städelsches Kunstinstitut und Städtische Galerie': 'Q163804',
                    # Freiburg im Breisgau, Städtische Sammlungen
                    # Halle/Salle, Museum for Arts and Crafts (April 2010)
                    'Hamm, Städtisches Gustav-Lübke-Museum': 'Q59926017',
                    'Hamburg, Kunsthalle' : 'Q169542',
                    'Jena, Kunstverein' : 'Q1686807',
                    'Karlsruhe, Staatliche Kunsthalle' : 'Q658725',
                    'Köln, Wallraf-Richartz-Museum' : 'Q700959',
                    'München, Bayerische Staatsgemäldesammlungen' : 'Q812285',
                    'München, Bayerische Staatsgemäldesammlungen – Pinakothek der Moderne' : 'Q812285',
                    'München, Bayerische Staatsgemälde-Sammlung' : 'Q812285',
                    'Oldenburg, Landesmuseum': 'Q1988652',
                    'Schwerin, Staatliches Museum': 'Q2324618',
                    'Stuttgart, Württembergische Staatsgalerie': 'Q14917275',
                    'Ulm, Stadtmuseum': 'Q2475379',
                    }

    session = requests.Session()

    # 109589 is the first one giving content
    # 130586 and above nothing (might be lower)

    for i in range(109589, 130586):
        url = 'http://emuseum.campus.fu-berlin.de/eMuseumPlus?service=ExternalInterface&module=collection&objectId=%s&viewType=detailView' % (i,)

        print (url)

        item_page = session.get(url)

        metadata = {}
        metadata['url'] = url

        instance_regex = '\<span class\=\"tspPrefix\"\>Category\/Object Type\:\<\/span\>\<span class\=\"tspValue\"\>Gem&#228\;lde\<\/span\>'
        instance_match = re.search(instance_regex, item_page.text)

        if not instance_match:
            # Not for us
            continue

        # It's a painting
        metadata['instanceofqid'] = 'Q3305213'
        metadata['collectionqid'] = 'Q111796449'
        metadata['collectionshort'] = 'entartete'
        metadata['locationqid'] = 'Q111796449'

        inv_regex = '\<li class\=\"ekInventarNr\"\>\<span class\=\"tspPrefix\"\>NS Inventar EK-Nr\.\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        inv_match = re.search(inv_regex, item_page.text)
        if not inv_match:
            continue

        # FIXME: Still need to check if it's not "nicht im NS Inventar"
        # FIXME: Also add the extended EK numbers here

        metadata['id'] = inv_match.group(1)
        metadata['idpid'] = 'P217'

        # Disable to trigger the url addition
        metadata['artworkid'] = inv_match.group(1)
        metadata['artworkidpid'] = 'P4627'

        title_regex = '\<li class\=\"titel\"\>\<h3\>\<span class\=\"tspPrefix\"\>Title\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        title_match = re.search(title_regex, item_page.text)
        # Burn if no title found
        title = html.unescape(title_match.group(1)).strip()

        metadata['title'] = { 'de' : title,
                              }

        creator_regex = '\<li class\=\"kuenstler\"\>\<span class\=\"tspPrefix\"\>Artist\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        creator_match = re.search(creator_regex, item_page.text)

        name = html.unescape(creator_match.group(1)).strip()
        metadata['creatorname'] = name

        if metadata.get('instanceofqid') == 'Q3305213':
            metadata['description'] = { 'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'),),
                                        'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                        'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                        }

        # This is for the collection where it got stolen from
        origin_regex = '\<li class\=\"herkunftsort\"\>\<span class\=\"tspPrefix\"\>Museum of Origin\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        origin_inv_regex = '\<li class\=\"herkunftsinventar\"\><span class\=\"tspPrefix\"\>Inventory of Origin\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        origin_match = re.search(origin_regex, item_page.text)
        origin_inv_match = re.search(origin_inv_regex, item_page.text)
        if origin_match:
            origin = html.unescape(origin_match.group(1)).strip()

            if origin in collections:
                metadata['extracollectionqid'] = collections.get(origin)
                if origin_inv_match:
                    origin_inv = html.unescape(origin_inv_match.group(1)).strip()
                    if origin in collections:
                        metadata['extraid'] = origin_inv
            else:
                print ('Collection %s not found' % (origin,))

        # This is for the collection where it currently is
        location_regex = '\<li class\=\"standort\"\>\<span class\=\"tspPrefix\"\>Location\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        location_match = re.search(location_regex, item_page.text)
        if location_match:
            location = html.unescape(location_match.group(1)).strip()

            if location in collections:
                metadata['extracollectionqid2'] = collections.get(location)
            else:
                print ('Collection %s not found' % (location,))

        date_field_regex = '\<li class\=\"datierung\"\>\<span class\=\"tspPrefix\"\>Date\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        date_field_match = re.search(date_field_regex, item_page.text)

        if date_field_match:
            date_field = date_field_match.group(1)
            # Quite incomplete, but covers a lot
            dateregex = '^(\d\d\d\d)$'
            datecircaregex = '^um\s*(\d\d\d\d)\s*$'
            periodregex = '^(\d\d\d\d)[-\/](\d\d\d\d)$'
            circaperiodregex = '(\d\d\d\d)[-\/](\d\d\d\d)\s*\(um\)\s*$' # No hits I think

            datematch = re.match(dateregex, date_field)
            datecircamatch = re.match(datecircaregex, date_field)
            periodmatch = re.match(periodregex, date_field)
            circaperiodmatch = re.match(circaperiodregex, date_field)

            if datematch:
                # Don't worry about cleaning up here.
                metadata['inception'] = int(datematch.group(1))
            elif datecircamatch:
                metadata['inception'] = int(datecircamatch.group(1))
                metadata['inceptioncirca'] = True
            elif periodmatch:
                metadata['inceptionstart'] = int(periodmatch.group(1),)
                metadata['inceptionend'] = int(periodmatch.group(2),)
            elif circaperiodmatch:
                metadata['inceptionstart'] = int(circaperiodmatch.group(1),)
                metadata['inceptionend'] = int(circaperiodmatch.group(2),)
                metadata['inceptioncirca'] = True
            else:
                print (u'Could not parse date: "%s"' % (date_field,))

        medium_regex = '\<li class\=\"material\"\>\<span class\=\"tspPrefix\"\>Material\/Technique\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        medium_match = re.search(medium_regex, item_page.text)

        if medium_match:
            medium = html.unescape(medium_match.group(1)).strip()
            mediums = { 'Öl auf Leinwand' : 'oil on canvas',
                        'Öl auf Holz' : 'oil on panel',
                        'Öl auf Papier' : 'oil on paper',
                        'Öl auf Kupfer' : 'oil on copper',
                        'Öl auf Pappe' : 'oil on cardboard',
                        'Tempera auf Leinwand' : 'tempera on canvas',
                        'Tempera auf Holz' : 'tempera on panel',
                        'Acryl auf Leinwand' : 'acrylic paint on canvas',
                        }
            if medium in mediums:
                metadata['medium'] = mediums.get(medium)
            else:
                print('Unable to match medium %s' % (medium,))

        dimensions_regex = '\<li class\=\"masse\"\><span class\=\"tspPrefix\"\>Measure\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        dimensions_match = re.search(dimensions_regex, item_page.text)

        if dimensions_match:
            dimensions = html.unescape(dimensions_match.group(1)).strip()
            regex_2d = '^Bildmaß\s*(?P<height>\d+(,\d+)?)\s*(x|×)\s*(?P<width>\d+(,\d+)?)\s*cm\s*$'
            match_2d = re.match(regex_2d, dimensions)
            if match_2d:
                metadata['heightcm'] = match_2d.group('height')
                metadata['widthcm'] = match_2d.group('width')

        yield metadata


def main(*args):
    dict_gen = get_entarte_generator()
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
        art_data_bot = artdatabot.ArtDataBot(dict_gen, create=create)
        art_data_bot.run()

if __name__ == "__main__":
    main()
