#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from the Dulwich Picture Gallery. Good old scraping from http://www.dulwichpicturegallery.org.uk/explore-the-collection/

* Loop over http://www.dulwichpicturegallery.org.uk/explore-the-collection/?page=2&artist=&country=&period=&subjectMatter=&search=
* Grab individual paintings like http://www.dulwichpicturegallery.org.uk/explore-the-collection/151-200/charles-small-pybus/

The naming of the pages is a bit weird.

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import urllib2
import re
import HTMLParser
import xml.etree.ElementTree as ET


def getDulwichGenerator():
    """
    Generator to return Dulwich paintings
    
    """

    # 1 - 22
    searchBaseUrl = u'http://www.dulwichpicturegallery.org.uk/explore-the-collection/?page=%s&artist=&country=&period=&subjectMatter=&search='
    #baseUrl = u'https://www.hermitagemuseum.org%s'
    htmlparser = HTMLParser.HTMLParser()

    foundit=True

    for i in range(1, 22):
        searchUrl = searchBaseUrl % (i,)
        print searchUrl
        searchPage = urllib2.urlopen(searchUrl)
        searchPageData = searchPage.read()

        searchRegex = u'<a href="(/explore-the-collection/\d+-\d+/[^\"]+/)">'
        matches = re.finditer(searchRegex, searchPageData)
        urllist = []
        for match in matches:
            try:
            #    #bla = unicode(match.group(1), u'utf-8')
                urllist.append(u'http://www.dulwichpicturegallery.org.uk%s' % (match.group(1),))
            except UnicodeDecodeError:
                pywikibot.output(u'Found an url I cannot parse: %s' % (unicode(match.group(1), u'utf-8'),))

        #print len(urllist)
        urlset = set(urllist)
        #print len(urlset)


        for url in urlset:
            print url
            if url==u'http://adsfasdfasdf':
                foundit=True
            if not foundit:
                continue
            metadata = {}

            metadata['collectionqid'] = u'Q1241163'
            metadata['collectionshort'] = u'Dulwich'
            metadata['locationqid'] = u'Q1241163'
            metadata['instanceofqid'] = u'Q3305213'
            
            metadata['url'] = url

            itemPage = urllib2.urlopen(url)
            itemPageData = unicode(itemPage.read(), u'utf-8')
            
            #print itemPageEnData
            titleRegex = u'<main class="main narrow">[\r\n\t\s]+<h1>[\r\n\t\s]*([^<]+)[\r\n\t\s]*</h1>'
            creatorRegex = u'<dt class="row-meta-title">Artist</dt>[\r\n\t\s]*<dd class="row-meta-definition">[\r\n\t\s]*([^<]+)[\r\n\t\s]*</dd>'
            dateRegex = u'<dt class="row-meta-title">Date</dt>[\r\n\t\s]*<dd class="row-meta-definition">[\r\n\t\s]*([^<]+)[\r\n\t\s]*</dd>'
            invRegex = u'<dt class="row-meta-title">Accession number</dt>[\r\n\t\s]*<dd class="row-meta-definition">[\r\n\t\s]*([^<]+)[\r\n\t\s]*</dd>'

            # Could also get Dimensions, Materials, Acquisition
            
            matchTitle = re.search(titleRegex, itemPageData)
            if not matchTitle:
                pywikibot.output(u'The title data for this painting is BORKED!')
                continue

            metadata['title'] = { u'en' : htmlparser.unescape(matchTitle.group(1)),
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
                                        }

            # Check for anonymous works
            if metadata.get('creatorname') in [ u'British School',
                                                u'Bolognese School',
                                                ]:
                metadata['creatorqid'] = u'Q4233718'
                
            elif metadata.get('creatorname').startswith(u'Attributed to') or metadata.get('creatorname').startswith(u'After ') or metadata.get('creatorname').startswith(u'Follower of '):
                metadata['creatorqid'] = u'Q4233718'

            #pywikibot.output(metadata.get('description'))

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
    dictGen = getDulwichGenerator()

    #for painting in dictGen:
    #   print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
