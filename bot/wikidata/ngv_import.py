#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape paintings from the National Gallery of Victoria website.

https://www.ngv.vic.gov.au/explore/collection/collection-areas/?area=painting

"""
import artdatabot
import pywikibot
import re
import HTMLParser
import requests

def ngvArtistOnWikidata():
    '''
    Just return all the NGV people as a dict
    :return: Dict
    '''
    result = {}
    query = u'SELECT ?item ?id WHERE { ?item wdt:P2041 ?id . ?item wdt:P31 wd:Q5 } LIMIT 10000003'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = qid
    return result

def getNGVGenerator():
    '''

    Doing a two step approach here. 
    * Loop over https://www.ngv.vic.gov.au/explore/collection/collection-areas/?area=painting&from=1 - 202 and grab paintings
    * Grab data from paintings
    '''

    baseurl = u'https://www.ngv.vic.gov.au/explore/collection/collection-areas/?area=painting&from=%s'

    htmlparser = HTMLParser.HTMLParser()
    session = requests.session()

    ngvArtistIds = ngvArtistOnWikidata()
    missedNgvIds = {}

    # 0 - 202

    for i in range(0, 203):
        searchurl = baseurl % (i,)
        pywikibot.output(searchurl)
        searchPage = session.get(searchurl)
        searchData = searchPage.text
        # <span class="italic"><a href="/aic/collections/artwork/47149?search_no=

        itemregex = u'<li class="exploreListingTile">\s*<a href="//www.ngv.vic.gov.au/explore/collection/work/(?P<id>\d+)">\s*<div class="work-image[^>]+>\s*</div>\s*<h3 class="title">(?P<title>[^>]+)</h3>\s*<h4 class="artist">(?P<artist>[^>]+)</h4>\s*</a>\s*</li>'

        for match in re.finditer(itemregex, searchData, flags=re.M):
            metadata = {}
            # No ssl, faster?
            url = u'https://www.ngv.vic.gov.au/explore/collection/work/%s/' % (match.group('id'),)
            metadata['url'] = url

            metadata['artworkid'] = match.group('id')
            metadata['artworkidpid'] = u'P4684'

            metadata['collectionqid'] = u'Q1464509'
            metadata['collectionshort'] = u'NGV'
            metadata['locationqid'] = u'Q1464509'

            # Search is for paintings
            metadata['instanceofqid'] = u'Q3305213'

            title = htmlparser.unescape(match.group('title'))
            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]

            metadata['title'] = { u'en' : title,
                                  }
            artistparts = htmlparser.unescape(match.group('artist')).split(u' ')

            creator = u''
            for artistpart in artistparts:
                if creator==u'':
                    creator = artistpart.capitalize()
                else:
                    creator = creator + u' ' + artistpart.capitalize()

            # Chop chop, several very long creator lists
            if len(creator) > 220:
                creator = creator[0:200]

            metadata['creatorname'] = creator

            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }

            itemPage = requests.get(url)
            itemData = itemPage.text

            metadata['idpid'] = u'P217'
            idregex = u'<dt>Accession Number</dt>\s*<dd>([^<]+)</dd>'
            idmatch = re.search(idregex, itemData, flags=re.M)
            metadata[u'id']=htmlparser.unescape(idmatch.group(1))

            # Get artist ID from url
            artistidregex = u'\<ul class\=\"artist-list\"\>\s*\<li\>\s*\<a href\=\"\/explore\/collection\/artist\/(\d+)\"\>'
            artistidmatch = re.search(artistidregex, itemData, flags=re.M)
            artistid = artistidmatch.group(1)
            if artistid in ngvArtistIds:
                print u'Found NGV id %s on %s' % (artistid, ngvArtistIds.get(artistid))
                metadata['creatorqid'] = ngvArtistIds.get(artistid)
            else:
                print u'Did not find id %s' % (artistid,)
                if artistid not in missedNgvIds:
                    missedNgvIds[artistid] = 0
                missedNgvIds[artistid] = missedNgvIds[artistid] + 1


            mediumregex = u'<dt>Medium</dt>\s*<dd>([^<]+)</dd>'
            mediummatch = re.search(mediumregex, itemData, flags=re.M)

            if mediummatch and mediummatch.group(1).strip().lower()==u'oil on canvas':
                metadata['medium'] = u'oil on canvas'

            dateregex = u'<h1>.+</em>\s*(\d\d\d\d)\s*</h1>'
            datematch = re.search(dateregex, itemData, flags=re.M|re.S)
            # Only matches on exact years
            if datematch:
                metadata[u'inception']=datematch.group(1)

            creditregex = u'<dd>([^<]+)\s*<br/>([^<]+), (\d\d\d\d)\s*(<br/>&copy; Public Domain\s*)?</dd>'
            creditmatch = re.search(creditregex, itemData, flags=re.M)

            # Matches most of the time, but not on things like http://www.ngv.vic.gov.au/explore/collection/work/4178/ (187l -> 1871)
            if creditmatch:
                #metadata[u'credit'] = htmlparser.unescape(unicode(creditmatch.group(1), "utf-8")).strip() + u' ' + htmlparser.unescape(unicode(creditmatch.group(2), "utf-8")).strip() + u', ' + htmlparser.unescape(unicode(creditmatch.group(3), "utf-8"))
                metadata[u'acquisitiondate'] = htmlparser.unescape(creditmatch.group(3))

            dimensionRegex = u'\<dt\>Measurements\<\/dt\>\s*<dd>([^\<]+)\<\/dd\>'
            dimensionMatch = re.search(dimensionRegex, itemData, flags=re.M)

            if dimensionMatch:
                dimensiontext = dimensionMatch.group(1).strip()
                regex_2d = u'^(?P<height>\d+(\.\d+)?)\s*\&times\;\s*(?P<width>\d+(\.\d+)?)\s*cm$'
                #regex_3d = u'^.+\((?P<height>\d+(\.\d+)?)\s*(cm\s*)?(x|×)\s*(?P<width>\d+(\.\d+)?)\s*(cm\s*)?(x|×)\s*(?P<depth>\d+(\.\d+)?)\s*cm\)$'
                match_2d = re.match(regex_2d, dimensiontext)
                #match_3d = re.match(regex_3d, dimensiontext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height')
                    metadata['widthcm'] = match_2d.group(u'width')
                #if match_3d:
                #    metadata['heightcm'] = match_3d.group(u'height')
                #    metadata['widthcm'] = match_3d.group(u'width')
                #    metadata['depthcm'] = match_3d.group(u'depth')
            yield metadata
    print u'The top 50 NGV artists id\'s that are missing in this run:'
    for identifier in sorted(missedNgvIds, key=missedNgvIds.get, reverse=True)[:50]:
        print u'* https://www.ngv.vic.gov.au/explore/collection/artist/%s/ - %s'  % (identifier, missedNgvIds[identifier])

def main():
    dictGen = getNGVGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
