#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Centraal Museum

API is provided that can give everything in JSON format!

* http://www.dimcon.nl/api/search?query=delving_spec:centraal-museum&searchIn=all&qf=dc_type_facet:schilderij&facetBoolType=OR&format=json&start=51&rows=50

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re
#import HTMLParser



def getCentraalGenerator():
    """
    Generator to return Kroller-Muller Museum. Keep grabbing the api until we have no more page left
    
    """
    searchBase=u'http://www.dimcon.nl/api/search?query=delving_spec:centraal-museum&searchIn=all&qf=dc_type_facet:schilderij&facetBoolType=OR&format=json&start=%s&rows=%s'
    
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

            if itemfields.get('delving_collection')[0]==u'Centraal Museum':
                metadata['collectionqid'] = u'Q260913'
                metadata['collectionshort'] = u'Centraal Museum'
                metadata['locationqid'] = u'Q260913'
            else:
                #Another collection, skip
                continue

            #No need to check, I'm actually searching for paintings
            metadata['instanceofqid'] = u'Q3305213' 

            if itemfields.get('europeana_uri')[0].startswith(u'centraal-museum/'):
                metadata['url'] = u'http://dimcon.nl/dimcon/%s' % (itemfields.get('europeana_uri')[0].replace(u' ', u'%20'),)
                metadata['id'] = itemfields.get('europeana_uri')[0].replace(u'centraal-museum/', u'')
                metadata['idpid'] = u'P217'
            else:
                #No url, skip
                continue               
                
            metadata['title'] = { u'nl' : itemfields.get('dc_title')[0],
                                  }
            if itemfields.get('dc_date'):
                metadata['inception'] = itemfields.get('dc_date')[0]
            metadata['describedbyurl'] = itemfields.get('delving_landingPage')[0] # .replace(u'%20', u' ')

            if itemfields.get('dc_creator'):
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
            else:
                metadata['description'] = { u'nl' : u'schilderij van een anonieme schilder',
                                            u'en' : u'painting by an anonymous painter',
                                            }
                metadata['creatorqid'] = u'Q4233718' # Set the creator to anonymous

            yield metadata

def main():
    dictGen = getCentraalGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
