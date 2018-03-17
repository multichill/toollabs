#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from the National Gallery of Australia

* Loop over https://artsearch.nga.gov.au/search.cfm?mystartrow=961&realstartrow=961&order%5Fselect=1&showrows=20&view%5Fselect=4&media=18
* Grab individual paintings like https://artsearch.nga.gov.au/detail.cfm?irn=141092

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

def getNGAGenerator():
    """
    Generator to return NGA paintings
    
    """
    htmlparser = HTMLParser()
    session = requests.session()

    perpage = 1000

    baseSearchUrl = u'https://artsearch.nga.gov.au/search.cfm?mystartrow=%s&realstartrow=%s&order_select=1&showrows=%s&view_select=4&media=18'
    # LOL, no limit. Just give me everything!
    #searchUrl = u'https://artsearch.nga.gov.au/search.cfm?mystartrow=1&realstartrow=1&order_select=1&showrows=7000&view_select=4&media=18'
    #for i in range(1, 64):
        #searchUrl = baseSearchUrl % (i,)
        #print(searchUrl)
    j = 0

    for i in range(1, 7000, perpage):
        searchUrl = baseSearchUrl % (i,i,perpage)
        print (searchUrl)
        # Mate, you don't like my default agent? I can just send you another one
        searchPage = requests.get(searchUrl, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36'})
        searchPageData = searchPage.text
        searchRegex = u'\<a href\=\"detail\.cfm\?irn\=(?P<irn>\d+)\" title\=\"[^\"]+\"\>[\r\n\t\s]*\<ul id\=\"LISTC\"\>[\r\n\t\s]*\<li class\=\"(?P<hasimage>[^\"]+)\"\>\&nbsp\;\<\/li\>[\r\n\t\s]*\<li class\=\"ARTIST\"\>[\r\n\t\s]*(?P<artist>[^\r\n]+)(?P<artistmeuk>[^\<])*\<\/li\>[\r\n\t\s]*\<li class\=\"WTITLE\"\>(?P<title>[^\<]+)\<\/li\>[\r\n\t\s]*\<li class\=\"EDITION\"\>(?P<edition>[^\<]*)\<\/li\>[\r\n\t\s]*\<li class\=\"CREDATE\"\>(?P<inception>[^\<]*)\<\/li\>[\r\n\t\s]*\<li class\=\"MEDIA\"\>(?P<media>[^\<]*)\<\/li\>[\r\n\t\s]*\<li class\=\"COLLECT\"\>(?P<culture>[^\<]*)\<\/li\>[\r\n\t\s]*\<li class\=\"ACCN\"\>(?P<inv>[^\<]+)\<\/li\>[\r\n\t\s]*\<\/ul\>'


        for match in re.finditer(searchRegex, searchPageData,flags=re.I):
            j = j + 1
            url = u'https://artsearch.nga.gov.au/detail.cfm?irn=%s' % (match.group(u'irn'),)
            print (url)
            metadata = {}
            metadata['url'] = url

            metadata['collectionqid'] = u'Q795228'
            metadata['collectionshort'] = u'NGA'
            metadata['locationqid'] = u'Q795228'

            # Search is for paintings
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'
            metadata['id'] = u'NGA %s' % (match.group(u'inv'),)

            title = htmlparser.unescape(match.group(u'title'))
            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                              }

            if not match.group(u'artist'):
                metadata['creatorqid'] = u'Q4233718'
                metadata['creatorname'] = u'anonymous'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
            else:
                name = htmlparser.unescape(match.group(u'artist')).strip()
                if name==u'':
                    metadata['creatorqid'] = u'Q4233718'
                    metadata['creatorname'] = u'anonymous'
                    metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                                u'en' : u'painting by anonymous painter',
                                                }
                else:
                    if u',' in name:
                        (surname, sep, firstname) = name.partition(u',')
                        name = u'%s %s' % (firstname.strip(), surname.strip().capitalize(),)
                    else:
                        name = name.capitalize()
                    metadata['creatorname'] = name
                    metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                                u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                                }

            if match.group(u'inception'):
                metadata['inception'] = htmlparser.unescape(match.group(u'inception'))


        # This was enough basic info. In the second pass I can grab more data

        #itemPage = requests.get(url)
        #itemPageData = itemPage.text
            """




            dateRegex = u'\<dt\>Date created\<\/dt\>[\r\n\t\s]*\<dd class\=\"no-fractions\"\>(\d\d\d\d)\<\/dd\>'
            dateMatch = re.search(dateRegex, itemPageData)
            if dateMatch:


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
            """
            yield metadata
    print (j)


def main():
    dictGen = getNGAGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
