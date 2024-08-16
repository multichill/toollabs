#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from National Gallery Prague to Wikidata.

This bot uses artdatabot to upload it to Wikidata
"""
import artdatabot
import pywikibot
import requests
import re
import html

def get_national_gallery_prague_generator():
    """
    Generator to return National Gallery Prague paintings (and more)
    """
    base_search_url = 'https://sbirky.ngprague.cz/en/katalog?technique=oil&page=%s'
    #base_search_url = 'https://sbirky.ngprague.cz/en/katalog?technique=tempera&page=%s'  # tempera

    locations = {'Convent of St Agnes of Bohemia': 'Q394832',  # https://sbirky.ngprague.cz/kolekcia/2
                 'Sternberg Palace': 'Q1291597',  # https://sbirky.ngprague.cz/en/kolekcia/4
                 'Trade Fair Palace': 'Q496259',  # https://sbirky.ngprague.cz/kolekcia/5
                 'The Art of Asia': 'Q1419555',  # https://sbirky.ngprague.cz/kolekcia/6 , just use NGP
                 'The Collection of Prints and Drawings': 'Q1419555',  # https://sbirky.ngprague.cz/kolekcia/7, just use NGP
                 'Schwarzenberg Palace': 'Q898695',  # https://sbirky.ngprague.cz/kolekcia/18
                 'Kinsky Palace': 'Q27017',  # https://sbirky.ngprague.cz/kolekcia/19
                 'Salm Palace': 'Q12050867',  # https://sbirky.ngprague.cz/kolekcia/20
                 }

    for i in range(1, 80):
        search_url = base_search_url % (i, )
        pywikibot.output(search_url)
        session = requests.Session()
        search_page = session.get(search_url)
        search_regex = '<div class="col-md-3 col-sm-4 col-xs-6 item">[\s\t\r\n]*<a href="https://sbirky.ngprague.cz/dielo/(CZE:[^"]+)">'

        for match in re.finditer(search_regex, search_page.text):
            metadata = {}
            metadata['artworkidpid'] = 'P9942'  # National Gallery Prague work ID (P9942)
            metadata['artworkid'] = match.group(1)

            metadata['collectionqid'] = 'Q1419555'
            metadata['collectionshort'] = 'NGPrague'

            url = 'https://sbirky.ngprague.cz/en/dielo/%s' % (match.group(1),)
            cs_url = 'https://sbirky.ngprague.cz/cs/dielo/%s' % (match.group(1),)
            pywikibot.output(url)
            metadata['url'] = url
            item_page = requests.get(url)
            cs_item_page = requests.get(cs_url)

            og_title_regex = '<meta property="og:title" content="([^"]+)" />'
            og_title_match = re.search(og_title_regex, item_page.text)
            cs_og_title_match = re.search(og_title_regex, cs_item_page.text)

            artist_title_regex = '^(.+) - (.+)$'
            artist_title_match = re.match(artist_title_regex, og_title_match.group(1))
            cs_artist_title_match = re.match(artist_title_regex, cs_og_title_match.group(1))

            metadata['creatorname'] = html.unescape(artist_title_match.group(1)).strip()

            title = html.unescape(artist_title_match.group(2))
            cs_title = html.unescape(cs_artist_title_match.group(2))
            if len(title) > 220:
                title = title[0:200]
            if len(cs_title) > 220:
                cs_title = cs_title[0:200]
            metadata['title'] = {'en': title,
                                 'cs': cs_title,
                                 }

            #print(artist_title_match.group(1))
            #print(artist_title_match.group(2))

            date_regex = '<td class="atribut">date:</td>[\s\t\r\n]*<td><time itemprop="dateCreated" datetime="\d+">([^<]+)</time></td>'
            date_match = re.search(date_regex, item_page.text)

            if date_match:
                date = date_match.group(1)
                year_regex = '^(\d\d\d\d)$'
                date_circa_regex = '^c\.\s*(\d\d\d\d)$'
                period_regex = '^(\d\d\d\d)\s*[--–−\/]\s*(\d\d\d\d)$'
                circa_period_regex = '^c\.\s*(\d\d\d\d)\s*[--–\/]\s*(\d\d\d\d)$'
                short_period_regex = '^(\d\d)(\d\d)[--–\/](\d\d)$'
                circa_short_period_regex = '^c\.\s*(\d\d)(\d\d)[-––/](\d\d)$'

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

            dimensions_regex = '<td class="atribut">measurements:</td>[\s\t\r\n]*<td>[\s\t\r\n]*height\s*(?P<height>\d+(,\d+)?)\s*cm<br>[\s\t\r\n]*width\s*(?P<width>\d+(,\d+)?)\s*cm<br>'
            match_2d = re.search(dimensions_regex, item_page.text)
            if match_2d:
                metadata['heightcm'] = match_2d.group('height').replace(',', '.')
                metadata['widthcm'] = match_2d.group('width').replace(',', '.')

            location_regex = '<td class="atribut">in collections:</td>[\s\t\r\n]*<td>[\s\t\r\n]*<div class="expandable">[\s\t\r\n]*<a href="https://sbirky.ngprague.cz/kolekcia/\d+">([^<]+)</a>'
            location_match = re.search(location_regex, item_page.text)
            if location_match:
                location = location_match.group(1)
                if location in locations:
                    metadata['locationqid'] = locations.get(location)
                else:
                    print('Unknown location: "%s"' % (location,))
                    print('Unknown location: "%s"' % (location,))

            material_regex = '<span itemprop="artMedium">([^<]+)</span>'
            material_match = re.search(material_regex, item_page.text)
            if material_match:
                material = material_match.group(1)
                if material == 'wood':
                    material = 'panel'
            else:
                material = None

            technique_regex = '<td class="atribut">technique:</td>[\s\t\r\n]*<td>[\s\t\r\n]*<a href="https://sbirky\.ngprague\.cz/katalog\?technique=[^"]+">([^<]+)</a>'
            technique_match = re.search(technique_regex, item_page.text)
            if technique_match:
                technique = technique_match.group(1)
                if technique in ['oil', 'tempera']:
                    metadata['instanceofqid'] = 'Q3305213'  # It's a painting
                    metadata['description'] = { 'nl': '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                                'en': '%s by %s' % ('painting', metadata.get('creatorname'),),
                                                'de': '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                                'fr': '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                                }
            else:
                technique = None

            if material and technique:
                metadata['medium'] = '%s on %s' % (technique, material)
                #print(material)
                #print(technique)

            inv_regex = '<td class="atribut">inventory number:</td>[\s\t\r\n]*<td>([^<]+)</td>'
            inv_match = re.search(inv_regex, item_page.text)
            if inv_match:
                metadata['id'] = html.unescape(inv_match.group(1).replace('&nbsp;', ' ')).strip()

            can_upload_image = True

            if metadata.get('inception') and metadata.get('inception') > 1920:
                can_upload_image = False
            elif metadata.get('inceptionend') and metadata.get('inceptionend') > 1920:
                can_upload_image = False

            og_image_regex = '<meta property="og:image" content="([^"]+)" />'
            og_image_match = re.search(og_image_regex, item_page.text)

            copyrighted_regex = 'Due to rights restrictions, this image cannot be downloaded'
            copyrighted_match = re.search(copyrighted_regex, item_page.text)

            if can_upload_image and og_image_match and not copyrighted_match:
                metadata['imageurl'] = og_image_match.group(1)
                metadata['imageurlformat'] = u'Q2195' #JPEG
                metadata['imageoperatedby'] = 'Q1419555'

            yield metadata


def main(*args):

    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True

    painting_generator = get_national_gallery_prague_generator()

    if dryrun:
        for painting in painting_generator:
            print(painting)
    else:
        artDataBot = artdatabot.ArtDataIdentifierBot(painting_generator, id_property='P9942', create=create)
        artDataBot.run()


if __name__ == "__main__":
    main()
