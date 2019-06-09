#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Whitney Museum of American Art in New York to Wikidata.

Just loop over pages like https://whitney.org/collection/works?q%5Bclassification_cont%5D=Paintings

This bot does use artdatabot to upload it to Wikidata and just asks the API for all it's paintings.

"""
import artdatabot
import pywikibot
import requests
import re
import time
#import HTMLParser
import json

def getWhitneyGenerator():
    """
    Generator to return Whitney Museum of American Art paintings
    """

    whitneyArtists = getWhitneyArtistsOnWikidata()
    basesearchurl = u'https://whitney.org/api/html/artworks?_page=%s&q[classification_cont]=Paintings'
    #htmlparser = HTMLParser.HTMLParser()

    # It's sorted by date. Want to go from old to new
    for i in range(80, 0, -1):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = requests.get(searchurl)
        #urls = []

        workidregex = u'\<a href\=\"\/collection\/works\/(\d+)\"\>'
        matches = re.finditer(workidregex, searchPage.text)
        for match in matches:
            url = u'https://whitney.org/collection/works/%s' % (match.group(1),)
            metadata = {}

            print (url)

            itempage = requests.get(url)
            metadata['url'] = url

            metadata['collectionqid'] = u'Q639791'
            metadata['collectionshort'] = u'Whitney'
            metadata['locationqid'] = u'Q639791'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['artworkidpid'] = u'P6738'
            metadata['artworkid'] = u'%s' % (match.group(1),)

            metadata['idpid'] = u'P217'

            invregex = u'\<p\>\<strong\>Accession number\<\/strong\>\<br\/\>([^\<]+)\<\/p\>'

            invmatch = re.search(invregex, itempage.text)
            metadata['id'] = invmatch.group(1).strip()

            ldjsonregex = u'\<script type\=\"application\/ld\+json\"\>(\{.+\})\<\/script\>'
            ldjsonmatch = re.search(ldjsonregex, itempage.text)

            ldjson = json.loads(ldjsonmatch.group(1))
            #print (ldjson)

            title = ldjson.get('name')

            ## Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                  }

            name = ldjson.get('creator')[0].get('name')

            metadata['creatorname'] = name
            metadata['description'] = { u'nl' : u'schilderij van %s' % (name, ),
                                        u'en' : u'painting by %s' % (name, ),
                                        u'de' : u'Gemälde von %s' % (name, ),
                                        }

            artistid = ldjson.get('creator')[0].get('sameAs').replace('https://whitney.org/artists/', u'')
            print (artistid)
            if artistid in whitneyArtists:
                pywikibot.output (u'Found Whitney Museum of American Art artist ID %s on %s' % (artistid, whitneyArtists.get(artistid)))
                metadata['creatorqid'] = whitneyArtists.get(artistid)

            # Older paintings have more difficult dates
            dateregex = u'\<p\>\<strong\>Date\<\/strong\>\<br\/\>(\d\d\d\d)\<\/p\>'
            datecircaregex = u'\<p\>\<strong\>Date\<\/strong\>\<br\/\>c\.\s*(\d\d\d\d)\<\/p\>'
            shortperiodregex = u'\<p\>\<strong\>Date\<\/strong\>\<br\/\>(\d\d)(\d\d)–(\d\d)\<\/p\>'
            circashortperiodregex = u'\<p\>\<strong\>Date\<\/strong\>\<br\/\>c\.\s*(\d\d)(\d\d)–(\d\d)\<\/p\>'
            otherdateregex = u'\<p\>\<strong\>Date\<\/strong\>\<br\/\>([^\<]+)\<\/p\>'

            datematch = re.search(dateregex, itempage.text)
            datecircamatch = re.search(datecircaregex, itempage.text)
            shortperiodmatch = re.search(shortperiodregex, itempage.text)
            circashortperiodmatch = re.search(circashortperiodregex, itempage.text)
            otherdatematch = re.search(otherdateregex, itempage.text)
            if datematch:
                metadata['inception'] = datematch.group(1).strip()
            elif datecircamatch:
                metadata['inception'] = datecircamatch.group(1).strip()
                metadata['inceptioncirca'] = True
            elif shortperiodmatch:
                metadata['inceptionstart'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(2),))
                metadata['inceptionend'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(3),))
            elif circashortperiodmatch:
                metadata['inceptionstart'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(2),))
                metadata['inceptionend'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(3),))
                metadata['inceptioncirca'] = True
            elif otherdatematch:
                print (u'Could not parse date: "%s"' % (otherdatematch.group(1),))

            # No data, could do a trick with the inventory number
            # metadata['acquisitiondate'] = acquisitiondatematch.group(1)

            mediumregex = u'\<strong\>Medium\<\/strong\>[\r\n\t\s]*\<br\>[\r\n\t\s]*\<a href\=\"\/collection\/works\?q%5Bmedium_cont%5D\=Oil on canvas\"\>Oil on canvas\<\/a\>'
            mediumematch = re.search(mediumregex, itempage.text)
            if mediumematch:
                metadata['medium'] = u'oil on canvas'

            """

            measurementsregex = u'\<h2 class\=\"label\"\>Maße\<\/h2\>\s*\<\/div\>\s*\<div class\=\"medium-8 columns\"\>\s*\<p\>([^\<]+)\<\/p\>'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(1)
                regex_2d = u'(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) cm.*'
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
            yield metadata


def getWhitneyArtistsOnWikidata():
    '''
    Just return all the Whitney people as a dict
    :return: Dict
    '''
    result = {}
    query = u'SELECT ?item ?id WHERE { ?item wdt:P6714 ?id . ?item wdt:P31 wd:Q5 }'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = qid
    return result


def main():
    dictGen = getWhitneyGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
