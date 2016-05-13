#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Stedelijk Museum Amsterdam (Stedelijk)

Good old screen scraping. Looks like we only have search pages.

* http://www.stedelijk.nl/en/collection/collection-online#/params?lang=en-GB&f=FilterType|Art&exclude=FilterType&f=FilterSubCollection|Paintings&q=
* http://www.stedelijk.nl/en/artwork/8042-zelfportret-1985-nr-49

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re
import HTMLParser

def getStedelijkGenerator():
    """
    Generator to return Stedelijk. 
    
    """
    searchBase=u'http://www.stedelijk.nl/params?lang=en-GB&f=FilterType|Art&f=FilterSubCollection|Paintings&exclude=FilterType&pnr=%s&q='

    htmlparser = HTMLParser.HTMLParser()

    itemRegex = u'<a href="(/en/artwork/\d+[^\"]+)"'

    for i in range(0, 143):
        searchUrl = searchBase % (i)
        searchPage = requests.get(searchUrl)
        searchText = searchPage.text
        itemmatches = re.finditer(itemRegex, searchText)

        for itemmatch in itemmatches:
            url = u'http://www.stedelijk.nl%s' % (itemmatch.group(1),)
            searchUrl = searchBase % (i)
            itemPage = requests.get(url)
            itemText = itemPage.text
            metadata = {}
            metadata[u'url'] = url
            metadata['collectionqid'] = u'Q924335'
            metadata['collectionshort'] = u'Stedelijk'
            metadata['locationqid'] = u'Q924335'
            metadata['instanceofqid'] = u'Q3305213'

            creatorTitleRegex = u'<h3>[\r\n\s]+<a href="[^\"]+">([^\<]+)</a>:\s*([^\<]+)[\r\n\s]+</h3>'

            creatorTitleMatch = re.search(creatorTitleRegex, itemText)

            name = htmlparser.unescape(creatorTitleMatch.group(1)).strip()
            metadata['creatorname'] = name
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }
            
            nltitle = htmlparser.unescape(creatorTitleMatch.group(2)).strip()
            dateRegex = u'^(.+), (\d\d\d\d)$'
            dateMatch = re.match(dateRegex, nltitle)
            if dateMatch:
                nltitle = dateMatch.group(1)
                metadata['inception'] = dateMatch.group(2)
                
            metadata[u'title'] = { u'nl' : nltitle,
                                   }

            translatedTitleRegex = u'<dt>translated title</dt>[\r\n\s]+<dd>[\r\n\s]+([^\<]+)[\r\n\s]+</dd>'
            translatedTitleMatch = re.search(translatedTitleRegex, itemText)
            if translatedTitleMatch:
                metadata[u'title'][u'en'] =  htmlparser.unescape(translatedTitleMatch.group(1)).strip()

            idRegex = u'<dt>object number</dt>[\r\n\s]+<dd>[\r\n\s]+([^\<\r\n]+)[\r\n\s]+</dd>'
            idMatch = re.search(idRegex, itemText)
            metadata['id'] = idMatch.group(1)
            metadata['idpid'] = u'P217'

            yield metadata

def main():
    dictGen = getStedelijkGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
