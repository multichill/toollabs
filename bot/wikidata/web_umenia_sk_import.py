#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from https://www.webumenia.sk
* This will loop over a bunch of collections and for each collection
* Loop over https://www.webumenia.sk/en/katalog?work_type=maliarstvo&gallery=Slovensk%C3%A1+n%C3%A1rodn%C3%A1+gal%C3%A9ria%2C+SNG
* Grab individual paintings like https://www.webumenia.sk/en/dielo/SVK:SNG.O_184
Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re

try:
    from html.parser import HTMLParser
except ImportError:
    import HTMLParser

def getWebUmeniaGenerator(collectioninfo, webumeniaArtists):
    """
    Generator to return Web Umenia paintings

    Collectioninfo should be a dict with:
    * name - The English name (not actually used)
    * gallery - Urlencoded name of the gallery for query
    * artworks - Number of artworks so we can calculate the paging
    * collectionqid - qid of the collection to fill the dict
    * collectionshort - Abbreviation of the collection to fill the dict
    * locationqid - qid of the location (usually same as collection) to fill the dict
    
    """
    htmlparser = HTMLParser()
    baseSearchUrl = u'https://www.webumenia.sk/en/katalog?work_type=maliarstvo&gallery=%s&page=%s'

    pages = (collectioninfo.get(u'artworks') // 18) + 2

    for i in range(1, pages):
        searchUrl = baseSearchUrl % (collectioninfo.get(u'gallery'), i,)
        print (searchUrl)

        idlist = []

        searchPage = requests.get(searchUrl)
        searchPageData = searchPage.text
        searchRegex = u'\<a href\=\"https\:\/\/www\.webumenia\.sk\/dielo\/([^\"]+)"\s*\>'
        #\<div class\=\"gallery-item col-result\" data-url\=\"\/collection\/([^\"]+)\"'

        for match in re.finditer(searchRegex, searchPageData):
            idlist.append(match.group(1))

        for workid in list(set(idlist)):
            # Use the generic url for links, the itemurl to force download of English
            url = u'https://www.webumenia.sk/dielo/%s' % (workid,)
            itemurl = u'https://www.webumenia.sk/en/dielo/%s' % (workid,)

            print (itemurl)
            itemPage = requests.get(itemurl)
            itemPageData = itemPage.text

            metadata = {}
            metadata['url'] = url

            metadata['collectionqid'] = collectioninfo['collectionqid']
            metadata['collectionshort'] = collectioninfo['collectionshort']
            metadata['locationqid'] = collectioninfo['locationqid']

            # Search is for paintings
            metadata['instanceofqid'] = u'Q3305213'

            titleRegex = u'\<h1 class\=\"nadpis-dielo\" itemprop\=\"name\"\>([^\<]+)\<\/h1\>'
            titleMatch = re.search(titleRegex, itemPageData)


            title = htmlparser.unescape(titleMatch.group(1)).strip()
            #else:
            #    title = u'(without title)'

            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'sk' : title,
                              }

            metadata['idpid'] = u'P217'
            invRegex = u'\<td class\=\"atribut\"\>inventory number\:\<\/td\>[\r\n\t\s]*\<td\>([^\<]+)\<\/td\>'
            invMatch = re.search(invRegex, itemPageData)
            metadata['id'] = invMatch.group(1).strip()

            artistlinkRegex = u'\<span itemprop\=\"creator\" itemscope itemtype\=\"http\:\/\/schema\.org\/Person\"\>\<a class\=\"underline\" href\=\"https\:\/\/www\.webumenia\.sk\/autor\/(\d+)\" itemprop\=\"sameAs\"\>\<span itemprop\=\"name\"\>([^\<]+)\<\/span\>\<\/a\>\<\/span\>'
            artistlinkMatch = re.search(artistlinkRegex, itemPageData)

            if artistlinkMatch:
                artistid = htmlparser.unescape(artistlinkMatch.group(1)).strip()

                if artistid in webumeniaArtists:
                    print (u'Found Webumenia id %s on %s' % (artistid, webumeniaArtists.get(artistid)))
                    metadata['creatorqid'] = webumeniaArtists.get(artistid)
                else:
                    print (u'Did not find id %s' % (artistid,))
                name = htmlparser.unescape(artistlinkMatch.group(2)).strip()
            else:
                artistRegex = u'\<a class\=\"underline\" href\=\"https\:\/\/www\.webumenia\.sk\/katalog\?author\=[^\"]+\"\>([^\<]+)\<\/a\>'
                artistMatch = re.search(artistRegex, itemPageData)
                name = htmlparser.unescape(artistMatch.group(1)).strip()
            metadata['creatorname'] = name
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }

            # Only match on years
            dateRegex = u'\<td class\=\"atribut\"\>date\:\<\/td\>[\r\n\t\s]*\<td\>\<time itemprop\=\"dateCreated\" datetime\=\"(\d\d\d\d)\"\>'
            dateMatch = re.search(dateRegex, itemPageData)
            if dateMatch:
                metadata['inception'] = htmlparser.unescape(dateMatch.group(1))

            # acquisitiondate not available
            # acquisitiondateRegex = u'\<em\>Acknowledgement\<\/em\>\:\s*.+(\d\d\d\d)[\r\n\t\s]*\<br\>'
            #acquisitiondateMatch = re.search(acquisitiondateRegex, itemPageData)
            #if acquisitiondateMatch:
            #    metadata['acquisitiondate'] = acquisitiondateMatch.group(1)

            canvasRegex = u'\<span itemprop\=\"artMedium\"\>plátno<\/\span\>'
            canvasMatch = re.search(canvasRegex, itemPageData)

            oilRegex = u'\<a href\=\"https\:\/\/www\.webumenia\.sk\/katalog\?technique\=olej\"\>olej\<\/a\>'
            oilMatch = re.search(oilRegex, itemPageData)

            if canvasMatch and oilMatch:
                metadata['medium'] = u'oil on canvas'

            dimensionRegex = u'\<td class\=\"atribut\"\>measurements\:\<\/td\>[\r\n\t\s]*\<td\>[\r\n\t\s]*([^\<]+)[\r\n\t\s]*\<'
            dimensionMatch = re.search(dimensionRegex, itemPageData)

            if dimensionMatch:
                dimensions = htmlparser.unescape(dimensionMatch.group(1)).strip()
                regex_2d = u'^výška (?P<height>\d+(\.\d+)?)\s*cm,\s*šírka\s*(?P<width>\d+(\.\d+)?)\s*cm$'
                match_2d = re.match(regex_2d, dimensions)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height')
                    metadata['widthcm'] = match_2d.group(u'width')

            isfreeRegex = u'\<a rel\=\"license\" href\=\"https\:\/\/www\.webumenia\.sk\/katalog\?is_free\=1\"'
            isfreeMatch = re.search(isfreeRegex, itemPageData)

            downloadRegex = u'\<a href\=\"(https\:\/\/www\.webumenia\.sk\/dielo\/[^\"]+\/stiahnut)\" class\=\"btn btn-default btn-outline\s*sans\" id\=\"download\"\>\<i class\=\"fa fa-download\"\>\<\/i\>\s*download\s*\<\/a\>'
            downloadMatch = re.search(downloadRegex, itemPageData)

            if isfreeMatch and downloadMatch:
                metadata[u'imageurl'] = downloadMatch.group(1)
                metadata[u'imageurlformat'] = u'Q2195' #JPEG

            yield metadata

