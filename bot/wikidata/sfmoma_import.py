#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from SFMOMA

* Loop over https://www.sfmoma.org/search/?type=artwork&q=&page=1&classification=painting (1-63)
* Grab individual paintings like https://www.sfmoma.org/artwork/62.19

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re
try:
    from html.parser import HTMLParser
except ImportError:
    import HTMLParser

def getSFMOMAGenerator():
    """
    Generator to return SFMOMA paintings
    
    """
    htmlparser = HTMLParser()

    baseSearchUrl = u'https://www.sfmoma.org/search/?type=artwork&q=&page=%s&classification=painting'
    for i in range(1, 64):
        searchUrl = baseSearchUrl % (i,)
        print(searchUrl)
        searchPage = requests.get(searchUrl)
        searchPageData = searchPage.text
        searchRegex = u'\<a href\=\"\/artwork\/([^\"]+)\"'

        for match in re.finditer(searchRegex, searchPageData):

            url = u'https://www.sfmoma.org/artwork/%s' % (match.group(1),)
            print (url)
            metadata = {}

            metadata['collectionqid'] = u'Q913672'
            metadata['collectionshort'] = u'SFMOMA'
            metadata['locationqid'] = u'Q913672'

            # Search is for paintings
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'
            metadata['id'] = match.group(1)
            
            metadata['url'] = url

            itemPage = requests.get(url)
            itemPageData = itemPage.text

            titleRegex = u'\<dt\>Artwork title\<\/dt\>[\r\n\t\s]*\<dd\>\<em\>([^\<]+)\<'
            
            matchTitle = re.search(titleRegex, itemPageData)
            if not matchTitle:
                titleRegex = u'\<dt\>Artwork title\<\/dt\>[\r\n\t\s]*\<dd\>\<em\>\<span class\=\"noItalics\"\>([^\<]+)\<'
                matchTitle = re.search(titleRegex, itemPageData)

            metadata['title'] = { u'en' : htmlparser.unescape(matchTitle.group(1)),
                                }
            creatorRegex = u'\<dt\>Artist name\<\/dt\>[\r\n\t\s]*\<dd\>\<a href\=\"[^\"]*\">([^\<]+)\<\/a\>\<\/dd\>'

            creatorMatch = re.search(creatorRegex, itemPageData)
            if not creatorMatch:
                creatorRegex = u'\<dt\>Artist names\<\/dt\>[\r\n\t\s]*\<dd\>\<a href\=\"[^\"]*\">([^\<]+)\<\/a\>'
                creatorMatch = re.search(creatorRegex, itemPageData)

            if creatorMatch:
                metadata['creatorname'] = htmlparser.unescape(creatorMatch.group(1))
            else:
                metadata['creatorname'] = u'anonymous'

            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }

            dateRegex = u'\<dt\>Date created\<\/dt\>[\r\n\t\s]*\<dd class\=\"no-fractions\"\>(\d\d\d\d)\<\/dd\>'
            dateMatch = re.search(dateRegex, itemPageData)
            if dateMatch:
                metadata['inception'] = dateMatch.group(1)

            acquisitiondateRegex = u'\<dt\>Date acquired\<\/dt\>[\r\n\t\s]*\<dd\>(\d\d\d\d)\<\/dd\>'
            acquisitiondateMatch = re.search(acquisitiondateRegex, itemPageData)
            if acquisitiondateMatch:
                metadata['acquisitiondate'] = acquisitiondateMatch.group(1)

            mediumRegex = u'\<dt\>Medium\<\/dt\>[\r\n\t\s]*\<dd\>([^\<]+)\<\/dd\>'
            mediumMatch = re.search(mediumRegex, itemPageData)

            if mediumMatch and mediumMatch.group(1).strip().lower()==u'oil on canvas':
                metadata['medium'] = u'oil on canvas'

            dimensionRegex = u'\<dt\>Dimensions\<\/dt\>[\r\n\t\s]*\<dd\>([^\<]+)\<\/dd\>'
            dimensionMatch = re.search(dimensionRegex, itemPageData)

            if dimensionMatch:
                dimensiontext = dimensionMatch.group(1).strip()
                regex_2d = u'^.+\((?P<height>\d+(\.\d+)?)\s*(cm\s*)?(x|×)\s*(?P<width>\d+(\.\d+)?)\s*cm\)$'
                regex_3d = u'^.+\((?P<height>\d+(\.\d+)?)\s*(cm\s*)?(x|×)\s*(?P<width>\d+(\.\d+)?)\s*(cm\s*)?(x|×)\s*(?P<depth>\d+(\.\d+)?)\s*cm\)$'
                match_2d = re.match(regex_2d, dimensiontext)
                match_3d = re.match(regex_3d, dimensiontext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height')
                    metadata['widthcm'] = match_2d.group(u'width')
                if match_3d:
                    metadata['heightcm'] = match_3d.group(u'height')
                    metadata['widthcm'] = match_3d.group(u'width')
                    metadata['depthcm'] = match_3d.group(u'depth')

            # Image use policy unclear and most (if not all) in copyright
            #imageMatch = re.search(imageregex, itemPageData)
            #if imageMatch:
            #    metadata[u'imageurl'] = imageMatch.group(1)
            #    metadata[u'imageurlformat'] = u'Q2195' #JPEG

            yield metadata


def main():
    dictGen = getSFMOMAGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
