#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the New Britain Museum of American Art to Wikidata.

Just loop over pages https://ink.nbmaa.org/objects/images?filter=classifications%3AOil%20Painting&page=4

This bot uses artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import html


def get_new_britain_generator():
    """
    Generator to return New Britain Museum of American Art paintings
    """
    # TODO: I could also add the watercolour paintings
    work_on = [('https://ink.nbmaa.org/objects/images?filter=classifications%%3AAcrylic%%20Painting&page=%s',
                'https://ink.nbmaa.org/objects/images?filter=classifications%3AAcrylic%20Painting',
                17,  # 154 hits, 10 per page
                ),
               ('https://ink.nbmaa.org/objects/images?filter=classifications%%3AOil%%20Painting&page=%s',
                'https://ink.nbmaa.org/objects/images?filter=classifications%3AOil%20Painting',
                138,  # 1360 hits, 10 per page.
                ),
               ]
    # Not sure if this needed for thie Emuseum instance
    session = requests.Session()
    session.get('https://ink.nbmaa.org/collections')

    for (basesearchurl, referer, end) in work_on:
        for i in range(1, end): # Was 138
            searchurl = basesearchurl % (i,)

            print (searchurl)
            searchPage = session.get(searchurl, headers={'X-Requested-With' : 'XMLHttpRequest',
                                                         'referer' : referer})

            workurlregex = '\<div class\=\"title text-wrap\s*\"\>\<a class="" href=\"(\/objects\/\d+\/[^\?]+)\?[^\"]+\"\>'
            matches = re.finditer(workurlregex, searchPage.text)

            for match in matches:
                metadata = {}
                #title = html.unescape(match.group(1)).strip()
                url = 'https://ink.nbmaa.org%s' % (match.group(1),)

                itempage = session.get(url)
                pywikibot.output(url)
                metadata['url'] = url

                metadata['collectionqid'] = 'Q7005718'
                metadata['collectionshort'] = 'NBMAA'
                metadata['locationqid'] = 'Q7005718'

                # FIXME: Watercolours later
                metadata['instanceofqid'] = 'Q3305213'
                metadata['idpid'] = 'P217'

                # The website also contains paintings outside of the collection.
                invregex = '\<div class\=\"detailField invnoField\"\>\<span class\=\"detailFieldLabel\"\>Object number\s*\<\/span\>\<span class\=\"detailFieldValue\"\>([^\<]+)\<\/span\>'
                invmatch = re.search(invregex, itempage.text)

                metadata['id'] = html.unescape(invmatch.group(1).replace('&nbsp;', ' ')).strip()

                title_regex = '<div class="detailField titleField"><h1 property="name" itemprop="name">([^<]+)</h1>'
                title_match = re.search(title_regex, itempage.text)
                title = html.unescape(title_match.group(1)).strip()

                # Chop chop, several very long titles
                if len(title) > 220:
                    title = title[0:200]
                title = title.replace('\t', '').replace('\n', '')
                metadata['title'] = {'en': title, }

                creator_regex = '<span class="detailFieldLabel">Artist</span><span class="detailFieldValue"><a property="url" itemprop="url" href="[^"]+"><span property="name" itemprop="name">[\t\r\n\s]*([^<]+)[\t\r\n\s]*</span>'
                creator_match = re.search(creator_regex, itempage.text)

                # Some paintings don't have a creator, but are not anonymous
                if creator_match:
                    creatorname = html.unescape(creator_match.group(1)).strip()

                    metadata['creatorname'] = creatorname
                    metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                                'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                                'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                                'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                                }

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
    dictGen = get_new_britain_generator()
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
