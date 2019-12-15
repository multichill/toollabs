#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Saint Louis Art Museum to Wikidata.

Just loop over pages like https://www.slam.org/wp-json/slam/v1/objects/?se=&paged=2&show_on_view=true&classification=paintings

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getSLAMmGenerator():
    """
    Generator to return Georgia Museum of Art paintings. One API call returns all the paintings
    """
    searchurl = u'https://www.slam.org/wp-json/slam/v1/objects/?se=&paged=20&show_on_view=false&classification=paintings&current_pg=40'
    # Really? You're throwing a 403 at me?
    headers = { 'User-Agent' : 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0' }
    session = requests.Session()
    session.headers.update(headers)
    searchPage = session.get(searchurl)
    searchJson = searchPage.json()
    htmlparser = HTMLParser()


    for itemjson in searchJson:

        metadata = {}
        url = itemjson.get(u'url')
        metadata['url'] = url

        itempage = session.get(url)
        pywikibot.output(url)

        metadata['collectionqid'] = u'Q1760539'
        metadata['collectionshort'] = u'SLAM'
        metadata['locationqid'] = u'Q1760539'

        #No need to check, I'm actually searching for paintings.
        metadata['instanceofqid'] = u'Q3305213'

        metadata['idpid'] = u'P217'

        invregex = u'\<dt class\=\"label label--no-spacing\"\>Object Number\<\/dt\>[\s\t\r\n]*\<dd\>([^\<]+)\<\/dd\>'
        invmatch = re.search(invregex, itempage.text)
        # Not sure if I need to replace space here
        metadata['id'] = htmlparser.unescape(invmatch.group(1).replace(u'&nbsp;', u' ')).strip()

        title = itemjson.get(u'title')

        # Chop chop, several very long titles
        if len(title) > 220:
            title = title[0:200]
        metadata['title'] = { u'en' : title,
                              }
        creatorname = itemjson.get(u'artist')

        metadata['creatorname'] = creatorname

        metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                    u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                    u'de' : u'%s von %s' % (u'Gemälde', metadata.get('creatorname'), ),
                                    u'fr' : u'%s de %s' % (u'peinture', metadata.get('creatorname'), ),
                                    }


        # Let's see if we can extract some dates. Json-ld is provided, but doesn't have circa and the likes
        dateregex = u'^(\d\d\d\d)$'
        datecircaregex = u'^c\.\s*(\d\d\d\d)$'
        periodregex = u'^(\d\d\d\d)–(\d\d\d\d)$'
        circaperiodregex = u'^c\.\s*(\d\d\d\d)–(\d\d\d\d)$'
        shortperiodregex = u'^(\d\d)(\d\d)–(\d\d)$'
        circashortperiodregex = u'^c\.\s*(\d\d)(\d\d)–(\d\d)$'

        datematch = re.match(dateregex, itemjson.get(u'dateCreated'))
        datecircamatch = re.match(datecircaregex, itemjson.get(u'dateCreated'))
        periodmatch = re.match(periodregex, itemjson.get(u'dateCreated'))
        circaperiodmatch = re.match(circaperiodregex, itemjson.get(u'dateCreated'))
        shortperiodmatch = re.match(shortperiodregex, itemjson.get(u'dateCreated'))
        circashortperiodmatch = re.match(circashortperiodregex, itemjson.get(u'dateCreated'))

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
            metadata['inceptionstart'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(2),))
            metadata['inceptionend'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(3),))
        elif circashortperiodmatch:
            metadata['inceptionstart'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(2),))
            metadata['inceptionend'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(3),))
            metadata['inceptioncirca'] = True
        else:
            print (u'Could not parse date: "%s"' % (itemjson.get(u'dateCreated'),))
            print (u'Could not parse date: "%s"' % (itemjson.get(u'dateCreated'),))
            print (u'Could not parse date: "%s"' % (itemjson.get(u'dateCreated'),))
            print (u'Could not parse date: "%s"' % (itemjson.get(u'dateCreated'),))
            print (u'Could not parse date: "%s"' % (itemjson.get(u'dateCreated'),))

        # Looks they got a lot of provenance data, but not in a suitable format.

        mediumregex = u'\<dt class\=\"label label--no-spacing\"\>Material\<\/dt\>[\s\t\r\n]*\<dd\>Oil on canvas\<\/dd\>'
        mediummatch = re.search(mediumregex, itempage.text)
        if mediummatch:
            metadata['medium'] = u'oil on canvas'

        ## Dimensions are messy and in inches + cm
        #measurementsregex = u'\<span class\=\"detailFieldLabel\"\>Dimensions\:\<\/span\>\<span class\=\"detailFieldValue\"\>\<div\>Sight\:[^\<]+in\.\s*\(([^\(]+)\)\<\/div\>'
        #measurementsmatch = re.search(measurementsregex, itempage.text)
        #if measurementsmatch:
        #    measurementstext = measurementsmatch.group(1)
        #    regex_2d = u'^(?P<height>\d+(\.\d+)?)\s*×\s*(?P<width>\d+(\.\d+)?)\s*cm$'
        #    match_2d = re.match(regex_2d, measurementstext)
        #    if match_2d:
        #        metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
        #        metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')

        # They provide free images and clear indication of what is in the public domain
        pdregex = u'\<dt class\=\"label label--no-spacing\"\>Rights\<\/dt\>[\s\t\r\n]*\<dd\>\<a href\=\"https\:\/\/www\.slam\.org\/public-domain-and-open-access\/\"\>Public Domain\<\/a\>\<\/dd\>'
        pdmatch = re.search(pdregex, itempage.text)

        imageregex = u'\<a href\=\"([^\"]+)\" class\=\"viewer-btn\" target=\"_blank\" title=\"Download\"\>'
        imagematch = re.search(imageregex, itempage.text)

        if pdmatch and imagematch:
            metadata[u'imageurl'] = htmlparser.unescape(imagematch.group(1))
            metadata[u'imageurlformat'] = u'Q2195' #JPEG
            metadata[u'imageoperatedby'] = u'Q1760539'
            # Used this to add suggestions everywhere
            metadata[u'imageurlforce'] = True

        yield metadata


def main():
    dictGen = getSLAMmGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
