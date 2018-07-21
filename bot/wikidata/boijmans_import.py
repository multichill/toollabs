#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape paintings from the Boijmans website. Uses artdatabot to do the actual work


"""
import artdatabot
import pywikibot
import re
import HTMLParser
import requests

def getPaintingGenerator(boijmansartists):
    '''
    The Boijmans painting generator
    '''
    
    basesearchurl = u'http://collectie.boijmans.nl/nl/objects?start=%s&search=&sort=&filters=objecttype:schilderij'

    htmlparser = HTMLParser.HTMLParser()

    # http://collectie.boijmans.nl/nl?p=54&f.type=schilderij is acting up

    # Nerds start at 0
    for i in range(0, 2026, 25):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = requests.get(searchurl)

        urls = []
        urlregex = u'\<a href\=\"(http\:\/\/collectie\.boijmans\.nl\/nl\/object\/\d+)\/'
        matches = re.finditer(urlregex, searchPage.text)
        for match in matches:
            # To remove duplicates
            url = match.group(1)
            if url not in urls:
                urls.append(url)

        for url in urls:
            #url = u'http://collectie.boijmans.nl/nl/collection/%s' % (match.group(1),)
            urlen = url.replace(u'http://collectie.boijmans.nl/nl/object/', u'http://collectie.boijmans.nl/en/object/')

            print (url)
            itempage = requests.get(url)
            itemenpage = requests.get(urlen)

            if u'500 - Serverfout' in itempage.text:
                pywikibot.output(u'Getting a 500 - Serverfout at %s, skipping' % (url,))
                continue

            metadata = {}
            metadata['url'] = url
            metadata['describedbyurl'] = url.replace(u'http://collectie.boijmans.nl/nl/object/', u'http://collectie.boijmans.nl/object/')

            metadata['collectionqid'] = u'Q679527'
            metadata['collectionshort'] = u'Boijmans'
            metadata['locationqid'] = u'Q679527'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'

            metadata['artworkidpid'] = u'P5499'
            metadata['artworkid'] = url.replace(u'http://collectie.boijmans.nl/nl/object/', u'')

            invregex = u'\<th scope\=\"heading\"\>Inventarisnummer\<\/th\>[\s\t\r\n]*\<td\>([^\<]+)\<\/td\>'
            invmatch = re.search(invregex, itempage.text)

            metadata['id'] = invmatch.group(1).strip()

            titleregex = u'\<div class\=\"object_title bg\"\>[\s\t\r\n]*\<div class\=\"restrict\"\>[\s\t\r\n]*\<h1\>([^\<]+)\<\/h1\>'

            titlematch = re.search(titleregex, itempage.text)
            title = htmlparser.unescape(titlematch.group(1).strip())

            titleenmatch = re.search(titleregex, itemenpage.text)
            titleen = htmlparser.unescape(titleenmatch.group(1).strip())

            if len(title) > 220:
                title = title[0:200]

            if len(titleen) > 220:
                titleen = titleen[0:200]

            metadata['title'] = { u'en' : titleen,
                                  u'nl' : title,
                                  }

            creatorregex = u'\<th scope\=\"heading\"\>Makers\<\/th\>[\s\t\r\n]*\<td\>[\s\t\r\n]*\<span class\=\"subfield\"\>([^\<]+)\:\<\/span\>[\s\t\r\n]*\<a href\=\"http\:\/\/collectie\.boijmans\.nl\/nl\/maker\/(\d+)\/[^\"]*\"\>([^\<]+)\<\/a\>'

            creatormatch = re.search(creatorregex, itempage.text)

            if creatormatch and not creatormatch.group(3)==u'Anoniem':
                artistrole =  creatormatch.group(1)
                artistid = creatormatch.group(2)
                name = htmlparser.unescape(creatormatch.group(3)).strip()

                if artistrole==u'Kunstenaar' or artistrole==u'Schilder':
                    metadata['creatorname'] = name
                    metadata['description'] = { u'nl' : u'schilderij van %s' % (name, ),
                                                u'en' : u'painting by %s' % (name, ),
                                                }
                    if artistid in boijmansartists:
                        pywikibot.output (u'Found Boijmans id %s on %s' % (artistid, boijmansartists.get(artistid)))
                        metadata['creatorqid'] = boijmansartists.get(artistid)
                else:
                    metadata['description'] = { u'nl' : u'schilderij %s %s' % (artistrole.lower(), name, ),
                                                }

            else:
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous paintiner',
                                            }
                metadata['creatorqid'] = u'Q4233718'

            dateregex = u'filters\=date\%3A(\d\d\d\d)-(\d\d\d\d)\&amp\;0\"\>(\d\d\d\d)\<\/a\>'
            datematch = re.search(dateregex, itempage.text)
            if datematch:
                if datematch.group(1)==datematch.group(2) and datematch.group(1)==datematch.group(3):
                    metadata['inception'] = u'%s' % (datematch.group(1),)

            acquisitiondateregex = u'\<th scope\=\"heading\"\>Verwervingsdatum\<\/th\>[\s\t\r\n]*\<td\>\<a href\=\"[^\"]+\"\>([^<]+)\<\/td\>'
            acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            if acquisitiondatematch:
                metadata['acquisitiondate'] = acquisitiondatematch.group(1)

            mediumregex = u'\<th scope\=\"heading\"\>Materiaal en techniek\<\/th\>[\s\t\r\n]*\<td\>([^\<]+)\<\/td\>'
            mediummatch = re.search(mediumregex, itempage.text)

            # Only return if a valid medium is found
            if mediummatch:
                if mediummatch.group(1).lower()==u'olieverf op doek':
                    metadata['medium'] = u'oil on canvas'

            # Doing measurements in one go here because of the structure of the page
            measurements2dregex = u'\<th scope\=\"heading\"\>Afmetingen[\s\t\r\n]*\<\/th\>[\s\t\r\n]*\<td\>[\s\t\r\n]*\<span class\=\"subfield\"\>(?P<typeA>Hoogte|Breedte)\:\<\/span\>\s*(?P<valueA>\d+(,\d+)?)\s*cm\s*\<br\/\>[\s\t\r\n]*\<span class\=\"subfield\"\>(?P<typeB>Hoogte|Breedte)\:\<\/span\>\s*(?P<valueB>\d+(,\d+)?)\s*cm\<br\/\>[\s\t\r\n]*\<\/td\>'
            measurements3dregex = u'\<th scope\=\"heading\"\>Afmetingen[\s\t\r\n]*\<\/th\>[\s\t\r\n]*\<td\>[\s\t\r\n]*\<span class\=\"subfield\"\>(?P<typeA>Hoogte|Breedte|Diepte)\:\<\/span\>\s*(?P<valueA>\d+(,\d+)?)\s*cm\s*\<br\/\>[\s\t\r\n]*\<span class\=\"subfield\"\>(?P<typeB>Hoogte|Breedte|Diepte)\:\<\/span\>\s*(?P<valueB>\d+(,\d+)?)\s*cm\<br\/\>[\s\t\r\n]*\<span class\=\"subfield\"\>(?P<typeC>Hoogte|Breedte|Diepte)\:\<\/span\>\s*(?P<valueC>\d+(,\d+)?)\s*cm\<br\/\>[\s\t\r\n]*\<\/td\>'

            match_2d = re.search(measurements2dregex, itempage.text)
            match_3d = re.search(measurements3dregex, itempage.text)

            if match_2d:
                if match_2d.group(u'typeA') == u'Hoogte':
                    metadata['heightcm'] = match_2d.group(u'valueA').replace(u',', u'.')
                elif match_2d.group(u'typeA') == u'Breedte':
                    metadata['widthcm'] = match_2d.group(u'valueA').replace(u',', u'.')

                if match_2d.group(u'typeB') == u'Hoogte':
                    metadata['heightcm'] = match_2d.group(u'valueB').replace(u',', u'.')
                elif match_2d.group(u'typeB') == u'Breedte':
                    metadata['widthcm'] = match_2d.group(u'valueB').replace(u',', u'.')
            elif match_3d:
                if match_3d.group(u'typeA') == u'Hoogte':
                    metadata['heightcm'] = match_3d.group(u'valueA').replace(u',', u'.')
                elif match_3d.group(u'typeA') == u'Breedte':
                    metadata['widthcm'] = match_3d.group(u'valueA').replace(u',', u'.')
                elif match_3d.group(u'typeA') == u'Diepte':
                    metadata['depthcm'] = match_3d.group(u'valueA').replace(u',', u'.')

                if match_3d.group(u'typeB') == u'Hoogte':
                    metadata['heightcm'] = match_3d.group(u'valueB').replace(u',', u'.')
                elif match_3d.group(u'typeB') == u'Breedte':
                    metadata['widthcm'] = match_3d.group(u'valueB').replace(u',', u'.')
                elif match_3d.group(u'typeB') == u'Diepte':
                    metadata['depthcm'] = match_3d.group(u'valueB').replace(u',', u'.')

                if match_3d.group(u'typeC') == u'Hoogte':
                    metadata['heightcm'] = match_3d.group(u'valueC').replace(u',', u'.')
                elif match_3d.group(u'typeC') == u'Breedte':
                    metadata['widthcm'] = match_3d.group(u'valueC').replace(u',', u'.')
                elif match_3d.group(u'typeC') == u'Diepte':
                    metadata['depthcm'] = match_3d.group(u'valueC').replace(u',', u'.')

            yield metadata


def boijmansArtistsOnWikidata():
    '''
    Just return all the Boijmans people as a dict
    :return: Dict
    '''
    result = {}
    query = u'SELECT ?item ?id WHERE { ?item wdt:P3888 ?id . ?item wdt:P31 wd:Q5 }'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = qid
    return result


def main(*args):
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        if arg.startswith('-create'):
            create = True

    boijmansartists = boijmansArtistsOnWikidata()
    paintingGen = getPaintingGenerator(boijmansartists)

    if dryrun:
        for painting in paintingGen:
            print (painting)
    else:
        artDataBot = artdatabot.ArtDataBot(paintingGen, create=create)
        artDataBot.run()

if __name__ == "__main__":
    main()
