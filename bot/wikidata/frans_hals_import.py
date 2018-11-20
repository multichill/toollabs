#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Frans Hals Museum (Q574961) to Wikidata.

Just loop over pages like http://www.franshalsmuseum.nl/nl/collectie/zoeken-de-collectie/?q=&categorie=&kunstenaar=&page=1&techniek=olieverf

Only hit "olieverf op doek" (1397) and "olieverf op paneel" (534) out of the 2018 olieverf works.

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import HTMLParser

def getFransHalsGenerator():
    """
    Generator to return Frans Hals Museum paintings
    """
    basesearchurl = u'http://www.franshalsmuseum.nl/nl/collectie/zoeken-de-collectie/?q=&categorie=&kunstenaar=&techniek=olieverf&page=%s'
    htmlparser = HTMLParser.HTMLParser()

    # 2018 results, 22 per page (starting at 0)
    for i in range(1, 93):
        searchurl = basesearchurl % (i,)

        pywikibot.output(searchurl)
        searchPage = requests.get(searchurl)

        #urlregex = u'\<a href\=\"(\/art\/detail\/\d+)\?returnUrl\=[^\"]+\"\>[^\<]+\<\/a\>'
        urlregex = u'\<a title\=\"[^\"]+\" href\=\"(\/nl\/collectie\/zoeken-de-collectie\/[^\"]+/)\"\>'
        matches = re.finditer(urlregex, searchPage.text)
        for match in matches:
            metadata = {}
            url = u'http://www.franshalsmuseum.nl%s' % (match.group(1),)

            # Museum site probably doesn't like it when we go fast
            # time.sleep(5)

            pywikibot.output(url)


            itempage = requests.get(url)
            metadata['url'] = url

            metadata['collectionqid'] = u'Q574961'
            metadata['collectionshort'] = u'FHM'
            metadata['locationqid'] = u'Q574961'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'


            # Let's see if this one works or if we have to make it a bit more liberal
            invregex = u'\<th\>\<span\>Inventarisnummer\<\/span\>\<\/th\>\<td\>\<span\>([^\<]+)\<\/span\>\<\/td\>'
            invmatch = re.search(invregex, itempage.text)

            metadata['idpid'] = u'P217'
            metadata['id'] = invmatch.group(1).strip()

            titlecreatordateregex = u'\<h1\>([^\<]+)\<\/h1\>[\s\t\r\n]*\<h2\>[\s\t\r\n]*([^\<]+),[\s\t\r\n]*\<span\>([^\<]+)\<\/span\>'
            titlecreatorregex = u'\<h1\>([^\<]+)\<\/h1\>[\s\t\r\n]*\<h2\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/h2>'

            titlecreatordatematch = re.search(titlecreatordateregex, itempage.text)
            titlecreatormatch = re.search(titlecreatorregex, itempage.text)

            if titlecreatordatematch:
                title = htmlparser.unescape(titlecreatordatematch.group(1).strip())
                name = htmlparser.unescape(titlecreatordatematch.group(2).strip())
                metadata['inception'] = htmlparser.unescape(titlecreatordatematch.group(3).strip())
            else:
                title = htmlparser.unescape(titlecreatormatch.group(1).strip())
                name = htmlparser.unescape(titlecreatormatch.group(2).strip())

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'nl' : title,
                                  }

            metadata['creatorname'] = name
            metadata['description'] = { u'en' : u'painting by %s' % (name, ),
                                        u'nl' : u'schilderij van %s' % (name, ),
                                        }


            dimensionregex = u'\<th\>\<span\>Afmeting\<\/span\>\<\/th\>\<td\>\<span\>([^\<]+)\<\/span\>\<\/td\>'
            dimensionmatch = re.search(dimensionregex, itempage.text)
            if dimensionmatch:
                dimensiontext = dimensionmatch.group(1)
                regex_2d = u'(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) cm.*'
                regex_3d = u'(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) x (?P<depth>\d+(,\d+)?) cm.*'
                match_2d = re.match(regex_2d, dimensiontext)
                match_3d = re.match(regex_3d, dimensiontext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')
                elif match_3d:
                    metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
                    metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')

            rcecreditlineregex = u'\<th\>\<span\>Creditline\<\/span\>\<\/th\>\<td\>\<span\>In langdurig bruikleen van de Rijksdienst voor het Cultureel Erfgoed\<\/span\>\<\/td\>'
            rcecreditlinematch = re.search(rcecreditlineregex, itempage.text)
            if rcecreditlinematch:
                metadata[u'extracollectionqid'] = u'Q18600731'

            # Can't really find dates
            # metadata['acquisitiondate'] = acquisitiondatematch.group(1)

            mediumregex = u'\<th\>\<span\>Materiaal en techniek\<\/span\>\<\/th\>\<td\>\<span\>(olieverf op doek|olieverf op paneel|olieverf op koper|olieverf op doek op paneel|olieverf op papier op paneel)\<\/span\>\<\/td\>'
            mediummatch = re.search(mediumregex, itempage.text)

            # Only return if a valid medium is found
            if mediummatch:
                if mediummatch.group(1)==u'olieverf op doek':
                    metadata['medium'] = u'oil on canvas'
                yield metadata


def main():
    dictGen = getFransHalsGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
