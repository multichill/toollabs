#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the  Bavarian State Painting Collections (Q812285)  to Wikidata.

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import HTMLParser
import os
import json
import logging

def getBavarianGenerator():
    """
    Generator to return bavarian State Painting Collections paintings

    https://www.sammlung.pinakothek.de/de/genre/malerei#filters={%22genre%22:%22malerei%22}

    Problem is that over 200 pages will return server errors. So have to work on different subsets.

    """
    basesearchurl = u'https://www.sammlung.pinakothek.de/api/search?&page=%s&filters={"genre":"malerei"}'
    #basesearchurl = u'https://www.sammlung.pinakothek.de/api/search?&page=%s&filters={"yearRange":{"min":1900,"max":2100},"genre":"malerei"}'
    #basesearchurl = u'https://www.sammlung.pinakothek.de/api/search?&page=%s&filters={"publicDomain":true,"genre":"malerei"}'
    #basesearchurl = u'https://www.sammlung.pinakothek.de/api/search?&page=%s&filters={"onDisplay":true,"genre":"malerei"}'
    # For the image upload
    #basesearchurl = u'https://www.sammlung.pinakothek.de/api/search?&page=%s&filters={"genre":"malerei","publicDomain":true}' # 1- 185
    #basesearchurl = u'https://www.sammlung.pinakothek.de/api/search?&page=%s&filters={"publicDomain":true,"genre":"malerei"}'
    origin = u'https://www.sammlung.pinakothek.de'
    referer = u'https://www.sammlung.pinakothek.de/de/genre/malerei'

    #logging.basicConfig()
    #logging.getLogger().setLevel(logging.DEBUG)
    #requests_log = logging.getLogger("requests.packages.urllib3")
    #requests_log.setLevel(logging.DEBUG)
    #requests_log.propagate = True

    htmlparser = HTMLParser.HTMLParser()

    # Not sure what is wrong with the website, but HTTPS setup is really slow and getting the wrong certificate
    # Just put everything in one session to not have to do that each time
    session = requests.Session()

    # Just loop over the pages
    for i in range(1, 200):
        print i
        searchurl = basesearchurl % (i,)
        print searchurl
        searchPage = session.get(searchurl, headers={'X-Requested-With' : 'XMLHttpRequest',
                                                      'referer' : referer,
                                                      'origin' : origin,
                                                      },verify=False) # For some reason I'm getting certificate errors?
                                                      #'origin' : origin} )
        #print searchPage.text
        searchJson = searchPage.json()
        for record in searchJson.get('items'):
            metadata = {}
            # ID is not the inventory number!
            url = record.get(u'url').replace(u'sammlung.pinakothek.de/de/artist/', u'sammlung.pinakothek.de/en/artist/')
            print url
            itempage = session.get(url, verify=False)
            metadata['url'] = url

            metadata['collectionqid'] = u'Q812285'
            metadata['collectionshort'] = u'BStGS'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            # Figure this part out, this seems to give a scaled image
            #if record.get(u'imageAvailable')==u'available' and record.get(u'image'):
            #    if record.get(u'image').get(u'url'):
            #        metadata['imageurl'] = record.get(u'image').get(u'url')

            titleregex = u'\<h1 class\=\"artwork__title\"\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/h1\>'
            titlematch = re.search(titleregex, itempage.text)
            if not titlematch:
                print(u'No title found, probably something went wrong. Skipping and sleeping for 2 minutes')
                time.sleep(120)
                continue
            title = htmlparser.unescape(titlematch.group(1).strip()) # This didn't work and included attributed to junk: record.get('title')

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]

            metadata['title'] = { u'de' : title,
                                  }

            #  record.get('artistInfo').get('fullName') didn't include the attribution part
            creatorregex = u'\<div class\=\"label-header\"\>[\s\t\r\n]*Artist[\s\t\r\n]*\<\/div\>[\s\t\r\n]*\<a href\=\"[^\"]+\"\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/a\>[\s\t\r\n]*\<\/div\>'
            creatormatch = re.search(creatorregex, itempage.text)
            metadata['creatorname'] = htmlparser.unescape(creatormatch.group(1).strip())

            metadata['description'] = { u'de' : u'%s von %s' % (u'Gemälde', metadata.get('creatorname'),),
                                        u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }
            creatordobregex = u'\<div class\=\"label-header\"\>[\s\t\r\n]*Birth year of the artist[\s\t\r\n]*\<\/div\>[\s\t\r\n]*\<a href\=\"https\:\/\/www\.sammlung\.pinakothek\.de\/en\/year\/(\d\d\d\d)\"\>'
            creatordodregex = u'\<div class\=\"label-header\"\>[\s\t\r\n]*Year the artist deceased[\s\t\r\n]*\<\/div\>[\s\t\r\n]*\<a href\=\"https\:\/\/www\.sammlung\.pinakothek\.de\/en\/year\/(\d\d\d\d)\"\>'

            creatordobmatch = re.search(creatordobregex, itempage.text)
            creatordodmatch = re.search(creatordodregex, itempage.text)

            # This will get the date field if it's filled
            if record.get(u'date'):
                circaperiodregex = u'^um (\d\d)(\d\d)\/(\d\d)$'
                circaregex = u'^um (\d\d\d\d)$'

                circaperiodmatch = re.match(circaperiodregex, record.get(u'date'))
                circamatch = re.match(circaregex, record.get(u'date'))

                if circaperiodmatch:
                    metadata['inceptionstart'] = int(u'%s%s' % (circaperiodmatch.group(1), circaperiodmatch.group(2)))
                    metadata['inceptionend'] = int(u'%s%s' % (circaperiodmatch.group(1), circaperiodmatch.group(3)))
                    metadata['inceptioncirca'] = True
                elif circamatch:
                    metadata['inception'] = circamatch.group(1)
                    metadata['inceptioncirca'] = True
                else:
                    metadata['inception'] = record.get(u'date')
            elif creatordobmatch and creatordodmatch:
                metadata['inceptionstart'] = int(creatordobmatch.group(1))
                metadata['inceptionend'] = int(creatordodmatch.group(1))

            metadata['idpid'] = u'P217'
            invregex = u'\<div class\=\"label-header\"\>[\s\t\r\n]*Inventory Number[\s\t\r\n]*\<\/div\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/div\>'
            invmatch = re.search(invregex, itempage.text)
            metadata['id'] = invmatch.group(1).strip()

            # Figure out later
            #locations = { u'Nicht ausgestellt' : u'Q123',
            #              }
            #
            #locationregex = u'\<div class\=\"label-header\"\>[\s\t\r\n]*Ausgestellt[\s\t\r\n]*\<\/div\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/div\>'
            #locationmatch = re.search(locationregex, itempage.text)

            # If the origin starts with a year, we'll take that
            acquisitiondateregex = u'\<div class\=\"label-header\"\>[\s\t\r\n]*Origin[\s\t\r\n]*\<\/div\>[\s\t\r\n]*(\d\d\d\d)[^\<]+[\s\t\r\n]*\<\/div\>'
            acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            if acquisitiondatematch:
                metadata['acquisitiondate'] = acquisitiondatematch.group(1)

            # Figure out the location
            locationregex = u'\<div class\=\"label-header\"\>[\s\t\r\n]*Stock[\s\t\r\n]*\<\/div\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/div\>'
            locationmatch = re.search(locationregex, itempage.text)
            if locationmatch:
                location = locationmatch.group(1).strip()
                if location ==u'Bayerische Staatsgemäldesammlungen - Alte Pinakothek München':
                    metadata[u'locationqid']=u'Q154568'
                elif location ==u'Bayerische Staatsgemäldesammlungen - Neue Pinakothek München':
                    metadata[u'locationqid']=u'Q170152'
                elif location ==u'Bayerische Staatsgemäldesammlungen - Sammlung Moderne Kunst in der Pinakothek der Moderne München':
                    metadata[u'locationqid']=u'Q250195'
                #elif location ==u'Bayerische Staatsgemäldesammlungen - Staatsgalerie in der Katharinenkirche Augsburg':
                #    metadata[u'locationqid']=u''
                #elif location ==u'Bayerische Staatsgemäldesammlungen - Staatsgalerie Neuburg':
                #    metadata[u'locationqid']=u''


            mediumregex = u'\<div class\=\"label-header\"\>[\s\t\r\n]*Material / Technology / Carrier[\s\t\r\n]*\<\/div\>[\s\t\r\n]*Öl auf Leinwand[\s\t\r\n]*\<\/div\>'
            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch:
                metadata['medium'] = u'oil on canvas'

            measurementsregex = u'\<div class\=\"label-header\"\>[\s\t\r\n]*Dimensions of the object[\s\t\r\n]*\<\/div\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/div\>'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(1)
                regex_2d = u'(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) cm'
                regex_3d = u'(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) x (?P<depth>\d+(,\d+)?) cm.*'
                match_2d = re.match(regex_2d, measurementstext)
                match_3d = re.match(regex_3d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')
                elif match_3d:
                    metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
                    metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')

            permalinkregex = u'\<div class\=\"label-header\"\>[\s\t\r\n]*Permalink[\s\t\r\n]*\<\/div\>[\s\t\r\n]*\<a href\=\"([^\"]+)\"\>([^\<]+)</a>[\s\t\r\n]*\<\/div\>'
            permalinkmatch = re.search(permalinkregex, itempage.text)
            if permalinkmatch:
                metadata[u'describedbyurl'] = permalinkmatch.group(1)

            # Find an image we can download
            imageregex = u'\<div class\=\"label-header\"\>[\s\t\r\n]*Dimensions of the object[\s\t\r\n]*\<\/div\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/div\>'
            imageregex = u'\<a class\=\"artwork__action action--download\" target\=\"_blank\" href\=\"(https\:\/\/media\.static\.sammlung\.pinakothek\.de[^\"]+\.jpg)\" download\>'
            imagematch = re.search(imageregex, itempage.text)
            if imagematch and u'https://creativecommons.org/licenses/by-sa/4.0/' in itempage.text:
                metadata[u'imageurl'] = imagematch.group(1)
                metadata[u'imageurlformat'] = u'Q2195' #JPEG
                metadata[u'imageurllicense'] = u'Q18199165' # cc-by-sa.40
            yield metadata

def main(*args):
    dictGen = getBavarianGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
