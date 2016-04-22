#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape artists from the Getty website

"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib2
import re
import pywikibot.data.wikidataquery as wdquery
import datetime
import HTMLParser
import posixpath
from urlparse import urlparse
from urllib import urlopen
import hashlib
import io
import base64
import upload
import tempfile
import os
import csv


def getArtistGenerator(query=u''):
    '''

    Doing a two step approach here. Could do one, but would be complicated
    * Loop over http://www.getty.edu/art/collection/search/?view=grid&query=YToxOntzOjEzOiJkZXBhcnRtZW50LmlkIjthOjE6e2k6MDtpOjE7fX0%3D&pg=1 - 25 and grab paintings
    * Grab data from paintings
    '''
    
    baseurl = u'http://www.getty.edu/art/collection/artists/%s/' 

    htmlparser = HTMLParser.HTMLParser()

    for i in range(1,1000):
        simpleurl = baseurl % (i,)

        artistPage = urllib2.urlopen(simpleurl)
        artistData = artistPage.read()

        metadata = {}
        metadata['Entry ID'] = unicode(i)
        #metadata['simpleurl'] = simpleurl

        nameregex = u'<meta name="name" content="([^"]+)"/>'
        cultureregex = u'<meta name="culture" content="([^"]+)"/>'
        dateregex = u'<meta name="date" content="([^"]+)"/>'
        urlregex = u'<link rel="canonical" href="([^"]+)"/>'

        namematch = re.search(nameregex, artistData)
        metadata[u'Entry name']=htmlparser.unescape(namematch.group(1)).encode(u'utf-8') 

        culture=u''
        culturematch = re.search(cultureregex, artistData)
        if culturematch:
            culture=htmlparser.unescape(culturematch.group(1))

        date=u''
        datematch = re.search(dateregex, artistData)
        if datematch:
            date=htmlparser.unescape(datematch.group(1))

        metadata['Entry description'] = u'%s, %s'.encode(u'utf-8') % (culture, date)
        metadata['Entry type'] = u'person'

        urlmatch = re.search(urlregex, artistData)
        metadata[u'Entry URL']=htmlparser.unescape(urlmatch.group(1))
        
        yield metadata   
            
        

def main():
    artistGen = getArtistGenerator()

    with open('getty_artists.tsv', 'wb') as tsvfile:
        fieldnames = [u'Entry ID', # (your alphanumeric identifier; must be unique within the catalog)
                      u'Entry name', # (will also be used for the search in mix'n'match later)
                      u'Entry description', # 
                      u'Entry type', # (short string, e.g. "person" or "location"; recommended)
                      u'Entry URL', # if omitted, it will be constructed from the URL pattern and the entry ID. Either a URL pattern or a URL column are required!
                      ]

        writer = csv.DictWriter(tsvfile, fieldnames, dialect='excel-tab')

        #No header!
        #writer.writeheader()
        

        for artist in artistGen:
            print artist
            writer.writerow(artist)


if __name__ == "__main__":
    main()
