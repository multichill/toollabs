#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Kroller-Muller Museum (KM)

API is provided that can give everything in JSON format!

* http://www.dimcon.nl/api/search?query=Kroller-Muller%20Museum&searchIn=all&qf=delving_hasDigitalObject_facet:true&facetBoolType=OR&format=json&start=51&rows=50

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
#import urllib2
import re
#import HTMLParser
#import xml.etree.ElementTree as ET


def getKMGenerator():
    """
    Generator to return Kroller-Muller Museum. Keep grabbing the api until we have no more page left
    
    """
    searchBase=u'http://www.dimcon.nl/api/search?query=Kroller-Muller%%20Museum&searchIn=all&qf=delving_hasDigitalObject_facet:true&facetBoolType=OR&format=json&start=%s&rows=%s'
    
    start = 1
    rows = 50
    hasNext = True

    #htmlparser = HTMLParser.HTMLParser()

    while hasNext:
        searchUrl = searchBase % (start, rows)
        searchPage = requests.get(searchUrl)
        searchJson = searchPage.json()

        start = searchJson.get(u'result').get(u'pagination').get(u'nextPage')
        hasNext = searchJson.get(u'result').get(u'pagination').get(u'hasNext')

        for item in searchJson.get(u'result').get(u'items'):
            itemfields = item.get('item').get(u'fields')
            metadata = {}
            #print itemfields

            if itemfields.get('delving_collection')[0]==u'Kroller-Muller Museum':
                metadata['collectionqid'] = u'Q1051928'
                metadata['collectionshort'] = u'KM'
                metadata['locationqid'] = u'Q1051928'
            else:
                #Another collection, skip
                continue

            if itemfields.get('dc_subject')[0].startswith(u'schilderkunst'):
                metadata['instanceofqid'] = u'Q3305213' #This is painting, let's do sculptures too?
                # Mind the description if we add sculptures!!!!!
            else:
                #Not a painting, skip
                continue

            if itemfields.get('europeana_uri')[0].startswith(u'kroller-muller/'):
                metadata['url'] = u'http://dimcon.nl/dimcon/%s' % (itemfields.get('europeana_uri')[0],)
            else:
                #No url, skip
                continue

            if itemfields.get('dc_identifier')[0].startswith(u'KM '):
                metadata['id'] = itemfields.get('dc_identifier')[0]
                metadata['idpid'] = u'P217'
            else:
                #Something wrong with this id, skip
                continue               
                
            metadata['title'] = { u'nl' : itemfields.get('dc_title')[0],
                                  }
            metadata['inception'] = itemfields.get('dc_date')[0]
            metadata['describedbyurl'] = itemfields.get('delving_landingPage')[0] # .replace(u'%20', u' ')

            name = itemfields.get('dc_creator')[0]
            nameRegex = u'^([^\(]+)\s\([^\)]+\)$'
            nameMatch = re.match(nameRegex, name)
            if nameMatch:
                metadata['creatorname'] = nameMatch.group(1)
            else:
                metadata['creatorname'] = name
                
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }
            #print metadata
            yield metadata

def main():
    dictGen = getKMGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