def webumeniaArtistsOnWikidata():
    '''
    Just return all the Web Umenia people as a dict
    :return: Dict
    '''
    result = {}
    query = u'SELECT ?item ?id WHERE { ?item wdt:P4887 ?id . ?item wdt:P31 wd:Q5 }'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = qid
    return result

def processCollection(collectioninfo, webumeniaArtists):

    dictGen = getWebUmeniaGenerator(collectioninfo, webumeniaArtists)

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()


def main(*args):
    collections = { u'Q1744024': { u'name' : u'Slovak National Gallery',
                                   u'gallery' : u'Slovenská+národná+galéria%2C+SNG',
                                   u'artworks' : 7021,
                                   u'collectionqid' : u'Q1744024',
                                   u'collectionshort' : u'SNG',
                                   u'locationqid' : u'Q1744024',
                                   },
                    u'Q50751848': { u'name' : u'Orava Gallery',
                                    u'gallery' : u'Oravská+galéria%2C+OGD',
                                    u'artworks' : 2231,
                                    u'collectionqid' : u'Q50751848',
                                    u'collectionshort' : u'Orava',
                                    u'locationqid' : u'Q50751848',
                                    },
                    u'Q30676307': { u'name' : u'Ernest Zmeták Art Gallery',
                                    u'gallery' : u'Galéria+umenia+Ernesta+Zmetáka%2C+GNZ',
                                    u'artworks' : 728,
                                    u'collectionqid' : u'Q30676307',
                                    u'collectionshort' : u'GNZ',
                                    u'locationqid' : u'Q30676307',
                                    },
                    u'Q50762402': { u'name' : u'Liptov Gallery of Peter Michal Bohúň',
                                    u'gallery' : u'Liptovská+galéria+Petra+Michala+Bohúňa%2C+GPB',
                                    u'artworks' : 1392,
                                    u'collectionqid' : u'Q50762402',
                                    u'collectionshort' : u'GPB',
                                    u'locationqid' : u'Q50762402',
                                    },
                    u'Q913415': { u'name' : u'Bratislava City Gallery',
                                    u'gallery' : u'Galéria+mesta+Bratislavy%2C+GMB',
                                    u'artworks' : 1510,
                                    u'collectionqid' : u'Q913415',
                                    u'collectionshort' : u'GMB',
                                    u'locationqid' : u'Q913415',
                                    },
                    u'Q12766245': { u'name' : u'Miloš Alexander Bazovský Gallery',
                                    u'gallery' : u'Galéria+Miloša+Alexandra+Bazovského%2C+GBT',
                                    u'artworks' : 193,
                                    u'collectionqid' : u'Q12766245',
                                    u'collectionshort' : u'MABG',
                                    u'locationqid' : u'Q12766245',
                                    },
                    u'Q50800751': { u'name' : u'Nitra Gallery',
                                    u'gallery' : u'Nitrianska+galéria%2C+NGN',
                                    u'artworks' : 12,
                                    u'collectionqid' : u'Q50800751',
                                    u'collectionshort' : u'NGN',
                                    u'locationqid' : u'Q50800751',
                                    },
                    u'Q16517556': { u'name' : u'Central Slovakian Gallery',
                                    u'gallery' : u'Stredoslovenská+galéria%2C+SGB',
                                    u'artworks' : 1561,
                                    u'collectionqid' : u'Q16517556',
                                    u'collectionshort' : u'SGB',
                                    u'locationqid' : u'Q16517556',
                                    },
                    u'Q50797802': { u'name' : u'Gallery of Spiš Artists ',
                                    u'gallery' : u'Galéria+umelcov+Spiša%2C+GUS',
                                    u'artworks' : 452,
                                    u'collectionqid' : u'Q50797802',
                                    u'collectionshort' : u'GUS',
                                    u'locationqid' : u'Q50797802',
                                    },
                 }
    collectionid = None

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-collectionid:'):
            if len(arg) == 14:
                collectionid = pywikibot.input(
                        u'Please enter the collectionid you want to work on:')
            else:
                collectionid = arg[14:]

    webumeniaArtists = webumeniaArtistsOnWikidata()

    if collectionid:
        if collectionid not in collections.keys():
            pywikibot.output(u'%s is not a valid collectionid!' % (collectionid,))
            return
        processCollection(collections[collectionid], webumeniaArtists)
    else:
        for collectionid in collections.keys():
            processCollection(collections[collectionid], webumeniaArtists)

if __name__ == "__main__":
    main()
