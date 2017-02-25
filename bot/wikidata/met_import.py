#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the  Metropolitan Museum of Art (Q160236) to Wikidata.

Clone https://github.com/tategallery/collection/tree/master/artworks . This bot works on those files.

usage:

 python pwb.py /path/to/code/toollabs/bot/wikidata/tate_import.py /path/to/tate/artworks/

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import HTMLParser
import os
import csv

def getMETGenerator(csvlocation):
    """
    Generator to return Museum of New Zealand Te Papa Tongarewa paintings
    """
    pubcount = 0
    paintingcount = 0
    pubpaintingcount = 0
    i = 0
    #htmlparser = HTMLParser.HTMLParser()
    with open(csvlocation, 'rb') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Running into fun encoding problems!
            cleanedrow = {}
            for key, value in row.iteritems():
                if u'Object Number' in unicode(key, u'utf-8'):
                    cleanedrow[u'Object Number'] = unicode(value, u'utf-8')
                else:
                    cleanedrow[unicode(key, u'utf-8')] = unicode(value, u'utf-8')
            #print cleanedrow
            # We process the fields in the order of the CSV
            # Object Number,Is Highlight,Is Public Domain,Object ID,Department,Object Name,Title,Culture,Period,Dynasty,
            # Reign,Portfolio,Artist Role,Artist Prefix,Artist Display Name,Artist Display Bio,Artist Suffix,
            # Artist Alpha Sort,Artist Nationality,Artist Begin Date,Artist End Date,
            # Object Date,Object Begin Date,Object End Date,Medium,Dimensions,Credit Line,
            # Geography Type,City,State,County,Country,Region,Subregion,Locale,Locus,Excavation,River,
            # Classification,Rights and Reproduction,Link Resource,Metadata Date,Repository
            metadata = {}

            metadata['collectionqid'] = u'Q160236'
            metadata['collectionshort'] = u'MET'
            metadata['locationqid'] = u'Q160236'

            metadata['idpid'] = u'P217'
            metadata['id'] = cleanedrow.get('Object Number')

            # 'Is Public Domain' can be used later for uploading
            if cleanedrow.get('Is Public Domain')==u'True':
                pubcount = pubcount + 1
            i = i + 1
            # 'Object ID' is part of the url, but not inventory number
            # 'Department' could be used for categorization on Commons
            # 'Object Name' contaings something like "Painting"

            title = cleanedrow.get('Title')
            # Chop chop, in case we have very long titles
            if title > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                  }

            metadata['creatorname'] = cleanedrow.get('Artist Display Name')

            if metadata['creatorname']==u'Unidentified Artist':
                metadata['creatorqid'] = u'Q4233718'
                metadata['creatorname'] = u'anonymous'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
            else:
                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            }

            if cleanedrow.get('Object Date')==cleanedrow.get(u'Object Begin Date') \
                    and cleanedrow.get('Object Date')==cleanedrow.get(u'Object End Date'):
                metadata['inception']=cleanedrow.get('Object Date')

            if cleanedrow.get('Medium')==u'Oil on canvas':
                metadata['medium'] = u'oil on canvas'

            dimensiontext = cleanedrow.get('Dimensions')
            regex_2d = u'^.+in\. \((?P<height>\d+(\.\d+)?) x (?P<width>\d+(.\d+)?) cm\)$'
            regex_3d = u'^.+in\. \((?P<height>\d+(\.\d+)?) x (?P<width>\d+(.\d+)?) x (?P<depth>\d+(,\d+)?) cm\)$'
            match_2d = re.match(regex_2d, dimensiontext)
            match_3d = re.match(regex_3d, dimensiontext)
            if match_2d:
                metadata['heightcm'] = match_2d.group(u'height')
                metadata['widthcm'] = match_2d.group(u'width')
            elif match_3d:
                metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
                metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
                metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')
            #else:
            #    pywikibot.output(u'No match found for %s' % (dimensiontext,))

            # 'Credit Line' can be used for image upload
            metadata['creditline'] = cleanedrow.get('Credit Line')

            acquisitiondateregex = u'^.+, (\d\d\d\d)$'
            acquisitiondatematch = re.match(acquisitiondateregex, cleanedrow.get('Credit Line'))
            if acquisitiondatematch:
                metadata['acquisitiondate'] = acquisitiondatematch.group(1)

            metadata['url'] = cleanedrow.get('Link Resource')

            if cleanedrow.get('Classification')==u'Paintings':
                metadata['instanceofqid'] = u'Q3305213'
                if cleanedrow.get('Is Public Domain')==u'True':
                    pubpaintingcount = pubpaintingcount + 1
                paintingcount = paintingcount + 1
                #for key, value in cleanedrow.iteritems():
                #    #if key in [u'Object Number',]:
                #    print u'%s : %s' % (key, value)
                yield metadata
    pywikibot.output(u'Processed %s items and %s are marked as public domain' % (i, pubcount))
    pywikibot.output(u'Processed %s paintings and %s are marked as public domain' % (paintingcount, pubpaintingcount))


def main(*args):
    csvlocation = u''
    for arg in pywikibot.handle_args(args):
        csvlocation = arg

    print csvlocation
    dictGen = getMETGenerator(csvlocation)

    for painting in dictGen:
        print painting

    #artDataBot = artdatabot.ArtDataBot(dictGen, create=False)
    #artDataBot.run()

if __name__ == "__main__":
    main()
