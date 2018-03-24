#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from the Museum of Fine Arts, Budapest (Szépművészeti Múzeum)

* Loop over http://www.szepmuveszeti.hu/lista_eng?classification=68&only_pictures=on (only_pictures is turned around)
* Grab individual paintings like http://www.szepmuveszeti.hu/adatlap_eng/portrait_of_man_frans_9237
* Also grab the Hungarian title at http://www.szepmuveszeti.hu/adatlap/9237

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

def getMFABudapestGenerator():
    """
    Generator to return Museum of Fine Arts, Budapest (Szépművészeti Múzeum) paintings
    
    """
    htmlparser = HTMLParser()
    baseSearchUrl = u'http://www.szepmuveszeti.hu/lista_eng?ajax=1&block=gyujtemeny_oldal_doboz_eng&classification%%5B%%5D=68&page=%s&search_text=&only_pictures=on&style=grid-text&search_inventory_number='

    for i in range(1, 102):
        searchUrl = baseSearchUrl % (i,)
        print (searchUrl)

        searchPage = requests.get(searchUrl)
        searchPageData = searchPage.text
        searchRegex = u'\<a class\=\"mutargy_megtekintese\" href\=\"\/adatlap_eng\/([^\"]+)_(\d+)\"\>([^\<]+)\<\/a\>'

        for match in re.finditer(searchRegex, searchPageData):
            url = u'http://www.szepmuveszeti.hu/adatlap_eng/%s_%s' % (match.group(1),match.group(2))
            url_hu = u'http://www.szepmuveszeti.hu/adatlap/%s_%s' % (match.group(1),match.group(2))
            #title = htmlparser.unescape(match.group(3))

            print (url)

            itemPage = requests.get(url)
            itemPageData = itemPage.text

            itemPageHu = requests.get(url_hu)
            itemPageHuData = itemPageHu.text

            metadata = {}
            metadata['url'] = url

            metadata['collectionqid'] = u'Q840886'
            metadata['collectionshort'] = u'Szépművészeti'
            metadata['locationqid'] = u'Q840886'

            # Search is for paintings
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'
            invRegex = u'\<td\>Inventory Number\:\<\/td\>[\r\n\t\s]*\<td\>([^\<]+)\<\/td\>'
            invMatch = re.search(invRegex, itemPageData)
            metadata['id'] = invMatch.group(1).strip()

            titleRegex = u'\<td colspan\=\"2\"\>[\r\n\t\s]*\<h1\>([^\<]+)\<\/h1\>'

            titleMatch = re.search(titleRegex, itemPageData)
            titleHuMatch = re.search(titleRegex, itemPageHuData)

            title = htmlparser.unescape(titleMatch.group(1)).strip()
            title_hu = htmlparser.unescape(titleHuMatch.group(1)).strip()
            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            if len(title_hu) > 220:
                title_hu = title_hu[0:200]
            metadata['title'] = { u'en' : title,
                                  u'hu' : title_hu,
                              }

            artistRegex = u'\<td\>[\r\n\t\s]*Artist\:[\r\n\t\s]*\<\/td\>[\r\n\t\s]*\<td\>[\r\n\t\s]*([^\<]+)[\r\n\t\s]*\<br \/\>'
            artistMatch = re.search(artistRegex, itemPageData)

            name = htmlparser.unescape(artistMatch.group(1)).strip()

            metadata['creatorname'] = name
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }

            # Only match on years
            dateRegex = u'\<td\>Date\:\s*\<\/td\>[\r\n\t\s]*\<td\>\s*(\d\d\d\d)\s*\<\/td\>'
            dateMatch = re.search(dateRegex, itemPageData)
            if dateMatch:
                metadata['inception'] = htmlparser.unescape(dateMatch.group(1))

            # acquisitiondate not available
            # acquisitiondateRegex = u'\<em\>Acknowledgement\<\/em\>\:\s*.+(\d\d\d\d)[\r\n\t\s]*\<br\>'
            #acquisitiondateMatch = re.search(acquisitiondateRegex, itemPageData)
            #if acquisitiondateMatch:
            #    metadata['acquisitiondate'] = acquisitiondateMatch.group(1)

            mediumRegex = u'\<td\>Medium\:\<\/td\>[\r\n\t\s]*\<td\>oil on canvas\<\/td\>'
            mediumMatch = re.search(mediumRegex, itemPageData)

            if mediumMatch:
                metadata['medium'] = u'oil on canvas'


            dimensionRegex = u'\<td\>Dimensions\:\<\/td\>[\r\n\t\s]*\<td\>([^\<]+)\<\/td\>'
            dimensionMatch = re.search(dimensionRegex, itemPageData)

            if dimensionMatch:
                dimensiontext = dimensionMatch.group(1).strip()
                regex_2d = u'^(?P<height>\d+(\.\d+)?)\s*(x|×)\s*(?P<width>\d+(\.\d+)?)\s*cm.*$'
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
    dictGen = getMFABudapestGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
