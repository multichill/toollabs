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
import urllib2
import re
import HTMLParser
import xml.etree.ElementTree as ET


def getYaleGenerator():
    """
    Generator to return Yale paintings
    
    searchurl= u''
    sparqlurl = u'http://collection.britishart.yale.edu/openrdf-sesame/repositories/ycba?query=PREFIX+owl%3A+%3Chttp%3A%2F%2Fwww.w3.org%2F2002%2F07%2Fowl%23%3E%0D%0APREFIX+rdf%3A+%3Chttp%3A%2F%2Fwww.w3.org%2F1999%2F02%2F22-rdf-syntax-ns%23%3E%0D%0APREFIX+rdfs%3A+%3Chttp%3A%2F%2Fwww.w3.org%2F2000%2F01%2Frdf-schema%23%3E%0D%0APREFIX+dc%3A+%3Chttp%3A%2F%2Fpurl.org%2Fdc%2Felements%2F1.1%2F%3E%0D%0APREFIX+crm%3A+%3Chttp%3A%2F%2Ferlangen-crm.org%2Fcurrent%2F%3E%0D%0APREFIX+foaf%3A+%3Chttp%3A%2F%2Fxmlns.com%2Ffoaf%2F0.1%2F%3E%0D%0APREFIX+skos%3A+%3Chttp%3A%2F%2Fwww.w3.org%2F2004%2F02%2Fskos%2Fcore%23%3E%0D%0APREFIX+xsd%3A+%3Chttp%3A%2F%2Fwww.w3.org%2F2001%2FXMLSchema%23%3E%0D%0APREFIX+lido%3A+%3Chttp%3A%2F%2Fwww.lido-schema.org%2F%3E%0D%0APREFIX+bibo%3A+%3Chttp%3A%2F%2Fpurl.org%2Fontology%2Fbibo%2F%3E%0D%0APREFIX+dcterms%3A+%3Chttp%3A%2F%2Fpurl.org%2Fdc%2Fterms%2F%3E%0D%0APREFIX+ycba%3A+%3Chttp%3A%2F%2Fcollection.britishart.yale.edu%2Fid%2F%3E%0D%0APREFIX+ycba_ont%3A+%3Chttp%3A%2F%2Fcollection.britishart.yale.edu%2Fid%2Fontology%2F%3E%0D%0APREFIX+ycba_aat%3A+%3Chttp%3A%2F%2Fcollection.britishart.yale.edu%2Fid%2Faat%2F%3E%0D%0APREFIX+ycba_ulan%3A+%3Chttp%3A%2F%2Fcollection.britishart.yale.edu%2Fid%2Fulan%2F%3E%0D%0APREFIX+ycba_tgn%3A+%3Chttp%3A%2F%2Fcollection.britishart.yale.edu%2Fid%2Ftgn%2F%3E%0D%0APREFIX+aat%3A+%3Chttp%3A%2F%2Fcollection.getty.edu%2Fid%2Faat%2F%3E%0D%0APREFIX+ulan%3A+%3Chttp%3A%2F%2Fcollection.getty.edu%2Fid%2Fulan%2F%3E%0D%0APREFIX+tgn%3A+%3Chttp%3A%2F%2Fcollection.getty.edu%2Fid%2Ftgn%2F%3E%0D%0ASELECT+DISTINCT+*+WHERE+%7B%0D%0A%09%3Frecord+crm%3AP2_has_type+%3Chttp%3A%2F%2Fvocab.getty.edu%2Faat%2F300033618%3E+.%0D%0A%7D&output=xml'
    sparqlpage = requests.get(sparqlurl)
    sparqlpage.encoding='utf-8'
    pywikibot.output(sparqlpage.text)

    baseurl = u'http://collections.britishart.yale.edu/vufind/Record/%s'
    basexmlurl = u'http://collections.britishart.yale.edu/oaicatmuseum/OAIHandler?verb=GetRecord&identifier=oai:tms.ycba.yale.edu:%s&metadataPrefix=lido'

    # BOOO HOOO, for some reason I get binary encoded crap. Let's just extract the id's so we can continue
    # Only seem to be getting about 800 id's, would have expected about 4000
    for match in re.finditer(u'(\d+)', sparqlpage.text):
        print match.group(1)
        if match.group(1)==u'0':
            continue
        url = baseurl % (match.group(1),)
        xmlurl = basexmlurl % (match.group(1),)

        xmlpage = requests.get(xmlurl)
        #xmlpage.encoding='utf-8'
        #pywikibot.output(xmlpage.text)
        

        root = ET.fromstring(xmlpage.text.encode(u'utf-8'))
        print root.keys()
        print root.items()
        for bla in root.iter():
            print bla
        
        ET.dump(root.find('OAI-PMH'))#.get('GetRecord').get('record').get('metadata'))
    """

    # 1 - 22
    searchBaseUrl = u'http://collections.britishart.yale.edu/vufind/Search/Results?join=AND&bool0[]=AND&lookfor0[]=%%22Paintings+and+Sculpture%%22&type0[]=collection&bool1[]=AND&lookfor1[]=Painting&type1[]=type_facet&page=%s&view=grid'
    baseUrl = u'https://www.hermitagemuseum.org%s'
    htmlparser = HTMLParser.HTMLParser()

    foundit=False

    for i in range(1, 22):
        searchUrl = searchBaseUrl % (i,)
        print searchUrl
        searchPage = urllib2.urlopen(searchUrl)
        searchPageData = searchPage.read()

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

            itemPage = urllib2.urlopen(url)
            itemPageData = unicode(itemPage.read(), u'utf-8')
            
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

            #pywikibot.output(metadata.get('description'))

            invRegex = u'<th id="titleHeaders">Accession Number[\r\n\t\s]+</th>[\r\n\t\s]+<td id="dataField">[\r\n\t\s]+<span title="Object ID:[\r\n\t\s]+\d+">[\r\n\t\s]+([^\r\n\t\s]+)[\r\n\t\s]+</span>[\r\n\t\s]+</td>'
            invMatch = re.search(invRegex, itemPageData)

            if not invMatch:
                pywikibot.output(u'No inventory number found! Skipping')
                continue
            
            metadata['id'] = invMatch.group(1)
            metadata['idpid'] = u'P217'


            dateRegex = u'<th id="titleHeaders">Date[\r\n\t\s]+</th>[\r\n\t\s]+<td id="dataField">[\r\n\t\s]+([^<]+)<br>[\r\n\t\s]+</td>'
            dateMatch = re.search(dateRegex, itemPageData)

            if dateMatch:
                metadata['inception'] = dateMatch.group(1)

            yield metadata

        

def main():
    dictGen = getYaleGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
