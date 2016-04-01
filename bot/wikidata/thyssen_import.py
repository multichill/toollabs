#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import Thyssen-Bornemisza Collection  paintings. No api, no csv, just plain old screen scraping stuff

* Loop over http://www.museothyssen.org/en/thyssen/ficha_obra/1 - ???

"""
import artdatabot
#import json
import pywikibot
#from pywikibot import pagegenerators
#import urllib2
import requests
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

    # 1 - 1000 ?
    baseUrl = u'http://www.museothyssen.org/en/thyssen/ficha_obra/%s'
    htmlparser = HTMLParser.HTMLParser()

    for i in range(1, 1500):
        url = baseUrl % (i,)
        print url

        metadata = {}

        metadata['collectionqid'] = u'Q176251'
        metadata['collectionshort'] = u'Thyssen-Bornemisza'
        metadata['locationqid'] = u'Q176251'
        metadata['instanceofqid'] = u'Q3305213'
        metadata['idpid'] = u'P217'
        
        metadata['url'] = url
        metadata['url_en'] = url
        metadata['url_es'] = u'http://www.museothyssen.org/thyssen/ficha_obra/%s' % (i,)

        itemPageEn = requests.get(metadata['url_en'])
        itemPageEs = requests.get(metadata['url_es'])

        itemPageEn.encoding='utf-8'
        itemPageEs.encoding='utf-8'

        itemPageEnData = itemPageEn.text
        #print itemPageEn.encoding
        #itemPageEnDataCleaned = re.sub("(<!--.*?-->)", "", itemPageEn.text, flags=re.DOTALL) # Strip out comment junk
        #pywikibot.showDiff(itemPageEnData, itemPageEnDataCleaned)
        #pywikibot.output(itemPageEnDataCleaned)
        itemPageEsData = itemPageEs.text

        if len(itemPageEn.text) < 100:
            #That's not a valid page
            continue

        regexes = {}

        regexes['creatorname'] = u'<dt>Autor:</dt>[\r\n\s]+<dd>[\r\n\s]+<a href="[^"]+" title="[^"]+">[\r\n\s]+<span>([^<]+)</span></a>[\r\n\s]+</dd>'
        regexes['title'] = u'tulo:</dt>[\r\n\s]+<dd class="dd_titulo"><em>([^<]+)<' # Also possible to have <BR />/em></dd>'
        regexes['date'] = u'<dt>Fecha:</dt>[\r\n\s]+<dd class="dd_fecha">([^<]+\d+[^<]+)</dd>'

        # Medium doesn't work
        #regexes['medium'] = u'<dt>T.?cnica:'#</dt>[\r\n\s]+'#<dd class="dd_tecnica">([^<]+)</dd>'
        #regexes['medium'] = u'cnica:</dt>[\r\n\s]+<dd class="dd_tecnica">([^<]+)</dd>'
        regexes['size'] = u'<dt>Medidas:</dt>[\r\n\s]+<dd class="dd_medidas">[\r\n\s]+(.+)x(.+)cm[\r\n\s]+</dd>'
        regexes['id'] = u'<dt>Numero de inventario</dt>[\r\n\s]+<dd><abbr title="INV. Nr.">INV. Nr.</abbr>([^<]+)</dd>'

        matches = {}

        matches['creatorname']=re.search(regexes['creatorname'], itemPageEnData)
        metadata['creatorname']=matches['creatorname'].group(1).strip()

        metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata['creatorname'],),
                                    u'en' : u'%s by %s' % (u'painting', metadata['creatorname'],),
                                    }

        matches['titleen']=re.search(regexes['title'], itemPageEnData)
        matches['titlees']=re.search(regexes['title'], itemPageEsData)     
        metadata['title']={ u'en' : htmlparser.unescape(matches['titleen'].group(1).strip()),
                            u'es' : htmlparser.unescape(matches['titlees'].group(1).strip()), 
                              }        

        matches['date']=re.search(regexes['date'], itemPageEnData)
        if matches['date']:
            metadata['date']=matches['date'].group(1).strip()

        #matches['medium']=re.search(regexes['medium'], itemPageEnData)
        #metadata['medium']=matches['medium'].group(1).strip()

        # Ignore size for now. Needs two fields anyway
        #matches['size']=re.search(regexes['size'], itemPageEnData)
        #metadata['size']=matches['size'].group(1)

        matches['id']=re.search(regexes['id'], itemPageEnData)
        metadata['id']=matches['id'].group(1).strip()

        # Crude way to filter out the non-painting
        if not metadata['id'].startswith(u'(CTB.DEC'):
            yield metadata
        '''
        for field, regex in regexes.iteritems():
            matches[field] = re.search(regex, itemPageEnData)
            print field
            #print regex
            if matches[field]:
                print matches[field].group(1)
            else:
                print u'No match found'
            
        

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
    #    pywikibot.output(painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
