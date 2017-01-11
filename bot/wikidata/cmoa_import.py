#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Carnegie Museum of Art (Q1043967) to Wikidata.

Just loop over pages like http://collection.cmoa.org/collection-search/ classification "Painting" and "paintings"

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import HTMLParser

def getCarnegieGenerator():
    """
    Generator to return Carnegie Museum of Art paintings
    """

    urls = []

     # First get the Painting

    # And let's get the paintings too

    apiurl = u'http://collection.cmoa.org/CollectionSearch.aspx/GetSearchResults'
    postjson = u'{"SearchText": "", "Nationality": "Any", "DateRange": "Any", "Classification": "%s", "Theme": "Any", "Department": "Any", "Location": "Any", "WithImages": "false", "WithVideo": "false", "WithAudio": "false", "TeenieHarris": "false", "SortOrder": "alpha-artist", "PageNumber": "%s", "NumberPerPage": "48", "PriorParams": "%s"}'
    #postjson = u'{"SearchText": "", "Nationality": "Any", "DateRange": "Any", "Classification": "%s", "Theme": "Any", "Department": "Any", "Location": "Any", "WithImages": "false", "WithVideo": "false", "WithAudio": "false", "TeenieHarris": "false", "SortOrder": "alpha-artist", "PageNumber": "%s", "NumberPerPage": "48", "PriorParams": "Y2xhc3NpZmljYXRpb249UGFpbnRpbmd8"}'
    referer = u'http://collection.cmoa.org/collection-search/'
    #for classification in [u'Painting', u'paintings']:
    #firsturl = u'http://collection.cmoa.org/collection-search/'

    htmlparser = HTMLParser.HTMLParser()

    session = requests.Session()
    searchPage = session.get(referer)

    urlregex = u'\<a href\=\"(CollectionDetail\.aspx\?item\=\d+)\&'

    tosearch = [(u'Painting', 12, u'Y2xhc3NpZmljYXRpb249UGFpbnRpbmd8'), # 488, 48 per page
                #(u'paintings', 13, u'Y2xhc3NpZmljYXRpb249cGFpbnRpbmdzfA9999'), # 605, 48 per page
                ]
    for (classification, endpage, priorsearch) in tosearch:
        for i in range(1,endpage):
            try:
                searchpage = session.post(apiurl,
                                           data=postjson % (classification, i, priorsearch, ),
                                           headers={'X-Requested-With' : 'XMLHttpRequest',
                                                    'referer' : referer,
                                                    u'Content-Type' : u'application/json; charset=utf-8'}
                                           )
            except requests.exceptions.ConnectionError:
                pywikibot.output(u'Could not get the search page. Sleeping and trying again')
                time.sleep(60)
                searchpage = session.post(apiurl,
                                          data=postjson % (classification, i, priorsearch, ),
                                          headers={'X-Requested-With' : 'XMLHttpRequest',
                                                   'referer' : referer,
                                                   u'Content-Type' : u'application/json; charset=utf-8'}
                                          )
            #print apiurl
            #print postjson % (classification, i,)
            #print searchpage.text
            searchjson =  searchpage.json()
            matches = re.finditer(urlregex, searchjson.get(u'd'))
            for match in matches:
                metadata = {}
                url = u'http://collection.cmoa.org/%s' % (match.group(1),)

                # Museum site probably doesn't like it when we go fast
                time.sleep(5)

                pywikibot.output(url)

                itempage = requests.get(url)
                metadata['url'] = url

                metadata['collectionqid'] = u'Q1043967'
                metadata['collectionshort'] = u'CMoA'
                metadata['locationqid'] = u'Q1043967'

                #No need to check, I'm actually searching for paintings.
                metadata['instanceofqid'] = u'Q3305213'

                titlecreatorregex = u'\<div id\=\"detail-data-container\"\>[\s\t\r\n]*\<hgroup class\=\"page-titles\"\>[\s\t\r\n]*\<h1 class\=\"italic\"\>(?P<title>[^\<]+)\<\/h1\>[\s\t\r\n]*\<h2 class\=\"sub1\"\>(?P<name>[^\<]+)\<\/h2\>[\s\t\r\n]*\<h2 class\=\"sub2\"\>(?P<date>[^\<]+)?\<\/h2\>'
                titlecreatormatch = re.search(titlecreatorregex, itempage.text)

                title = htmlparser.unescape(titlecreatormatch.group(u'title').strip())
                name = htmlparser.unescape(titlecreatormatch.group(u'name').strip())

                # Chop chop, in case we have very long titles
                if title > 220:
                    title = title[0:200]
                metadata['title'] = { u'en' : title,
                                      }
                metadata['creatorname'] = name
                metadata['description'] = { u'en' : u'painting by %s' % (name, ),
                                            u'nl' : u'schilderij van %s' % (name, ),
                                            }

                if titlecreatormatch.group(u'date'):
                    metadata['inception'] = htmlparser.unescape(titlecreatormatch.group(u'date').strip())



                idregex = u'\<span class\=\"label\"\>Accession Number\<\/span\>[\s\t\r\n]*\<span class\=\"value\"\>([^\<]+)\<\/span\>'
                idmatch = re.search(idregex, itempage.text)
                metadata['idpid'] = u'P217'
                metadata['id'] = idmatch.group(1).strip()

                mediumregex = u'\<span class\=\"label\"\>Medium\<\/span\>[\s\t\r\n]*\<span class\=\"value\"\>oil on canvas\<\/span\>'
                mediummatch = re.search(mediumregex, itempage.text)
                if mediummatch:
                    metadata['medium'] = u'oil on canvas'

                dimensionsregex = u'\<span class\=\"label\"\>Measurements\<\/span\>[\s\t\r\n]*\<span class\=\"value\"\>([^\<]+)\<\/span\>'
                dimensionsmatch = re.search(dimensionsregex, itempage.text)

                if dimensionsmatch:
                    dimensiontext = dimensionsmatch.group(1).strip()
                    regex_2d = u'.+\((?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) cm\)$'
                    regex_3d = u'.+\((?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) x (?P<depth>\d+(\.\d+)?) cm\)$'
                    match_2d = re.match(regex_2d, dimensiontext)
                    match_3d = re.match(regex_3d, dimensiontext)
                    if match_2d:
                        metadata['heightcm'] = match_2d.group(u'height')
                        metadata['widthcm'] = match_2d.group(u'width')
                    elif match_3d:
                        metadata['heightcm'] = match_3d.group(u'height')
                        metadata['widthcm'] = match_3d.group(u'width')
                        metadata['depthcm'] = match_3d.group(u'depth')

                yield metadata


def main():
    dictGen = getCarnegieGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
