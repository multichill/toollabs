#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from https://www.webumenia.sk
* This will loop over a bunch of collections and for each collection
* Old system: Loop over https://www.webumenia.sk/en/katalog?work_type=maliarstvo&gallery=Slovensk%C3%A1+n%C3%A1rodn%C3%A1+gal%C3%A9ria%2C+SNG
* New system: Ask the api at http://api.webumenia.sk ( https://github.com/SlovakNationalGallery/web-umenia-2/wiki/ElasticSearch-Public-API )
* Grab individual paintings like https://www.webumenia.sk/en/dielo/SVK:SNG.O_184 as items in the API
Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import json

def getWebUmeniaGenerator(collectioninfo, webumeniaArtists):
    """
    Generator to return Web Umenia paintings

    Collectioninfo should be a dict with:
    * name - The English name (not actually used)
    * gallery - (not urlencoded) name of the gallery for query
    * artworks - Number of artworks so we can calculate the paging
    * collectionqid - qid of the collection to fill the dict
    * collectionshort - Abbreviation of the collection to fill the dict
    * locationqid - qid of the location (usually same as collection) to fill the dict
    """

    baseSearchUrl = u'http://api.webumenia.sk/items/_search'
    size = 100
    session = requests.Session()
    #session.auth = ('', '') set in your .netrc file, see https://www.labkey.org/Documentation/wiki-page.view?name=netrc

    # Topics to genre
    topics = { u'portrét' : u'Q134307', # https://www.webumenia.sk/en/katalog?topic=portr%C3%A9t -> portrait
               u'náboženský motív' : u'Q2864737', # https://www.webumenia.sk/en/katalog?topic=n%C3%A1bo%C5%BEensk%C3%BD%20mot%C3%ADv -> religious art
               u'krajina' : u'Q191163', # https://www.webumenia.sk/en/katalog?work_type=maliarstvo&topic=krajina -> landscape art
               }

    # TODO: Get number of artworks from API instead of hard coding

    for i in range(0, collectioninfo.get(u'artworks'), size):
        searchdata = { u'size' : size,
                       u'from' : i,
                       u'query': { u'bool': { u'must': [
                           { u'match': { u'gallery': collectioninfo.get(u'gallery') }},
                           { u'match': { u'work_type': u'maliarstvo' }},
                       ] } },}
        data = json.dumps(searchdata)
        page = session.get(baseSearchUrl, data=data)
        #print (json.dumps(page.json(), indent = 2, separators=(',', ': ')))
        for bigitem in page.json().get(u'hits').get(u'hits'):
            item = bigitem.get(u'_source')

            # Use the generic url for links, this will resolve to English for most of us
            url = u'https://www.webumenia.sk/dielo/%s' % (item.get('id'),)
            pywikibot.output (url)

            metadata = {}
            metadata['url'] = url

            metadata['collectionqid'] = collectioninfo['collectionqid']
            metadata['collectionshort'] = collectioninfo['collectionshort']
            metadata['locationqid'] = collectioninfo['locationqid']

            # Search is for paintings
            metadata['instanceofqid'] = u'Q3305213'

            title = item.get(u'title')

            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'sk' : title,
                                  }

            # I had one item with missing identifier, wonder if it shows up here too
            metadata['idpid'] = u'P217'
            if not item.get('identifier'):
                # Few rare items without an inventory number, just skip them
                continue
            metadata['id'] = item.get('identifier')

            # Get the  Web umenia work ID (P5269)
            metadata['artworkid'] = url.replace(u'https://www.webumenia.sk/dielo/', u'')
            metadata['artworkidpid'] = u'P5269'

            name = item.get('author')[0]
            if u',' in name:
                (surname, sep, firstname) = name.partition(u',')
                name = u'%s %s' % (firstname.strip(), surname.strip(),)
            metadata['creatorname'] = name

            metadata['creatorname'] = name
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }
            if item.get('authority_id') and item.get('authority_id')[0]:
                artistid = item.get('authority_id')[0]
                if artistid in webumeniaArtists:
                    pywikibot.output (u'Found Webumenia id %s on %s' % (artistid, webumeniaArtists.get(artistid)))
                    metadata['creatorqid'] = webumeniaArtists.get(artistid)

            if item.get(u'date_earliest') and item.get(u'date_earliest')==item.get(u'date_latest'):
                metadata['inception'] = item.get(u'date_earliest')
            elif item.get(u'date_earliest') and item.get(u'date_latest'):
                if 1000 < item.get(u'date_earliest') < 2500 and 1000 < item.get(u'date_latest') < 2500:
                    metadata['inceptionstart'] = item.get(u'date_earliest')
                    metadata['inceptionend'] = item.get(u'date_latest')

            # acquisitiondate not available
            # acquisitiondateRegex = u'\<em\>Acknowledgement\<\/em\>\:\s*.+(\d\d\d\d)[\r\n\t\s]*\<br\>'
            #acquisitiondateMatch = re.search(acquisitiondateRegex, itemPageData)
            #if acquisitiondateMatch:
            #    metadata['acquisitiondate'] = acquisitiondateMatch.group(1)

            if item.get(u'medium') and item.get(u'medium')==u'plátno' and item.get(u'technique') and \
                item.get(u'technique')[0] and item.get(u'technique')[0]==u'olej':
                metadata['medium'] = u'oil on canvas'

            # Add the genre based on the topic. Only when we have one topic
            if item.get(u'topic') and len(item.get(u'topic'))==1:
                if item.get(u'topic')[0] in topics:
                    metadata[u'genreqid'] = topics.get(item.get(u'topic')[0])

            # The search API returns null for measurement
            # Already indexed it in the previous run so leaving it for now
            #dimensionRegex = u'\<td class\=\"atribut\"\>measurements\:\<\/td\>[\r\n\t\s]*\<td\>[\r\n\t\s]*([^\<]+)[\r\n\t\s]*\<'
            #dimensionMatch = re.search(dimensionRegex, itemPageData)
            #if dimensionMatch:
            #    dimensions = htmlparser.unescape(dimensionMatch.group(1)).strip()
            #    regex_2d = u'^výška (?P<height>\d+(\.\d+)?)\s*cm,\s*šírka\s*(?P<width>\d+(\.\d+)?)\s*cm$'
            #    match_2d = re.match(regex_2d, dimensions)
            #    if match_2d:
            #        metadata['heightcm'] = match_2d.group(u'height')
            #        metadata['widthcm'] = match_2d.group(u'width')

            if item.get(u'has_image') and item.get(u'is_free') and item.get(u'has_iip'):
                metadata[u'imageurl'] = u'https://www.webumenia.sk/dielo/%s/stiahnut' % (item.get('id'),)
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

