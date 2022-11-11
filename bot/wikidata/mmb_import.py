#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from Museum Mayer van den Bergh to Wikidata.

The have Adlib/Axiel running at https://search.museummayervandenbergh.be/results
Not sure if they have the API enabled, going to scrape it.

This bot uses artdatabot to upload it to Wikidata.
"""
import artdatabot
import pywikibot
import requests
import re
import html


def get_mmb_generator():
    """
    Generator to return Museum Mayer van den Bergh paintings
    """
    start_url = 'https://search.museummayervandenbergh.be/search/detail?database=collect&fieldname=Field_Objectname&value=schilderij'
    #start_url = 'https://search.museummayervandenbergh.be/search/detail?database=collect&fieldname=Field_Objectname&value=triptiek'
    #start_url = 'https://search.museummayervandenbergh.be/search/detail?database=collect&fieldname=Field_Objectname&value=altaar'
    #start_url = 'https://search.museummayervandenbergh.be/search/detail?database=collect&fieldname=Field_Objectname&value=miniatuur%20[schildering]'
    #start_url = 'https://search.museummayervandenbergh.be/search/detail?database=collect&fieldname=Field_Technique&value=geschilderd'

    # TODO: Find missing ones
    session = requests.Session()
    session.get(start_url)

    base_search_url = 'https://search.museummayervandenbergh.be/resultsnavigate/%s'

    for i in range(1, 15):
        search_url = base_search_url % (i,)

        print(search_url)
        search_page = session.get(search_url)

        work_url_regex = '<a title="" href="/Details/collect/(\d+)">'
        matches = re.finditer(work_url_regex, search_page.text)

        for match in matches:
            metadata = {}
            url = 'https://search.museummayervandenbergh.be/Details/collect/%s' % (match.group(1),)

            item_page = session.get(url)
            pywikibot.output(url)
            metadata['url'] = url

            metadata['collectionqid'] = 'Q1699233'
            metadata['collectionshort'] = 'MMB'
            metadata['locationqid'] = 'Q1699233'

            object_name_regex = '<div class="label">Objectnaam</div><div class="value"><a href="[^\"]+">([^\<]+)</a>'
            object_name_match = re.search(object_name_regex, item_page.text)
            object_name = object_name_match.group(1)

            if object_name in ['schilderij', 'triptiek', 'miniatuur [schildering]']:
                print('%s is a valid object name' % (object_name,))
                pass
            else:
                techniek_regex = '<div class="label">Techniek</div><div class="value"><a href="[^\"]+">([^\<]+)</a>'
                techniek_match = re.search(techniek_regex, item_page.text)
                if not techniek_match:
                    continue
                elif techniek_match.group(1) != 'geschilderd':
                    continue
                elif object_name in ['altaar', 'retabel', 'tekening']:
                    print('%s is a valid painted object name' % (object_name,))
                    pass
                else:
                    continue

            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = 'P217'

            inv_regex = '<div class="label">Objectnummer</div><div class="value">([^\<]+)</div>'
            inv_match = re.search(inv_regex, item_page.text)

            metadata['id'] = html.unescape(inv_match.group(1).replace('&nbsp;', ' ')).strip()

            title_regex = '<div class="label">Titel</div><div class="value">([^\<]+)</div>'
            title_match = re.search(title_regex, item_page.text)
            if title_match:
                title = html.unescape(title_match.group(1)).strip()

                # Chop chop, might have long titles
                if len(title) > 220:
                    title = title[0:200]
                title = title.replace('\t', '').replace('\n', '')
                metadata['title'] = {'nl': title, }

            creator_regex = '<div class="label">Vervaardiger</div><div class="value"><a href="/search/detail[^\"]+">([^\<]+)</a>\s*\(schilder\)</div>'
            creator_match = re.search(creator_regex, item_page.text)

            uncertain_creator_regex = '<div class="label">Vervaardiger</div><div class="value">([^\<]+)<a href="/search/detail[^\"]+">([^\<]+)</a>\s*\(schilder\)</div>'
            uncertain_creator_match = re.search(uncertain_creator_regex, item_page.text)

            if creator_match:
                name = html.unescape(creator_match.group(1)).strip()
                if ',' in name:
                    (surname, sep, firstname) = name.partition(',')
                    name = '%s %s' % (firstname.strip(), surname.strip(),)

                metadata['creatorname'] = name

                if name in ['onbekend', 'anoniem']:
                    metadata['description'] = {'nl': 'schilderij van anonieme schilder',
                                               'en': 'painting by anonymous painter',
                                               }
                    metadata['creatorqid'] = 'Q4233718'
                else:
                    metadata['description'] = { 'nl': '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                                'en': '%s by %s' % ('painting', metadata.get('creatorname'),),
                                                'de': '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                                'fr': '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                                }
            elif uncertain_creator_match:
                name_prefix = html.unescape(uncertain_creator_match.group(1)).strip().strip(':')
                name = html.unescape(uncertain_creator_match.group(2)).strip()
                if ',' in name:
                    (surname, sep, firstname) = name.partition(',')
                    name = '%s %s' % (firstname.strip(), surname.strip(),)
                name = '%s %s' % (name_prefix, name)
                metadata['creatorname'] = name
                metadata['description'] = {'nl': 'schilderij %s' % (metadata.get('creatorname'),)}

            date_regex = '<div class="label">Datum</div><div class="value">([^\<]+)</div>'
            date_match = re.search(date_regex, item_page.text)
            if date_match:
                date = date_match.group(1).strip()
                year_regex = '^\s*(\d\d\d\d)\s*$'
                date_circa_regex = '^ca?\.\s*(\d\d\d\d)$'
                period_regex = '^(\d\d\d\d)\s*[--\/]\s*(\d\d\d\d)$'
                circa_period_regex = '^ca?\.\s*(\d\d\d\d)\s*[--\/]\s*c?i?r?ca\.?\s*(\d\d\d\d)$'
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

            material_regex = '<a href="/search/detail\?database=collect&amp;fieldname=Field_Material&amp;value=[^\"]+">([^\<]+)</a>'
            material_matches = re.finditer(material_regex, item_page.text)
            materials = set()
            for material_match in material_matches:
                materials.add(material_match.group(1))

            if materials == {'olieverf', 'doek'} or materials == {'olieverf', 'canvas'} \
                    or materials == {'textiel', 'verf', 'olieverf', 'doek'}:
                metadata['medium'] = 'oil on canvas'
            elif materials == {'olieverf', 'paneel'} or materials == {'hout', 'olieverf', 'paneel'}:
                metadata['medium'] = 'oil on panel'
            elif materials == {'olieverf', 'eikenhout', 'hout [plantaardig materiaal]'} or materials == {'eikenhout', 'olieverf'}:
                metadata['medium'] = 'oil on oak panel'
            elif materials == {'olieverf', 'koper'}:
                metadata['medium'] = 'oil on copper'
            elif materials == {'olieverf', 'papier'}:
                metadata['medium'] = 'oil on paper'
            elif materials == {'olieverf', 'karton'}:
                metadata['medium'] = 'oil on cardboard'
                #elif (material1 == 'doek' and material2 == 'tempera') or (material1 == 'tempera' and material2 == 'doek'):
                #    metadata['medium'] = 'tempera on canvas'
                #elif (material1 == 'paneel' and material2 == 'tempera') or (material1 == 'tempera' and material2 == 'paneel'):
                #    metadata['medium'] = 'tempera on panel'
                #elif (material1 == 'doek' and material2 == 'acrylverf') or (material1 == 'acrylverf' and material2 == 'doek'):
                #    metadata['medium'] = 'acrylic paint on canvas'
            elif materials == {'acryl', 'doek'}:
                metadata['medium'] = 'acrylic paint on canvas'
                #elif (material1 == 'paneel' and material2 == 'acrylverf') or (material1 == 'acrylverf' and material2 == 'paneel'):
                #    metadata['medium'] = 'acrylic paint on panel'
                #elif (material1 == 'papier' and material2 == 'aquarel') or (material1 == 'aquarel' and material2 == 'papier'):
                #    metadata['medium'] = 'watercolor on paper'
                #else:
                #    print('Unable to match %s & %s' % (material1, material2,))
            elif materials == {'olieverf', 'doek', 'paneel'} or materials == {'hout [plantaardig materiaal]', 'stof [textiel]', 'olieverf'}:
                metadata['medium'] = 'oil on canvas on panel'
            elif materials == {'olieverf', 'papier', 'paneel'}:
                metadata['medium'] = 'oil on paper on panel'
            elif materials == {'olieverf', 'karton', 'paneel'}:
                metadata['medium'] = 'oil on cardboard on panel'
            elif materials == {'olieverf', 'koper', 'paneel'}:
                metadata['medium'] = 'oil on copper on panel'
            elif materials == {'olieverf', 'doek', 'karton'}:
                metadata['medium'] = 'oil on canvas on cardboard'
            elif materials == {'olieverf', 'papier', 'karton'}:
                metadata['medium'] = 'oil on paper on cardboard'
            else:
                print('Unable to match %s' % (materials,))

            # All sorts of sizes. First two should be of the actual painting
            simple_2d_regex = '<div class="label">Formaat</div><div class="value"><ul>hoogte:\s*(?P<height>\d+(\.\d+)?)\scm<br>breedte:\s*(?P<width>\d+(\.\d+)?)\s*cm<br>'
            simple_2d_match = re.search(simple_2d_regex, item_page.text)
            if simple_2d_match:
                metadata['heightcm'] = simple_2d_match.group('height')
                metadata['widthcm'] = simple_2d_match.group(u'width')

            locations = {'Amsterdam [plaats]': 'Q727',
                         'Antwerpen [plaats]': 'Q12892',
                         'Brugge [plaats]': 'Q12994',
                         'Brussel [plaats]': 'Q239',
                         'Delft [plaats]': 'Q690',
                         'Den Haag [plaats]': 'Q36600',
                         'Duitsland [staat]': 'Q183',
                         'Frankenthal [plaats]': 'Q6905',
                         'Frankrijk [staat]': 'Q142',
                         'Haarlem [plaats]': 'Q9920',
                         'Hoorn [plaats]': 'Q9938',
                         'Italië [staat]': 'Q38',
                         'Lucca [plaats]': 'Q13373',
                         'Middelburg [plaats]': 'Q52101',
                         'Noordelijke Nederlanden [voormalige staat]': 'Q27996474',
                         'Vlaanderen [regio]': 'Q9337',
                         'Zuidelijke Nederlanden [voormalige staat]': 'Q6581823',
                         }

            location_regex = '<div class="label" valign="top">Vervaardiging plaats</div><div class="value">([^\<]+)</div>'
            location_match = re.search(location_regex, item_page.text)

            if location_match:
                location = location_match.group(1)
                if location in locations:
                    metadata['madeinqid'] = locations.get(location)
                elif ',' in location:
                    (location1, sep, location2) = location.partition(',')
                    if location1.strip() == location2.strip():
                        if location1.strip() in locations:
                            metadata['madeinqid'] = locations.get(location1.strip())
                        else:
                            print('Location %s (double) not found' % (location1,))
                    else:
                        print('Location %s (different) not found' % (location,))
                else:
                    print('Location %s not found' % (location,))

            # balat_regex = '<div class="label">Externe links</div><div class="value"><a href="http://balat\.kikirpa\.be/object/(\d+)" target="_blank">'
            # balat_match = re.search(balat_regex, item_page.text)
            # if balat_match:
            #    metadata['artworkidpid'] = 'P3293'  #  BALaT object ID (P3293)
            #    metadata['artworkid'] = '%s' % (balat_match.group(1),)


            dams_id_regex = '<input type="hidden" class="ais-image-filename-value" value="https://dams\.antwerpen\.be/asset/([^\/]+)/embed(/viewer)?">'
            dams_id_match = re.search(dams_id_regex, item_page.text)

            if dams_id_match:
                dams_id = dams_id_match.group(1)
                metadata['iiifmanifesturl'] = 'https://dams.antwerpen.be/iiif/%s/manifest' % (dams_id,)

                dams_page = requests.get(metadata['iiifmanifesturl'])
                dams_json = dams_page.json()
                rendering = dams_json.get('sequences')[0].get('rendering')[0]
                if rendering.get('format') == 'image/tiff':
                    metadata['imageurl'] = rendering.get('@id')
                    metadata['imageurlformat'] = 'Q215106'  # TIFF
                    metadata['imageoperatedby'] = 'Q107392906'
                    # Can use this to add suggestions everywhere
                    # metadata['imageurlforce'] = True
                elif rendering.get('format') == 'image/jpeg':
                    metadata['imageurl'] = rendering.get('@id')
                    metadata['imageurlformat'] = 'Q27996264'  # JPEG
                    metadata['imageoperatedby'] = 'Q107392906'
            yield metadata


def main(*args):
    dictGen = get_mmb_generator()
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True

    if dryrun:
        for painting in dictGen:
            print (painting)
    else:
        artDataBot = artdatabot.ArtDataBot(dictGen, create=create)
        artDataBot.run()


if __name__ == "__main__":
    main()
