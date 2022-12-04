#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Stedelijk Museum Alkmaar to Wikidata.

The have Adlib/Axiel running at https://smalkmaar.adlibhosting.com/ais6/results
No API found, going to scrape it.

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re
import html

def get_stedelijk_museum_alkmaar_generator():
    """
    Generator to return  Stedelijk Museum Alkmaar paintings
    """
    start_url = 'https://smalkmaar.adlibhosting.com/ais6/search/detail?database=museum&fieldname=Field_Objectname&value=schilderij'

    session = requests.Session()
    session.get(start_url)

    base_search_url = 'https://smalkmaar.adlibhosting.com/ais6/resultsnavigate/%s'

    for i in range(1, 67):
        search_url = base_search_url % (i,)

        print(search_url)
        search_page = session.get(search_url)

        work_url_regex = '<a title="[^"]+" href="https://smalkmaar.adlibhosting.com/ais6/Details/museum/(\d+)">'
        matches = re.finditer(work_url_regex, search_page.text)

        for match in matches:
            metadata = {}
            url = 'https://smalkmaar.adlibhosting.com/ais6/Details/museum/%s' % (match.group(1),)

            item_page = session.get(url)
            pywikibot.output(url)
            metadata['url'] = url

            metadata['collectionqid'] = 'Q4623539'
            metadata['collectionshort'] = 'smalkmaar'
            metadata['locationqid'] = 'Q4623539'

            # Searching for paintings
            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = 'P217'

            inv_regex = '<span class="label">Object number</span><span class="value">([^<]+)</span>'
            inv_match = re.search(inv_regex, item_page.text)

            #if not inv_match:
            #    # Getting some errors like on https://collectie.groningermuseum.nl/Details/collect/95
            #    continue

            metadata['id'] = html.unescape(inv_match.group(1).replace('&nbsp;', ' ')).strip()

            title_regex = '<span class="label">Title</span><span class="value">([^<]+)</span>'
            title_match = re.search(title_regex, item_page.text)
            if title_match:
                title = html.unescape(title_match.group(1)).strip()

                # Chop chop, might have long titles
                if len(title) > 220:
                    title = title[0:200]
                title = title.replace('\t', '').replace('\n', '')
                metadata['title'] = {'nl': title, }

            creator_regex = '<span class="label">Creator</span><span class="value"><a href="https://smalkmaar\.adlibhosting\.com/ais6/search/detail\?database=museum&amp;fieldname=Field_Creator[^"]+">([^<]+)</a>\s*(\((schilder|kunstenaar)\)‎)?\s*</span></div>'
            creator_match = re.search(creator_regex, item_page.text)

            uncertain_creator_regex = '<div class="label">Vervaardiger</div>[\s\t\r\n]*<div class="value">([^\<]+)<a href="https://collectie\.museumgouda\.nl/search/detail[^\"]+">([^\<]+)</a>\s*\(kunstenaar\)[^<]*</div>'
            uncertain_creator_match = re.search(uncertain_creator_regex, item_page.text)

            plain_creator_regex = '<div class="label">Vervaardiger</div>[\s\t\r\n]*<div class="value">([^\<]+)<br></div>'
            plain_creator_match = re.search(plain_creator_regex, item_page.text)

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
            elif plain_creator_match:
                name = html.unescape(plain_creator_match.group(1)).strip('‎').strip()
                metadata['creatorname'] = name
                if name in ['onbekend', 'anoniem (schilder)']:
                    metadata['description'] = {'nl': 'schilderij van anonieme schilder',
                                               'en': 'painting by anonymous painter',
                                               }
                    metadata['creatorqid'] = 'Q4233718'
                else:
                    metadata['description'] = {'nl': 'schilderij van %s' % (metadata.get('creatorname'),)}

            date_regex = '<span class="label">Production date</span><span class="value">\s*([^<]+)</span>'
            date_match = re.search(date_regex, item_page.text)
            if date_match:
                date = date_match.group(1).strip()
                year_regex = '^\s*(\d\d\d\d)\s*$'
                date_circa_regex = '^c?i?r?ca\.?\s*(\d\d\d\d)$'
                period_regex = '^(\d\d\d\d)\s*[--\/]\s*(\d\d\d\d)$'
                circa_period_regex = '^c?i?r?ca\.?\s*(\d\d\d\d)\s*[--\/]\s*c?i?r?ca\.?\s*(\d\d\d\d)$'
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

            material_regex = '<a href="https://smalkmaar\.adlibhosting\.com/ais6/search/detail\?database=museum&amp;fieldname=Field_Material&amp;value=[^\"]+">([^\<]+)</a>'
            material_matches = re.finditer(material_regex, item_page.text)
            materials = set()
            for material_match in material_matches:
                materials.add(material_match.group(1))

            if materials == {'olieverf', 'doek'} or materials == {'olieverf', 'canvas'} \
                    or materials == {'verf', 'doek', 'olieverf'} or materials == {'olieverf', 'textiel', 'doek'}:
                metadata['medium'] = 'oil on canvas'
            elif materials == {'olieverf', 'paneel'} or materials == {'olieverf', 'paneel (hout)'} \
                    or materials == {'verf', 'paneel', 'olieverf'} or materials == {'olieverf', 'paneel', 'hout'}:
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
            elif materials == {'acryl', 'doek'} or materials == {'acrylverf', 'doek'}:
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
                print('Unable to match materials for %s' % (materials,))

            """
            # Find the genre
            object_name_regex = '<a href="https://collectie\.groningermuseum\.nl/search/detail\?database=collect&amp;fieldname=Field_Objectname&amp;value=[^\"]+">([^\<]+)</a>'
            object_name_matches = re.finditer(object_name_regex, item_page.text)
            object_names = set()
            for object_name_match in object_name_matches:
                object_names.add(object_name_match.group(1))

            if object_names == {'schilderijen'}:
                # No genre info
                pass
            elif 'zelfportretten' in object_names:
                metadata['genreqid'] = 'Q192110'  # self-portrait
            elif 'portretten' in object_names:
                metadata['genreqid'] = 'Q134307'  # portrait
            elif 'stillevens' in object_names:
                metadata['genreqid'] = 'Q170571'  # still life
            elif 'landschappen (voorstellingen)' in object_names:
                metadata['genreqid'] = 'Q191163'  # landscape art
            elif 'zeestukken' in object_names:
                metadata['genreqid'] = 'Q158607'  # marine art
            else:
                print('Unable to match genre for %s' % (object_names,))
            """

            # They only seem to have the size of the complete thing (so with frame)
            #dagmaat_2d_regex = '<div class="label">Afmetingen</div>[\s\t\r\n]*<div class="value">[\s\t\r\n]*<ul>.*hoogte:\s*(?P<height>\d+(\.\d+)?)\s*cm\s*\(dagmaat\)<br>breedte:\s*(?P<width>\d+(\.\d+)?)\s*cm \(dagmaat\)<br>.*</ul>'
            #simple_2d_regex = '<div class="label">Afmetingen</div>[\s\t\r\n]*<div class="value">[\s\t\r\n]*<ul>hoogte:\s*(?P<height>\d+(\.\d+)?)\s*cm\s*<br>breedte:\s*(?P<width>\d+(\.\d+)?)\s*cm<br>.*</ul>'

            #dagmaat_2d_match = re.search(dagmaat_2d_regex, item_page.text)
            #simple_2d_match = re.search(simple_2d_regex, item_page.text)
            #if dagmaat_2d_match:
            #    metadata['heightcm'] = dagmaat_2d_match.group('height')
            #    metadata['widthcm'] = dagmaat_2d_match.group(u'width')
            #elif simple_2d_match:
            #    metadata['heightcm'] = simple_2d_match.group('height')
            #    metadata['widthcm'] = simple_2d_match.group(u'width')


            image_regex = 'href="(https://smalkmaar\.adlibhosting\.com/ais6/webapi/wwwopac\.ashx\?command=getcontent&amp;server=images&amp;value=[^"]+&amp;imageformat=jpg)" title="'
            image_match = re.search(image_regex, item_page.text)

            if image_match:
                image_url = html.unescape(image_match.group(1)).replace(' ', '%20')
                recent_inception = False
                if metadata.get('inception') and metadata.get('inception') > 1924:
                    recent_inception = True
                if metadata.get('inceptionend') and metadata.get('inceptionend') > 1924:
                    recent_inception = True
                if not recent_inception:
                    metadata['imageurl'] = image_url
                    metadata['imageurlformat'] = 'Q2195'  # JPEG
                    #    metadata['imageurllicense'] = 'Q18199165' # cc-by-sa.40
                    metadata['imageoperatedby'] = metadata.get('collectionqid')
                    metadata['imageurlforce'] = True  # Used this to add suggestions everywhere
            yield metadata


def main(*args):
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        if arg.startswith('-create'):
            create = True

    paintingGen = get_stedelijk_museum_alkmaar_generator()

    if dryrun:
        for painting in paintingGen:
            print(painting)
    else:
        artDataBot = artdatabot.ArtDataBot(paintingGen, create=create)
        artDataBot.run()

if __name__ == "__main__":
    main()
