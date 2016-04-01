#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape paintings from the Van Gogh website


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

class ArtistBot:
    """
    A bot to add MoMA artist id's to Wikidata
    """
    def __init__(self, dictGenerator):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.generator = dictGenerator
        self.repo = pywikibot.Site().data_repository()
        self.moma = pywikibot.ItemPage(self.repo, u'Q188740')
        
                        
    def run(self):
        """
        Starts the robot.
        """
        for artist in self.generator:
            artistItem = pywikibot.ItemPage(self.repo, artist.get('wikidata'))
            if artistItem.isRedirectPage():
                artistItem = artistItem.getRedirectTarget()
                
            data = artistItem.get()
            claims = data.get('claims')

            #P2174: MOMA artist id
            if u'P2174' not in claims and artist.get(u'moma'):
                newclaim = pywikibot.Claim(self.repo, u'P2174')
                newclaim.setTarget(artist[u'moma'])
                pywikibot.output('Adding MOMA artist id claim %s based on [%s MOMA website]' % (artist[u'moma'], artist[u'url']))
                artistItem.addClaim(newclaim)
                self.addReference(artistItem, newclaim, artist[u'url'])

            #P245: ULAN
            if u'P245' not in claims and artist.get(u'ulan'):
                newclaim = pywikibot.Claim(self.repo, u'P245')
                newclaim.setTarget(artist[u'ulan'])
                pywikibot.output('Adding ULAN claim %s based on [%s MOMA website]' % (artist[u'ulan'], artist[u'url']))
                artistItem.addClaim(newclaim)
                self.addReference(artistItem, newclaim, artist[u'url'])
       

    def addReference(self, item, newclaim, uri):
        """
        Add a reference with a retrieval url and todays date
        """
        pywikibot.output('Adding new reference claim to %s' % item)
        refstated = pywikibot.Claim(self.repo, u'P248')
        refstated.setTarget(self.moma)
        refurl = pywikibot.Claim(self.repo, u'P854') 
        refurl.setTarget(uri)
        refdate = pywikibot.Claim(self.repo, u'P813')
        today = datetime.datetime.today()
        date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
        refdate.setTarget(date)
        newclaim.addSources([refstated, refurl, refdate])


def getArtistGenerator(query=u''):
    '''
    Bla %02d
    '''
    baseurl = u'http://www.moma.org/collection/artists/%s'

    for i in range(9998, 20000):
        try:
            url = baseurl % (i,)
            print url
            page = urllib2.urlopen(url)
            pageData = page.read()

            wikidataregex = u'<dt class=\'label\'>\nWikidata\n</dt>\n<dd class=\'text\'>\n(Q\d+)\n</dd>'
            ulanregex = u'<dt class=\'label\'>\nULAN\n</dt>\n<dd class=\'text\'>\n(\d+)\n</dd>'

            metadata = {}
            metadata['url'] = url
            metadata['moma'] = str(i)
            wikidataidmatch = re.search(wikidataregex, pageData)
            if wikidataidmatch:
                wikidataid = wikidataidmatch.group(1)
                metadata['wikidata'] = wikidataid

                ulanidmatch = re.search(ulanregex, pageData)
                if ulanidmatch:
                    ulanid = ulanidmatch.group(1)
                    metadata['ulan'] = ulanid
            
                yield metadata
        except urllib2.HTTPError:
            print u'Oops, that page does not exist, skipping'
            pass
        
        
            
        

def main():
    artistGen = getArtistGenerator()
    repo = pywikibot.Site().data_repository()
  
    artistBot = ArtistBot(artistGen)
    artistBot.run()
    
    

if __name__ == "__main__":
    main()
