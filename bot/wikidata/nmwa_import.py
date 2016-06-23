#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from the National Museum of Western Art (NMWA)

Good old scraping from http://www.nmwa.go.jp/en/collection/index1.html (and 2 and 3)

* Loop over http://www.nmwa.go.jp/en/collection/index1.html
* Loop over http://www.nmwa.go.jp/en/collection/index2.html
* Loop over http://www.nmwa.go.jp/en/collection/index3.html
* Grab individual paintings like http://www.phillipscollection.org/collection/browse-the-collection?id=0957

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import urllib2
import re
import HTMLParser
import xml.etree.ElementTree as ET


def getNMWAGenerator():
    """
    Generator to return National Museum of Western Art paintings
    
    """

    searchurls = [ u'http://www.nmwa.go.jp/en/collection/index1.html',
                   u'http://www.nmwa.go.jp/en/collection/index2.html',
                   u'http://www.nmwa.go.jp/en/collection/index3.html',
                   ]

    # 0 - 86 (something between 80 and 90
    #searchBaseUrl = u'http://www.phillipscollection.org/search?i=1&page=%s&tpc_q=painting&q1=Collection&x1=tpc_type'
    htmlparser = HTMLParser.HTMLParser()

    foundit=True

    for searchUrl in searchurls:
        print searchUrl
        searchPage = urllib2.urlopen(searchUrl)
        searchPageData = searchPage.read()

        searchRegex = u'>Paintings</td>[\r\n\t\s]*<td width="90px" class="word"><a href="(http://collection.nmwa.go.jp/en/P\.([^\"]+).html)">'
        itemmatches = re.finditer(searchRegex, searchPageData)
        #urllist = []
        #for match in matches:
        #    try:
        #    #    #bla = unicode(match.group(1), u'utf-8')
        #        urllist.append(u'http://www.dulwichpicturegallery.org.uk%s' % (match.group(1),))
        #    except UnicodeDecodeError:
        #        pywikibot.output(u'Found an url I cannot parse: %s' % (unicode(match.group(1), u'utf-8'),))#

        #print len(urllist)
        #urlset = set(urllist)
        #print len(urlset)


        for itemmatch in itemmatches:
            metadata = {}
            url = itemmatch.group(1)
            print url

            metadata['url'] = url
            metadata['collectionqid'] = u'Q1362629'
            metadata['collectionshort'] = u'NMWA'
            metadata['locationqid'] = u'Q1362629'
            metadata['instanceofqid'] = u'Q3305213'

            itemPage = urllib2.urlopen(url)
            itemPageData = unicode(itemPage.read(), u'utf-8')
            
            #print itemPageEnData
            #headerRegex = u'<figure class="main">[\r\n\t\s]*<figcaption class="grid_7">[\r\n\t\s]*<header>[\r\n\t\s]*<h1>([^<]+)</h1>[\r\n\t\s]*<h2>([^<]+)<' #em>1872-1944</em></h2></header>
            titleRegex = u'<h2 class="title">([^<]+)</h2>'
            #titleEnRegex = u'<main class="main narrow">[\r\n\t\s]+<h1>[\r\n\t\s]*([^<]+)[\r\n\t\s]*</h1>'
            creatorRegex = u'<h2 class="artist"><a href="[^\"]+">([^<]+)<'

            #<tr><th class="text_s">Materials/Techniques</th><td>oil on canvas</td></tr>
            #<tr><th>Size (cm)</th><td>82 x 100</td></tr>
            #<tr><th>Inscriptions</th><td>Signed lower right: GdE</td></tr>
            #<tr><th>Credit Line</th><td>Matsukata Collection</td></tr>
            #<tr><th>Category</th><td>Paintings</td></tr>
            invRegex = u'<tr><th>Collection Number</th><td>(P\.[^<]+)</td></tr>'
            dateRegex = u'<tr><th>Date</th><td>([^<]+)</td></tr>'

            # Could also get Dimensions, Medium and credit line
            
            titleMatch = re.search(titleRegex, itemPageData)
            if not titleMatch:
                pywikibot.output(u'The title data for this painting is BORKED!')
                continue

            #FIXME: Check encoding

            metadata['title'] = { u'en' : htmlparser.unescape(titleMatch.group(1)),
                                  }
            creatorMatch = re.search(creatorRegex, itemPageData)
            if not creatorMatch:
                pywikibot.output(u'The creator data for this painting is BORKED!')
                continue

            name = htmlparser.unescape(creatorMatch.group(1)).strip()
            ## We need to normalize the name
            #if u',' in name:
            #    (surname, sep, firstname) = name.partition(u',')
            #    name = u'%s %s' % (firstname.strip(), surname.strip(),)
            metadata['creatorname'] = name
    
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }


            invMatch = re.search(invRegex, itemPageData)

            if not invMatch:
                pywikibot.output(u'No inventory number found! Skipping')
                continue
            
            metadata['id'] = invMatch.group(1)
            metadata['idpid'] = u'P217'

            dateMatch = re.search(dateRegex, itemPageData)
            if dateMatch:
                metadata['inception'] = dateMatch.group(1)

            yield metadata

        

def main():
    dictGen = getNMWAGenerator()

    #for painting in dictGen:
    #   print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
