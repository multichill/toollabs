#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Dallas Museum of Art to Wikidata.

Just loop over pages like https://collections.dma.org/api/search/?q=&per_page=40&page=7&facets=0&facet_classification=Paintings

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getDMAGenerator():
    """
    Generator to return allas Museum of Art paintings
    """
    basesearchurl = u'https://collections.dma.org/api/search/?q=&per_page=40&page=%s&facets=0&facet_classification=Paintings'
    htmlparser = HTMLParser()

    # Really? You're throwing a 403 at me?
    headers = { 'User-Agent' : 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0' }
    session = requests.Session()
    session.headers.update(headers)

    # 1383 hits, 40 per page

    for i in range(1, 36):
        searchurl = basesearchurl % (i,)
        searchPage = session.get(searchurl)

        for iteminfo in searchPage.json().get(u'data'):
            url = u'https://collections.dma.org/artwork/%s' % (iteminfo.get(u'id'),)
            metadata = {}

            #itempage = requests.get(url, verify=False)
            pywikibot.output(url)

            metadata['url'] = url

            metadata['collectionqid'] = u'Q745866'
            metadata['collectionshort'] = u'DMA'
            metadata['locationqid'] = u'Q745866'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'

            # Let's assume these 4 are always set
            for keyvalue in iteminfo.get(u'metadata'):
                key = keyvalue.get(u'key')
                value = keyvalue.get(u'value')
                if key==u'constituent':
                    creatorname = value
                elif key==u'dated':
                    rawdate = value
                elif key==u'medium':
                    rawmedium = value
                elif key==u'number':
                    rawinv = value

            metadata['id'] = rawinv

            title = iteminfo.get(u'title').strip()

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                  }

            metadata['creatorname'] = creatorname

            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        u'de' : u'%s von %s' % (u'Gemälde', metadata.get('creatorname'), ),
                                        u'fr' : u'%s de %s' % (u'peinture', metadata.get('creatorname'), ),
                                        }

            # We already have the raw date. Let's see if we can extract some variant dates.
            dateregex = u'^(\d\d\d\d)$'
            datecircaregex = u'^c\.\s*(\d\d\d\d)$'
            periodregex = u'^(\d\d\d\d)–(\d\d\d\d)$'
            circaperiodregex = u'^c\.\s*(\d\d\d\d)–(\d\d\d\d)$'
            shortperiodregex = u'^(\d\d)(\d\d)–(\d\d)$'
            circashortperiodregex = u'^c\.\s*(\d\d)(\d\d)–(\d\d)$'

            datematch = re.match(dateregex, rawdate)
            datecircamatch = re.match(datecircaregex, rawdate)
            periodmatch = re.match(periodregex, rawdate)
            circaperiodmatch = re.match(circaperiodregex, rawdate)
            shortperiodmatch = re.match(shortperiodregex, rawdate)
            circashortperiodmatch = re.match(circashortperiodregex, rawdate)

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
                print (u'Could not parse date: "%s"' % (rawdate,))

            if rawmedium.strip().lower()==u'oil on canvas':
                metadata['medium'] = u'oil on canvas'

            # We're grabbing the JPG, not the high resolution tiff file
            if iteminfo.get(u'primary_media'):
                if iteminfo.get(u'primary_media').get(u'derivatives'):
                    if iteminfo.get(u'primary_media').get(u'derivatives').get(u'original'):
                        metadata[u'imageurl'] = iteminfo.get(u'primary_media').get(u'derivatives').get(u'original').get(u'url')
                        metadata[u'imageurlformat'] = u'Q2195' #JPEG
                        metadata[u'imageoperatedby'] = u'Q745866'
                        # Use this to add suggestions everywhere
                        # metadata[u'imageurlforce'] = True

            """
            #For this part I need to actually open the linked page and grab things

            # Credit line doesn't seem to contain a date
            #acquisitiondateregex = u'\<div class\=\"detailField creditlineField\"\>\<span class\=\"detailFieldLabel\"\>Credit Line\: \<\/span\>\<!--\<div t\:type\=\"relatedfield\" t\:module\=\"eognl\:module\" t\:name\=\"propertyName\" t\:value\=\"value\"\>--\>\<span class\=\"detailFieldValue\"\>[^\<]+(\d\d\d\d)\<\/span\>'
            #acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            #if acquisitiondatematch:
            #    metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))


            # Dimensions
            measurementsregex = u'\<div class\=\"detailField dimensionsField\"\>\<span class\=\"detailFieldLabel\"\>Dimensions\:\<\/span\>\<span class\=\"detailFieldValue\"\>\<div\>(board|canvas|panel)?\:\s*(?P<dim>[^\<]+)\<\/div\>'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(u'dim')
                regex_2d = u'^(?P<height>\d+(\.\d+)?)\s*x\s*(?P<width>\d+(\.\d+)?)\s*cm'
                match_2d = re.match(regex_2d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')

            # Add genre
            keywordregex = u'\<a href\=\"\/vocabularies\/thesaurus\/(\d+)\;[^\"]+\"\>'
            keywordmatches = re.finditer(keywordregex, itempage.text)

            genres = { u'1545838' : u'Q134307', # Portrait
                       u'1546170' : u'Q2864737', # Religious art
                       }

            for keywordmatch in keywordmatches:
                keyid = keywordmatch.group(1)
                if keyid in genres:
                    metadata[u'genreqid'] = genres.get(keyid)

            ## NO free images
            #imageregex = u'\<meta property\=\"og:image\" content\=\"([^\"]+)\"\ \/\>'
            #imagematch = re.search(imageregex, itempage.text)
            #if imagematch and u'https://creativecommons.org/licenses/by-sa/4.0/' in itempage.text:
            #    metadata[u'imageurl'] = imagematch.group(1)
            #    metadata[u'imageurlformat'] = u'Q2195' #JPEG
            #    metadata[u'imageurllicense'] = u'Q18199165' # cc-by-sa.40
            #    metadata[u'imageoperatedby'] = u'Q262234'
            #    # Used this to add suggestions everywhere
            #    #metadata[u'imageurlforce'] = True
            """

            yield metadata


def main():
    dictGen = getDMAGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
