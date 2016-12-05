#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import Hermitage paintings. No api, no csv, just plain old screen scraping stuff

* Loop over https://www.hermitagemuseum.org/wps/portal/hermitage/explore/collections/col-search/?lng=en&p1=category:%22Painting%22&p15=1
* Grab individual paintings like https://www.hermitagemuseum.org/wps/portal/hermitage/digital-collection/01.+Paintings/25685/ (remove the language)


"""
import artdatabot
import pywikibot
import requests
import re
import HTMLParser
import time

def getHermitageGenerator():
    '''
    Generator to return Hermitage paintings
    '''

    # Use one session for everything
    session = requests.Session()

    # 1 - 367
    searchBaseUrl = u'https://www.hermitagemuseum.org/wps/portal/hermitage/explore/collections/col-search/?lng=en&p1=category:%%22Painting%%22&p15=%s'
    baseUrl = u'https://www.hermitagemuseum.org%s'
    htmlparser = HTMLParser.HTMLParser()

    for i in range(1, 432):
        searchUrl = searchBaseUrl % (i,)
        print searchUrl
        searchPage = session.get(searchUrl, verify=False)

        # searchRegex = u'<div class="her-search-results-row">[\r\n\s]+<div class="her-col-35 her-search-results-img">[\r\n\s]+<a href="(/wps/portal/hermitage/digital-collection/01.+Paintings/\d+/)?lng=en"'
        searchRegex = u'<div class="her-search-results-row">[\r\n\s]+<div class="her-col-35 her-search-results-img">[\r\n\s]+<a href="(/wps/portal/hermitage/digital-collection/01\.\+Paintings/\d+/)\?lng=en"'
        matches = re.finditer(searchRegex, searchPage.text)
        for match in matches:
            metadata = {}

            metadata['collectionqid'] = u'Q132783'
            metadata['collectionshort'] = u'Hermitage'
            metadata['locationqid'] = u'Q132783'
            metadata['instanceofqid'] = u'Q3305213'
            
            metadata['url'] = baseUrl % match.group(1)
            metadata['url_en'] = '%s?lng=en' % (metadata['url'],)
            metadata['url_ru'] = '%s?lng=ru' % (metadata['url'],)

            # Don't go too fast
            # time.sleep(15)
            itemPageEn = requests.get(metadata['url_en'], verify=False)
            itemPageRu = requests.get(metadata['url_ru'], verify=False)
            print metadata['url_en']

            headerRegex = u'<header>[\r\n\s]+<h3>([^<]*)</h3>[\r\n\s]+<h1>([^<]*)</h1>[\r\n\s]+<p>([^<]*)</p>[\r\n\s]+</header>'
            matchEn = re.search(headerRegex, itemPageEn.text)
            if not matchEn:
                pywikibot.output(u'The data for this painting is BORKED!')
                continue

            matchRu = re.search(headerRegex, itemPageRu.text)


            metadata['title'] = { u'en' : htmlparser.unescape(matchEn.group(2)),
                                  u'ru' : htmlparser.unescape(matchRu.group(2)), 
                                  }

            painterName = matchEn.group(1)

            painterRegexes = [u'([^,]+),\s([^\.]+)\.(.+)',
                              u'([^,]+),\s([^,]+),(.+)',
                              ]
            for painterRegex in painterRegexes:
                painterMatch = re.match(painterRegex, painterName)
                if painterMatch:
                    painterName = '%s %s' % (painterMatch.group(2), painterMatch.group(1),)
                    continue

            if painterName==u'Unknown artist' or not painterName.strip():
                metadata['creatorname'] = u'anonymous'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
                metadata['creatorqid'] = u'Q4233718'
            else:
                metadata['creatorname'] = painterName

                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', painterName,),
                                            u'en' : u'%s by %s' % (u'painting', painterName,),
                                            }

            invRegex = u'\<p\>[\r\n\s]+Inventory Number:[\r\n\s]+\<\/p\>[\r\n\s]+\<\/div\>[\r\n\s]+\<div class=\"her-data-tbl-val\"\>[\r\n\s]+\<p\>[\r\n\s]+(.*\d+[^\>]+)[\r\n\s]+\<\/p\>'
            invMatch = re.search(invRegex, itemPageEn.text)

            if not invMatch:
                pywikibot.output(u'No inventory number found! Skipping')
                continue
            
            metadata['id'] = invMatch.group(1).strip()
            metadata['idpid'] = u'P217'

            materialregex = u'\<p\>[\r\n\s]+Material:[\r\n\s]+\<\/p\>[\r\n\s]+\<\/div\>[\r\n\s]+\<div class=\"her-data-tbl-val\"\>[\r\n\s]+\<a [^\>]+\>canvas\<\/a\>'
            techniqueregex = u'\<p\>[\r\n\s]+Technique:[\r\n\s]+\<\/p\>[\r\n\s]+\<\/div\>[\r\n\s]+\<div class=\"her-data-tbl-val\"\>[\r\n\s]+\<p\>[\r\n\s]+oil[\r\n\s]+\<\/p\>'

            materialMatch = re.search(materialregex, itemPageEn.text)
            techniqueMatch = re.search(techniqueregex, itemPageEn.text)

            if materialMatch and techniqueMatch:
                metadata['medium'] = u'oil on canvas'

            dateRegex = u'\<p\>[\r\n\s]+Date:[\r\n\s]+\<\/p\>[\r\n\s]+\<\/div\>[\r\n\s]+\<div class=\"her-data-tbl-val\"\>[\r\n\s]+\<a [^\>]+\>(\d\d\d\d)\<\/a\>'
            dateMatch = re.search(dateRegex, itemPageEn.text)
            if dateMatch:
                metadata['inception'] = dateMatch.group(1)

            dimRegex = u'\<p\>[\r\n\s]+Dimensions:[\r\n\s]+\<\/p\>[\r\n\s]+\<\/div\>[\r\n\s]+\<div class=\"her-data-tbl-val\"\>[\r\n\s]+\<p\>[\r\n\s]+([^\>]+)[\r\n\s]+\<\/p\>'
            dimMatch = re.search(dimRegex, itemPageEn.text)

            # Weird, sometimes they do width x height instead of height x width
            if dimMatch:
                dimtext = dimMatch.group(1).strip()
                regex_2d = u'(?P<height>\d+(,\d+)?)\s*x\s*(?P<width>\d+(,\d+)?)\s*cm.*'
                regex_3d = u'(?P<height>\d+(,\d+)?)\s*x\s*(?P<width>\d+(,\d+)?)\s*x\s*(?P<depth>\d+(,\d+)?)\s*cm.*'
                match_2d = re.match(regex_2d, dimtext)
                match_3d = re.match(regex_3d, dimtext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')
                elif match_3d:
                    metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
                    metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')

            yield metadata


def main():
    dictGen = getHermitageGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
