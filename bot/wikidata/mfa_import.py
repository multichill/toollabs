#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape paintings from the Museum of Fine Arts, Boston website.

https://www.mfa.org/collections/search?search_api_views_fulltext=&f%5B0%5D=field_classifications%3A16

"""
import pywikibot
import artdatabot
import requests
import re
from html.parser import HTMLParser

def getMFAGenerator():
    """

    Do Americas, Europe, Contemporary Art. Leave Asia for later

    Doing a two step approach here. 
    * Loop over https://www.mfa.org/collections/search?search_api_views_fulltext&sort=search_api_aggregation_1&order=asc&f[0]=field_classifications%3A16&f[1]=field_collections%3A5=&page=4 - 66 and grab paintings
    * Grab data from paintings

    Sorted by author name

    Americas = 3, 0 - 120 = 2153
    Contemporary = 4, 0 - 38 = 681
    Europe = 5, 0 - 81 = 1452

    Bot doesn't seem to catch everything. For Americas:
    Excepted 2160 items, got 1559 items
    (probably because I started half way)
    
    
    """
    collectionurls = [
        (u'https://www.mfa.org/collections/search?search_api_views_fulltext=&sort=search_api_aggregation_1&order=asc&f[0]=field_classifications%%3A16&f[1]=field_collections%%3A3&page=%s', 121),
        (u'https://www.mfa.org/collections/search?search_api_views_fulltext=&sort=search_api_aggregation_1&order=asc&f[0]=field_classifications%%3A16&f[1]=field_collections%%3A4&page=%s', 39),
        (u'https://www.mfa.org/collections/search?search_api_views_fulltext=&sort=search_api_aggregation_1&order=asc&f[0]=field_classifications%%3A16&f[1]=field_collections%%3A5&page=%s', 82),
    ]

    htmlparser = HTMLParser()
    session = requests.Session()

    for (baseurl, lastpage) in collectionurls:
        n = 0
        for i in range(0, lastpage):
            searchurl = baseurl % (i,)
            pywikibot.output(searchurl)
            searchPage = session.get(searchurl)
            searchData = searchPage.text
            # <span class="italic"><a href="/aic/collections/artwork/47149?search_no=

            itemregex = u'<a href="(https://www.mfa.org/collections/object/[^"]+)">' # <div class="object">\s

            for match in re.finditer(itemregex, searchData, flags=re.M):
                n = n + 1
                metadata = {}

                # No ssl, faster?
                url = match.group(1)
                metadata['url'] = url
                print (url)

                metadata['artworkidpid'] = u'P4625'
                metadata['artworkid'] = url.replace(u'https://www.mfa.org/collections/object/', u'')

                metadata['collectionqid'] = u'Q49133'
                metadata['collectionshort'] = u'MFA'
                metadata['locationqid'] = u'Q49133'
                metadata['idpid'] = u'P217'

                #No need to check, I'm actually searching for paintings.
                metadata['instanceofqid'] = u'Q3305213'

                # Grab the data for the item
                itemPage = session.get(url)
                itemData = itemPage.text

                idregex = u'<h4>Accession Number</h4>\s*<p>([^<]+)</p>'
                idmatch = re.search(idregex, itemData, flags=re.M)
                if idmatch:
                    metadata['id'] = htmlparser.unescape(idmatch.group(1))
                else:
                    print (u'No ID found. Something is really wrong on this page')
                    continue

                titleregex = u'<meta property="og:title" content="([^"]+)" />'
                titlematch = re.search(titleregex, itemData, flags=re.M)

                # Chop chop, several very long titles
                if len(htmlparser.unescape(titlematch.group(1))) > 220:
                    title = htmlparser.unescape(titlematch.group(1))[0:200]
                else:
                    title = htmlparser.unescape(titlematch.group(1))
                metadata['title'] = { u'en' : title,
                                      }

                creatorregex = u'<a href="/collections/search\?f\[0\]=field_artists%253Afield_artist%3A\d+">([^<]+)</a>'
                creatormatch = re.search(creatorregex, itemData, flags=re.M)
                if creatormatch:
                    metadata['creatorname'] = htmlparser.unescape(creatormatch.group(1))
                else:
                    metadata['creatorname'] = u'anonymous'

                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            }

                mediumregex = u'<h4>Medium or Technique</h4>\s*<p>([^<]+)</p>'
                mediummatch = re.search(mediumregex, itemData, flags=re.M)
                if mediummatch and htmlparser.unescape(mediummatch.group(1))==u'Oil on canvas':
                    metadata['medium'] = u'oil on canvas'

                dateregex = u'\<p\>\s*(\d\d\d\d)\s*\<br\>\s*\<a href=\"/collections/search\?f\[0\]=field_artists%253Afield_artist'
                circadateregex = u'\<p\>\s*about\s*(\d\d\d\d)\s*\<br\>\s*\<a href=\"/collections/search\?f\[0\]=field_artists%253Afield_artist'
                circaperiodregex = u'\<p\>\s*about\s*(\d\d\d\d)[-–](\d\d\d\d)\s*\<br\>\s*\<a href=\"/collections/search\?f\[0\]=field_artists%253Afield_artist'
                circashortperiodregex = u'\<p\>\s*about\s*(\d\d)(\d\d)[-–](\d\d)\s*\<br\>\s*\<a href=\"/collections/search\?f\[0\]=field_artists%253Afield_artist'
                otherdateregex = u'\<p\>([^\<]+)\<br\>\s*\<a href=\"/collections/search\?f\[0\]=field_artists%253Afield_artist'

                datematch = re.search(dateregex, itemData, flags=re.M)
                circadatematch = re.search(circadateregex, itemData, flags=re.M)
                circaperiodmatch = re.search(circaperiodregex, itemData, flags=re.M)
                circashortperiodmatch = re.search(circashortperiodregex, itemData, flags=re.M)
                otherdatematch = re.search(otherdateregex, itemData, flags=re.M)

                if datematch:
                    metadata['inception'] = htmlparser.unescape(datematch.group(1))
                elif circadatematch:
                    metadata['inception'] = htmlparser.unescape(circadatematch.group(1))
                    metadata['inceptioncirca'] = True
                elif circaperiodmatch:
                    metadata['inceptionstart'] = int(circaperiodmatch.group(1),)
                    metadata['inceptionend'] = int(circaperiodmatch.group(2),)
                    metadata['inceptioncirca'] = True
                elif circashortperiodmatch:
                    metadata['inceptionstart'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(2),))
                    metadata['inceptionend'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(3),))
                    metadata['inceptioncirca'] = True
                elif otherdatematch:
                    print (u'Could not parse date: "%s"' % (otherdatematch.group(1),))
                #elif shortperiodmatch:
                #    metadata['inceptionstart'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(2),))
                #    metadata['inceptionend'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(3),))

                accessionDateRegex = u'\(Accession [dD]ate\:\s*(?P<month>(January|February|March|April|May|June|July|August|September|October|November|December))\s*(?P<day>\d+),\s*(?P<year>\d+\d+\d+\d+)\s*\)'
                accessionDateMatch = re.search(accessionDateRegex, itemData)
                accessionDateRegex2 = u'\<h3\>\s*Provenance\s*\<\/h3\>\s*<p>[^<]+to MFA,\s*(Boston,)?\s*(?P<year>\d\d\d\d)(\s*,)?[^<]*\<\/p\>'
                accessionDateMatch2 = re.search(accessionDateRegex2, itemData, flags=re.M)
                if accessionDateMatch:
                    months = { u'January' : 1,
                               u'February' : 2,
                               u'March' : 3,
                               u'April' : 4,
                               u'May' : 5,
                               u'June' : 6,
                               u'July' : 7,
                               u'August' : 8,
                               u'September' : 9,
                               u'October' : 10,
                               u'November' : 11,
                               u'December' : 12,
                               }

                    metadata[u'acquisitiondate'] = u'%04d-%02d-%02d' % (int(accessionDateMatch.group(u'year')),
                                                                           months.get(accessionDateMatch.group(u'month')),
                                                                           int(accessionDateMatch.group(u'day')),)
                elif accessionDateMatch2:
                    metadata[u'acquisitiondate'] = accessionDateMatch2.group(u'year')


                dimensionregex = u'<h4>Dimensions</h4>\s*<p>([^<]+)</p>'
                dimensionMatch = re.search(dimensionregex, itemData, flags=re.M)
                if dimensionMatch:
                    dimensiontext = dimensionMatch.group(1).strip()
                    regex_2d = u'^(Overall:)?\s*(?P<height>\d+(\.\d+)?)\s*(x|×)\s*(?P<width>\d+(\.\d+)?)\s*cm\s*\(.*\)'
                    regex_3d = u'.*\((?P<height>\d+(\.\d+)?) (x|×) (?P<width>\d+(\.\d+)?) (x|×) (?P<depth>\d+(\.\d+)?) cm\)'
                    match_2d = re.match(regex_2d, dimensiontext)
                    match_3d = re.match(regex_3d, dimensiontext)
                    if match_2d:
                        metadata['heightcm'] = match_2d.group(u'height')
                        metadata['widthcm'] = match_2d.group(u'width')
                    elif match_3d:
                        metadata['heightcm'] = match_3d.group(u'height')
                        metadata['widthcm'] = match_3d.group(u'width')
                        metadata['depthcm'] = match_3d.group(u'depth')
                # On https://www.mfa.org/collections/object/download they indicate public domain images are for download
                downloadregex = u'\<li\><a  href\=\"\/collections\/object\/download\/\d+\" class\=\"action\"\>Download\<\/a\>\<\/li\>'
                imageurlregex = u'\<div class\=\"image fix-height zoom-viewport\"\>[\r\n\t\s]*\<div class\=\"zoom\"\>[\r\n\t\s]*\<img src\=\"([^\"]+)\" alt\=\"\" title\=\"\" class\=\"image-aspect'
                downloadmatch = re.search(downloadregex, itemData)
                imageurlmatch = re.search(imageurlregex, itemData)

                if downloadmatch and imageurlmatch:
                    metadata[u'imageurl'] = imageurlmatch.group(1)
                    metadata[u'imageurlformat'] = u'Q2195' #JPEG
                    # Could use this later to force
                    metadata[u'imageurlforce'] = False
                yield metadata

            print (u'Excepted %s items, got %s items' % ((i+1) * 18, n))

def main():
    dictGen = getMFAGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
