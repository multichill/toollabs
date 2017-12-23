#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from Yale Center for British Art. Could get their sparql and xml stuff to work so I ended up just scraping it.

* Loop over http://collections.britishart.yale.edu/vufind/Search/Results?join=AND&bool0[]=AND&lookfor0[]=%22Paintings+and+Sculpture%22&type0[]=collection&bool1[]=AND&lookfor1[]=Painting&type1[]=type_facet&page=2&view=grid
* Grab individual paintings like http://collections.britishart.yale.edu/vufind/Record/1668715

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re
import HTMLParser

def getYaleGenerator():
    """
    Generator to return Yale paintings
    
    """

    # 1 - 22
    #searchBaseUrl = u'http://collections.britishart.yale.edu/vufind/Search/Results?join=AND&bool0[]=AND&lookfor0[]=%%22Paintings+and+Sculpture%%22&type0[]=collection&bool1[]=AND&lookfor1[]=Painting&type1[]=type_facet&page=%s&view=grid'
    searchBaseUrl = u'http://collections.britishart.yale.edu/vufind/Search/Results?lookfor=&type=AllFields&filter[]=object_name_facet%%3A%%22painting%%22&page=%s&view=grid'
    htmlparser = HTMLParser.HTMLParser()

    session = requests.Session()

    foundit=True

    for i in range(1, 22):
        searchUrl = searchBaseUrl % (i,)
        print searchUrl
        searchPage = session.get(searchUrl)
        searchPageData = searchPage.text

        searchRegex = u'(http://collections.britishart.yale.edu/vufind/Record/\d+)'
        matches = re.finditer(searchRegex, searchPageData)
        urllist = []
        for match in matches:
            urllist.append(match.group(1))

        #print len(urllist)
        urlset = set(urllist)
        #print len(urlset)

        for url in urlset:
            print url
            if url==u'http://collections.britishart.yale.edu/vufind/Record/1668520':
                foundit=True
            if not foundit:
                continue
            metadata = {}

            metadata['collectionqid'] = u'Q6352575'
            metadata['collectionshort'] = u'Yale'
            metadata['locationqid'] = u'Q6352575'
            metadata['instanceofqid'] = u'Q3305213'
            
            metadata['url'] = url

            itemPage = session.get(url)
            itemPageData = itemPage.text # unicode(itemPage.read(), u'utf-8')
            
            #print itemPageEnData
            titleRegex = u'<th id\="titleHeaders">Title\s*</th>[\r\n\t\s]+<td id="dataField">[\r\n\t\s]+([^<]+)[\r\n\t\s]+</td>'
            
            matchTitle = re.search(titleRegex, itemPageData)
            if not matchTitle:
                pywikibot.output(u'The title data for this painting is BORKED!')
                continue


            metadata['title'] = { u'en' : htmlparser.unescape(matchTitle.group(1).strip(u'\s\r\n\t')),
                                  }
            #pywikibot.output(metadata.get('title'))

            creatorRegex = u'<th id="titleHeaders">Creator[\r\n\t\s]+</th>[\r\n\t\s]+<td id="dataField">[\r\n\t\s]+<a href="[^"]+">([^,<]+)[,<]'

            creatorMatch = re.search(creatorRegex, itemPageData)
            if not creatorMatch:
                pywikibot.output(u'The creator data for this painting is BORKED!')
                continue

            metadata['creatorname'] = creatorMatch.group(1)

    
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }

            invRegex = u'<th id=\"titleHeaders\">Accession Number[\r\n\t\s]+</th>[\r\n\t\s]+<td id=\"dataField\">[\r\n\t\s]+<span title="Object ID:[\r\n\t\s]+\d+">[\r\n\t\s]+([^\r\n\t\s]+)[\r\n\t\s]+</span>[\r\n\t\s]+</td>'
            invMatch = re.search(invRegex, itemPageData)

            if not invMatch:
                pywikibot.output(u'No inventory number found! Skipping')
                continue
            
            metadata['id'] = invMatch.group(1)
            metadata['idpid'] = u'P217'

            dateRegex = u'<th id=\"titleHeaders\">Date[\r\n\t\s]+</th>[\r\n\t\s]+<td id=\"dataField\">[\r\n\t\s]+([^<]+)<br>[\r\n\t\s]+</td>'
            dateMatch = re.search(dateRegex, itemPageData)

            if dateMatch:
                metadata['inception'] = dateMatch.group(1)

            # Data not available
            # record.get('acquisition')

            mediumRegex = u'<th id=\"titleHeaders\">Medium[\r\n\t\s]+</th>[\r\n\t\s]+<td id=\"dataField\">[\r\n\t\s]+([^<]+)[\r\n\t\s]+</td>'
            mediumMatch = re.search(mediumRegex, itemPageData)

            if mediumMatch and mediumMatch.group(1).strip()==u'Oil on canvas':
                metadata['medium'] = u'oil on canvas'

            dimensionRegex = u'<th id=\"titleHeaders\">Dimensions[\r\n\t\s]+</th>[\r\n\t\s]+<td id=\"dataField\">[\r\n\t\s]+([^<]+)[\r\n\t\s]+</td>'
            dimensionMatch = re.search(dimensionRegex, itemPageData)

            if dimensionMatch:
                dimensiontext = dimensionMatch.group(1).strip()
                regex_2d = u'.*\((?P<height>\d+(\.\d+)?) (x|×) (?P<width>\d+(\.\d+)?) cm\)'
                regex_3d = u'.*\((?P<height>\d+(\.\d+)?) (x|×) (?P<width>\d+(\.\d+)?) (x|×) (?P<depth>\d+(\.\d+)?) cm\)'
                match_2d = re.match(regex_2d, dimensiontext)
                match_3d = re.match(regex_3d, dimensiontext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height')
                    metadata['widthcm'] = match_2d.group(u'width')
                elif match_3d:
                    metadata['heightcm'] = match_3d.group(u'height')
                    metadata['widthcm'] = match_3d.group(u'width')
                    metadata['depthcm'] = match_3d.group(u'depth')
            yield metadata


def main():
    dictGen = getYaleGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
