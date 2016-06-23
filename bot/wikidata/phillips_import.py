#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from The Phillips Collection.

Good old scraping from http://www.phillipscollection.org/search?i=1&page=1&tpc_q=painting&q1=Collection&x1=tpc_type

* Loop over http://www.phillipscollection.org/search?i=1&page=1&tpc_q=painting&q1=Collection&x1=tpc_type
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


def getPhillipsGenerator():
    """
    Generator to return Phillips paintings
    
    """

    # 0 - 86 (something between 80 and 90
    searchBaseUrl = u'http://www.phillipscollection.org/search?i=1&page=%s&tpc_q=painting&q1=Collection&x1=tpc_type'
    htmlparser = HTMLParser.HTMLParser()

    foundit=True

    for i in range(1, 160):
        searchUrl = searchBaseUrl % (i,)
        print searchUrl
        searchPage = urllib2.urlopen(searchUrl)
        searchPageData = searchPage.read()

        searchRegex = u'<a href="http://www.phillipscollection.org/collection/browse-the-collection\?id=([^\"]+)">http://www.phillipscollection.org'
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
            invnum = itemmatch.group(1)
            url = u'http://www.phillipscollection.org/collection/browse-the-collection?id=%s' % (invnum,)
            print url
            metadata['url'] = url
            metadata['id'] = invnum
            metadata['collectionqid'] = u'Q578485'
            metadata['collectionshort'] = u'Phillips'
            metadata['locationqid'] = u'Q578485'
            metadata['instanceofqid'] = u'Q3305213'

            itemPage = urllib2.urlopen(url)
            itemPageData = unicode(itemPage.read(), u'utf-8')
            
            #print itemPageEnData
            headerRegex = u'<figure class="main">[\r\n\t\s]*<figcaption class="grid_7">[\r\n\t\s]*<header>[\r\n\t\s]*<h1>([^<]+)</h1>[\r\n\t\s]*<h2>([^<]+)<' #em>1872-1944</em></h2></header>
            #titleRegex = u'<li class="ca first"><a href="/ca/colleccio/[^\"]+" class="language-link" xml:lang="ca" title="([^\"]+)">Català</a></li>[\r\n\t\s]*<li class="es"><a href="/es/colleccio/[^\"]+" class="language-link" xml:lang="es" title="([^\"]+)">Español</a></li>[\r\n\t\s]*<li class="en last active"><a href="/en/colleccio/[^\"]+" class="language-link active" xml:lang="en" title="([^\"]+)">English</a></li>'
            #titleEnRegex = u'<main class="main narrow">[\r\n\t\s]+<h1>[\r\n\t\s]*([^<]+)[\r\n\t\s]*</h1>'
            #creatorRegex = u'<div class="ds-author-piece">([^<]+)</div>'

            #<li><strong>Nationality</strong> <span class="value">Dutch</span></li>
            dateRegex = u'<li><strong>Creating Date</strong>[\r\n\t\s]*<span class="value">([^<]+)</span></li>'
            #<li><strong>Medium</strong> <span class="value">Oil on canvas</span></li>
            #<li><strong>Dimensions</strong> <span class="value">31 3/8 x 29 1/4 in.; 79.6925 x 74.295 cm</span></li>
            #<li><strong>Credit Line</strong> <span class="value">Gift from the estate of Katherine S. Dreier, 1953</span></li>

            # Could also get Dimensions, Medium and credit line
            
            matchHeader = re.search(headerRegex, itemPageData)
            if not matchHeader:
                pywikibot.output(u'The title data for this painting is BORKED!')
                continue

            #FIXME: Check encoding

            metadata['title'] = { u'en' : htmlparser.unescape(matchHeader.group(1)),
                                  }

            name = htmlparser.unescape(matchHeader.group(2)).strip()
            ## We need to normalize the name
            #if u',' in name:
            #    (surname, sep, firstname) = name.partition(u',')
            #    name = u'%s %s' % (firstname.strip(), surname.strip(),)
            metadata['creatorname'] = name
    
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        u'ca' : u'%s de %s' % (u'pintura', metadata.get('creatorname'),),
                                        u'es' : u'%s de %s' % (u'pintura', metadata.get('creatorname'),),
                                        }


            #invMatch = re.search(invRegex, itemPageData)

            #if not invMatch:
            #    pywikibot.output(u'No inventory number found! Skipping')
            #    continue
            
            #metadata['id'] = invMatch.group(1)
            metadata['idpid'] = u'P217'

            dateMatch = re.search(dateRegex, itemPageData)

            if dateMatch:
                metadata['inception'] = dateMatch.group(1)

            yield metadata

        

def main():
    dictGen = getPhillipsGenerator()

    #for painting in dictGen:
    #   print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
