#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to get paintings from the Leiden Collection website

Some WordPress json is provided combined with some regular expressions.
"""
import artdatabot
import pywikibot
import requests
import re
import html

def get_leiden_generator():
    """
    Use the search API to get all the paintings
    :return:
    """
    search_url = 'https://www.theleidencollection.com/wp-json/leiden/v1/artworks/?posts_per_page=400&paged=1&meta_key=collection_grid_sort&order=ASC&orderby=meta_value_num&template=collection'
    # Really? You're throwing a 403 at me?
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0'}
    session = requests.Session()
    session.headers.update(headers)
    search_page = session.get(search_url)
    search_json = search_page.json()

    for record in search_json:
        metadata = {}
        leiden_id = record.get('id')
        title = record.get('title')
        record_html = record.get('html')

        #print (record_html)

        url_regex = '\<a href\=\"(https\:\/\/www\.theleidencollection\.com\/artwork\/[^\"]+)\" class\=\"collection-grid-item\"'
        url_match = re.search(url_regex, record_html)
        url = url_match.group(1)
        metadata['url'] = url

        inv_regex = '\<dt class\=\"sr-only\"\>inventory number\<\/dt\>[\s\t\r\n]+\<dd\>([^\<]+)\<\/dd\>'
        inv_match = re.search(inv_regex, record_html)
        metadata['id'] = inv_match.group(1)
        metadata['idpid'] = 'P217'

        metadata['collectionqid'] = 'Q15638014'
        metadata['collectionshort'] = 'Leiden'
        #metadata['locationqid'] = 'Q15638014' no location

        metadata['title'] = { 'en' : html.unescape(title).strip(), }

        creator_regex = '<span class="db mb3">([^<]+)[\s\t\r\n]*</span>'
        creator_match = re.search(creator_regex, record_html)
        metadata['creatorname'] = html.unescape(creator_match.group(1)).strip()

        medium_regex = '<dt class="sr-only">medium</dt>[\t\r\n\s]+<dd>([^<]+)</dd>'
        medium_match = re.search(medium_regex, record_html)
        metadata['medium'] = medium_match.group(1).lower()

        if metadata.get('medium').startswith('oil on'):
            # It's a painting. Just English for now
            metadata['instanceofqid'] = 'Q3305213'
            metadata['description'] = {'en': '%s by %s' % ('painting', metadata.get('creatorname'),),}
        else:
            # Looks like the others are drawings
            metadata['instanceofqid'] = 'Q93184'
            metadata['description'] = {'en': '%s by %s' % ('drawing', metadata.get('creatorname'),),}

        dimensions_regex = '<dt class="sr-only">dimensions</dt>[\t\r\n\s]+<dd>([^<]+)</dd>'
        dimensions_match = re.search(dimensions_regex, record_html)
        dimensions = dimensions_match.group(1)

        if dimensions:
            regex_2d = '\s*(?P<height>\d+(\.\d+)?)\s*x\s(?P<width>\d+(\.\d+)?)\s*cm\s*$'
            match_2d = re.match(regex_2d, dimensions)
            if match_2d:
                metadata['heightcm'] = match_2d.group('height')
                metadata['widthcm'] = match_2d.group(u'width')

        date_regex = '<dt class="sr-only">date</dt>[\t\r\n\s]+<dd>([^<]+)</dd>'
        date_match = re.search(date_regex, record_html)
        date = date_match.group(1)

        if date:
            year_regex = '^(\d\d\d\d)$'
            date_circa_regex = '^ca\.\s*(\d\d\d\d)$'
            period_regex = '^(\d\d\d\d)[--\/](\d\d\d\d)$'
            circa_period_regex = '^ca\.\s*(\d\d\d\d)–(\d\d\d\d)$'
            short_period_regex = '^(\d\d)(\d\d)[--\/](\d\d)$'
            circa_short_period_regex = '^ca\.\s*(\d\d)(\d\d)[-–/](\d\d)$'

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

        item_page = session.get(url)
        image_regex = '<a href="(https://www\.theleidencollection\.com/wp-content/uploads/downloadable/[^"]+\.jpg)" target="_blank">[\r\n\t\s]*<span class="sr-only">download</span>[\r\n\t\s]*High Resolution[\r\n\t\s]*</a>'
        image_match = re.search(image_regex, item_page.text)

        if image_match:
            metadata['imageurl'] = image_match.group(1)
            metadata['imageurlformat'] = 'Q27996264' #JPEG
            # metadata['imageurllicense'] = 'Q20007257' # None found
            metadata['imageoperatedby'] = 'Q15638014'
            # Used this to get the images complete
            # metadata['imageurlforce'] = True

        # Provenance is very extensive! Let's try to extract the year when it entered the collection
        acquisition_regex = '<div role="tabpanel" class="tab-pane tab-pane--basic" id="provenance">[\r\n\t\s]*<div class="container">[\r\n\t\s]*<div class="row">[\r\n\t\s]*<div class="tab-pane-content">[\r\n\t\s]*<ul>.+present owner in (\d\d\d\d)\.?<\/li>[\r\n\t\s]*<\/ul>'
        acquisition_match = re.search(acquisition_regex, item_page.text, flags=re.DOTALL)
        if acquisition_match:
            metadata['acquisitiondate'] = int(acquisition_match.group(1))
        yield metadata


def main(*args):
    dictGen = get_leiden_generator()
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
        art_data_bot = artdatabot.ArtDataBot(dictGen, create=create)
        art_data_bot.run()

if __name__ == "__main__":
    main()
