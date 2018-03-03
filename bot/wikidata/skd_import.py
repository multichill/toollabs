#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from the Staatliche Kunstsammlungen Dresden

* Loop over https://skd-online-collection.skd.museum/Home/Index?page=1&tIds=2891,2700,2870,2854,2889
* Grab individual paintings like https://skd-online-collection.skd.museum/Details/Index/515978

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

def getSKDGenerator():
    """
    Generator to return Staatliche Kunstsammlungen Dresden paintings
    
    """
    htmlparser = HTMLParser()

    # No watercolors
    baseSearchUrl = u'https://skd-online-collection.skd.museum/Home/Index?page=%s&tIds=2891,2700,2870,2854,2889'
    for i in range(1, 317):
        searchUrl = baseSearchUrl % (i,)
        print(searchUrl)
        searchPage = requests.get(searchUrl)
        searchPageData = searchPage.text
        searchRegex = u'\<a href\=\"\/Details\/Index\/([^\"]+)\"\>'

        idlist = []

        for match in re.finditer(searchRegex, searchPageData):
            idlist.append(match.group(1))

        for pageid in list(set(idlist)):
            url = u'https://skd-online-collection.skd.museum/Details/Index/%s' % (pageid,)
            print (url)
            metadata = {}

            metadata['collectionqid'] = u'Q653002'
            metadata['collectionshort'] = u'SKD'
            # Search is for paintings
            metadata['instanceofqid'] = u'Q3305213'

            metadata['url'] = url

            itemPage = requests.get(url)
            itemPageData = itemPage.text

            titleRegex = u'\<div class\=\"skd-module-text detail-module-text\"\>[\r\n\t\s]*\<h2\>([^\<]+)\<\/h2\>'
            
            matchTitle = re.search(titleRegex, itemPageData)
            #if not matchTitle:
            #    titleRegex = u'\<dt\>Artwork title\<\/dt\>[\r\n\t\s]*\<dd\>\<em\>\<span class\=\"noItalics\"\>([^\<]+)\<'
            #    matchTitle = re.search(titleRegex, itemPageData)

            metadata['title'] = { u'de' : htmlparser.unescape(matchTitle.group(1).strip()),
                                }

            creatorRegex = u'\<a href\=\"\/Home\/Index\?page\=1\&pId\=\d+\"\>([^\<]+)\<span\>\s*\|\s*(Maler|Autor|K\&\#xFC\;nstler)\<\/span\>\<\/a\>'

            creatorMatch = re.search(creatorRegex, itemPageData)
            #if not creatorMatch:
            #    creatorRegex = u'\<dt\>Artist names\<\/dt\>[\r\n\t\s]*\<dd\>\<a href\=\"[^\"]*\">([^\<]+)\<\/a\>'
            #    creatorMatch = re.search(creatorRegex, itemPageData)

            if creatorMatch:
                name = htmlparser.unescape(creatorMatch.group(1).strip())
                print (u'Before name: %s' % (name,))
                # Handle a couple of cases otherwise just fallback to what we got
                cregexes = [(u'^unbekannt$', u'anonymous'),
                            (u'^([^,]+) \([^\)]*\d+[^\)]\d+\)$', u'\\1'),
                            (u'^(.+), (.+) \(\d\d\d\d-\)$', u'\\2 \\1'),
                            (u'^(.+), (.+) \([^\)]*\d+[^\)]\d+\)$', u'\\2 \\1'),
                            (u'^([^,]+) \([^\)]*\d+[^\)]\d+\)\s*(Kopie nach|Nachfolger|Schule|Werkstatt|zugeschrieben)$', u'\\2 \\1'),
                            (u'^(.+), (.+) \([^\)]*\d+[^\)]\d+\)\s*(Kopie nach|Nachfolger|Schule|Werkstatt|zugeschrieben)$', u'\\3 \\2 \\1'),]

                for (regex, replace) in cregexes:
                    if re.match(regex, name):
                        name = re.sub(regex, replace, name)
                        print (u'After name: %s' % (name,))
                        break
                metadata['creatorname'] = name
            else:
                metadata['creatorname'] = u'anonymous (not found in metadata)'

            # Set the creator qid to anonymous in these cases
            if metadata['creatorname'] == u'anonymous' or metadata['creatorname'].startswith(u'Kopie nach ') or \
                    metadata['creatorname'].startswith(u'Nachfolger ') or \
                    metadata['creatorname'].startswith(u'Schule ') or \
                    metadata['creatorname'].startswith(u'Werkstatt '):
                metadata['creatorqid'] = u'Q4233718'

            # Customized description if the creator is completely unknown
            if metadata['creatorname'] == u'anonymous':
                metadata['description'] = { u'de' : u'Gemälde von unbekannt',
                                            u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
            else:
                metadata['description'] = { u'de' : u'%s von %s' % (u'Gemälde', metadata.get('creatorname'),),
                                            u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            }
            # https://skd-online-collection.skd.museum/Home/Index?page=1&sId=1
            locations = { 1 : u'Q4890', # Gemäldegalerie Alte Meister
                          2 : u'Q472706', #  Galerie Neue Meister
                          3 : u'Q707407', # Grünes Gewölbe
                          4 : u'Q50320660', # Kunstfonds
                          5 : u'Q1331753', # Kunstgewerbemuseum
                          6 : u'Q570620', # Kupferstich-Kabinett
                          7 : u'Q321088', # Mathematisch-Physikalischer Salon
                          8 : u'Q324263', # Münzkabinett
                          9 : u'Q1305061', # Museum für Sächsische Volkskunst
                          10 : u'Q1754671', # Puppentheatersammlung
                          11 : u'Q473848', # Porzellansammlung
                          12 : u'Q571773', # Rüstkammer
                          13 : u'Q869690', # Skulpturensammlung
                          }


            locationRegex = u'\<span class\=\"skd-headline-roof\"\>Museum\<\/span\>[\r\n\t\s]*\<\/div\>[\r\n\t\s]*\<div class\=\"col-xs-12 col-sm-8\"\>[\r\n\t\s]*\<span\>\<a href\=\"\/Home\/Index\?page\=1\&sId\=(\d\d?)\"\>'
            locationMatch = re.search(locationRegex, itemPageData)

            metadata['locationqid'] = locations.get(int(locationMatch.group(1)))

            invRegex = u'\<span class\=\"skd-headline-roof\"\>Inventarnummer\<\/span\>[\r\n\t\s]*\<\/div\>[\r\n\t\s]*\<div class\=\"col-xs-12 col-sm-8\"\>[\r\n\t\s]*\<span\>([^\<]+)\<\/span\>'
            invMatch = re.search(invRegex, itemPageData)
            metadata['id'] = invMatch.group(1).strip()
            metadata['idpid'] = u'P217'


            dateRegex = u'\<span class\=\"skd-headline-roof\"\>Datum\<\/span\>[\r\n\t\s]*\<\/div\>[\r\n\t\s]*\<div class\=\"col-xs-12 col-sm-8\"\>[\r\n\t\s]*\<span\>\<a href\=\"\/Home\/Index\?page=1&dVon\=(\d\d\d\d)\&dBis\=(\d\d\d\d)\"\>'
            dateMatch = re.search(dateRegex, itemPageData)
            if dateMatch and dateMatch.group(1)==dateMatch.group(2):
                metadata['inception'] = dateMatch.group(1)

            # acquisition date is not available
            #metadata['acquisitiondate'] = acquisitiondateMatch.group(1)

            mediumRegex = u'\<span class\=\"skd-headline-roof\"\>Material und Technik\<\/span\>[\r\n\t\s]*\<\/div\>[\r\n\t\s]*\<div class\=\"col-xs-12 col-sm-8\"\>[\r\n\t\s]*\<span\>\<a href\=\"\/Home\/Index\?page\=1\&q\=([^\"]+)\"\>'
            mediumMatch = re.search(mediumRegex, itemPageData)

            if mediumMatch and mediumMatch.group(1).strip()==u'%C3%96l%20auf%20Leinwand':
                metadata['medium'] = u'oil on canvas'

            dimensionRegex = u'\<span class\=\"skd-headline-roof\"\>Abmessungen\<\/span\>[\r\n\t\s]*\<\/div\>[\r\n\t\s]*\<div class\=\"col-xs-12 col-sm-8\"\>[\r\n\t\s]*\<span\>([^\<]+)\<\/span\>'
            dimensionMatch = re.search(dimensionRegex, itemPageData)

            if dimensionMatch:
                dimensiontext = dimensionMatch.group(1).strip()
                regex_2d = u'^(?P<height>\d+(,\d+)?)\s*(cm\s*)?(x|×)\s*(?P<width>\d+(,\d+)?)\s*cm$'
                regex_3d = u'^(?P<height>\d+(,\d+)?)\s*(cm\s*)?(x|×)\s*(?P<width>\d+(,\d+)?)\s*(cm\s*)?(x|×)\s*(?P<depth>\d+(,\d+)?)\s*cm$'
                match_2d = re.match(regex_2d, dimensiontext)
                match_3d = re.match(regex_3d, dimensiontext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')
                if match_3d:
                    metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
                    metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')

            # Image use policy unclear and most (if not all) in copyright
            #imageMatch = re.search(imageregex, itemPageData)
            #if imageMatch:
            #    metadata[u'imageurl'] = imageMatch.group(1)
            #    metadata[u'imageurlformat'] = u'Q2195' #JPEG
            yield metadata


def main():
    dictGen = getSKDGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
