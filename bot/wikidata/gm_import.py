#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Gemeentemuseum Den Haag (GM)

Good old screen scraping. Looks like we only have search pages.

* http://www.gemeentemuseum.nl/topstukken/zoeken?s=olieverf&page=1

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
#import urllib2
import re
import HTMLParser
#import xml.etree.ElementTree as ET


def getGMGenerator():
    """
    Generator to return Gemeentemuseum. 
    
    """
    searchBase=u'http://www.gemeentemuseum.nl/topstukken/zoeken?s=olieverf&page=%s'

    htmlparser = HTMLParser.HTMLParser()

    # Looks like out of 600+ hits, 2 are not found
    bigRegex = '<h3><a href="(?P<url>/collection/item/\d+)">(?P<title>[^\<]+)</a></h3><p class="coll-creator">(?P<creator>[^\<]+)</p><div class="coll-prod-place">(?P<place>[^\<]*)</div><div class="coll-created">(?P<date>[^\<]*)</div><div class="coll-dimensions">(?P<dimensions>[^\<]+)</div><div class="coll-material">(?P<material>[^\<]+)</div><div class="coll-object-number">Gemeentemuseum Den Haag: (?P<id>\d+)</div><div class="coll-more-link">'
 
    for i in range(0, 40):
        searchUrl = searchBase % (i)
        searchPage = requests.get(searchUrl)
        searchText = searchPage.text
        itemmatches = re.finditer(bigRegex, searchText)

        for itemmatch in itemmatches:
            metadata = {}
            metadata['collectionqid'] = u'Q1499958'
            metadata['collectionshort'] = u'GM'
            metadata['locationqid'] = u'Q1499958'
            metadata['instanceofqid'] = u'Q3305213'
            metadata[u'url'] = u'http://www.gemeentemuseum.nl%s' % (itemmatch.group(u'url'),)
            metadata[u'title'] = { u'nl' : htmlparser.unescape(itemmatch.group(u'title')).strip(),
                                   }

            name = itemmatch.group(u'creator')
            nameRegex = u'^([^\[]+)\s\[[^\)]+\]$'
            nameMatch = re.match(nameRegex, name)
            if nameMatch:
                metadata['creatorname'] = nameMatch.group(1)
            else:
                metadata['creatorname'] = name
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }
            if itemmatch.group(u'date'):
                metadata['inception'] = itemmatch.group(u'date')
            metadata['id'] = itemmatch.group(u'id')
            metadata['idpid'] = u'P217'            
            yield metadata

def main():
    dictGen = getGMGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
