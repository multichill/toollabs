#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Rhode Island School of Design Museum to Wikidata.

Just loop over pages like https://risdmuseum.org/art-design/collection?field_type=107&page=5

This bot does use artdatabot to upload it to Wikidata and just asks the API for all it's paintings.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getRISDGenerator():
    """
    Generator to return Rhode Island School of Design Museum paintings
    """
    basesearchurl = u'https://risdmuseum.org/art-design/collection?field_type=107&page=%s'
    htmlparser = HTMLParser()

    for i in range(0, 80):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = requests.get(searchurl)

        urlregex = u'role\=\"article\" about\=\"\/art-design\/collection\/([^\"]+)\"'
        matches = re.finditer(urlregex, searchPage.text)
        for match in matches:
            url = u'https://risdmuseum.org/art-design/collection/%s' % (match.group(1),)
            metadata = {}

            print (url)

            itempage = requests.get(url)
            metadata['url'] = url

            metadata['collectionqid'] = u'Q2148186'
            metadata['collectionshort'] = u'RISD'
            metadata['locationqid'] = u'Q2148186'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'

            invregex = u'\<h3 class\=\"object__accordion-title\"\>Object Number\<\/h3\>\<\/dt\>[\r\n\t\s]*\<dd\>[\r\n\t\s]*\<div\>[\r\n\t\s]*\<div class\=\"field field--name-field-object-number field--type-string field--label-hidden\"\>([^\<]+)\<\/div\>'

            invmatch = re.search(invregex, itempage.text)
            metadata['id'] = invmatch.group(1).strip()

            titleregex = u'\<h3 class\=\"object__accordion-title\"\>Title\<\/h3\>[\r\n\t\s]*\<div class\=\"object__info--content\"\>[\r\n\t\s]*\<span class\=\"field field--name-title field--type-string field--label-hidden\"\>([^\<]+)\<\/span\>'
            titlematch = re.search(titleregex, itempage.text)
            title = htmlparser.unescape(titlematch.group(1)).strip()

            ## Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                  }
            creatorregex = u'\<h1 class\=\"page-title\"\>([^\<]+)\<\/h1\>'
            creatormatch = re.search(creatorregex, itempage.text)
            name = htmlparser.unescape(creatormatch.group(1)).strip()

            metadata['creatorname'] = name
            metadata['description'] = { u'nl' : u'schilderij van %s' % (name, ),
                                        u'en' : u'painting by %s' % (name, ),
                                        u'de' : u'Gemälde von %s' % (name, ),
                                        }

            # Older paintings have more difficult dates
            dateregex = u'\<h3 class\=\"object__accordion-title\"\>Year\<\/h3\>[\r\n\t\s]*\<div class\=\"object__info--content\"\>[\r\n\t\s]*\<div class\=\"field field--name-field-dating field--type-string field--label-hidden\"\>(\d\d\d\d)\<\/div\>'
            datecircaregex = u'\<h3 class\=\"object__accordion-title\"\>Year\<\/h3\>[\r\n\t\s]*\<div class\=\"object__info--content\"\>[\r\n\t\s]*\<div class\=\"field field--name-field-dating field--type-string field--label-hidden\"\>ca\.\s*(\d\d\d\d)\<\/div\>'
            periodregex = u'\<h3 class\=\"object__accordion-title\"\>Year\<\/h3\>[\r\n\t\s]*\<div class\=\"object__info--content\"\>[\r\n\t\s]*\<div class\=\"field field--name-field-dating field--type-string field--label-hidden\"\>(\d\d\d\d)-(\d\d\d\d)\<\/div\>'
            #shortperiodregex = u'\<p\>\<strong\>Date\<\/strong\>\<br\/\>(\d\d)(\d\d)–(\d\d)\<\/p\>'
            circaperiodregex = u'\<h3 class\=\"object__accordion-title\"\>Year\<\/h3\>[\r\n\t\s]*\<div class\=\"object__info--content\"\>[\r\n\t\s]*\<div class\=\"field field--name-field-dating field--type-string field--label-hidden\"\>ca\.\s*(\d\d\d\d)-(\d\d\d\d)\<\/div\>'
            #circashortperiodregex = u'\<p\>\<strong\>Date\<\/strong\>\<br\/\>c\.\s*(\d\d)(\d\d)–(\d\d)\<\/p\>'
            otherdateregex = u'\<h3 class\=\"object__accordion-title\"\>Year\<\/h3\>[\r\n\t\s]*\<div class\=\"object__info--content\"\>[\r\n\t\s]*\<div class\=\"field field--name-field-dating field--type-string field--label-hidden\"\>([^\<]+)\<\/div\>'

            datematch = re.search(dateregex, itempage.text)
            datecircamatch = re.search(datecircaregex, itempage.text)
            periodmatch = re.search(periodregex, itempage.text)
            #shortperiodmatch = re.search(shortperiodregex, itempage.text)
            circaperiodmatch = re.search(circaperiodregex, itempage.text)
            #circashortperiodmatch = re.search(circashortperiodregex, itempage.text)
            otherdatematch = re.search(otherdateregex, itempage.text)
            if datematch:
                metadata['inception'] = datematch.group(1).strip()
            elif datecircamatch:
                metadata['inception'] = datecircamatch.group(1).strip()
                metadata['inceptioncirca'] = True
            elif periodmatch:
                metadata['inceptionstart'] = int(periodmatch.group(1))
                metadata['inceptionend'] = int(periodmatch.group(2))
            #elif shortperiodmatch:
            #    metadata['inceptionstart'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(2),))
            #    metadata['inceptionend'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(3),))
            elif circaperiodmatch:
                metadata['inceptionstart'] = int(circaperiodmatch.group(1))
                metadata['inceptionend'] = int(circaperiodmatch.group(2))
                metadata['inceptioncirca'] = True
            #elif circashortperiodmatch:
            #    metadata['inceptionstart'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(2),))
            #    metadata['inceptionend'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(3),))
            #    metadata['inceptioncirca'] = True
            elif otherdatematch:
                print (u'Could not parse date: "%s"' % (otherdatematch.group(1),))

            # No data, could do a trick with the inventory number
            # metadata['acquisitiondate'] = acquisitiondatematch.group(1)

            mediumregex = u'\<h3 class\=\"object__accordion-title\"\>Medium\<\/h3\>[\r\n\t\s]*\<div class\=\"object__info--content\"\>[\r\n\t\s]*\<div class\=\"field field--name-field-medium-technique field--type-string field--label-hidden\"\>oil on canvas\<\/div\>'

            mediumematch = re.search(mediumregex, itempage.text)
            if mediumematch:
                metadata['medium'] = u'oil on canvas'

            measurementsregex = u'\<dt\>\<h3 class\=\"object__accordion-title\"\>Dimensions\<\/h3\>\<\/dt\>[\r\n\t\s]*\<dd\>[\r\n\t\s]*\<div\>[\r\n\t\s]*\<div class\=\"field field--name-field-dimensions field--type-string field--label-hidden\"\>([^\<]+)\<\/div\>'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(1)
                regex_2d = u'^(?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) cm.*'
                regex_3d = u'^(?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) x (?P<depth>\d+(\.\d+)?) cm.*'
                match_2d = re.match(regex_2d, measurementstext)
                match_3d = re.match(regex_3d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')
                elif match_3d:
                    metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
                    metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')

            imageurlregex = u'\<div class\=\"carousel-inner\"\>[\r\n\t\s]*\<div class\=\"carousel-item active\" data-full-url\=\"(https\:\/\/risdmuseum\.org\/sites\/default\/files\/museumplus\/\d+\.jpg)\"\>'
            imageurlmatch = re.search(imageurlregex, itempage.text)
            publicdomaintext = u'This object is in the <a href="https://creativecommons.org/publicdomain/zero/1.0/" title="Creative Commons Public Domain Dedication" target="_blank">public domain (CC0 1.0)</a>'
            if publicdomaintext in itempage.text and imageurlmatch:
                metadata[u'imageurl'] = imageurlmatch.group(1)
                metadata[u'imageurlformat'] = u'Q2195' #JPEG
                metadata[u'imageurllicense'] = u'Q6938433' # CC0
                # Could use this later to force
                metadata[u'imageurlforce'] = False

            yield metadata


def main():
    dictGen = getRISDGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
