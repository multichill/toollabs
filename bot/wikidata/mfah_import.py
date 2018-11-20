#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Museum of Fine Arts in Houston to Wikidata.

Just loop over pages like https://www.mfah.org/art/search?classification=Painting&page=1

This bot does use artdatabot to upload it to Wikidata and just asks the API for all it's paintings.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import HTMLParser

def getMFAHGenerator():
    """
    Generator to return Museum of Fine Arts, Houston paintings
    """
    basesearchurl = u'https://www.mfah.org/art/search?classification=Painting&show=50&page=%s'
    htmlparser = HTMLParser.HTMLParser()

    # 1952 results, 50 per page
    for i in range(1, 41):
        searchurl = basesearchurl % (i,)

        pywikibot.output(searchurl)
        searchPage = requests.get(searchurl)

        urlregex = u'\<a href\=\"\/art\/detail\/(\d+)\?returnUrl\=[^\"]+\"\>[^\<]+\<\/a\>'
        matches = re.finditer(urlregex, searchPage.text)
        for match in matches:
            metadata = {}
            url = u'https://www.mfah.org/art/detail/%s' % (match.group(1),)

            # Museum site doesn't seem to like it when we go fast
            #time.sleep(15)

            pywikibot.output(url)

            itempage = requests.get(url)
            metadata['url'] = url

            metadata['artworkidpid'] = u'P4673'
            metadata['artworkid'] = match.group(1)

            metadata['collectionqid'] = u'Q1565911'
            metadata['collectionshort'] = u'MFAH'
            metadata['locationqid'] = u'Q1565911'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'
            invregex = u'\<dt\>Accession Number\<\/dt\>[\s\t\r\n]+\<dd\>([^\<]+)\<\/dd\>'
            invmatch = re.search(invregex, itempage.text)
            metadata['id'] = invmatch.group(1).strip()

            #else:
            #    pywikibot.output(u'Something went wrong, no inventory number found, skipping this one')
            #    continue

            creatorritleregex = u'\<div class\=\"page-header clearfix\"\>[\s\t\r\n]+\<h1\>\<small\>([^\<]+)\<\/small\>\<br \/\>([^\<]+)\<\/h1\>'
            onlytitleregex = u'\<div class\=\"page-header clearfix\"\>[\s\t\r\n]+\<h1\>\<small\>\<\/small\>\<br \/\>([^\<]+)\<\/h1\>'
            creatorritlematch = re.search(creatorritleregex, itempage.text)

            if creatorritlematch:
                title = htmlparser.unescape(creatorritlematch.group(2).strip())
                name = htmlparser.unescape(creatorritlematch.group(1).strip())
            else:
                # Fun edge cases like https://www.mfah.org/art/detail/39197
                onlytitlematch = re.search(onlytitleregex, itempage.text)
                title = htmlparser.unescape(onlytitlematch.group(1).strip())
                name = u''

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                  }

            metadata['creatorname'] = name
            metadata['description'] = { u'nl' : u'schilderij van %s' % (name, ),
                                        u'en' : u'painting by %s' % (name, ),
                                        }

            # TODO: Handle circa like https://www.mfah.org/art/detail/102501
            dateregex = u'\<dt\>Date\<\/dt\>[\s\t\r\n]+\<dd\>([^\<]+)\<\/dd\>'
            datematch = re.search(dateregex, itempage.text)
            # Don't worry about cleaning up here.
            metadata['inception'] = htmlparser.unescape(datematch.group(1).strip())

            # Not available in the metadata
            # metadata['acquisitiondate'] = acquisitiondatematch.group(1)

            mediumregex = u'\<dt\>Medium\<\/dt\>[\s\t\r\n]+\<dd\>[^\<]+Oil on canvas[^\<]+\<\/dd\>'
            mediummatch = match = re.search(mediumregex, itempage.text, flags=re.I)
            if mediummatch:
                metadata['medium'] = u'oil on canvas'

            # Not consistent at all. I could do it later
            """
            measurementsregex = u'\<dt\>Dimensions\<\/dt\>[\s\t\r\n]+\<dd\>([^\<]+)\<\/dd\>'
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
            """
            imageidregex = u'\<img class\=\"img-responsive\" style\=\"display:inline-block\" src\=\"https\:\/\/static\.mfah\.com\/collection\/(\d+)\.jpg\?maxWidth\=550&maxHeight\=550&format\=jpg&quality\=90\" \/\>'
            pubdomainregex = u'\<div class\=\"text-muted text-left\" style\=\"border-top:1px solid #e0e0e0;margin-top:1em\"\>\<small\>Public Domain\<\/small\>\<\/div\>'

            imageidmatch = re.search(imageidregex, itempage.text)
            pubdomaimatch = re.search(pubdomainregex, itempage.text)

            if imageidmatch and pubdomaimatch:
                # They limit the max size to 3200 x 3200 so i'll use that
                metadata[u'imageurl'] = u'https://static.mfah.com/collection/%s.jpg?maxWidth=3200&maxHeight=3200&format=jpg' % (imageidmatch.group(1),)
                metadata[u'imageurlformat'] = u'Q2195' #JPEG
                #No license, just something about educational use. Commons is very educational.
                #metadata[u'imageurllicense'] = u'Q18199165' # cc-by-sa-4.0
                metadata[u'imageurlforce'] = False
            yield metadata


def main():
    dictGen = getMFAHGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
