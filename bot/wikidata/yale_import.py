#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import Hermitage paintings. No api, no csv, just plain old screen scraping stuff

* Loop over https://www.hermitagemuseum.org/wps/portal/hermitage/explore/collections/col-search/?lng=en&p1=category:%22Painting%22&p15=1
* Grab individual paintings like https://www.hermitagemuseum.org/wps/portal/hermitage/digital-collection/01.+Paintings/25685/ (remove the language)


The bot takes three csv files:
* One with the artists
* One with the type of works
* One with all the works

Combines these and uploads the data to Wikidata
"""
import artdatabot
#import json
import pywikibot
#from pywikibot import pagegenerators
import requests
import urllib2
import re
#import pywikibot.data.wikidataquery as wdquery
#import datetime
import HTMLParser
#import posixpath
#from urlparse import urlparse
#from urllib import urlopen
#import hashlib
#import io
#import base64
#import upload
#import tempfile
#import os
#import csv
import xml.etree.ElementTree as ET


def getYaleGenerator():
    '''
    Generator to return Hermitage paintings
    '''


    """
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
    

    

    #searchPage = urllib2.urlopen(sparqlurl)
    #searchPageData = searchPage.read()
    #print searchPageData


    # 1 - 22
    searchBaseUrl = u'http://collections.britishart.yale.edu/vufind/Search/Results?join=AND&bool0[]=AND&lookfor0[]=%%22Paintings+and+Sculpture%%22&type0[]=collection&bool1[]=AND&lookfor1[]=Painting&type1[]=type_facet&page=%s&view=grid'
    baseUrl = u'https://www.hermitagemuseum.org%s'
    htmlparser = HTMLParser.HTMLParser()

    j = 0

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
            metadata = {}

            metadata['collectionqid'] = u'Q6352575'
            metadata['collectionshort'] = u'Yale'
            metadata['locationqid'] = u'Q6352575'
            metadata['instanceofqid'] = u'Q3305213'
            
            metadata['url'] = url

            itemPage = urllib2.urlopen(url)
            itemPageData = itemPage.read()
            
            #print itemPageEnData
            titleRegex = u'<th id\="titleHeaders">Title\s*</th>[\r\n\t\s]+<td id="dataField">[\r\n\t\s]+([^<]+)[\r\n\t\s]+</td>'
            
            matchTitle = re.search(titleRegex, itemPageData)
            if not matchTitle:
                pywikibot.output(u'The title data for this painting is BORKED!')
                continue


            metadata['title'] = { u'en' : htmlparser.unescape(matchTitle.group(1).strip(u'\s\r\n\t')),
                                  }
            #pywikibot.output(metadata.get('title'))

            creatorRegex = u'<th id="titleHeaders">Creator[\r\n\t\s]+</th>[\r\n\t\s]+<td id="dataField">[\r\n\t\s]+<a href="[^"]+">([^,]+)[,<] '

            creatorMatch = re.search(creatorRegex, itemPageData)
            if not creatorMatch:
                pywikibot.output(u'The creator data for this painting is BORKED!')
                continue

            metadata['creatorname'] = creatorMatch.group(1)

            print metadata

            continue	
    
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', painterName,),
                                        u'en' : u'%s by %s' % (u'painting', painterName,),
                                        }

            #pywikibot.output(metadata.get('description'))

            invRegex = u'<p>[\r\n\s]+Inventory Number:[\r\n\s]+</p>[\r\n\s]+</div>[\r\n\s]+<div class="her-data-tbl-val">[\r\n\s]+<p>[\r\n\s]+(.*\d+)[\r\n\s]+</p>'
            invMatch = re.search(invRegex, itemPageEnData)

            if not invMatch:
                pywikibot.output(u'No inventory number found! Skipping')
                continue
            
            metadata['id'] = invMatch.group(1)
            metadata['idpid'] = u'P217'

            dateDimRegex = u'var descriptionWoA = \'.*Date of creation: (.+), Dimension: ([^\s]+)x([^\s]+)\s?[sc]m\.?\';'
            dateDimMatch = re.search(dateDimRegex, itemPageEnData)
            if dateDimMatch:
                metadata['inception'] = dateDimMatch.group(1)
                metadata['height'] = dateDimMatch.group(2)
                metadata['heightunitqid'] = u'Q174728'
                metadata['width'] = dateDimMatch.group(2)
                metadata['widthunitqid'] = u'Q174728'


            yield metadata

            
            
            #print matchEn.group(1)
            #print matchEn.group(2)
            #print matchEn.group(3)
            
            

        
    '''        

    paintinglisturl = u'https://raw.githubusercontent.com/artsmia/collection/master/departments/6.json'    
    paintinglistPage = urllib2.urlopen(paintinglisturl)
    paintinglistData = paintinglistPage.read()
    paintinglistDataObject = json.loads(paintinglistData)

    artists = {}
    objectnames = {}
    
    # Open the artists and dump it in a dict id -> qid

    with open('msk_artist_completed_2015-12_04.csv', 'rb') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            artists[row.get('creatorId')] = row.get('creatorWikidataPid').replace('http://www.wikidata.org/entity/', '').replace('http://www.wikidata.org/wiki/', '')
    #print artists

    # Open the types
    # FIXME: Werkt nu alleen voor schilderijen!!!!
    with open('MSK Gent AAT-Wikidata matching.csv', 'rb') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            objectnames[row.get('objectNameId')] = row.get('Wikidata Q')
    #print objectnames

    with open('MSK_import_wikidata_objects_16112015.csv', 'rb') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            metadata = {}


            

            metadata['title'] = { u'nl' : unicode(row.get('title'), u'utf-8') } # Hier iets met Nederlands doen
            metadata['url'] = unicode(row.get('workPid'), u'utf-8')

            name = unicode(row.get('creator'), u'utf-8')
            # We need to normalize the name
            if u',' in name:
                (surname, sep, firstname) = name.partition(u',')
            name = u'%s %s' % (firstname.strip(), surname.strip(),)
            metadata['creatorname'] = name
            
            metadata['objectname'] = unicode(row.get('objectName'), u'utf-8')               

            if metadata['creatorname'] and metadata['objectname']:
                metadata['description'] = { u'nl' : u'%s van %s' % (metadata['objectname'], metadata['creatorname']) }
                if metadata['objectname']==u'olieverfschilderij':
                    metadata['description']['en'] = u'painting by %s' % (metadata['creatorname'],)
                elif metadata['objectname']==u'beeldhouwwerk':
                    metadata['description']['en'] = u'sculpture by %s' % (metadata['creatorname'],)
                elif metadata['objectname']==u'aquarel':
                    metadata['description']['en'] = u'watercolor painting by %s' % (metadata['creatorname'],)
                    
            if row.get('creatorId') in artists:
                metadata['creatorqid'] = artists.get(row.get('creatorId'))

            if row.get('objectNameId') in objectnames:
                metadata['instanceofqid'] = objectnames.get(row.get('objectNameId'))

            if row.get('dateIso8601'):
                metadata['inception'] = unicode(row.get('dateIso8601'), u'utf-8')

            # Start with only paintings
            workwork = [u'olieverfschilderij',
                        #u'beeldhouwwerk',
                        #u'aquarel',
                        ]
            if metadata['objectname'] in workwork:
                yield metadata
            #else:
            #    yield metadata
    '''            
        

def main():
    dictGen = getYaleGenerator()

    for painting in dictGen:
        print painting

    #artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    #artDataBot.run()
    
    

if __name__ == "__main__":
    main()
