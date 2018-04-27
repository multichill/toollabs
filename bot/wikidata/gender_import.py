#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add gender based on RKDartists and ULAN.
Over time more sources were added. Now it's in need in some serious clean up.

Probably best to have a dict with the sources and a genertic + specific functions to process all sources.

Current sources:
* ULAN ID (P245)
* RKDartists ID (P650)
* Biografisch Portaal number (P651)
* DAAO ID (P1707) - TODO
* Benezit ID (P2843) - TODO
* ECARTICO person ID (P2915) - TODO
* Auckland Art Gallery artist ID (P3372)

See also https://www.wikidata.org/wiki/User:Multichill/Humans_no_gender

"""

import pywikibot
from pywikibot import pagegenerators
import re
import datetime
import requests

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
            if not itempage.exists():
                pywikibot.output(u'Item does not exist, skipping')
                continue

            if itempage.isRedirectPage():
                itempage = itempage.getRedirectTarget()
                
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

            biogender = None
            aucklandgender = None
            benezitgender = None

            newclaim = None

            if not gender:
                pywikibot.output(u'No gender found in ULAN and RKD')
                if u'P651' in claims:
                    bioid = claims.get('P651')[0].getTarget()
                    print bioid
                    biourl = u'http://www.biografischportaal.nl/persoon/%s' % (bioid,)
                    bioPage = requests.get(biourl, verify=False)

                    biogenderregex = u'\<th\>sekse\</th\>\s*\<td\>\s*\<ul\>\<li\>(man|vrouw)\</li\>\</ul\>'

                    biogendermatch = re.search(biogenderregex, bioPage.text)
                    if biogendermatch:
                        biogender = True
                        if biogendermatch.group(1) == u'man':
                            newclaim = self.addItemStatement(itempage, u'P21', u'Q6581097')
                        elif biogendermatch.group(1) == u'vrouw':
                            newclaim = self.addItemStatement(itempage, u'P21', u'Q6581072')
                elif u'P3372' in claims:
                    aucklandid = claims.get('P3372')[0].getTarget()
                    print aucklandid
                    aucklandurl = u'http://www.aucklandartgallery.com/explore-art-and-ideas/artist/%s/' % (aucklandid,)
                    aucklandPage = requests.get(aucklandurl, verify=False)

                    aucklandgenderregex = u'\<dt\>Gender\<\/dt\>\s*\n\s*\<dd\>(Male|Female)\<\/dd\>'

                    aucklandgendermatch = re.search(aucklandgenderregex, aucklandPage.text)
                    if aucklandgendermatch:
                        aucklandgender = True
                        if aucklandgendermatch.group(1) == u'Male':
                            newclaim = self.addItemStatement(itempage, u'P21', u'Q6581097')
                        elif aucklandgendermatch.group(1) == u'Female':
                            newclaim = self.addItemStatement(itempage, u'P21', u'Q6581072')
                elif u'P2843' in claims:
                    benezitid = claims.get('P2843')[0].getTarget()
                    print benezitid
                    beneziturl = u'http://oxfordindex.oup.com/view/10.1093/benz/9780199773787.article.%s' % (benezitid,)
                    benezitPage = requests.get(beneziturl)

                    benezitgenderregex = u'\<abstract\>\<p\>[^\<]+, (male|female)\.\<\/p\>'

                    benezitgendermatch = re.search(benezitgenderregex, benezitPage.text)
                    if benezitgendermatch:
                        benezitgender = True
                        if benezitgendermatch.group(1) == u'male':
                            newclaim = self.addItemStatement(itempage, u'P21', u'Q6581097')
                        elif benezitgendermatch.group(1) == u'female':
                            newclaim = self.addItemStatement(itempage, u'P21', u'Q6581072')


            elif gender==u'm':
                newclaim = self.addItemStatement(itempage, u'P21', u'Q6581097')
            elif gender==u'f':
                newclaim = self.addItemStatement(itempage, u'P21', u'Q6581072')

            if newclaim:
                if ulangender:
                    self.addReference(itempage, newclaim, ulanurl)
                if rkdgender:
                    self.addReference(itempage, newclaim, rkdurl)
                if biogender:
                    self.addReference(itempage, newclaim, biourl)
                if aucklandgender:
                    self.addReference(itempage, newclaim, aucklandurl)
                if benezitgender:
                    self.addReference(itempage, newclaim, beneziturl)

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
    query = u"""SELECT DISTINCT ?item WHERE {
  { ?item wdt:P245 [] } UNION # ULAN ID (P245)
  { ?item wdt:P650 [] } UNION # RKDartists ID (P650)
  { ?item wdt:P651 [] } UNION # Biografisch Portaal number (P651)
  { ?item wdt:P1707 [] } UNION # DAAO ID (P1707)
  { ?item wdt:P3372 [] } UNION  # Auckland Art Gallery artist ID (P3372)
  { ?item wdt:P2843 [] } . # Benezit ID (P2843)
  ?item wdt:P31 wd:Q5 .
  MINUS { ?item p:P21 [] } .
}"""

    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    genderBot = GenderBot(generator)
    genderBot.run()

if __name__ == "__main__":
    main()
