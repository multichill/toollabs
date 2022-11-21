#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from Bonnefanten Museum to Wikidata.

Looping over https://www.bonnefanten.nl/nl/@@search?object_name_index=schilderij

This bot uses artdatabot to upload it to Wikidata.
"""
import artdatabot
import pywikibot
import requests
import re
import html


def get_bonnefanten_generator():
    """
    Generator to return Bonnefanten paintings
    """
    base_search_url = 'https://www.bonnefanten.nl/nl/@@search?object_name_index=schilderij&sort_on=relevance&b_start:int=%s'

    session = requests.Session()

    for i in range(0, 1350, 10):
        search_url = base_search_url % (i,)

        print(search_url)
        search_page = session.get(search_url)

        work_url_regex = '<h4 class="item-title"><a href="(https://www\.bonnefanten\.nl/nl/collectie/\d+[^"]+)"'
        matches = re.finditer(work_url_regex, search_page.text)

        for match in matches:
            metadata = {}
            url = match.group(1)

            item_page = session.get(url)
            pywikibot.output(url)
            metadata['url'] = url

            metadata['collectionqid'] = 'Q892727'
            metadata['collectionshort'] = 'Bonnefanten'
            metadata['locationqid'] = 'Q892727'

            # We're searching for paintings
            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = 'P217'

            inv_regex = '<div class="[^"]+ object-label"><p>Objectnummer</p></div>[\s\r\t\n]*<div class="[^"]+ object-value"><p>([^<]+)</p></div>'
            inv_match = re.search(inv_regex, item_page.text)

            metadata['id'] = html.unescape(inv_match.group(1)).strip()

            title_regex = '<div class="[^"]+ object-label"><p>Titel</p></div>[\s\r\t\n]*<div class="[^"]+ object-value"><p>([^<]+)</p></div>'
            title_match = re.search(title_regex, item_page.text)
            if title_match:
                title = html.unescape(title_match.group(1)).strip()

                # Chop chop, might have long titles
                if len(title) > 220:
                    title = title[0:200]
                title = title.replace('\t', '').replace('\n', '')
                metadata['title'] = {'nl': title, }

            creator_regex = '<div class="[^"]+ object-label"><p>Vervaardiger</p></div>[\s\r\t\n]*<div class="[^"]+ object-value"><p><a href="https://www\.bonnefanten\.nl/nl/maker/[^"]+">([^<]+)</a> \(<a href="/nl/@@search\?creator_role=schilder">schilder</a>\)[^<]*</p></div>'
            creator_match = re.search(creator_regex, item_page.text)

            some_creator_regex = '<div class="[^"]+ object-label"><p>Vervaardiger</p></div>'
            some_creator_match = re.search(some_creator_regex, item_page.text)

            if creator_match:
                name = html.unescape(creator_match.group(1)).strip()
                #if ',' in name:
                #    (surname, sep, firstname) = name.partition(',')
                #    name = '%s %s' % (firstname.strip(), surname.strip(),)

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
            elif not some_creator_match:
                # No creator mentioned at all
                metadata['description'] = {'nl': 'schilderij van anonieme schilder',
                                           'en': 'painting by anonymous painter',
                                           }
                metadata['creatorqid'] = 'Q4233718'

            date_regex = '<div class="[^"]+ object-label"><p>Datering</p></div>[\s\r\t\n]*<div class="[^"]+ object-value"><p>([^<]+)</p></div>'
            date_match = re.search(date_regex, item_page.text)
            if date_match:
                date = date_match.group(1).strip()
                year_regex = '^\s*(\d\d\d\d)\s*$'
                date_circa_regex = '^circa\s*(\d\d\d\d)$'
                period_regex = '^(\d\d\d\d)\s*[--\/]\s*(\d\d\d\d)$'
                circa_period_regex = '^circa\s*(\d\d\d\d)\s*[--\/]\s*circa\s*(\d\d\d\d)$'
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

            material_regex = '<div class="[^"]+ object-label"><p>Materialen</p></div>[\s\r\t\n]*<div class="[^"]+ object-value"><p><a href="[^"]+">([^<]+)</a>, <a href="[^"]+">([^<]+)</a></p></div>'
            material_match = re.search(material_regex, item_page.text)
            if material_match:
                materials = {material_match.group(1), material_match.group(2)}

                if materials == {'olieverf', 'doek'} or materials == {'olieverf', 'canvas'} \
                        or materials == {'olieverf', 'linnen'}:
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
                elif materials == {'acryl', 'doek'} or materials == {'acrylverf', 'doek'} \
                        or materials == {'acrylverf', 'linnen'}:
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
                    print('Unable to match materials %s' % (materials,))

            acquisition_regex = '<div class="[^"]+ object-label"><p>Verwerving</p></div>[\s\r\t\n]*<div class="[^"]+ object-value"><p>(bruikleen|aankoop|schenking|legaat)\s*(\d\d\d\d)</p></div>'
            acquisition_match = re.search(acquisition_regex, item_page.text)

            if acquisition_match:
                metadata['acquisitiondate'] = int(acquisition_match.group(2))

            credit_regex = '<div class="[^"]+ object-label"><p>Credit line</p></div>[\s\r\t\n]*<div class="[^"]+ object-value"><p>([^<]+)</p></div>'
            credit_match = re.search(credit_regex, item_page.text)

            # Collectie Bonnefanten, langdurig bruikleen LGOG <- what's that?

            if credit_match:
                credit_line = credit_match.group(1)
                if credit_line.startswith('Collectie Bonnefanten, langdurig bruikleen Rijksmuseum.'):
                    metadata['extracollectionqid'] = 'Q190804'
                elif credit_line.startswith('Collectie Bonnefanten, in langdurig bruikleen van Koninklijk Kabinet van Schilderijen Mauritshuis, Den Haag.'):
                    metadata['extracollectionqid'] = 'Q221092'
                elif credit_line.startswith('Collectie Bonnefanten, langdurig bruikleen Rijksdienst voor het Cultureel Erfgoed.'):
                    metadata['extracollectionqid'] = 'Q18600731'

            # Sizes are all over the place so skipping for now
            #simple_2d_regex = '<div class="label">Formaat</div><div class="value"><ul>hoogte:\s*(?P<height>\d+(\.\d+)?)\scm<br>breedte:\s*(?P<width>\d+(\.\d+)?)\s*cm<br>'
            #simple_2d_match = re.search(simple_2d_regex, item_page.text)
            #if simple_2d_match:
            #    metadata['heightcm'] = simple_2d_match.group('height')
            #    metadata['widthcm'] = simple_2d_match.group(u'width')

            og_image_regex = '<meta content="(https://www\.bonnefanten\.nl/nl/collectie/[^"]+)" property="og:image" /><meta content="image/jpeg" property="og:image:type" />'
            og_image_match = re.search(og_image_regex, item_page.text)

            dc_rights_regex = '<meta name="DC.rights" content="([^"]+)" />'
            dc_rights_match = re.search(dc_rights_regex, item_page.text)

            pd_text = 'Gebruik van deze afbeelding is toegestaan voor iedereen. De afbeelding mag worden bewerkt en verder verspreid o.v.v. naam vervaardiger, titel, datering, ©naam fotograaf'
            cc_text = 'Gebruik van deze afbeelding is toegestaan voor iedereen. De afbeelding mag worden bewerkt en verder verspreid o.v.v. naam vervaardiger, titel, datering, CC BY SA 3.0, ©naam fotograaf. Meer info: www.creativecommons.nl.'

            if dc_rights_match and og_image_match:
                if dc_rights_match.group(1).startswith(pd_text):
                    image_url = '%s/@@images/image/large' % (og_image_match.group(1),)
                    metadata['imageurl'] = image_url
                    metadata['imageurlformat'] = 'Q27996264'  # JPEG
                    metadata['imageoperatedby'] = 'Q892727'
                    # metadata['imageurlforce'] = True
            yield metadata


def main(*args):
    dictGen = get_bonnefanten_generator()
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
