#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Birmingham Museums Trust to Wikidata.

This one uses their website at https://www.birminghammuseums.org.uk/explore-art/items/search?subject=Paintings+%28Visual+Works%29
and artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import json
from html.parser import HTMLParser

def getBirminghamMuseumsGenerator():
    """
    Generator to return Birmingham Museums Trust paintings
    """
    htmlparser = HTMLParser()
    baseSearchUrl = 'https://www.birminghammuseums.org.uk/explore-art/items/search?page=%s&subject=Paintings+%%28Visual+Works%%29'

    for i in range(1,142):
        searchUrl = baseSearchUrl % (i,)
        print (searchUrl)

        searchPage = requests.get(searchUrl)
        searchPageData = searchPage.text
        searchRegex = '\<a href\=\"(\/explore-art\/items\/[^\/]+\/[^\?]+)\?[^\"]+\"\>'

        for match in re.finditer(searchRegex, searchPageData):
            metadata = {}

            url = 'https://www.birminghammuseums.org.uk%s' % (match.group(1),)
            print (url)

            itemPage = requests.get(url)
            itemPageData = itemPage.text

            metadata['url'] = url

            metadata['collectionqid'] = 'Q4916759'
            metadata['collectionshort'] = 'Birmingham Museums'

            # Most of the paintings are in the Birmingham Museum and Art Gallery
            metadata['locationqid'] = 'Q1799857'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            invRegex = '\<li\>\<span class\=\"category\"\>Accession Number\:\s*\<\/span\>([^\<]+)\<\/li\>'
            invMatch = re.search(invRegex, itemPageData)

            metadata['id'] = invMatch.group(1).strip()
            metadata['idpid'] = u'P217'

            titleRegex = '\<meta property\=\"og\:title\" content\=\"([^\"]+)\"\s*\/\>'
            titleMatch = re.search(titleRegex, itemPageData)

            title = htmlparser.unescape(titleMatch.group(1)).strip()

            ## Chop chop, if we encounter long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { 'en' : title,
                                }

            creatorregex = '\<li\>\<span class\=\"category\"\>Artist\:\<\/span\>[\r\n\t\s]*\<a href\=\"[^\"]+\"\>([^\<]+)\<\/a\>'
            creatormatch = re.search(creatorregex, itemPageData)

            if creatormatch:
                if '\n' in creatormatch.group(1):
                    name = htmlparser.unescape(creatormatch.group(1)).split('\n')[0].strip()
                else:
                    name = htmlparser.unescape(creatormatch.group(1)).replace('(Artist)', '').strip()
                metadata['creatorname'] = name
                metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                            'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                            'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'),),
                                            'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                            }
            else:
                metadata['creatorqid'] = 'Q4233718'
                metadata['creatorname'] = 'anonymous'
                metadata['description'] = { 'nl' : 'schilderij van anonieme schilder',
                                            'en' : 'painting by anonymous painter',
                                            }

            # Try to extract the date
            dateregex = '\<li\>\<span class\=\"category\"\>Date\:\<\/span\>[\r\n\t\s]*(\d\d\d\d)[\r\n\t\s]*\<\/li\>'
            #datecircaregex = u'^(c\.|circa)\s*(\d\d\d\d)$'
            periodregex = '\<li\>\<span class\=\"category\"\>Date\:\<\/span\>[\r\n\t\s]*(\d\d\d\d)\s*-\s*(\d\d\d\d)[\r\n\t\s]*\<\/li\>'
            #shortperiodregex = u'^(\d\d)(\d\d)\s*-\s*(\d\d)$'
            #circaperiodregex = u'^c\.\s*(\d\d\d\d)\s*-\s*(\d\d\d\d)$'
            #circashortperiodregex = u'^c\.\s*(\d\d)(\d\d)\s*-\s*(\d\d)$'
            #circaveryshortperiodregex = u'^c\.\s*(\d\d\d)(\d)\s*-\s*(\d)$'
            otherdateregex = '\<li\>\<span class\=\"category\"\>Date\:\<\/span\>[\r\n\t\s]*([^\<]+)[\r\n\t\s]*\<\/li\>'

            datematch = re.search(dateregex, itemPageData)
            datecircamatch = None # re.search(datecircaregex, itemPageData)
            periodmatch = re.search(periodregex, itemPageData)
            circaperiodmatch = None # re.search(circaperiodegex, itemPageData)
            otherdatematch = re.search(otherdateregex, itemPageData)

            if datematch:
                metadata['inception'] = int(datematch.group(1))
            elif datecircamatch:
                metadata['inception'] = int(datecircamatch.group(2))
                metadata['inceptioncirca'] = True
            elif periodmatch:
                metadata['inceptionstart'] = int(periodmatch.group(1),)
                metadata['inceptionend'] = int(periodmatch.group(2),)
            #elif shortperiodmatch:
            #    metadata['inceptionstart'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(2),))
            #    metadata['inceptionend'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(3),))
            elif circaperiodmatch:
                metadata['inceptionstart'] = int(circaperiodmatch.group(1),)
                metadata['inceptionend'] = int(circaperiodmatch.group(2),)
                metadata['inceptioncirca'] = True
            elif otherdatematch:
                print (u'Could not parse date: "%s"' % (otherdatematch.group(1),))

            # Extract the acquisitiondate from the inventory number
            acquisitiondateregex = '^(\d\d\d\d)P.+$'
            acquisitiondatematch = re.match(acquisitiondateregex, metadata.get('id'))
            if acquisitiondatematch:
                metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

            # Only add the medium if it's oil on canvas
            oilcanvasregex = '\<li\>\<span class\=\"category\"\>Medium\:\<\/span\>[\r\n\t\s]*Oil on canvas[\r\n\t\s]*\<\/li\>'
            oilcanvasmatch = re.search(oilcanvasregex, itemPageData, flags=re.IGNORECASE)
            if oilcanvasmatch:
                metadata['medium'] = u'oil on canvas'

            '''
            # Seems to be missing in the data

                measurementsregex = u'\<h4\>Measurements\<\/h4\>[\s\r\t\n]*\<p\>([^\<]+)\<\/p\>'
                measurementsmatch = re.search(measurementsregex, itempage.text)
                if measurementsmatch:
                    measurementstext = measurementsmatch.group(1)
                    regex_2d = u'(?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) cm.*'
                    regex_3d = u'(?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) x (?P<depth>\d+(\.\d+)?) cm.*'
                    match_2d = re.match(regex_2d, measurementstext)
                    match_3d = re.match(regex_3d, measurementstext)
                    if match_2d:
                        metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                        metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')
                    elif match_3d:
                        metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
                        metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
                        metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')

            # We're filtering for items with images that are from before 1900
            if item.get('primaryLargeImage') and not 'placeholder' in item.get('primaryLargeImage'):
                metadata[u'imageurl'] = u'https:%s' % (item.get('primaryLargeImage'),)
                metadata[u'imageurlformat'] = u'Q2195' #JPEG
                metadata[u'imageoperatedby'] = u'Q1459037'
                # Used this to add suggestions everywhere
                metadata[u'imageurlforce'] = True
            '''
            yield metadata


def main():
    dictGen = getBirminghamMuseumsGenerator()

    #for painting in dictGen:
    #    print(painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
