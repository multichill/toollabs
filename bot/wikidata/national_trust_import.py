#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from the National Trust (Collections) to Wikidata

* Loop over http://www.nationaltrustcollections.org.uk/results?Categories=7456ee20fffffe0702132e04e5764fd3&Sort=collection
* Grab individual paintings like http://www.nationaltrustcollections.org.uk/object/1514019
* Also do some tricks to match the location

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re
import time
try:
    from html.parser import HTMLParser
except ImportError:
    import HTMLParser

def getNTGenerator():
    """
    Generator to return Hungarian National Trust paintings

    Search has a max of 250 pages, so that's 5*5*250=6250 of the 12,472 paintings.
    So need to try the different ways to get all of them.
    
    """
    htmlparser = HTMLParser()
    baseSearchUrl = u'http://www.nationaltrustcollections.org.uk/results?Categories=7456ee20fffffe0702132e04e5764fd3&Sort=collection&Page=%s'

    for i in range(1, 250):
        searchUrl = baseSearchUrl % (i,)
        print (searchUrl)

        searchPage = requests.get(searchUrl)
        searchPageData = searchPage.text
        searchRegex = u'\<a href\=\"\/object\/(\d+)\"\>'

        for match in re.finditer(searchRegex, searchPageData):
            url = u'http://www.nationaltrustcollections.org.uk/object/%s' % (match.group(1),)

            print (url)

            itemPage = requests.get(url)
            itemPageData = itemPage.text

            metadata = {}
            metadata['url'] = url

            metadata['collectionqid'] = u'Q333515'
            metadata['collectionshort'] = u'NT'
            # TODO: Add location logic
            #metadata['locationqid'] = u'Q252071'

            # Search is for paintings
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'
            metadata['id'] = u'%s' % (match.group(1),)
            metadata['artworkidpid'] = u'P4373'
            metadata['artworkid'] = u'%s' % (match.group(1),)

            titleRegex = u'\<h2 class\=\"section-title\"\>([^\<]+)\<\/h2\>'
            titleMatch = re.search(titleRegex, itemPageData)

            if titleMatch:
                title = htmlparser.unescape(titleMatch.group(1)).strip()
            else:
                # Sometimes nothing is returned. Just sleep and continue with the next one
                pywikibot.output(u'No title found, probably something went wrong. Sleeping and skipping')
                time.sleep(60)
                continue
                #title = u'(without title)'

            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                              }

            artistRegex = u'\<h3 class\=\"section-subtitle\"\>([^\<]+)\<\/h3\>'
            artistMatch = re.search(artistRegex, itemPageData)

            artistCleanupRegex = u'^(.+)\(([^\)]+)\)$'

            if artistMatch:
                dirtyname = htmlparser.unescape(artistMatch.group(1)).strip()
            else:
                dirtyname = u'anonymous'

            artistCleanupMatch = re.match(artistCleanupRegex, dirtyname)

            if artistCleanupMatch:
                name = artistCleanupMatch.group(1).strip()
            else:
                name = dirtyname.strip()

            metadata['creatorname'] = name
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }

            # Only match on years
            dateRegex = u'\<h4\>Date\<\/h4\>[\r\n\t\s]*\<p\>\s*(\d\d\d\d)\s*(\(signed and dated\))?\<\/p\>'
            dateMatch = re.search(dateRegex, itemPageData)
            if dateMatch:
                metadata['inception'] = htmlparser.unescape(dateMatch.group(1))

            # acquisitiondate not available
            # acquisitiondateRegex = u'\<em\>Acknowledgement\<\/em\>\:\s*.+(\d\d\d\d)[\r\n\t\s]*\<br\>'
            #acquisitiondateMatch = re.search(acquisitiondateRegex, itemPageData)
            #if acquisitiondateMatch:
            #    metadata['acquisitiondate'] = acquisitiondateMatch.group(1)

            mediumRegex = u'\<h4\>Materials\<\/h4\>[\r\n\t\s]*\<p\>Oil on canvas\<\/p\>'
            mediumMatch = re.search(mediumRegex, itemPageData)

            if mediumMatch:
                metadata['medium'] = u'oil on canvas'

            dimensionRegex = u'\<h4\>Measurements\<\/h4\>[\r\n\t\s]*\<p\>([^\<]+)\<\/p\>'
            dimensionMatch = re.search(dimensionRegex, itemPageData)

            if dimensionMatch:
                dimensiontext = dimensionMatch.group(1).strip()
                regex_2d = u'^(?P<height>\d+)\s*(x|×)\s*(?P<width>\d+)\s*mm'
                #regex_3d = u'^.+\((?P<height>\d+(\.\d+)?)\s*(cm\s*)?(x|×)\s*(?P<width>\d+(\.\d+)?)\s*(cm\s*)?(x|×)\s*(?P<depth>\d+(\.\d+)?)\s*cm\)$'
                match_2d = re.match(regex_2d, dimensiontext)
                #match_3d = re.match(regex_3d, dimensiontext)
                if match_2d:
                    metadata['heightcm'] = u'%s' % (float(match_2d.group(u'height'))/10, )
                    metadata['widthcm'] = u'%s' % (float(match_2d.group(u'width'))/10, )
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
    dictGen = getNTGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
