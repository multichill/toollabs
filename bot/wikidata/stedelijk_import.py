#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Stedelijk Museum Amsterdam (Stedelijk). Second version because of link rot.

Good old screen scraping. Looks like we only have search pages.

* https://www.stedelijk.nl/en/dig-deeper/collection-online?subcollection=Schilderijen&page=1
* http://www.stedelijk.nl/en/artwork/8042-zelfportret-1985-nr-49

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re
from html.parser import HTMLParser

def getStedelijkGenerator():
    """
    Generator to return Stedelijk. 
    
    """
    searchBase=u'https://www.stedelijk.nl/en/dig-deeper/collection-online?subcollection=Schilderijen&page=%s'

    htmlparser = HTMLParser()

    itemRegex = u'\<a[\r\n\s]+href\=\"(https\:\/\/www\.stedelijk\.nl\/en\/collection\/\d+[^\"]+)\"'

    for i in range(1, 120):
        searchUrl = searchBase % (i)
        print (searchUrl)
        searchPage = requests.get(searchUrl)
        searchText = searchPage.text
        itemmatches = re.finditer(itemRegex, searchText)

        for itemmatch in itemmatches:
            # Just the English URL
            url = itemmatch.group(1)
            print (url)
            itemPage = requests.get(url)
            itemText = itemPage.text
            metadata = {}
            metadata[u'url'] = url
            metadata['collectionqid'] = u'Q924335'
            metadata['collectionshort'] = u'Stedelijk'
            metadata['locationqid'] = u'Q924335'
            metadata['instanceofqid'] = u'Q3305213'

            idRegex = u'\<h3\>Object number\<\/h3\>[\r\n\s]+\<p\>([^\<]+)\<\/p\>'
            idMatch = re.search(idRegex, itemText)
            metadata['id'] = idMatch.group(1)
            metadata['idpid'] = u'P217'

            creatorTitleRegex = u'\<h1 class\=\"page-header__title\s*\"\>[\r\n\s]*([^\<]+)[\r\n\s]*\<\/h1\>[\r\n\s]*\<h2 class\=\"page-header__subtitle\"\>[\r\n\s]*([^\<]+)[\r\n\s]*\<\/h2\>'
            creatorTitleMatch = re.search(creatorTitleRegex, itemText)

            # Languages seem to be all mixed up so I'll just put it in Dutch and English
            title = htmlparser.unescape(creatorTitleMatch.group(1)).strip()
            metadata[u'title'] = { u'en' : title,
                                   u'nl' : title,
                                   }

            # We do have translated title on some paintings, let's use that for the English part
            ttregex = u'\<h3\>Translated title\<\/h3\>[\r\n\s]*\<p\>([^\<]+)\<\/p\>'
            ttmatch = re.search(ttregex, itemText)
            if ttmatch:
                metadata['title'][u'en'] = htmlparser.unescape(ttmatch.group(1)).strip()

            name = htmlparser.unescape(creatorTitleMatch.group(2)).strip()
            metadata['creatorname'] = name
            metadata['description'] = { u'nl' : u'schilderij van %s' % (name, ),
                                        u'en' : u'painting by %s' % (name, ),
                                        u'de' : u'Gemälde von %s' % (name, ),
                                        u'fr' : u'peinture de %s' % (name, ),
                                        }

            dateregex = u'\<h3\>Production date\<\/h3\>[\r\n\s]+\<p\>(\d\d\d\d)\<\/p\>'
            dateMatch = re.search(dateregex, itemText)
            if dateMatch:
                metadata['inception'] = dateMatch.group(1)

            # Add the extra collection for the RCE artworks. Makes merging easier
            creditsregex = u'\<h3\>Credits\<\/h3\>[\r\n\s]*\<p\>bruikleen Rijksdienst voor het Cultureel Erfgoed\s*\/\s*on loan from the Cultural Heritage Agency of the Netherlands\<\/p\>'
            creditsmatch = re.search(creditsregex, itemText)
            if creditsmatch:
                metadata['extracollectionqid'] = u'Q18600731'

            yield metadata


def main():
    dictGen = getStedelijkGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
