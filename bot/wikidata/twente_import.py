#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to upload the paintings of the Rijksmuseum Twente

Use api under https://collectie.rijksmuseumtwenthe.nl

"""
import json
import requests
import artdatabot
import pywikibot
import re
import time
#import HTMLParser

def rkdArtistsOnWikidata():
    '''
    Twente has a RKDartist link for every work. Make a lookup table
    :return: Dict
    '''
    result = {}
    sq = pywikibot.data.sparql.SparqlQuery()
    query = u'SELECT ?item ?id WHERE { ?item wdt:P650 ?id  }'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[int(resultitem.get('id'))] = qid
    return result

def getTwentePaintingGenerator():
    '''
    Generate the paintings based on the JSON file you can find at http://kokoelmat.fng.fi/api/v2support/docs/#/download

    Yield the dict items suitable for artdatabot
    '''

    apiurl = u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie'
    postjson = u''
    referer = apiurl
    searchurl = u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:"olieverf op doek"' # 5 pagina's
    #searchurl = u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:"olieverf op paneel"' # 3 pagina's
    #searchurl = u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?q=search_s_creator_rkd:("https://rkd.nl/explore/artists/39877") AND -id:"01e10f50-bc52-5f8b-a675-91702dbb586f"'

    #htmlparser = HTMLParser.HTMLParser()

    #session = requests.Session()
    #searchPage = session.get(referer, verify=False)

    rkdartists = rkdArtistsOnWikidata()

    tosearch = [(u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:"olieverf op doek"', 6),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:"olieverf op paneel"', 4),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22acryl%20op%20doek%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%20op%20doek%20op%20karton%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%20op%20papier%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%20op%20koper%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%20op%20doek%20op%20spaanplaat%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%20op%20hardboard%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22doek%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%20of%20acryl%20op%20doek%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%20of%20acryl?%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%20op%20karton%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%20op%20doek%20op%20paneel%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%20op%20linnen%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%20op%20papier%20op%20paneel%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%20en%20acryl%20op%20doek%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%20op%20board%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%20op%20doek%20op%20MDF%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf,%20potlood%20en%20zeefdruk%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%20op%20doek%20op%20board%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22olieverf%20op%20doek%20op%20meubelplaat%22', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?fq[0]=search_s_medium:%22tempera%20en%20olieverf%20(?)%20op%20paneel%22', 2),
                ]
    tosearch = [(u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?q=paneel', 5),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?q=doek', 8),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?q=tempera', 2),
                (u'https://collectie.rijksmuseumtwenthe.nl/zoeken-in-de-collectie?q=olieverf', 10),
                ]


    for (basesearchurl, pages) in tosearch:
        for i in range(1,pages):
            searchurl= basesearchurl + u'&page=%s' % (i,)
            searchpage = requests.post(searchurl,
                                      headers={'X-Requested-With' : 'XMLHttpRequest',
                                               'referer' : referer,
                                               u'Content-Type' : u'application/json'},

                                              )

            #print (searchpage.text)
            searchjson =  searchpage.json()
            for item in searchjson.get('media'):
                metadata = {}

                url = u'https://collectie.rijksmuseumtwenthe.nl%s' % (item.get('link'),)

                pywikibot.output(url)
                # Museum site probably doesn't like it when we go fast
                time.sleep(1)
                itempage = requests.get(url)
                metadata['url'] = url


                metadata['collectionqid'] = u'Q1505892'
                metadata['collectionshort'] = u'RMT'
                metadata['locationqid'] = u'Q1505892'

                #No need to check, I'm actually searching for paintings.
                metadata['instanceofqid'] = u'Q3305213'
                # We only have the title in Dutch
                metadata['title'] = {}
                metadata['title']['nl'] = item.get('title')

                # We pretty much exhausted the json. Time for regexes
                # First the inventory number
                idregex = u'\<span class\=\"label\"\>Accession Number\<\/span\>[\s\t\r\n]*\<span class\=\"value\"\>([^\<]+)\<\/span\>'
                idregex = u'\<div class\=\"ds-field dc_identifier\"\>[\s\t\r\n]*\<span class\=\"ds-field-value\" property\=\"dc:identifier\"\>[\s\t\r\n]*inv\.\s([^\<]+)[\s\t\r\n]*\<\/span\>'
                idmatch = re.search(idregex, itempage.text)
                metadata['idpid'] = u'P217'
                metadata['id'] = idmatch.group(1).strip()

                rkdnameregex = u'\<div class\=\"ds-field foaf_name \"\>[\s\t\r\n]*\<a href\=\"https\:\/\/rkd\.nl\/explore\/artists\/(\d+)\" target\=\"_blank\"\>[\s\t\r\n]*\<span class\=\"ds-field-value foaf-name tag-rmt\" property\=\"foaf:name\"\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/span\>'
                rkdnamematch = re.search(rkdnameregex, itempage.text)
                nameregex = u'\<span class\=\"ds-field-value foaf-name tag-rmt\" property\=\"foaf:name\"\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/span\>'
                namematch = re.search(nameregex, itempage.text)
                if rkdnamematch:
                    rkdid = rkdnamematch.group(1).strip()
                    if int(rkdid) in rkdartists:
                        metadata['creatorqid'] = rkdartists.get(int(rkdid))
                    name = rkdnamematch.group(2).strip()
                else:
                    name = namematch.group(1).strip()
                metadata['creatorname'] = name
                metadata['description'] = { u'en' : u'painting by %s' % (name, ),
                                            u'nl' : u'schilderij van %s' % (name, ),
                                            }

                # Inception
                dateregex = u'\<span class\=\"dc_date\"\>[\s\t\r\n]*(\d\d\d\d)[\s\t\r\n]*\<\/span\>'
                datematch = re.search(dateregex, itempage.text)
                if datematch:
                    metadata['inception'] = datematch.group(1).strip()
                # Oil on canvas
                mediumregex = u'\<span class\=\"ds-field-value\" property\=\"nave\:material\"\>[\s\t\r\n]*olieverf op doek[\s\t\r\n]*\<\/span\>'
                mediummatch = re.search(mediumregex, itempage.text)
                if mediummatch:
                    metadata['medium'] = u'oil on canvas'

                # Size
                # FIXME: Doesn't seem to match everything
                dimensionsregex = u'\<span class\=\"ds-field-value\" property\=\"nave\:dimension\">[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/span\>'
                dimensionsmatch = re.search(dimensionsregex, itempage.text)
                if dimensionsmatch:
                    dimensiontext = dimensionsmatch.group(1).strip()
                    regex_2d = u'(?P<height>\d+(,\d+)?) (x|×) (?P<width>\d+(,\d+)?) cm$'
                    match_2d = re.match(regex_2d, dimensiontext)
                    if match_2d:
                        metadata['heightcm'] = match_2d.group(u'height').replace(',', '.')
                        metadata['widthcm'] = match_2d.group(u'width').replace(',', '.')

                downloadregex = u'data-media-download\=\"(http\:\/\/images\.memorix\.nl\/rmt\/download\/default\/[^\"]+\.jpg)\"'
                downloadmatch = re.search(downloadregex, itempage.text)

                if downloadmatch:
                    metadata[u'imageurl'] = downloadmatch.group(1)
                    metadata[u'imageurlformat'] = u'Q2195' #JPEG

                yield metadata


def main(*args):
    paintingGen = getTwentePaintingGenerator()

    #for painting in paintingGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(paintingGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
