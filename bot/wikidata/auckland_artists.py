#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to get all the artists from the Auckland Art Gallery website so these can be added to mix'n'match.

They seem to provide json:

http://www.aucklandartgallery.com/search/artworks?section=collection&undated=undated&objectType[0]=Painting&reference=artworks&page=2

Loop over all works and insert it into a dict based on the unique key. Output it as a tsv


"""
import artdatabot
import pywikibot
import requests
import re
import time
import csv

def getAucklandArtistsGenerator():
    """
    Generator to return Auckland Art Gallery paintings

    """

    basesearchurl=u'http://www.aucklandartgallery.com/search/artworks?section=collection&undated=undated&reference=artworks&page=%s'

    #basesearchurl = u'http://www.aucklandartgallery.com/search/artworks?section=collection&undated=undated&objectType[0]=Painting&reference=artworks&page=%s'
    origin = u'http://www.aucklandartgallery.com'
    referer = u'http://www.aucklandartgallery.com/search/artworks?section=collection&undated=undated&objectType%5B0%5D=Painting'

    result = {}
    notdone = []



    # Just loop over the pages
    for i in range(1, 1341):
        print i
        searchurl = basesearchurl % (i,)
        searchPage = requests.get(searchurl, headers={'X-Requested-With' : 'XMLHttpRequest',
                                                      'referer' : referer,
                                                      'origin' : origin} )

        # This might bork evey once in a while, we'll see
        try:
            searchJson = searchPage.json()
        except ValueError:
            print u'Oh, noes, no JSON. Wait and try again'
            time.sleep(15)
            searchPage = requests.get(searchurl, headers={'X-Requested-With' : 'XMLHttpRequest',
                                                          'referer' : referer,
                                                          'origin' : origin} )
            searchJson = searchPage.json()

        for record in searchJson.get('data'):

            entryid = record.get('user_sym_91')
            if not isinstance(entryid, list):
                result = processEntry(entryid, record.get('user_sym_32'),record.get('classification'), result)
            else:
                i = 0
                for ndentry in entryid:
                    result = processEntry(ndentry, record.get('user_sym_32')[i],record.get('classification'), result)
                    i = i + 1
                    #notdone.append(ndentry)
                #print u'No idea how to process this one'

            #yield
    for entrynum in result:
        result[entrynum][u'description'] =  result[entrynum]['shortdescription'] + u' (field of work: ' + u'/'.join(result[entrynum]['classification']) + u')'

    return result

def processEntry(entryid, user_sym_32, classification, result):
    descregex = u'^([^\)]+)\s*\((.+)\)'
    if int(entryid) not in result:
        metadata = { u'id' : entryid,
                     u'name' : u'',
                     u'shortdescription' : u'',
                     u'url' : u'http://www.aucklandartgallery.com/explore-art-and-ideas/artist/%s/' % (entryid,),
                     u'classification' : [classification,]
                     }
        match = re.match(descregex, user_sym_32)
        if match:
            metadata[u'name'] = match.group(1).strip()
            metadata[u'shortdescription'] = match.group(2)
        else:
            metadata[u'name'] =  user_sym_32
            metadata[u'shortdescription'] = user_sym_32
        result[int(entryid)]=metadata
    else:
        if classification not in result[int(entryid)][u'classification']:
            result[int(entryid)][u'classification'].append(classification)
    return result

def main():
    artistsDict = getAucklandArtistsGenerator()

    with open('/tmp/auckland_artists.tsv', 'wb') as tsvfile:
        fieldnames = [u'Entry ID', # (your alphanumeric identifier; must be unique within the catalog)
                      u'Entry name', # (will also be used for the search in mix'n'match later)
                      u'Entry description', #
                      u'Entry type', # (short string, e.g. "person" or "location"; recommended)
                      u'Entry URL', # if omitted, it will be constructed from the URL pattern and the entry ID. Either a URL pattern or a URL column are required!
                      ]

        writer = csv.DictWriter(tsvfile, fieldnames, dialect='excel-tab')

        #No header!
        #writer.writeheader()

        for artist in sorted(artistsDict):
            artistdict = {u'Entry ID' : artistsDict[artist][u'id'].encode(u'utf-8'),
                          u'Entry name' : artistsDict[artist][u'name'].encode(u'utf-8'),
                          u'Entry description' : artistsDict[artist][u'description'].encode(u'utf-8'),
                          u'Entry type' : u'person'.encode(u'utf-8'),
                          u'Entry URL': artistsDict[artist][u'url'].encode(u'utf-8'),
                          }
            print artist
            writer.writerow(artistdict)

if __name__ == "__main__":
    main()
