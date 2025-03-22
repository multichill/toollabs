#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape https://www.lichtensteincatalogue.org/

"""
import artdatabot
import pywikibot
import requests
import re
import html


def get_lichtenstein_generator():
    """
    Search for paintings and loop over it. Have to do filter in a session
    """
    session = requests.session()
    get_entries_url = 'https://www.lichtensteincatalogue.org/catalogue/getEntries.php'

    start_data = {
        'getType': 'filters',
        'layout': 'html',
        'filterOpts[]': 'Classifications::painting'
    }
    session.post(get_entries_url, data=start_data)

    for i in range(0, 20):
        print('%s page %s' % (get_entries_url, i))
        entries_data = {'getType': 'entries',
                        'layout': 'html',
                        'filterOpts': '',
                        'pageNum': '%s' % (i,),
                        'maxRows': '60'}
        search_page = session.post(get_entries_url, data=entries_data)

        id_regex = '<a href="/catalogue/entry\.php\?id=(\d+)">'
        id_matches = re.finditer(id_regex, search_page.text)

        for id_match in id_matches:
            metadata = {}
            url = 'https://www.lichtensteincatalogue.org/catalogue/entry.php?id=%s' % (id_match.group(1),)
            print(url)
            metadata['url'] = url

            metadata['artworkidpid'] = 'P11885'  # Roy Lichtenstein: A Catalogue Raisonné ID
            metadata['artworkid'] = id_match.group(1)

            item_page = requests.get(url)
            painting_text = '<div id="classificationDescription"><a class="closeButton" href="javascript:hideDiv(\'classificationDescription\')"></a><h4>Painting</h4><div id="classificationDescriptionText">'
            if painting_text not in item_page.text:
                # Something wrong, should be a painting
                print('NOT A PAINTING!!!')
                continue
            metadata['instanceofqid'] = 'Q3305213'

            # The site is a catalog
            catalog_regex = '<div class="tombstone div_CatalogueNumber">(RLCR \d+) \('
            catalog_match = re.search(catalog_regex, item_page.text)
            if catalog_match:
                metadata['catalog_code'] = catalog_match.group(1)
                metadata['catalog'] = 'Q119041898'

            # Get title
            title_regex = '<div class="tombstone div_Title"><em>([^<]+)</em></div>'
            title_match = re.search(title_regex, item_page.text)

            metadata['title'] = {'en' : html.unescape(title_match.group(1))}
            metadata['description'] = { 'de' : 'Gemälde von Roy Lichtenstein',
                                        'nl' : 'schilderij van Roy Lichtenstein',
                                        'en' : 'painting by Roy Lichtenstein',
                                        'fr': 'peinture de Roy Lichtenstein'
                                        }
            # Only paintings by Roy Lichtenstein
            metadata['creatorqid'] = 'Q151679'

            # Get date
            date_regex = '<div class="tombstone div_fullDate">([^<]+)</div>'
            date_match = re.search(date_regex, item_page.text)

            if date_match:
                date = date_match.group(1)

                year_regex = '^(\d\d\d\d)$'
                year_circa_regex = '^c\.\s*(\d\d\d\d)$'
                short_period_regex = '^(\d\d)(\d\d)–(\d\d)$'
                circa_short_period_regex = '^c\.\s*(\d\d)(\d\d)–(\d\d)$'

                year_match = re.match(year_regex, date)
                year_circa_match = re.match(year_circa_regex, date)
                short_period_match = re.match(short_period_regex, date)
                circa_short_period_match = re.match(circa_short_period_regex, date)
                # Could add more variants if needed

                if year_match:
                    metadata['inception'] = int(year_match.group(1))
                elif year_circa_match:
                    metadata['inception'] = int(year_circa_match.group(1))
                    metadata['inceptioncirca'] = True
                elif short_period_match:
                    metadata['inceptionstart'] = int('%s%s' % (short_period_match.group(1),
                                                               short_period_match.group(2),))
                    metadata['inceptionend'] = int('%s%s' % (short_period_match.group(1),
                                                             short_period_match.group(3),))
                elif circa_short_period_match:
                    metadata['inceptionstart'] = int('%s%s' % (circa_short_period_match.group(1),
                                                               circa_short_period_match.group(2),))
                    metadata['inceptionend'] = int('%s%s' % (circa_short_period_match.group(1),
                                                             circa_short_period_match.group(3),))
                    metadata['inceptioncirca'] = True
                else:
                    print ('Could not parse date: "%s"' % (date,))

            medium_regex = '<div class="tombstone div_fullMedium"><div class="sectionHeading">Media</div>[\r\n\t\s]*([^<]+)</div>'
            medium_match = re.search(medium_regex, item_page.text)
            if medium_match:
                medium = medium_match.group(1).strip().lower()
                metadata['medium'] = medium

            # Dimensions are a pain in inches
            dimension_regex = '<div class="tombstone div_fullDimension"><div class="sectionHeading">Dimensions</div>[\r\n\t\s]*([^<]+)</div>'
            dimension_match = re.search(dimension_regex, item_page.text)
            if dimension_match:
                dimensions = dimension_match.group(1).strip().lower()

                regex_2d = '^.+in\.\s+\((?P<height>\d+(\.\d+)?)\s*x\s*(?P<width>\d+(\.\d+)?)\s*cm\)$'
                match_2d = re.match(regex_2d, dimensions)
                if match_2d:
                    metadata['heightcm'] = match_2d.group('height').replace(',', '.')
                    metadata['widthcm'] = match_2d.group('width').replace(',', '.')

            yield metadata


def main(*args):
    dict_gen = get_lichtenstein_generator()
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
        art_data_bot = artdatabot.ArtDataIdentifierBot(dict_gen, id_property='P11885', create=create)
        art_data_bot.run()

if __name__ == "__main__":
    main()
