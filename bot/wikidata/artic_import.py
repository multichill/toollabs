#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape paintings from the Art institute of Chicago website.

http://www.artic.edu/aic/collections/artwork-search/results/painting?filters=object_type_s%3APainting

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getArticGenerator():
    """
    Generator to return Artic paintings
    """

    # This one is for all the paintings
    basesearchurl = u'https://www.artic.edu/collection?classification_ids=painting&page=%s'
    htmlparser = HTMLParser()

    session = requests.Session()

    # 2683 results, 51 per page
    for i in range(1, 55):
        searchurl = basesearchurl % (i,)

        pywikibot.output(searchurl)
        searchPage = session.get(searchurl)

        urlregex = u'\<a href\=\"https\:\/\/www\.artic\.edu\/artworks\/(\d+)\/'
        matches = re.finditer(urlregex, searchPage.text)
        for match in matches:
            metadata = {}
            url = u'https://www.artic.edu/artworks/%s' % (match.group(1),)

            metadata['artworkidpid'] = u'P4610'
            metadata['artworkid'] = match.group(1)

            # Museum site doesn't seem to like it when we go fast
            #time.sleep(15)

            pywikibot.output(url)
            itempage = session.get(url)
            metadata['url'] = url

            metadata['collectionqid'] = u'Q239303'
            metadata['collectionshort'] = u'Artic'
            metadata['locationqid'] = u'Q239303'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'
            invregex = u'\<h2 class\=\"f-module-title-1\"\>Reference Number\<\/h2\>[\r\n\t\s]*\<\/dt\>[\r\n\t\s]*\<dd\>[\r\n\t\s]*\<span class\=\"f-secondary\"\>([^\<]+)\<\/span\>'
            invmatch = re.search(invregex, itempage.text)
            if not invmatch:
                # FIXME: Check later
                print(u'No inventory number found, skipping this one')
                continue
            metadata['id'] = invmatch.group(1).strip()
            #else:
            #    pywikibot.output(u'Something went wrong, no inventory number found, skipping this one')
            #    continue

            titleregex = u'\<h2 class\=\"f-module-title-1\"\>Title\<\/h2\>[\r\n\t\s]*\<\/dt\>[\r\n\t\s]*\<dd itemprop\=\"name\"\>[\r\n\t\s]*\<span class\=\"f-secondary\"\>([^\<]+)\<\/span\>'
            titlematch = re.search(titleregex, itempage.text)
            title = htmlparser.unescape(titlematch.group(1).strip())
            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                  }

            # Didn't check this one very well
            # creatorregex = u'\<meta content\=\"([^\"]+)\" property\=\"schema:creator\" itemprop\=\"creator\"\>'
            creatorregex = u'\<a href\=\"https\:\/\/www\.artic\.edu\/artists\/(\d+)\" data-gtm-event\=\"([^\"]+)\"'
            creatormatch = re.search(creatorregex, itempage.text)
            if creatormatch:
                name = htmlparser.unescape(creatormatch.group(2).strip())

                metadata['creatorname'] = name
                metadata['description'] = { u'nl' : u'schilderij van %s' % (name, ),
                                            u'en' : u'painting by %s' % (name, ),
                                            u'de' : u'Gemälde von %s' % (name, ),
                                            }
            else:
                metadata['creatorname'] = u'anonymous'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
                metadata['creatorqid'] = u'Q4233718'


            dateregex = u'\<dd itemprop\=\"dateCreated\">[\r\n\t\s]*\<span class\=\"f-secondary\"\>[\r\n\t\s]*\<a href\=\"https\:\/\/www\.artic\.edu\/collection\?date-start\=(\d\d\d\d)\&date-end\=(\d\d\d\d)\"\>(\d\d\d\d)\<\/a\>'
            datematch = re.search(dateregex, itempage.text)
            if datematch:
                if datematch.group(1).strip()==datematch.group(2).strip() and datematch.group(2).strip()==datematch.group(3).strip():
                    # Don't worry about cleaning up here.
                    metadata['inception'] = htmlparser.unescape(datematch.group(1).strip())

            # Not available
            #acquisitiondateregex = u'\<span class\=\"detailFieldLabel\"\>Inventarzugang:\s*\<\/span\>\<span class\=\"detailFieldValue\"\>(\d\d\d\d)([^\<]+)\<\/span\>'
            #acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            #if acquisitiondatematch:
            #    metadata['acquisitiondate'] = acquisitiondatematch.group(1)


            mediumregex = u'\<h2 class\=\"f-module-title-1\"\>Medium\<\/h2\>[\r\n\t\s]*\<\/dt\>[\r\n\t\s]*\<dd itemprop\=\"material\"\>[\r\n\t\s]*\<span class\=\"f-secondary\"\>Oil on canvas\<\/span\>'
            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch:
                metadata['medium'] = u'oil on canvas'

            measurementsregex = u'\<h2 class\=\"f-module-title-1\"\>Dimensions\<\/h2\>[\r\n\t\s]*\<\/dt\>[\r\n\t\s]*\<dd\>[\r\n\t\s]*\<span class\=\"f-secondary\"\>([^\<]+)\<\/span\>'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(1)
                # FIXME: They are not consistent, sometimes other way around
                regex_2d = u'^(?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) cm \(.*$'
                regex_3d = u'^(?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) x (?P<depth>\d+(\.\d+)?) cm \(.*$'
                match_2d = re.match(regex_2d, measurementstext)
                match_3d = re.match(regex_3d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height')
                    metadata['widthcm'] = match_2d.group(u'width')
                elif match_3d:
                    metadata['heightcm'] = match_3d.group(u'height')
                    metadata['widthcm'] = match_3d.group(u'width')
                    metadata['depthcm'] = match_3d.group(u'depth')

                # Checks if it's CC0 and gets the url
                imageregex = u'data-gallery-img-credit\=\"CC0 Public Domain Designation\"[\r\n\t\s]*data-gallery-img-credit-url\=\"\/image-licensing\"[\r\n\t\s]*data-gallery-img-share-url\=\"\#\"[\r\n\t\s]*data-gallery-img-download-url\=\"(https\:\/\/www\.artic\.edu/\iiif\/2\/[^\/]+\/full\/full\/0\/default\.jpg)\"'
                imagematch = re.search(imageregex, itempage.text)
                if imagematch:
                    metadata[u'imageurl'] = imagematch.group(1)
                    metadata[u'imageurlformat'] = u'Q2195' #JPEG
                    metadata[u'imageurllicense'] = u'Q6938433' # cc-zero
                    metadata[u'imageurlforce'] = True

            yield metadata


def main():
    dictGen = getArticGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
