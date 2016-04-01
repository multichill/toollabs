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
import os
import csv



def getHermitageGenerator():
    '''
    Generator to return Hermitage paintings
    '''

    # 1 - 367
    searchBaseUrl = u'https://www.hermitagemuseum.org/wps/portal/hermitage/explore/collections/col-search/?lng=en&p1=category:%%22Painting%%22&p15=%s'
    baseUrl = u'https://www.hermitagemuseum.org%s'
    htmlparser = HTMLParser.HTMLParser()

    for i in range(1, 378):
        searchUrl = searchBaseUrl % (i,)
        print searchUrl
        searchPage = urllib2.urlopen(searchUrl)
        searchPageData = searchPage.read()

        searchRegex = u'<div class="her-search-results-row">[\r\n\s]+<div class="her-col-35 her-search-results-img">[\r\n\s]+<a href="(/wps/portal/hermitage/digital-collection/01.+Paintings/\d+/)?lng=en"'
        searchRegex = u'<div class="her-search-results-row">[\r\n\s]+<div class="her-col-35 her-search-results-img">[\r\n\s]+<a href="(/wps/portal/hermitage/digital-collection/01\.\+Paintings/\d+/)\?lng=en"'
        matches = re.finditer(searchRegex, searchPageData)
        for match in matches:
            metadata = {}

            metadata['collectionqid'] = u'Q132783'
            metadata['collectionshort'] = u'Hermitage'
            metadata['locationqid'] = u'Q132783'
            metadata['instanceofqid'] = u'Q3305213'
            
            metadata['url'] = baseUrl % match.group(1)
            metadata['url_en'] = '%s?lng=en' % (metadata['url'],)
            metadata['url_ru'] = '%s?lng=ru' % (metadata['url'],)

            itemPageEn = urllib2.urlopen(metadata['url_en'])
            itemPageRu = urllib2.urlopen(metadata['url_ru'])
            print metadata['url_en']
            itemPageEnData = unicode(itemPageEn.read(), u'utf-8')
            itemPageRuData = unicode(itemPageRu.read(), u'utf-8')

            #print itemPageEnData
            headerRegex = u'<header>[\r\n\s]+<h3>([^<]*)</h3>[\r\n\s]+<h1>([^<]*)</h1>[\r\n\s]+<p>([^<]*)</p>[\r\n\s]+</header>'
            matchEn = re.search(headerRegex, itemPageEnData)
            if not matchEn:
                pywikibot.output(u'The data for this painting is BORKED!')
                continue

            matchRu = re.search(headerRegex, itemPageRuData)


            metadata['title'] = { u'en' : htmlparser.unescape(matchEn.group(2)),
                                  u'ru' : htmlparser.unescape(matchRu.group(2)), 
                                  }
            #pywikibot.output(metadata.get('title'))

            painterName = matchEn.group(1)

            painterRegexes = [u'([^,]+),\s([^\.]+)\.(.+)',
                              u'([^,]+),\s([^,]+),(.+)',
                              ]
            for painterRegex in painterRegexes:
                painterMatch = re.match(painterRegex, painterName)
                if painterMatch:
                    painterName = '%s %s' % (painterMatch.group(2), painterMatch.group(1),)
                    continue
            metadata['creatorname'] = painterName

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
    dictGen = getHermitageGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
