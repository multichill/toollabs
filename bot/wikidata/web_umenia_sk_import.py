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
import random
import re

def getWebUmeniaGenerator(collectioninfo, webumeniaArtists):
    """
    Generator to return Web Umenia paintings

    Collectioninfo should be a dict with:
    * name - The English name (not actually used)
    * gallery - (not urlencoded) name of the gallery for query
    * collectionqid - qid of the collection to fill the dict
    * collectionshort - Abbreviation of the collection to fill the dict
    * locationqid - qid of the location (usually same as collection) to fill the dict
    """

    baseSearchUrl = 'https://www.webumenia.sk/api/items_sk/_search'

    session = requests.Session()
    #session.auth = ('', '') set in your .netrc file, see https://www.labkey.org/Documentation/wiki-page.view?name=netrc

    # Topics to genre
    topics = { 'portrét' : 'Q134307', # https://www.webumenia.sk/en/katalog?topic=portr%C3%A9t -> portrait
               'náboženský motív' : 'Q2864737', # https://www.webumenia.sk/en/katalog?topic=n%C3%A1bo%C5%BEensk%C3%BD%20mot%C3%ADv -> religious art
               'krajina' : 'Q191163', # https://www.webumenia.sk/en/katalog?work_type=maliarstvo&topic=krajina -> landscape art
               }

    # Use the returned number in the API
    size = 100
    i = 0
    while True:
        searchdata = { 'size' : size,
                       'from' : i,
                       'query': { 'bool': { 'must': [
                           { 'match': { 'gallery': collectioninfo.get('gallery') }},
                           { 'match': { 'work_type': 'maliarstvo' }},
                       ] } },}

        data = json.dumps(searchdata)
        page = session.get(baseSearchUrl, data=data, headers = { 'Content-Type' : 'application/json'})

        # Stop condition for the loop
        if not page.json().get(u'hits'):
            return
        i += size

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
            metadata['instanceofqid'] = 'Q3305213'

            title = item.get(u'title').strip()

            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { 'sk' : title,
                                  }

            # I had one item with missing identifier, wonder if it shows up here too
            metadata['idpid'] = 'P217'
            if not item.get('identifier'):
                # Few rare items without an inventory number, just skip them
                continue
            metadata['id'] = item.get('identifier')

            # Get the  Web umenia work ID (P5269)
            metadata['artworkid'] = url.replace(u'https://www.webumenia.sk/dielo/', u'')
            metadata['artworkidpid'] = u'P5269'

            if item.get('author') and item.get('author')[0]:
                name = item.get('author')[0]
                if u',' in name:
                    (surname, sep, firstname) = name.partition(u',')
                    name = u'%s %s' % (firstname.strip(), surname.strip(),)
            else:
                name = 'unknown'
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

            if item.get('medium') and item.get('technique') \
                    and item.get('medium')[0] and item.get('technique')[0]:
                technique = item.get('technique')[0].lower()
                medium = item.get('medium')[0].lower()

                # Cardboard etc. still needs to be done
                techniquemedium = { ('olej','plátno') :  'oil on canvas',
                                    ('olej','dřevo') :  'oil on panel', # wood
                                    ('olej','drevo') :  'oil on panel', # wood
                                    ('olej','překližka') :  'oil on panel', # plywood
                                    ('olej','papier') :  'oil on paper',
                                    ('olej','lepenka') :  'oil on cardboard',
                                    ('olej','kartón') :  'oil on cardboard',
                                    ('tempera','plátno') :  'tempera on canvas',
                                    ('tempera','dřevo') :  'tempera on panel',
                                    ('tempera','drevo') :  'tempera on panel',
                                    ('tempera','překližka') :  'tempera on panel',
                                    ('tempera','papier') :  'tempera on paper',
                                    ('akryl','plátno') :  'acrylic paint on canvas',
                                    ('akryl','dřevo') :  'acrylic paint on panel',
                                    ('akvarel','papier') :  'watercolor on paper',
                                    }
                if (technique, medium) in techniquemedium:
                    metadata['medium'] = techniquemedium.get((technique, medium))
                else:
                    print('Unable to match technique %s and medium %s' % (technique, medium))

            # Add the genre based on the topic. Only when we have one topic
            if item.get(u'topic') and len(item.get(u'topic'))==1:
                if item.get(u'topic')[0] in topics:
                    metadata[u'genreqid'] = topics.get(item.get(u'topic')[0])

            # The search API returns measurements, but have to use regex to extract it
            if item.get('measurement') and item.get('measurement')[0]:
                dimensions = item.get('measurement')[0].strip()
                regex_2d = '^výška (?P<height>\d+(\.\d+)?)\s*cm,\s*šírka\s*(?P<width>\d+(\.\d+)?)\s*cm$'
                match_2d = re.match(regex_2d, dimensions)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height')
                    metadata['widthcm'] = match_2d.group(u'width')

            if item.get('has_image') and item.get('is_free') and item.get('has_iip'):
                metadata['imageurl'] = 'https://www.webumenia.sk/dielo/%s/stiahnut' % (item.get('id'),)
                metadata['imageurlformat'] = 'Q2195' #JPEG
                metadata['imageoperatedby'] = 'Q50828580'
            #elif item.get(u'has_image') and item.get(u'has_iip') and item.get(u'date_latest') < 1900:
            #    # Work around for some of the missing images that are not marked as free
            #    #print (item.get(u'is_free'))
            #    #print (json.dumps(item, indent = 2, separators=(',', ': ')))
            #    metadata[u'imageurl'] = u'https://www.webumenia.sk/dielo/%s/stiahnut' % (item.get('id'),)
            #    metadata[u'imageurlformat'] = u'Q2195' #JPEG
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
    collections = { 'Q1744024': { 'name' : 'Slovak National Gallery',
                                  'gallery' : 'Slovenská národná galéria, SNG',
                                  'collectionqid' : 'Q1744024',
                                  'collectionshort' : 'SNG',
                                  'locationqid' : 'Q1744024',
                                   },
                    'Q50751848': { 'name' : 'Orava Gallery',
                                   'gallery' : 'Oravská galéria, OGD',
                                   'collectionqid' : 'Q50751848',
                                   'collectionshort' : 'Orava',
                                   'locationqid' : 'Q50751848',
                                    },
                    'Q30676307': { 'name' : 'Ernest Zmeták Art Gallery',
                                   'gallery' : 'Galéria umenia Ernesta Zmetáka, GNZ',
                                   'collectionqid' : 'Q30676307',
                                   'collectionshort' : 'GNZ',
                                   'locationqid' : 'Q30676307',
                                   },
                    'Q50762402': { 'name' : 'Liptov Gallery of Peter Michal Bohúň',
                                   'gallery' : 'Liptovská galéria Petra Michala Bohúňa, GPB',
                                   'collectionqid' : 'Q50762402',
                                   'collectionshort' : 'GPB',
                                   'locationqid' : 'Q50762402',
                                   },
                    'Q913415': { 'name' : 'Bratislava City Gallery',
                                 'gallery' : 'Galéria mesta Bratislavy, GMB',
                                 'collectionqid' : 'Q913415',
                                 'collectionshort' : 'GMB',
                                 'locationqid' : 'Q913415',
                                 },
                    'Q12766245': { 'name' : 'Miloš Alexander Bazovský Gallery',
                                   'gallery' : 'Galéria Miloša Alexandra Bazovského, GBT',
                                   'collectionqid' : 'Q12766245',
                                   'collectionshort' : 'MABG',
                                   'locationqid' : 'Q12766245',
                                   },
                    'Q50800751': { 'name' : 'Nitra Gallery',
                                   'gallery' : 'Nitrianska galéria, NGN',
                                   'collectionqid' : 'Q50800751',
                                   'collectionshort' : 'NGN',
                                   'locationqid' : 'Q50800751',
                                   },
                    'Q16517556': { 'name' : 'Central Slovakian Gallery',
                                   'gallery' : 'Stredoslovenská galéria, SGB',
                                   'collectionqid' : 'Q16517556',
                                   'collectionshort' : 'SGB',
                                   'locationqid' : 'Q16517556',
                                    },
                    'Q50797802': { 'name' : 'Gallery of Spiš Artists',
                                   'gallery' : 'Galéria umelcov Spiša, GUS',
                                   'collectionqid' : 'Q50797802',
                                   'collectionshort' : 'GUS',
                                   'locationqid' : 'Q50797802',
                                   },
                    'Q3094617': { 'name' : 'Moravian Gallery in Brno', # This one is in Czech Republic
                                  'gallery' : 'Moravská galerie, MG',
                                  'collectionqid' : 'Q3094617',
                                  'collectionshort' : 'MG',
                                  'locationqid' : 'Q3094617',
                                  },
                    'Q24705922': { 'name' : 'Šariš Gallery',
                                   'gallery' : 'Šarišská galéria, SGP',
                                   'collectionqid' : 'Q24705922',
                                   'collectionshort' : 'SGP',
                                   'locationqid' : 'Q24705922',
                                   },
                    'Q4120060': { 'name' : 'Andy Warhol Museum of Modern Art',
                                  'gallery' : 'Múzeum moderného umenia A. Warhola, MAW',
                                  'collectionqid' : 'Q4120060',
                                  'collectionshort' : 'MAW',
                                  'locationqid' : 'Q4120060',
                                  },
                    'Q3094652' : { 'name' : 'East Slovak Gallery',
                                    'gallery' : 'Východoslovenská galéria, VSG',
                                    'collectionqid' : 'Q3094652',
                                    'collectionshort' : 'VSG',
                                    'locationqid' : 'Q3094652',
                                    },
                    'Q62430225' : { 'name' : 'Tatra Gallery',
                                    'gallery' : 'Tatranská galéria, TGP', # For some reason didn't work
                                    'collectionqid' : 'Q62430225',
                                    'collectionshort' : 'TGP',
                                    'locationqid' : 'Q62430225',
                                    },
                    'Q12774288' : { 'name' : 'Považská galéria umenia',
                                    'gallery' : 'Považská galéria umenia, PGU',
                                    'collectionqid' : 'Q12774288',
                                    'collectionshort' : 'PGU',
                                    'locationqid' : 'Q12774288',
                                    },
                    'Q72948957' : { 'name' : 'Kysucká galéria',
                                    'gallery' : 'Kysucká galéria, KGC',
                                    'collectionqid' : 'Q72948957',
                                    'collectionshort' : 'KGC',
                                    'locationqid' : 'Q72948957',
                                    },
                    'Q111621674' : { 'name' : 'Turčianska galéria',
                                     'gallery' : 'Turčianska galéria, TGM',
                                     'collectionqid' : 'Q111621674',
                                     'collectionshort' : 'TGM',
                                     'locationqid' : 'Q111621674',
                                    },
                    # Súkromný majetok
                    # Galéria Jána Koniarka, GJK
                    # Nezaradená inštitúcia alebo súkromná osoba, NIS
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
        collectionlist = list(collections.keys())
        random.shuffle(collectionlist) # Different order every time we run
        for collectionid in collectionlist:
            processCollection(collections[collectionid], webumeniaArtists, dryrun=dryrun, create=create)

if __name__ == "__main__":
    main()
