#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from the Hungarian National Gallery (Magyar Nemzeti Galéria)

* Loop over http://mng.hu/collection/p/1?kereses=painting
* Grab individual paintings like http://mng.hu/collection/gipsy-bride-2534
* Grab the Hungarian title from pages like http://mng.hu/gyujtemeny/gipsy-bride-2534

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
    baseSearchUrl = u'http://mng.hu/collection/p/%s?kereses=painting'

    for i in range(1, 50):
        searchUrl = baseSearchUrl % (i,)
        print (searchUrl)

        searchPage = requests.get(searchUrl)
        searchPageData = searchPage.text
        searchRegex = u'\<div class\=\"gallery-item col-result\" data-url\=\"\/collection\/([^\"]+)\"'

        for match in re.finditer(searchRegex, searchPageData):
            url = u'http://mng.hu/collection/%s' % (match.group(1),)
            url_hu = u'http://mng.hu/gyujtemeny/%s' % (match.group(1),)

            print (url)

            itemPage = requests.get(url)
            itemPageData = itemPage.text

            itemPageHu = requests.get(url_hu)
            itemPageHuData = itemPageHu.text

            metadata = {}
            metadata['url'] = url

            metadata['collectionqid'] = u'Q252071'
            metadata['collectionshort'] = u'MNG'
            metadata['locationqid'] = u'Q252071'

            # Search is for paintings
            metadata['instanceofqid'] = u'Q3305213'

            titleRegex = u'\<meta name\=\"og\:title\" content\=\"([^\"]+)\"\s*\>'
            titleMatch = re.search(titleRegex, itemPageData)
            titleHuMatch = re.search(titleRegex, itemPageHuData)

            if titleMatch:
                title = htmlparser.unescape(titleMatch.group(1)).strip()
            else:
                title = u'(without title)'

            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                              }

            # Also add the Hungarian title
            if titleHuMatch:
                title_hu = htmlparser.unescape(titleHuMatch.group(1)).strip()
                # Chop chop, several very long titles
                if len(title_hu) > 220:
                    title_hu = title_hu[0:200]
                metadata['title'][u'hu'] = title_hu

            metadata['idpid'] = u'P217'
            invRegex = u'\<td class\=\"data-label\"\>accession number\:\<\/td\>[\r\n\t\s]*\<td\>([^\<]+)\<\/td\>'
            invMatch = re.search(invRegex, itemPageData)
            metadata['id'] = invMatch.group(1).strip()


            artistRegex = u'\<td class\=\"data-label\"\>artist\:\<\/td\>[\r\n\t\s]*\<td\>[\r\n\t\s]*([^\<]+)\<br\>'
            artistMatch = re.search(artistRegex, itemPageData)

            if artistMatch:
                name = htmlparser.unescape(artistMatch.group(1)).strip()
            else:
                name = u'anonymous'
            metadata['creatorname'] = name
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }

            # Only match on years
            dateRegex = u'\<td class\=\"data-label\"\>date\:\<\/td\>[\r\n\t\s]*\<td\>(\d\d\d\d)\s*\<\/td\>'
            dateMatch = re.search(dateRegex, itemPageData)
            if dateMatch:
                metadata['inception'] = htmlparser.unescape(dateMatch.group(1))

            # acquisitiondate not available
            # acquisitiondateRegex = u'\<em\>Acknowledgement\<\/em\>\:\s*.+(\d\d\d\d)[\r\n\t\s]*\<br\>'
            #acquisitiondateMatch = re.search(acquisitiondateRegex, itemPageData)
            #if acquisitiondateMatch:
            #    metadata['acquisitiondate'] = acquisitiondateMatch.group(1)

            mediumRegex = u'data-type-value\=\"technika\"\>oil, canvas\<\/a\>\<\/td\>'
            mediumMatch = re.search(mediumRegex, itemPageData)

            if mediumMatch:
                metadata['medium'] = u'oil on canvas'

            dimensionRegex = u'\<td class\=\"data-label\"\>size\:\<\/td\>[\r\n\t\s]*\<td\>([^\<]+)\<'
            dimensionMatch = re.search(dimensionRegex, itemPageData)

            if dimensionMatch:
                dimensiontext = dimensionMatch.group(1).strip()
                regex_2d = u'^(?P<height>\d+(\.\d+)?)\s*(x|×)\s*(?P<width>\d+(\.\d+)?)\s*cm$'
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


def main():
    dictGen = getMNGGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
