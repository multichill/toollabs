#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to fix Amsterdam Museum links 

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
import time
import itertools

class FixCollectionBot:
    """
    A bot to enrich and create paintings on Wikidata
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.
            The dict in this generator needs to contain 'idpid' and 'collectionqid'
            * create       - Boolean to say if you want to create new items or just update existing

        """
        self.generator = generator
        self.repo = pywikibot.Site().data_repository()


        

                        
    def run(self):
        """
        Starts the robot.
        """
            
        for itempage in self.generator:
            
                
            data = itempage.get()
            claims = data.get('claims')

            if u'P727' not in claims:
                pywikibot.output(u'No Europeana id found, nothing to extract')
                continue
            
            europeanaurl = claims.get('P727')[0].getTarget()
            #print europeanaurl

            amid = europeanaurl.replace('2021608/dispatcher_aspx_action_search_database_ChoiceCollect_search_priref_', u'')
            if europeanaurl==amid:
                pywikibot.output(u'Can\'t extract the id, skipping')
                continue

            
            print amid

            if u'P1184' not in claims:
                handletext = u'11259/collection.%s' % (amid,)
                newclaim = pywikibot.Claim(self.repo, u'P1184')
                newclaim.setTarget(handletext)
                pywikibot.output('Adding handle at claim to %s' % itempage)
                itempage.addClaim(newclaim)
                
            if u'P973' not in claims:
                url = u'http://am.adlibhosting.com/amonline/details/collect/%s' % (amid,)
                newclaim = pywikibot.Claim(self.repo, u'P973')
                newclaim.setTarget(url)
                pywikibot.output('Adding described at claim to %s' % itempage)
                itempage.addClaim(newclaim)
                
                

    def addItemStatement(self, item, pid, qid, url):
        '''
        Helper function to add a statement
        '''
        if not qid:
            return False

        claims = item.get().get('claims')
        if pid in claims:
            return
        
        newclaim = pywikibot.Claim(self.repo, pid)
        destitem = pywikibot.ItemPage(self.repo, qid)
        newclaim.setTarget(destitem)
        pywikibot.output(u'Adding %s->%s to %s' % (pid, qid, item))
        item.addClaim(newclaim)
        self.addReference(item, newclaim, url)
        
    def addReference(self, item, newclaim, url):
        """
        Add a reference with a retrieval url and todays date
        """
        pywikibot.output('Adding new reference claim to %s' % item)
        refurl = pywikibot.Claim(self.repo, u'P854') # Add url, isReference=True
        refurl.setTarget(url)
        refdate = pywikibot.Claim(self.repo, u'P813')
        today = datetime.datetime.today()
        date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
        refdate.setTarget(date)
        newclaim.addSources([refurl, refdate])
      
        
def WikidataQueryPageGenerator(query, site=None):
    """Generate pages that result from the given WikidataQuery.

    @param query: the WikidataQuery query string.
    @param site: Site for generator results.
    @type site: L{pywikibot.site.BaseSite}

    """
    if site is None:
        site = pywikibot.Site()
    repo = site.data_repository()

    wd_queryset = wdquery.QuerySet(query)

    wd_query = wdquery.WikidataQuery(cacheMaxAge=0)
    data = wd_query.query(wd_queryset)

    pywikibot.output(u'retrieved %d items' % data[u'status'][u'items'])

    foundit=True
    
    for item in data[u'items']:
        if int(item) > 17380752:
            foundit=True
        if foundit:
            itempage = pywikibot.ItemPage(repo, u'Q' + unicode(item))
            yield itempage

        

def main():
    query = u'CLAIM[31:3305213] AND CLAIM[195:1820897] AND CLAIM[727] AND NOCLAIM[1184]' # Has VIAF and RKDartists, but not ULAN

    generator = WikidataQueryPageGenerator(query)


    #for painting in dictGen:
    #    pywikibot.output(painting)

    fixCollectionBot = FixCollectionBot(generator)
    fixCollectionBot.run() 
    

if __name__ == "__main__":
    main()
