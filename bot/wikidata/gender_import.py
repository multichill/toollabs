#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add gender based on RKDartists and ULAN.
Is in need in some serious clean up.

"""
import json
import pywikibot
from pywikibot import pagegenerators
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
import tempfile
import os
import time
import itertools
import requests
import simplejson

class GenderBot:
    """
    A bot to add gender to people
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

            if u'P21' in claims:
                pywikibot.output(u'Already has gender, skipping')
                continue


            ulanid = None
            ulanurl = None
            ulanapiurl = None
            ulangender = None
            if u'P245' in claims:
                ulanid = claims.get('P245')[0].getTarget()
                print ulanid
                ulanurl = u'http://vocab.getty.edu/page/ulan/%s' % (ulanid,)
                ulanapiurl = u'http://vocab.getty.edu/download/json?uri=http://vocab.getty.edu/ulan/%s.json' % (ulanid,)
                ulanPage = requests.get(ulanapiurl)
                try:
                    ulanPageDataDataObject = ulanPage.json()

                    if ulanPageDataDataObject.get(u'results'):
                        if ulanPageDataDataObject.get(u'results').get(u'bindings'):
                            for binding in ulanPageDataDataObject.get(u'results').get(u'bindings'):
                                # We only care about this item and literals
                                if binding.get(u'Predicate').get(u'type')==u'uri' and binding.get(u'Predicate').get(u'value')==u'http://schema.org/gender' and binding.get(u'Object').get(u'type')==u'uri':
                                    #Female
                                    print binding.get(u'Object').get(u'value')
                                    if binding.get(u'Object').get(u'value')==u'http://vocab.getty.edu/aat/300189557':
                                        ulangender=u'f'
                                    elif binding.get(u'Object').get(u'value')==u'http://vocab.getty.edu/aat/300189559':
                                        ulangender=u'm'
                                    elif binding.get(u'Object').get(u'value')==u'http://vocab.getty.edu/aat/300400512':
                                        ulangender=None
                                    else:
                                        pywikibot.output(u'Found weird ulan gender: %s' % (binding.get(u'Object').get(u'value'),))
                                    break
                                                         
                                        
                except simplejson.scanner.JSONDecodeError:
                    pywikibot.output('On %s I got a json error while working on %s, skipping it' % (itempage.title(), ulanapiurl))
                    ulangender = None


            rkdid = None
            rkdurl = None
            rkdapiurl = None
            rkdgender = None
                
            if u'P650'in claims:
                rkdid = claims.get('P650')[0].getTarget()
                print rkdid
                rkdurl = u'http://rkd.nl/explore/artists/%s' % (rkdid,)
                rkdapiurl = u'https://api.rkd.nl/api/record/artists/%s?format=json' % (rkdid,)
                rkdPage = requests.get(rkdapiurl, verify=False)
                try:
                    rkdPageDataObject = rkdPage.json()

                    if rkdPageDataObject.get(u'response'):
                        if rkdPageDataObject.get(u'response').get(u'docs'):
                            if rkdPageDataObject.get(u'response').get(u'docs')[0].get('geslacht'):
                                if rkdPageDataObject.get(u'response').get(u'docs')[0].get('geslacht')==u'm':
                                    rkdgender=u'm'
                                elif rkdPageDataObject.get(u'response').get(u'docs')[0].get('geslacht')==u'v': 
                                    rkdgender=u'f'
                                else:
                                    pywikibot.output(u'Found weird RKD  gender: %s' % (rkdPageDataObject.get(u'response').get(u'docs')[0].get('geslacht'),))    
                                        
                except simplejson.scanner.JSONDecodeError:
                    pywikibot.output('On %s I got a json error while working on %s, skipping it' % (itempage.title(), rkdapiurl))
                    #rkdgender = None          

            print rkdgender
            print u'ulan thinks %s and rkd thinks %s ' % (ulangender,rkdgender, )
            gender = None
            if ulangender and rkdgender:
                if ulangender==rkdgender:
                    gender=ulangender
                    pywikibot.output(u'Ulan and RKD agree that it\'s a %s' % (gender,))
                else:
                    pywikibot.output(u'Ulan and RKD don\'t agree')
                    continue
                
            elif ulangender:
                gender=ulangender
            elif rkdgender:
                gender=rkdgender

            if not gender:
                pywikibot.output(u'No gender found')
                continue

            if gender==u'm':
                newclaim = self.addItemStatement(itempage, u'P21', u'Q6581097')
            elif gender==u'f':
                newclaim = self.addItemStatement(itempage, u'P21', u'Q6581072')

            if newclaim:
                if ulangender:
                    self.addReference(itempage, newclaim, ulanurl)
                if rkdgender:
                    self.addReference(itempage, newclaim, rkdurl)
                
                
            '''
            europeanaurl = 
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
                
            '''

    def addItemStatement(self, item, pid, qid):
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
        return newclaim
        #self.addReference(item, newclaim, url)
        
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

    wd_query = wdquery.WikidataQuery(cacheMaxAge=100)
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
    #query = u'CLAIM[650] AND CLAIM[245] AND NOCLAIM[21] AND CLAIM[31:5]' # Humans, no gender, ULAN and RKD
    #query = u'CLAIM[650] AND NOCLAIM[21] AND CLAIM[31:5]' # Humans, no gender, RKD
    query = u'(claim[650] OR CLAIM[245]) and noclaim[21] AND CLAIM[31:5]' # Humans, no gender, RKD or ULAN

    generator = WikidataQueryPageGenerator(query)


    #for painting in dictGen:
    #    pywikibot.output(painting)

    genderBot = GenderBot(generator)
    genderBot.run() 
    

if __name__ == "__main__":
    main()
