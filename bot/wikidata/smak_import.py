#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import SMAK stuff

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
#import urllib2
import re
#import pywikibot.data.wikidataquery as wdquery
#import datetime
#import HTMLParser
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



def getSMAKGenerator():
    '''
    Generator that combines 3 csv files and returns dicts
    '''

    artists = {}
    objectnames = {}
    
    # Open the artists and dump it in a dict id -> qid

    with open('SMAK-creators-completed-2016-01-23.csv', 'rb') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            artists[row.get('creatorId')] = row.get('creatorWikidataPid').replace('http://www.wikidata.org/entity/', '').replace('http://www.wikidata.org/wiki/', '')
    #print artists

    # Open the types
    with open('SMAK-objectnames-20160124.csv', 'rb') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            objectnames[row.get('objectNameId')] = row.get('Wikidata Q')
    #print objectnames

    foundit=False
    with open('SMAK-objects-20160124.csv', 'rb') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            metadata = {}

            metadata['collectionqid'] = u'Q1540707'
            metadata['collectionshort'] = u'SMAK'
            metadata['locationqid'] = u'Q1540707'
            
            metadata['id'] = unicode(row.get('objectNumber'), u'utf-8')
            metadata['idpid'] = u'P217'
            title = unicode(row.get('title'), u'utf-8')

            if len(title) > 200:
                title = re.sub('^(.{20,200})\.(.+)$', u'\\1.', title)

            if len(title) > 200:
                title = re.sub('^(.{20,200}),(.+)$', u'\\1.', title)
                
            metadata['title'] = { u'nl' : title } # Hier iets met Nederlands doen

            # Welcome in URL hell.
            # Data url in the reference
            metadata['refurl'] = unicode(row.get('dataPid'), u'utf-8')
            # The Pid url for described by url
            metadata['describedbyurl'] = unicode(row.get('workPid'), u'utf-8')
            # The Pid url for the inventory number reference
            metadata['idrefurl'] = unicode(row.get('workPid'), u'utf-8')
            # This shouldn't actually be used
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
                if metadata['objectname']==u'schilderij': 
                    metadata['description']['en'] = u'painting by %s' % (metadata['creatorname'],)
                elif metadata['objectname']==u'beeldhouwwerk': 
                    metadata['description']['en'] = u'sculpture by %s' % (metadata['creatorname'],)
                elif metadata['objectname']==u'kunstwerk': 
                    metadata['description']['en'] = u'work of art by %s' % (metadata['creatorname'],)
                    
            if row.get('creatorId') in artists:
                metadata['creatorqid'] = artists.get(row.get('creatorId'))

            if row.get('objectNameId') in objectnames:
                metadata['instanceofqid'] = objectnames.get(row.get('objectNameId'))
            #metadata['instanceofqid'] = unicode(row.get('instanceofqid'), u'utf-8')

            if row.get('dateIso8601'):
                metadata['inception'] = unicode(row.get('dateIso8601'), u'utf-8')

            ## Start with only paintings
            #workwork = [u'olieverfschildering',
            #            #u'beeldhouwwerk',
            #            #u'aquarel',
            #            ]
            #if metadata['objectname'] in workwork:
            #    yield metadata
            ##else:
            # De dubbele regels hebben geen id
            if metadata['id']:
                if metadata['id']==u'5892':
                    foundit=True
                if foundit: # and metadata['objectname'] and metadata['objectname']==u'schilderij':
                    yield metadata
            
        

def main():
    dictGen = getSMAKGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
