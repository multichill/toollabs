#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from the Hungarian National Gallery (Magyar Nemzeti Galéria). Second version after new website

* Loop over https://en.mng.hu/artworks/?per_page=20&offset=20&current_page=2&orderby=author&order=asc&artwork_type=painting,panel-painting
* Grab individual paintings like https://en.mng.hu/artworks/duttyan-tent-tent-with-awning/
* No longer grab the Hungarian title from pages like http://mng.hu/gyujtemeny/gipsy-bride-2534 (can't find it)

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re
#import http.client
try:
    from html.parser import HTMLParser
except ImportError:
    import HTMLParser

def getMNGGenerator():
    """
    Generator to return Hungarian National Gallery (Magyar Nemzeti Galéria) paintings
    """
    htmlparser = HTMLParser()
    # They switched to Wordpress so I have to ask Wordpress for a list of relevant posts
    baseSearchUrl = 'https://en.mng.hu/wp/wp-admin/admin-ajax.php'

    session = requests.Session()

    step = 20

    # 3150, 20 per page
    for i in range(1, 159):
        offset = ( i * step ) - step
        print('Working on page %s and offset %s on %s' % (i, offset, baseSearchUrl))

        postdata = { 'action' : 'post_filter',
                     'post_type' : 'artwork',
                     'list_mode' : 'grid',
                     'filter_object[per_page]' : step,
                     'filter_object[offset]' :  offset,
                     'filter_object[current_page]' : i,
                     'filter_object[orderby]' : 'author',
                     'filter_object[order]' : 'asc',
                     'filter_object[artwork_type][0]' : 'painting',
                     'filter_object[artwork_type][1]' : 'panel-painting'
                     }

        searchPage = session.post(baseSearchUrl, data=postdata)
        searchPageData = searchPage.text
        searchRegex = '\<div class\=\"card card--artwork-x\"\>[\s\t\r\n]*\<a href\=\"(https\:\/\/en\.mng\.hu\/artworks\/[^\"]+\/)\" class\=\"card__link\"\>'

        for match in re.finditer(searchRegex, searchPageData):
            url = match.group(1)
            print (url)

            itemPage = requests.get(url)
            itemPageData = itemPage.text

            metadata = {}
            metadata['url'] = url

            metadata['collectionqid'] = 'Q252071'
            metadata['collectionshort'] = 'MNG'
            metadata['locationqid'] = 'Q252071'

            objecttyperegex = '\<th\>Object type\<\/th\>[\s\t\r\n]*\<td\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/td\>'
            objecttypematch = re.search(objecttyperegex, itemPageData)
            objecttype = htmlparser.unescape(objecttypematch.group(1)).strip()

            # Search is for paintings
            if objecttype=='panel painting' or objecttype=='painting':
                metadata['instanceofqid'] = u'Q3305213'
            else:
                # Just to be sure
                print('Found a unexpected object type: %s!!!!' % (objecttype,))
                continue

            titlecreatorregex = '\<h1 class\=\"headline__title\"\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<span class\=\"author\"\>[\s\t\r\n]*\<span class\=\"author__name\"\>([^\<]+)\<\/span\>'
            titlecreatormatch = re.search(titlecreatorregex, itemPageData)

            titleregex = '\<h1 class\=\"headline__title\"\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/h1>'
            titlematch = re.search(titleregex, itemPageData)

            if titlecreatormatch:
                title = htmlparser.unescape(titlecreatormatch.group(1)).strip()
                name = htmlparser.unescape(titlecreatormatch.group(2)).strip()
            else:
                title = htmlparser.unescape(titlematch.group(1)).strip()
                name = None

            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { 'en' : title,
                                  }

            if name:
                metadata['creatorname'] = name
                metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                            'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                            'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                            'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                        }
            else:
                metadata['creatorname'] = 'anonymous'
                metadata['description'] = { 'nl' : 'schilderij van anonieme schilder',
                                            'en' : 'painting by anonymous painter',
                                            }
                metadata['creatorqid'] = 'Q4233718'

            # That seems to work. Delete this part later
            #if titleMatch:
            #    title = htmlparser.unescape(titleMatch.group(1)).strip()
            #else:
            #    title = u'(without title)'

            #artistRegex = u'\<td class\=\"data-label\"\>artist\:\<\/td\>[\r\n\t\s]*\<td\>[\r\n\t\s]*([^\<]+)\<br\>'
            #artistMatch = re.search(artistRegex, itemPageData)
            #if artistMatch:
            #    name = htmlparser.unescape(artistMatch.group(1)).strip()
            #else:
            #    name = u'anonymous'
            #metadata['creatorname'] = name
            #metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
            #                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
            #                            }

            metadata['idpid'] = u'P217'
            invRegex = '\<th\>Inventory number\<\/th\>[\s\t\r\n]*\<td\>([^\<]+)\<\/td\>'
            invMatch = re.search(invRegex, itemPageData)
            metadata['id'] = invMatch.group(1).strip()

            # Find different types of dates
            dateregex = '\<th\>Date\<\/th\>[\s\t\r\n]*\<td\>(\d\d\d\d)\<\/td\>'
            datecircaregex = '\<th\>Date\<\/th\>[\s\t\r\n]*\<td\>ca\.\s*(\d\d\d\d)\<\/td\>'
            periodregex = '\<th\>Date\<\/th\>[\s\t\r\n]*\<td\>(\d\d\d\d)\s*[-–]\s*(\d\d\d\d)\<\/td\>'
            circaperiodregex = '\<th\>Date\<\/th\>[\s\t\r\n]*\<td\>ca\.\s*(\d\d\d\d)\s*[-–]\s*(\d\d\d\d)\<\/td\>'
            shortperiodregex = '\<th\>Date\<\/th\>[\s\t\r\n]*\<td\>(\d\d)(\d\d)\s*[-–]\s*(\d\d)\<\/td\>'
            circashortperiodregex = '\<th\>Date\<\/th\>[\s\t\r\n]*\<td\>ca\.\s*(\d\d)(\d\d)\s*[-–]\s*(\d\d)\<\/td\>'
            otherdateregex = '\<th\>Date\<\/th\>[\s\t\r\n]*\<td\>([^\<]+)\<\/td\>'

            datematch = re.search(dateregex, itemPageData)
            datecircamatch = re.search(datecircaregex, itemPageData)
            periodmatch = re.search(periodregex, itemPageData)
            circaperiodmatch = re.search(circaperiodregex, itemPageData)
            shortperiodmatch = re.search(shortperiodregex, itemPageData)
            circashortperiodmatch = re.search(circashortperiodregex, itemPageData)
            otherdatematch = re.search(otherdateregex, itemPageData)

            if datematch:
                metadata['inception'] = int(datematch.group(1).strip())
            elif datecircamatch:
                metadata['inception'] = int(datecircamatch.group(1).strip())
                metadata['inceptioncirca'] = True
            elif periodmatch:
                metadata['inceptionstart'] = int(periodmatch.group(1))
                metadata['inceptionend'] = int(periodmatch.group(2))
            elif circaperiodmatch:
                metadata['inceptionstart'] = int(circaperiodmatch.group(1))
                metadata['inceptionend'] = int(circaperiodmatch.group(2))
                metadata['inceptioncirca'] = True
            elif shortperiodmatch:
                metadata['inceptionstart'] = int('%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(2),))
                metadata['inceptionend'] = int('%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(3),))
            elif circashortperiodmatch:
                metadata['inceptionstart'] = int('%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(2),))
                metadata['inceptionend'] = int('%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(3),))
                metadata['inceptioncirca'] = True
            elif otherdatematch:
                print ('Could not parse date: "%s"' % (otherdatematch.group(1),))

            # acquisitiondate not available
            # acquisitiondateRegex = u'\<em\>Acknowledgement\<\/em\>\:\s*.+(\d\d\d\d)[\r\n\t\s]*\<br\>'
            #acquisitiondateMatch = re.search(acquisitiondateRegex, itemPageData)
            #if acquisitiondateMatch:
            #    metadata['acquisitiondate'] = acquisitiondateMatch.group(1)

            mediumRegex = '\<th\>Medium, technique\<\/th\>[\s\t\r\n]*\<td\>([^\<]+)\<\/td\>'
            mediumMatch = re.search(mediumRegex, itemPageData)

            if mediumMatch:
                medium = mediumMatch.group(1).strip().lower()
                mediums = { 'oil on canvas' : 'oil on canvas',
                            'canvas, oil' : 'oil on canvas',
                            'oil, canvas' : 'oil on canvas',
                            'oil on wood' : 'oil on panel',
                            'oil on wood panel' : 'oil on panel',
                            'wood, oil' : 'oil on panel',
                            'wood panel, oil' : 'oil on panel',
                            'oil on paper' : 'oil on paper',
                            'paper, oil' : 'oil on paper',
                            'tempera on wood' : 'tempera on panel',
                            'wood, tempera' : 'tempera on panel',
                            'wood panel, tempera' : 'tempera on panel',
                            'paper, tempera' : 'tempera on paper',
                            'acrylic on canvas' : 'acrylic paint on canvas',
                            'acrylic, canvas' : 'acrylic paint on canvas',
                            'canvas, acrylic' : 'acrylic paint on canvas',
                            'watercolour on paper' : 'watercolor on paper',
                            'aquarelle on paper' : 'watercolor on paper',
                            }
                if medium in mediums:
                    metadata['medium'] = mediums.get(medium)
                else:
                    # Maybe artdatabot can make some sense out of it
                    metadata['medium'] = medium
                    print('Unable to match medium %s' % (medium,))

            dimensionRegex = '\<th\>Dimensions\<\/th\>[\s\t\r\n]*\<td\>\<p\>([^\<]+)\<\/p\>'
            dimensionMatch = re.search(dimensionRegex, itemPageData)

            if dimensionMatch:
                dimensiontext = dimensionMatch.group(1).strip()
                regex_2d = '^(?P<height>\d+(\.\d+)?)\s*(x|×)\s*(?P<width>\d+(\.\d+)?)\s*cm$'
                #regex_3d = u'^.+\((?P<height>\d+(\.\d+)?)\s*(cm\s*)?(x|×)\s*(?P<width>\d+(\.\d+)?)\s*(cm\s*)?(x|×)\s*(?P<depth>\d+(\.\d+)?)\s*cm\)$'
                match_2d = re.match(regex_2d, dimensiontext, re.DOTALL)
                #match_3d = re.match(regex_3d, dimensiontext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height')
                    metadata['widthcm'] = match_2d.group(u'width')
                #if match_3d:
                #    metadata['heightcm'] = match_3d.group(u'height')
                #    metadata['widthcm'] = match_3d.group(u'width')
                #    metadata['depthcm'] = match_3d.group(u'depth')

            # Image use policy unclear
            #imageMatch = re.search(imageregex, itemPageData)
            #if imageMatch:
            #    metadata[u'imageurl'] = imageMatch.group(1)
            #    metadata[u'imageurlformat'] = u'Q2195' #JPEG
            yield metadata


def main(*args):
    dictGen = getMNGGenerator()
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
