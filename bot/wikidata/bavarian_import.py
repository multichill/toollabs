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
from html.parser import HTMLParser
import os
import json
import logging

def getBavarianGenerator():
    """
    Generator to return bavarian State Painting Collections paintings

    https://www.sammlung.pinakothek.de/de/genre/malerei#filters={%22genre%22:%22malerei%22}

    Problem is that over 200 pages will return server errors. So have to work on different subsets.

    """
    basesearchurl = 'https://www.sammlung.pinakothek.de/api/search?&page=%s&filters={"genre":"malerei"}'
    #basesearchurl = u'https://www.sammlung.pinakothek.de/api/search?&page=%s&filters={"yearRange":{"min":1900,"max":2100},"genre":"malerei"}'
    #basesearchurl = u'https://www.sammlung.pinakothek.de/api/search?&page=%s&filters={"publicDomain":true,"genre":"malerei"}'
    #basesearchurl = u'https://www.sammlung.pinakothek.de/api/search?&page=%s&filters={"onDisplay":true,"genre":"malerei"}'
    # For the image upload
    #basesearchurl = u'https://www.sammlung.pinakothek.de/api/search?&page=%s&filters={"genre":"malerei","publicDomain":true}' # 1- 185
    #basesearchurl = u'https://www.sammlung.pinakothek.de/api/search?&page=%s&filters={"publicDomain":true,"genre":"malerei"}'
    origin = 'https://www.sammlung.pinakothek.de'
    referer = 'https://www.sammlung.pinakothek.de/de/genre/malerei'

    #logging.basicConfig()
    #logging.getLogger().setLevel(logging.DEBUG)
    #requests_log = logging.getLogger("requests.packages.urllib3")
    #requests_log.setLevel(logging.DEBUG)
    #requests_log.propagate = True

    htmlparser = HTMLParser()

    # Not sure what is wrong with the website, but HTTPS setup is really slow and getting the wrong certificate
    # Just put everything in one session to not have to do that each time
    session = requests.Session()

    # Just loop over the pages
    for i in range(1, 200):
        searchurl = basesearchurl % (i,)
        print (searchurl,)
        searchPage = session.get(searchurl, headers={'X-Requested-With' : 'XMLHttpRequest',
                                                      'referer' : referer,
                                                      'origin' : origin,
                                                      },verify=False) # For some reason I'm getting certificate errors?
                                                      #'origin' : origin} )
        #print searchPage.text
        searchJson = searchPage.json()
        for record in searchJson.get('items'):
            metadata = {}
            #print (record)
            urlregex = '^https\:\/\/www\.sammlung\.pinakothek\.de\/de\/artwork\/([^\/]+)\/(.+)$'
            urlmatch = re.match(urlregex, record.get('url'))

            url = 'https://www.sammlung.pinakothek.de/en/artwork/%s/%s' % (urlmatch.group(1), urlmatch.group(2))

            ## ID is not the inventory number!
            #
            #url = record.get('url').replace(u'sammlung.pinakothek.de/de/artwork/', u'sammlung.pinakothek.de/en/artwork/')
            print (url)
            itempage = session.get(url, verify=False)
            metadata['url'] = url


            metadata['collectionqid'] = 'Q812285'
            metadata['collectionshort'] = 'BStGS'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = 'Q3305213'

            metadata['idpid'] = 'P217'
            metadata['id'] = '%s' % (record.get('inventoryId'))
            metadata['artworkidpid'] = 'P8948'
            metadata['artworkid'] = '%s' % (urlmatch.group(1),)


            # Figure this part out, this seems to give a scaled image
            #if record.get(u'imageAvailable')==u'available' and record.get(u'image'):
            #    if record.get(u'image').get(u'url'):
            #        metadata['imageurl'] = record.get(u'image').get(u'url')

            titleregex = '\<h1 class\=\"artwork__title\"\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/h1\>'
            titlematch = re.search(titleregex, itempage.text)
            if not titlematch:
                print('No title found, probably something went wrong. Skipping and sleeping for 2 minutes')
                time.sleep(120)
                continue
            title = htmlparser.unescape(titlematch.group(1).strip()) # This didn't work and included attributed to junk: record.get('title')

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]

            metadata['title'] = { 'de' : title,
                                  }

            #  record.get('artistInfo').get('fullName') didn't include the attribution part
            creatorregex = '\<div class\=\"label-header\"\>[\s\t\r\n]*Artist[\s\t\r\n]*\<\/div\>[\s\t\r\n]*\<a href\=\"[^\"]+\"\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/a\>[\s\t\r\n]*\<\/div\>'
            creatormatch = re.search(creatorregex, itempage.text)
            metadata['creatorname'] = htmlparser.unescape(creatormatch.group(1).strip())

            metadata['description'] = { 'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'),),
                                        'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                        'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                        }
            creatordobregex = '\<div class\=\"label-header\"\>[\s\t\r\n]*Birth year of the artist[\s\t\r\n]*\<\/div\>[\s\t\r\n]*\<a href\=\"https\:\/\/www\.sammlung\.pinakothek\.de\/en\/year\/(\d\d\d\d)\"\>'
            creatordodregex = '\<div class\=\"label-header\"\>[\s\t\r\n]*Year the artist deceased[\s\t\r\n]*\<\/div\>[\s\t\r\n]*\<a href\=\"https\:\/\/www\.sammlung\.pinakothek\.de\/en\/year\/(\d\d\d\d)\"\>'

            creatordobmatch = re.search(creatordobregex, itempage.text)
            creatordodmatch = re.search(creatordodregex, itempage.text)

            # This will get the date field if it's filled
            if record.get('date'):
                dateregex = '^(\d\d\d\d)$'
                datecircaregex = '^(um|ca\.)\s*(\d\d\d\d)$'
                periodregex = '^\s*(\d\d\d\d)\s*[-\/]\s*(\d\d\d\d)\s*$'
                shortperiodregex = '^\s*(\d\d)(\d\d)\s*[-\/]\s*(\d\d)\s*$'
                circaperiodregex = '^um\s*(\d\d\d\d)\s*[-\/]\s*(\d\d\d\d)$'
                circashortperiodregex = '^um\s*(\d\d)(\d\d)\s*[-\/]\s*(\d\d)$'

                datematch = re.match(dateregex, record.get('date'))
                datecircamatch = re.match(datecircaregex, record.get('date'))
                periodmatch = re.match(periodregex, record.get('date'))
                shortperiodmatch = re.match(shortperiodregex, record.get('date'))
                circaperiodmatch = re.match(circaperiodregex, record.get('date'))
                circashortperiodmatch = re.match(circashortperiodregex, record.get('date'))

                if datematch:
                    metadata['inception'] = int(datematch.group(1))
                elif datecircamatch:
                    metadata['inception'] = int(datecircamatch.group(2))
                    metadata['inceptioncirca'] = True
                elif periodmatch:
                    metadata['inceptionstart'] = int(periodmatch.group(1))
                    metadata['inceptionend'] = int(periodmatch.group(2))
                elif shortperiodmatch:
                    metadata['inceptionstart'] = int('%s%s' % (shortperiodmatch.group(1), shortperiodmatch.group(2)))
                    metadata['inceptionend'] = int('%s%s' % (shortperiodmatch.group(1), shortperiodmatch.group(3)))
                elif circaperiodmatch:
                    metadata['inceptionstart'] = int(circaperiodmatch.group(1))
                    metadata['inceptionend'] = int(circaperiodmatch.group(2))
                    metadata['inceptioncirca'] = True
                elif circashortperiodmatch:
                    metadata['inceptionstart'] = int('%s%s' % (circashortperiodmatch.group(1), circashortperiodmatch.group(2)))
                    metadata['inceptionend'] = int('%s%s' % (circashortperiodmatch.group(1), circashortperiodmatch.group(3)))
                    metadata['inceptioncirca'] = True
                else:
                    print ('Could not parse date: "%s"' % record.get(u'date'))
                    print ('Could not parse date: "%s"' % record.get(u'date'))
                    print ('Could not parse date: "%s"' % record.get(u'date'))
                    print ('Could not parse date: "%s"' % record.get(u'date'))
            elif creatordobmatch and creatordodmatch:
                metadata['inceptionstart'] = int(creatordobmatch.group(1))
                metadata['inceptionend'] = int(creatordodmatch.group(1))


            # We already got the inventory number earlier
            #metadata['idpid'] = 'P217'
            #invregex = '\<div class\=\"label-header\"\>[\s\t\r\n]*Inventory Number[\s\t\r\n]*\<\/div\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/div\>'
            #invmatch = re.search(invregex, itempage.text)
            #if invmatch.group(1).strip()!=metadata.get('id'):
            #    print('FOUND TWO DIFFERENT INVENTORY NUMBERS')


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
