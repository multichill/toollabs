#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Mesdag Collectie to Wikidata.

Website similar to Van Gogh Museum

This bot uses artdatabot to upload it to Wikidata
"""
import artdatabot
import pywikibot
import requests
import re
import html

def get_mesdag_collectie_generator():
    """
    Generator to return Mesdag Collectie paintings
    """
    urls = ['https://www.demesdagcollectie.nl/nl/zoeken/collectie?type=schilderij']
    session = requests.Session()

    for search_url in urls:
        print(search_url)
        search_page = session.get(search_url)

        work_url_regex = '<a class="link-teaser triggers-slideshow-effect" href="/nl/collectie/([^"]+)">'
        matches = re.finditer(work_url_regex, search_page.text)

        for match in matches:
            metadata = {}
            url = 'https://www.demesdagcollectie.nl/nl/collectie/%s' % (match.group(1),)

            item_page = session.get(url)
            pywikibot.output(url)
            metadata['url'] = url

            metadata['collectionqid'] = 'Q255409'
            metadata['collectionshort'] = 'Mesdag'
            metadata['locationqid'] = 'Q255409'

            # Searching for paintings
            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = 'P217'

            inv_regex = '<dt class="text-titlecase">Inventarisnummer</dt>[\s\t\r\n]*<dd>([^<]+)</dd>'
            inv_match = re.search(inv_regex, item_page.text)

            #print(item_page.text)

            if not inv_match:
                # Getting some errors like on https://www.demesdagcollectie.nl/nl/collectie/hwm0273
                continue

            metadata['id'] = html.unescape(inv_match.group(1).replace('&nbsp;', ' ')).strip()

            title_creator_date_regex = '<h1 class="h2">[\s\t\r\n]*<a name="info"></a>[\s\t\r\n]*([^<]+)[\s\t\r\n]*</h1>[\s\t\r\n]*<p class="text-italic">[\s\t\r\n]*<p class="text-bold">[\s\t\r\n]*([^<]+), ([^<]+\d\d[^<]+)[\s\t\r\n]*</p>'
            title_creator_date_match = re.search(title_creator_date_regex, item_page.text)

            if title_creator_date_match:
                title = html.unescape(title_creator_date_match.group(1)).strip()
                # Chop chop, might have long titles
                if len(title) > 220:
                    title = title[0:200]
                title = title.replace('\r', '').replace('\t', '').replace('\n', '').replace('  ', ' ').strip()
                metadata['title'] = {'nl': title, }

                name = html.unescape(title_creator_date_match.group(2)).strip()
                metadata['creatorname'] = name.strip()


                metadata['description'] = { 'nl': '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                            'en': '%s by %s' % ('painting', metadata.get('creatorname'),),
                                            'de': '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                            'fr': '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                            }
                date = html.unescape(title_creator_date_match.group(3)).strip()
                year_regex = '^\s*(\d\d\d\d)\s*$'
                weird_year_regex = '^\s*(\d\d\d\d)\s*-\s*(\d\d\d\d)\s*-12-31$'
                date_circa_regex = '^c\.\s*(\d\d\d\d)$'
                period_regex = '^(\d\d\d\d)\s*[--\/]\s*(\d\d\d\d)$'
                circa_period_regex = '^c\.\s*(\d\d\d\d)\s*[--\/]\s*(\d\d\d\d)$'
                short_period_regex = '^(\d\d)(\d\d)[--\/](\d\d)$'
                circa_short_period_regex = '^c\.um\s*(\d\d)(\d\d)[-–/](\d\d)$'

                year_match = re.match(year_regex, date)
                weird_year_year_match = re.match(weird_year_regex, date)
                date_circa_match = re.match(date_circa_regex, date)
                period_match = re.match(period_regex, date)
                circa_period_match = re.match(circa_period_regex, date)
                short_period_match = re.match(short_period_regex, date)
                circa_short_period_match = re.match(circa_short_period_regex, date)

                if year_match:
                    # Don't worry about cleaning up here.
                    metadata['inception'] = int(year_match.group(1))
                elif weird_year_year_match and weird_year_year_match.group(1) == weird_year_year_match.group(2):
                    metadata['inception'] = int(weird_year_year_match.group(1))
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

            medium_dimensions_regex = '<p>[\s\t\r\n]*([^<]+),[\s\t\r\n]*([^<]+ cm x [^<]+ cm)[\s\t\r\n]*<br />De Mesdag Collectie, Den Haag\s*</p>'
            medium_dimensions_match = re.search(medium_dimensions_regex, item_page.text)

            if medium_dimensions_match:
                medium = html.unescape(medium_dimensions_match.group(1)).strip()
                dimensions = html.unescape(medium_dimensions_match.group(2)).strip()

                mediums = {'olieverf op doek': 'oil on canvas',
                           'olieverf op paneel': 'oil on panel',
                           'olieverf op doek op paneel': 'oil on canvas on panel',
                           'olieverf op karton': 'oil on cardboard',
                           }
                if medium in mediums:
                    metadata['medium'] = mediums.get(medium)
                else:
                    print('Unable to match materials for %s' % (medium,))

                regex_2d = '^\s*(?P<height>\d+(\.\d+)?)\s*cm\s*x\s*(?P<width>\d+(\.\d+)?)\s*cm$'
                match_2d = re.match(regex_2d, dimensions)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')

            else:
                print('No match on %s' % (url,))

            image_regex = '<a href="(/download/[^"]+.jpg\?size=l)"'
            image_match = re.search(image_regex, item_page.text)

            if image_match:
                image_url = 'https://www.demesdagcollectie.nl%s' % (image_match.group(1),)
                # Just throw in all
                metadata['imageurl'] = image_url
                metadata['imageurlformat'] = 'Q2195'  # JPEG
                #    metadata['imageurllicense'] = 'Q18199165' # cc-by-sa.40
                metadata['imageoperatedby'] = metadata.get('collectionqid')
                metadata['imageurlforce'] = False  # Used this to add suggestions everywhere
            yield metadata


def main(*args):
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        if arg.startswith('-create'):
            create = True

    paintingGen = get_mesdag_collectie_generator()

    if dryrun:
        for painting in paintingGen:
            print(painting)
    else:
        artDataBot = artdatabot.ArtDataBot(paintingGen, create=create)
        artDataBot.run()

if __name__ == "__main__":
    main()
