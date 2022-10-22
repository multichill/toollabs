#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from Museum Flehite to Wikidata.

The have Adlib/Axiel running at https://ais.axiellcollections.cloud/FLEHITE/results
Unfortunately didn't enable the API part so we have to scrape it.

This bot uses artdatabot to upload it to Wikidata.
"""
import artdatabot
import pywikibot
import requests
import re
import html


def get_flehite_generator():
    """
    Generator to return Museum Flehite paintings
    """
    starturl = 'https://ais.axiellcollections.cloud/FLEHITE/search/detail?database=collect&fieldname=Field_Objectname&value=schilderij'
    session = requests.Session()
    session.get(starturl)

    base_search_url = 'https://ais.axiellcollections.cloud/FLEHITE/resultsnavigate/%s'

    for i in range(1, 59):
        search_url = base_search_url % (i,)

        print (search_url)
        search_page = session.get(search_url)

        work_url_regex = '<a title="" href="https?://ais\.axiellcollections\.cloud/FLEHITE/Details/collect/(\d+)">'
        matches = re.finditer(work_url_regex, search_page.text)

        for match in matches:
            metadata = {}
            url = 'https://ais.axiellcollections.cloud/FLEHITE/Details/collect/%s' % (match.group(1),)

            item_page = session.get(url)
            pywikibot.output(url)
            metadata['url'] = url

            #print (urlitem_page.text)

            metadata['collectionqid'] = 'Q29908492'
            metadata['collectionshort'] = 'Flehite'
            metadata['locationqid'] = 'Q29908492'

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



            creator_regex = '<div class="label">Vervaardiger</div><div class="value"><a href="http[^\"]+">([^\<]+)</a></div>'
            creator_match = re.search(creator_regex, item_page.text)

            if creator_match:
                name = html.unescape(creator_match.group(1)).strip()
                if ',' in name:
                    (surname, sep, firstname) = name.partition(',')
                    name = '%s %s' % (firstname.strip(), surname.strip(),)

                metadata['creatorname'] = name

                if name in ['onbekend', 'anoniem']:
                    metadata['description'] = { 'nl' : 'schilderij van anonieme schilder',
                                                'en' : 'painting by anonymous painter',
                                                }
                    metadata['creatorqid'] = 'Q4233718'
                else:
                    metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                                'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                                'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                                'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                                }

            yield metadata
            continue

            # TODO: Add inception
            # TODO: Add material
            # TODO: Add size

            if False:

                date_regex = '<span class="detailFieldLabel">Date</span><span property="dateCreated" itemprop="dateCreated" class="detailFieldValue">([^<]+)</span>'
                date_match = re.search(date_regex, itempage.text)
                if date_match:
                    date = date_match.group(1)
                    year_regex = '^(\d\d\d\d)$'
                    date_circa_regex = '^ca?\.\s*(\d\d\d\d)$'
                    period_regex = '^(\d\d\d\d)[--\/](\d\d\d\d)$'
                    circa_period_regex = '^ca?\.\s*(\d\d\d\d)–(\d\d\d\d)$'
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

                medium_regex = '<span class="detailFieldLabel">Medium</span><span property="artMedium" itemprop="artMedium" class="detailFieldValue">([^<]+)</span>'
                medium_match = re.search(medium_regex, itempage.text)
                # Artdatabot will sort this out
                if medium_match:
                    metadata['medium'] = medium_match.group(1).lower()

                dimensions_regex = '<div class="detailField dimensionsField"><span class="detailFieldLabel">Dimensions</span><span class="detailFieldValue">[^\(]+\(([^\)]+ cm)\)</span>'
                dimensions_match = re.search(dimensions_regex, itempage.text)

                if dimensions_match:
                    dimensions = dimensions_match.group(1)
                    regex_2d = '\s*(?P<height>\d+(\.\d+)?)\s*×\s*(?P<width>\d+(\.\d+)?)\s*cm\s*$'
                    match_2d = re.match(regex_2d, dimensions)
                    if match_2d:
                        metadata['heightcm'] = match_2d.group('height')
                        metadata['widthcm'] = match_2d.group(u'width')

                ### Nothing useful here, might be part of the inventory number
                #acquisitiondateregex = '\<div class\=\"detailField creditlineField\"\>[^\<]+,\s*(\d\d\d\d)\<\/div\>'
                #acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
                #if acquisitiondatematch:
                #    metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

                # Image url is provided and it's a US collection. Just check the date
                image_regex = '<meta content="(https://ink\.nbmaa\.org/internal/media/dispatcher/\d+/full)" name="og:image">'
                image_match = re.search(image_regex, itempage.text)
                if image_match:
                    recent_inception = False
                    if metadata.get('inception') and metadata.get('inception') > 1924:
                        recent_inception = True
                    if metadata.get('inceptionend') and metadata.get('inceptionend') > 1924:
                        recent_inception = True
                    if not recent_inception:
                        metadata['imageurl'] = image_match.group(1)
                        metadata['imageurlformat'] = 'Q2195' #JPEG
                    #    metadata['imageurllicense'] = 'Q18199165' # cc-by-sa.40
                        metadata['imageoperatedby'] = 'Q7005718'
                    #    # Can use this to add suggestions everywhere
                    #    metadata['imageurlforce'] = True
                yield metadata


def main(*args):
    dictGen = get_flehite_generator()
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
