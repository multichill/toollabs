#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add gender based on RKDartists and ULAN.
Is in need in some serious clean up.

"""

import pywikibot
from pywikibot import pagegenerators
import re
import datetime
import requests
#import simplejson

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
                # I didn't import simplejson. Does this still work?
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

def main():
    #query = u'CLAIM[650] AND CLAIM[245] AND NOCLAIM[21] AND CLAIM[31:5]' # Humans, no gender, ULAN and RKD
    #query = u'CLAIM[650] AND NOCLAIM[21] AND CLAIM[31:5]' # Humans, no gender, RKD
    query = u'(claim[650] OR CLAIM[245]) and noclaim[21] AND CLAIM[31:5]' # Humans, no gender, RKD or ULAN
    query = u"""SELECT DISTINCT ?item WHERE {
  { ?item wdt:P245 [] } UNION
  { ?item wdt:P650 [] } UNION
  { ?item wdt:P651 [] } .
  ?item wdt:P31 wd:Q5 .
  MINUS { ?item wdt:P21 [] } .
}"""

    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    genderBot = GenderBot(generator)
    genderBot.run()

if __name__ == "__main__":
    main()