def processCollection(collectioninfo, webumeniaArtists, dryrun=False, create=False):

    dictGen = getWebUmeniaGenerator(collectioninfo, webumeniaArtists)

    if dryrun:
        for painting in dictGen:
            print (painting)
    else:
        artDataBot = artdatabot.ArtDataBot(dictGen, create=create)
        artDataBot.run()


def main(*args):
    collections = { u'Q1744024': { u'name' : u'Slovak National Gallery',
                                   u'gallery' : u'Slovenská národná galéria, SNG',
                                   u'artworks' : 7054,
                                   u'collectionqid' : u'Q1744024',
                                   u'collectionshort' : u'SNG',
                                   u'locationqid' : u'Q1744024',
                                   },
                    u'Q50751848': { u'name' : u'Orava Gallery',
                                    u'gallery' : u'Oravská galéria, OGD',
                                    u'artworks' : 2231,
                                    u'collectionqid' : u'Q50751848',
                                    u'collectionshort' : u'Orava',
                                    u'locationqid' : u'Q50751848',
                                    },
                    u'Q30676307': { u'name' : u'Ernest Zmeták Art Gallery',
                                    u'gallery' : u'Galéria umenia Ernesta Zmetáka, GNZ',
                                    u'artworks' : 728,
                                    u'collectionqid' : u'Q30676307',
                                    u'collectionshort' : u'GNZ',
                                    u'locationqid' : u'Q30676307',
                                    },
                    u'Q50762402': { u'name' : u'Liptov Gallery of Peter Michal Bohúň',
                                    u'gallery' : u'Liptovská galéria Petra Michala Bohúňa, GPB',
                                    u'artworks' : 1392,
                                    u'collectionqid' : u'Q50762402',
                                    u'collectionshort' : u'GPB',
                                    u'locationqid' : u'Q50762402',
                                    },
                    u'Q913415': { u'name' : u'Bratislava City Gallery',
                                    u'gallery' : u'Galéria mesta Bratislavy, GMB',
                                    u'artworks' : 1510,
                                    u'collectionqid' : u'Q913415',
                                    u'collectionshort' : u'GMB',
                                    u'locationqid' : u'Q913415',
                                    },
                    u'Q12766245': { u'name' : u'Miloš Alexander Bazovský Gallery',
                                    u'gallery' : u'Galéria Miloša Alexandra Bazovského, GBT',
                                    u'artworks' : 193,
                                    u'collectionqid' : u'Q12766245',
                                    u'collectionshort' : u'MABG',
                                    u'locationqid' : u'Q12766245',
                                    },
                    u'Q50800751': { u'name' : u'Nitra Gallery',
                                    u'gallery' : u'Nitrianska galéria, NGN',
                                    u'artworks' : 44,
                                    u'collectionqid' : u'Q50800751',
                                    u'collectionshort' : u'NGN',
                                    u'locationqid' : u'Q50800751',
                                    },
                    u'Q16517556': { u'name' : u'Central Slovakian Gallery',
                                    u'gallery' : u'Stredoslovenská galéria, SGB',
                                    u'artworks' : 1561,
                                    u'collectionqid' : u'Q16517556',
                                    u'collectionshort' : u'SGB',
                                    u'locationqid' : u'Q16517556',
                                    },
                    u'Q50797802': { u'name' : u'Gallery of Spiš Artists',
                                    u'gallery' : u'Galéria umelcov Spiša, GUS',
                                    u'artworks' : 452,
                                    u'collectionqid' : u'Q50797802',
                                    u'collectionshort' : u'GUS',
                                    u'locationqid' : u'Q50797802',
                                    },
                    u'Q3094617': { u'name' : u'Moravian Gallery in Brno',
                                    u'gallery' : u'Moravská galerie, MG',
                                    u'artworks' : 944,
                                    u'collectionqid' : u'Q3094617',
                                    u'collectionshort' : u'MG',
                                    u'locationqid' : u'Q3094617',
                                    },
                    u'Q24705922': { u'name' : u'Šariš Gallery',
                                   u'gallery' : u'Šarišská galéria, SGP',
                                   u'artworks' : 68,
                                   u'collectionqid' : u'Q24705922',
                                   u'collectionshort' : u'SGP',
                                   u'locationqid' : u'Q24705922',
                                   },
                    u'Q4120060': { u'name' : u'Andy Warhol Museum of Modern Art',
                                    u'gallery' : u'Múzeum moderného umenia A. Warhola, MAW',
                                    u'artworks' : 43,
                                    u'collectionqid' : u'Q4120060',
                                    u'collectionshort' : u'MAW',
                                    u'locationqid' : u'Q4120060',
                                    },
                 }
    collectionid = None
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-collectionid:'):
            if len(arg) == 14:
                collectionid = pywikibot.input(
                        u'Please enter the collectionid you want to work on:')
            else:
                collectionid = arg[14:]
        elif arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True

    webumeniaArtists = webumeniaArtistsOnWikidata()

    if collectionid:
        if collectionid not in collections.keys():
            pywikibot.output(u'%s is not a valid collectionid!' % (collectionid,))
            return
        processCollection(collections[collectionid], webumeniaArtists, dryrun=dryrun, create=create)
    else:
        for collectionid in collections.keys():
            processCollection(collections[collectionid], webumeniaArtists, dryrun=dryrun, create=create)

if __name__ == "__main__":
    main()
