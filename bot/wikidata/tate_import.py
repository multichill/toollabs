#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Tate (Q430682) to Wikidata.

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
import json

def getTateGenerator(artworkdir):
    """
    Generator to return Museum of New Zealand Te Papa Tongarewa paintings
    """

    #htmlparser = HTMLParser.HTMLParser()
    for subdir, dirs, files in os.walk(artworkdir):
        for file in files:
            filepath = subdir + os.sep + file
            if filepath.endswith(".json"):
                with open(filepath, 'rb') as jsonfile:
                    jsondata = json.load(jsonfile)

                    if jsondata.get('classification')!=u'painting':
                        continue

                    metadata = {}
                    url = jsondata.get('url')

                    pywikibot.output(url)

                    metadata['url'] = url

                    metadata['collectionqid'] = u'Q430682'
                    metadata['collectionshort'] = u'Tate'
                    metadata['locationqid'] = u'Q430682'

                    metadata['idpid'] = u'P217'
                    metadata['id'] = jsondata.get('acno')

                    # AR artist rooms is also in the  National Galleries of Scotland (Q2051997)
                    if jsondata.get('acno').startswith(u'AR') and u'National Galleries of Scotland' in jsondata.get('creditLine'):
                        metadata['extracollectionqid'] = u'Q2051997'
                        metadata['extraid'] = jsondata.get('acno')
                    # N are from National Gallery
                    elif jsondata.get('acno').startswith(u'N'):
                        metadata['extracollectionqid'] = u'Q180788'
                        metadata['extraid'] = u'NG%s' % (int(jsondata.get('acno')[1:]),)

                    #No need to check, I'm actually searching for paintings.
                    metadata['instanceofqid'] = u'Q3305213'

                    title = jsondata.get('title')
                    # Chop chop, in case we have very long titles
                    if len(title) > 220:
                        title = title[0:200]
                    metadata['title'] = { u'en' : title,
                                            }

                    # Sometimes foreign title is available. Mostly in French so i'll accept a couple of mistakes
                    if jsondata.get('foreignTitle'):
                        metadata['title']['fr'] = jsondata.get('foreignTitle')

                    name = jsondata.get('all_artists')

                    #if not name:
                    #    metadata['creatorqid'] = u'Q4233718'
                    #    metadata['creatorname'] = u'anonymous'
                    #    metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                    #                                u'en' : u'painting by anonymous painter',
                    #                                }
                    #else:
                    #if u',' in name:
                    #(surname, sep, firstname) = name.partition(u',')
                    #name = u'%s %s' % (firstname.strip(), surname.strip(),)
                    metadata['creatorname'] = name

                    metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                                u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                               }

                    # Not sure if it's always sset
                    if jsondata.get('dateRange') and \
                                    jsondata.get('dateRange').get(u'startYear')==jsondata.get('dateRange').get(u'endYear'):
                        metadata['inception'] = jsondata.get('dateRange').get(u'startYear')
                    elif jsondata.get('dateRange') and jsondata.get('dateRange').get(u'startYear') \
                            and jsondata.get('dateRange').get(u'endYear'):
                        metadata['inceptionstart'] = int(jsondata.get('dateRange').get(u'startYear'))
                        metadata['inceptionend'] = int(jsondata.get('dateRange').get(u'endYear'))

                    metadata['acquisitiondate'] = jsondata.get('acquisitionYear')

                    if jsondata.get('medium')==u'Oil paint on canvas':
                        metadata['medium'] = u'oil on canvas'

                    # I think this data was incorrect
                    #if jsondata.get('units')==u'mm':
                    #    if jsondata.get('width') and jsondata.get('width').isnumeric():
                    #        metadata['widthcm'] = unicode(float(jsondata.get('width'))/10)
                    #    if jsondata.get('height') and jsondata.get('height').isnumeric():
                    #        metadata['heightcm'] = unicode(float(jsondata.get('height'))/10)
                    #    if jsondata.get('depth') and jsondata.get('depth').isnumeric():
                    #        metadata['depthcm'] = unicode(float(jsondata.get('depth'))/10)

                    yield metadata


def main(*args):
    artworkdir = u''
    for arg in pywikibot.handle_args(args):
        artworkdir = arg

    print artworkdir
    dictGen = getTateGenerator(artworkdir)

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=False)
    artDataBot.run()

if __name__ == "__main__":
    main()
