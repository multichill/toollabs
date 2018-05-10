#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Cincinnati Art Museum to Wikidata.

This bot does use artdatabot to upload it to Wikidata and just asks the API for all it's paintings.


"""
import artdatabot
import pywikibot
import requests
import json
import re

def getCincinnatiGenerator():
    """
    Generator to return Cincinnati Art Museum paintings

    
    """
    baseposturl = u'http://www.cincinnatiartmuseum.org/umbraco/surface/CollectionSurface/LoadMoreArtwork'

    #basesearchurl = u'https://www.rijksmuseum.nl/api/nl/collection?key=%s&format=json&type=schilderij&ps=%s&p=%s'
    #appendurl = u'?key=%s&format=json'
    session = requests.Session()

    basepage = session.get(u'http://www.cincinnatiartmuseum.org/art/explore-the-collection/')
    headers = {'Host' : 'www.cincinnatiartmuseum.org',
               'Accept' : '*/*',
               'Accept-Language' : 'en-US,en;q=0.5',
               'Accept-Encoding' : 'gzip, deflate',
               'Referer' : 'http://www.cincinnatiartmuseum.org/art/explore-the-collection/',
               'Content-Type' : 'application/x-www-form-urlencoded; charset=UTF-8',
               'X-Requested-With' : 'XMLHttpRequest' }
    basepostjson = u'keyword=&classification=Painting&department=&specialCollection=&imagesOnly=&page=%s'


    for i in range(0,97):
        postjson = basepostjson % (i,)
        searchPage = session.post(baseposturl, data=postjson, headers=headers)
        searchJson = searchPage.json()
        realJson = json.loads(searchJson)
        for record in realJson:
            #print u'BEGIN RECORD'
            #print record
            #for key in record.keys():
            #    print u'%s - %s' % (key, record[key])
            #print u'END RECORD'

            metadata = {}
            url =  u'http://www.cincinnatiartmuseum.org/art/explore-the-collection?id=%s' % (record.get('ArtworkId'),)

            # If it get's it's own property, update here
            # metadata['artworkidpid'] = u'Pxxx'
            # metadata['artworkid'] = u'%s' % (record.get('ArtworkId'),)

            metadata['url'] = url

            metadata['collectionqid'] = u'Q2970522'
            metadata['collectionshort'] = u'CAM'
            metadata['locationqid'] = u'Q2970522'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = record[u'AccessionNumber']
            metadata['idpid'] = u'P217'

            if record.get('Title'):
                # Chop chop, several very long titles
                if len(record.get('Title')) > 220:
                    title = record.get('Title')[0:200]
                else:
                    title = record.get('Title')
                metadata['title'] = { u'en' : title,
                                    }

            if record.get(u'PrimaryArtist') and not record.get(u'PrimaryArtist')==u'N/A':
                metadata['creatorname'] = record.get(u'PrimaryArtist')
            elif record.get(u'Artist'):
                (name, sep, extraname) = record.get(u'Artist').partition(u'(')
                metadata['creatorname'] = name

            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }
            # FIXME : This will only catch oil on canvas
            if record.get('Medium')==u'oil on canvas':
                metadata['medium'] = u'oil on canvas'

            # Set the inception only if start only start or if start and end are the same
            if record.get('Date') and record.get('StartYear') and record.get('EndYear'):
                if record.get('Date')==str(record.get('StartYear')) and record.get('Date')==str(record.get('EndYear')):
                    metadata['inception'] = record.get('Date')

            # Provenance not available
            # metadata[u'acquisitiondate']

            # Get the dimensions
            if record.get('Measurements'):
                dimensiontext = record.get('Measurements')
                regex_2d = u'^[^\(]*\((?P<height>\d+(\.\d+)?)\s*(x|×)\s*(?P<width>\d+(\.\d+)?)\s*cm\s*\).*'
                regex_3d = u'^[^\(]*\((?P<height>\d+(\.\d+)?)\s*(x|×)\s*(?P<width>\d+(\.\d+)?)\s*(x|×)\s*(?P<depth>\d+(\.\d+)?)\s*cm\s*\).*'
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
    dictGen = getCincinnatiGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
