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

            if work_type == 'portret[schildering]' or work_type == 'portrait[peinture]':
                metadata['genreqid'] = 'Q134307'  # portrait (Q134307)

            # Inventory number
            inv_regex = '<strong>Inventory number</strong>:\s*</div><div class=\'three-fifth last\'>([^<]+)</div>'
            inv_match = re.search(inv_regex, item_page.text)
            if inv_match:
                metadata['idpid'] = 'P217'
                metadata['id'] = html.unescape(inv_match.group(1)).strip()

            if collectionid:
                metadata['collectionqid'] = collectionid
                metadata['locationqid'] = collectionid

            # Institution place
            place_regex = '<strong>Institution place</strong>:\s*</div><div class=\'three-fifth last\'><a class=\'lite1\' href=\'results\.php\?[^\']+\'>([^<]+)</a>'
            place_match = re.search(place_regex, item_page.text)
            if place_match:
                metadata['location_name'] = html.unescape(place_match.group(1)).strip()

            # Institution
            # https://balat.kikirpa.be/object/153627
            institution_regex = '<strong>Institution</strong>:\s*</div><div class=\'three-fifth last\'><a class=\'lite1\' href=\'results\.php\?[^\']+\'>([^<]+)</a>'
            instiution_repository_regex = '<strong>Institution \(repository\)</strong>:\s*</div><div class=\'three-fifth last\'><a class=\'lite1\' href=\'results\.php\?[^\']+\'>([^<]+)</a>'
            instiution_owner_regex = '<strong>Institution \(owner\)</strong>:\s*</div><div class=\'three-fifth last\'>([^<]+)</div'
            institution_match = re.search(institution_regex, item_page.text)
            instiution_repository_match = re.search(instiution_repository_regex, item_page.text)
            instiution_owner_match = re.search(instiution_owner_regex, item_page.text)
            if institution_match:
                metadata['collection_name'] = html.unescape(institution_match.group(1)).strip()
            elif instiution_repository_match and instiution_owner_match:
                instiution_repository = html.unescape(instiution_repository_match.group(1)).strip()
                instiution_owner = html.unescape(instiution_owner_match.group(1)).strip()
                metadata['collection_name'] = '%s / %s' % (instiution_repository, instiution_owner)
            elif instiution_repository_match:
                metadata['collection_name'] = html.unescape(instiution_repository_match.group(1)).strip()

            # Creator
            # TODO: Handle attribution
            # TODO: Do something with multiple creators?
            creator_date_regex = '<strong>Creator</strong>:\s*</div><div class=\'three-fifth last\'><a class="lite1" href="results\.php\?[^"]+">([^<]+)</a>\s*\([^\)]+\)\s*<a href="people\.php\?[^"]+" title="People & institutions">\s*<i class="icon-user-1"></i></a><br/>Date:\s*([^<]+)</div>'
            #creator_date_regex = '<strong>Creator</strong>:\s*</div><div class=\'three-fifth last\'><a class="lite1" href="results\.php\?[^"]+">([^<]+)</a>\s*\(schilder\)\s*<a href="people\.php\?[^"]+" title="People & institutions">\s*<i class="icon-user-1"></i></a><br/>Date:\s*([^<]+)</div>'
            uncertain_creator_date_regex = '<strong>Creator</strong>:\s*</div><div class=\'three-fifth last\'><a class="lite1" href="results\.php\?[^"]+">([^<]+)</a>\s*\([^\)]+\)\s*\(([^\)]+)\)\s*<a href="people\.php\?[^"]+" title="People & institutions">\s*<i class="icon-user-1"></i></a><br/>Date:\s*([^<]+)</div>'
            #uncertain_creator_date_regex = '<strong>Creator</strong>:\s*</div><div class=\'three-fifth last\'><a class="lite1" href="results\.php\?[^"]+">([^<]+)</a>\s*\(schilder\)\s*\(([^\)]+)\)\s*<a href="people\.php\?[^"]+" title="People & institutions">\s*<i class="icon-user-1"></i></a><br/>Date:\s*([^<]+)</div>'
            creator_date_match = re.search(creator_date_regex, item_page.text)
            uncertain_creator_date_match = re.search(uncertain_creator_date_regex, item_page.text)
            date = None
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
            elif uncertain_creator_date_match:
                creatorname = html.unescape(uncertain_creator_date_match.group(1)).strip()
                creatorrole = html.unescape(uncertain_creator_date_match.group(2)).strip()
                date = html.unescape(uncertain_creator_date_match.group(3)).strip()

                metadata['creatorname_raw'] = '%s (%s)' % (creatorname, creatorrole)
                metadata['date_raw'] = date

                creator_regex = '^([^,]+), ([^,]+)$'
                creator_match = re.match(creator_regex, creatorname)
                if creator_match:
                    creatorname = '%s %s' % (creator_match.group(2), creator_match.group(1))
                metadata['creatorname'] = '%s (%s)' % (creatorname, creatorrole)
                if metadata.get('collection_name'):
                    metadata['description'] = {'nl': '%s van %s, %s' % ('schilderij',
                                                                        metadata.get('creatorname'),
                                                                        metadata.get('collection_name')),
                                               }

            if date:
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
            # Materal
            found_materials = set()
            material_regex = '<a class="lite1" href="results.php\?linkthrough\=MA&linkval=[^"]+">([^<]+)</a>'
            for material_match in re.finditer(material_regex, item_page.text):
                material = html.unescape(material_match.group(1)).strip()
                found_materials.add(material)

            if found_materials:
                if found_materials == {'olieverf', 'schilderdoek'}:
                    metadata['medium'] = 'oil on canvas'
                elif found_materials == {"peinture à l'huile", 'toile à peindre'}:
                    metadata['medium'] = 'oil on canvas'
                elif found_materials == {'verf', 'schilderdoek'}:
                    metadata['medium'] = 'paint on canvas'
                elif found_materials == {'olieverf', 'paneel[drager]'}:
                    metadata['medium'] = 'oil on panel'
                elif found_materials == {"peinture à l'huile", 'panneau[support]'}:
                    metadata['medium'] = 'oil on panel'
                elif found_materials == {"peinture à l'huile", 'bois'}:
                    metadata['medium'] = 'oil on panel'
                elif found_materials == {'paneel[drager]', 'eik', 'olieverf'}:
                    metadata['medium'] = 'oil on oak panel'
                else:
                    print('Could not parse materials: "%s"' % (found_materials,))

            # Movement
            movements = {'Vlaamse primitieven': 'Q443153',
                         'Primitifs flamands': 'Q443153',
                         }
            # See https://balat.kikirpa.be/object/20024607
            movement_regex = '<strong>Style/School/Ethnic group</strong>:\s*</div><div class=\'three-fifth last\'>([^<]+)</div'
            movement_match = re.search(movement_regex, item_page.text)
            if movement_match:
                movement = movement_match.group(1)
                if movement in movements:
                    metadata['movementqid'] = movements.get(movement)
                else:
                    print('Could not parse movement: "%s"' % (movement,))

            # Place of production: Zuidelijke Nederlanden
            creation_locations = {'Antwerpen': 'Q12892',
                                  'Brugge': 'Q12994',
                                  'Gent': 'Q1296',
                                  'Mechelen[deelgemeente]': 'Q162022',
                                  'Vlaanderen': 'Q234',
                                  'Zuidelijke Nederlanden': 'Q6581823',
                                  'Pays-Bas méridionaux': 'Q6581823',
                                  }
            creation_location_regex = '<strong>Place of production</strong>:\s*</div><div class=\'three-fifth last\'>([^<]+)</div'
            creation_location_match = re.search(creation_location_regex, item_page.text)
            if creation_location_match:
                creation_location = creation_location_match.group(1)
                if creation_location in creation_locations:
                    metadata['madeinqid'] = creation_locations.get(creation_location)
                else:
                    print('Could not parse Place of production: "%s"' % (creation_location,))

            # Technique. Probably not?

            # Dimensions
            #dimensions_regex = '<strong>Creator</strong>:\s*</div><div class=\'three-fifth last\'><a class="lite1" href="results\.php\?[^"]+">([^<]+)</a>\s*\([^\)]+\)\s*<a href="people\.php\?[^"]+" title="People & institutions">\s*<i class="icon-user-1"></i></a><br/>Date:\s*([^<]+)</div>'
            dimensions_regex = '<strong>Dimensions</strong>:\s*<br/>\s*</div><div class\=\'three-fifth last\'><i>hoogte</i>:\s*(?P<height>\d+(\.\d+)?)\s*cm<br/>\s*<i>breedte</i>:\s*(?P<width>\d+(\.\d+)?)\s*cm</div><div class="clear">'
            #dimensions_regex = '<h5>Measurements</h5>[\s\t\r\n]+<p>H\s*(?P<height>\d+(\.\d+)?)\s*x\s*W\s*(?P<width>\d+(\.\d+)?)\s*cm</p>'
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
                   'Q3044768': 'Musée+du+Louvre',  # Department of Paintings of the Louvre (Q3044768)
                   'Q2628596': 'Musée+des+Beaux-Arts[Lille%2C+FR]',  # Palais des Beaux-Arts de Lille (Q2628596)
                   'Q2536986': 'Koninklijke+Verzameling+België',  # Royal Collection of Belgium (Q2536986)
                   'Q595802': 'Museum+Plantin-Moretus%2FPrentenkabinet',  # Museum Plantin-Moretus (Q595802)
                   }

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-createjson'):
            createjson = True
        elif arg.startswith('-create'):
            create = True
        elif arg.startswith('-earlyned'):
            balat_search_string = 'typesearch=advanced&schoolstyle=Vlaamse+primitieven'
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
