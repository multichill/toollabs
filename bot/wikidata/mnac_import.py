#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from the Museu Nacional d'Art de Catalunya (MNAC).

Good old scraping from http://www.museunacional.cat/en/advanced-piece-search?title_1=&title=&field_piece_inventory_number_value=&keys=&field_piece_type_value_i18n[0]=pintura&&&page=0

* Loop over http://www.museunacional.cat/en/advanced-piece-search?title_1=&title=&field_piece_inventory_number_value=&keys=&field_piece_type_value_i18n[0]=pintura&&&page=0
* Grab individual paintings like http://www.museunacional.cat/en/colleccio/market-zaragoza/joaquin-pallares/011513-000

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import urllib2
import re
import HTMLParser
import xml.etree.ElementTree as ET


def getMNACGenerator():
    """
    Generator to return MANC paintings
    
    """

    # 0 - 86 (something between 80 and 90
    searchBaseUrl = u'http://www.museunacional.cat/en/advanced-piece-search?title_1=&title=&field_piece_inventory_number_value=&keys=&field_piece_type_value_i18n[0]=pintura&&&page=%s'
    htmlparser = HTMLParser.HTMLParser()

    foundit=True

    for i in range(0, 86):
        searchUrl = searchBaseUrl % (i,)
        print searchUrl
        searchPage = urllib2.urlopen(searchUrl)
        searchPageData = searchPage.read()

        searchRegex = u'<a href="(/en/colleccio/[^\"]+)">Read more</a>'
        itemmatches = re.finditer(searchRegex, searchPageData)
        urllist = []
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
            url = u'http://www.museunacional.cat%s' % (itemmatch.group(1),)
            print url

            if url==u'http://adsfasdfasdf':
                foundit=True
            if not foundit:
                continue
            metadata = {}

            metadata['collectionqid'] = u'Q861252'
            metadata['collectionshort'] = u'MNAC'
            metadata['locationqid'] = u'Q861252'
            metadata['instanceofqid'] = u'Q3305213'
            
            metadata['url'] = url

            itemPage = urllib2.urlopen(url)
            itemPageData = unicode(itemPage.read(), u'utf-8')
            
            #print itemPageEnData
            titleRegex = u'<li class="ca first"><a href="/ca/colleccio/[^\"]+" class="language-link" xml:lang="ca" title="([^\"]+)">Català</a></li>[\r\n\t\s]*<li class="es"><a href="/es/colleccio/[^\"]+" class="language-link" xml:lang="es" title="([^\"]+)">Español</a></li>[\r\n\t\s]*<li class="en last active"><a href="/en/colleccio/[^\"]+" class="language-link active" xml:lang="en" title="([^\"]+)">English</a></li>'
            #titleEnRegex = u'<main class="main narrow">[\r\n\t\s]+<h1>[\r\n\t\s]*([^<]+)[\r\n\t\s]*</h1>'
            creatorRegex = u'<div class="ds-author-piece">([^<]+)</div>'
            dateRegex = u'Painting<div class="ds-feature"><p>(\d\d\d\d)</p></div>' #FIXME: Only matches on real years
            invRegex = u'Inventory number:&nbsp;</div><p>([^<]+)</p>'

            # Could also get Dimensions, Materials, Acquisition
            
            matchTitle = re.search(titleRegex, itemPageData)
            if not matchTitle:
                pywikibot.output(u'The title data for this painting is BORKED!')
                continue

            #FIXME: Check encoding

            metadata['title'] = { u'ca' : htmlparser.unescape(matchTitle.group(1)),
                                  u'es' : htmlparser.unescape(matchTitle.group(2)),
                                  u'en' : htmlparser.unescape(matchTitle.group(3)),
                                  }
            
            #pywikibot.output(metadata.get('title'))

            creatorMatch = re.search(creatorRegex, itemPageData)
            if not creatorMatch:
                pywikibot.output(u'The creator data for this painting is BORKED!')
                continue

            #FIXME: Add some logic for work after and clean up

            name = htmlparser.unescape(creatorMatch.group(1))
            # We need to normalize the name
            if u',' in name:
                (surname, sep, firstname) = name.partition(u',')
                name = u'%s %s' % (firstname.strip(), surname.strip(),)
            metadata['creatorname'] = name
    
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        u'ca' : u'%s de %s' % (u'pintura', metadata.get('creatorname'),),
                                        u'es' : u'%s de %s' % (u'pintura', metadata.get('creatorname'),),
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
    dictGen = getMNACGenerator()

    #for painting in dictGen:
    #   print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
