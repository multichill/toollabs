#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Compare https://lod-cloud.net/ with Wikidata and see what can be improved.

https://lod-cloud.net/dataset/wikidata is the Wikidata info

http://lod-cloud.net/lod-data.json is all info

"""
import json
import pywikibot
from pywikibot import pagegenerators
import re
#import datetime
import requests
import pywikibot.data.sparql


class LodCloudBot:
    """
    
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields wikidata item objects.

        """
        
        self.repo = pywikibot.Site().data_repository()
        # Split up in, training, test and validation
        self.wdinfo = self.getWikidataInfo()
        self.lodinfo = self.getLodCloudInfo()


    def getWikidataInfo(self):
        """
        Get the generator of items to consider
        """
        query = u"""SELECT ?property ?propertyLabel ?propertyDescription ?formatterurl ?formatteruri WHERE {
  ?property wikibase:propertyType wikibase:ExternalId .
  ?property wdt:P1630 ?formatterurl .
  OPTIONAL { ?property wdt:P1921 ?formatteruri }.
  
  SERVICE wikibase:label {            # ... include the labels
		bd:serviceParam wikibase:language "en" .
	}
} 
LIMIT 10000"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)
        #print queryresult


        return queryresult

        #for resultitem in queryresult:
        #    resultitem['item'] = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        #    yield resultitem

    def getLodCloudInfo(self):
        localfile = u'/home/mdammers/Downloads/lod-data.json'
        with open(localfile, 'rb') as lodfile:
            data = json.loads(lodfile.read())
            return data

        #url = u'http://lod-cloud.net/lod-data.json'
        #page = requests.get(url)
        #return page.json()

    def run(self):
        """
        Work on all items
        """
        #print self.wdinfo
        #print self.lodinfo
        cleanRegex = u'^https?\:\/\/(.+)\$1$'
        for propertyInfo in self.wdinfo:
            print propertyInfo.get(u'formatterurl')
            #print propertyInfo
            if propertyInfo.get(u'formatteruri'):
                # Already has RDF link
                continue
            formatMatch = re.match(cleanRegex, propertyInfo.get(u'formatterurl'))
            if not formatMatch:
                # Format didn't match, skipping for now
                continue
            urlsearch = formatMatch.group(1)
            print urlsearch
            for siteinfo in self.lodinfo:


        return
        """


        #for item in self.generator:
            if not item.exists():
                continue

            if item.isRedirectPage():
                item = item.getRedirectTarget()

            data = item.get()
            claims = data.get('claims')

            if u'P214' not in claims:
                print u'No viaf found, skipping'
                continue

            if u'P245' in claims:
                # Already has ULAN, great!
                continue

            viafid = claims.get(u'P214')[0].getTarget()

            if not viafid:
                print u'Viaf is set to novalue, skipping'
                continue
            
            viafurl = u'http://www.viaf.org/viaf/%s/' % (viafid,)
            viafurljson = u'%sjustlinks.json' % (viafurl,)
            viafPage = requests.get(viafurljson)

            try:
                viafPageDataDataObject = viafPage.json()
            except ValueError:
                pywikibot.output('On %s the VIAF link %s returned this junk:\n %s' % (item.title(),
                                                                                      viafurljson,
                                                                                      viafPage.text))
                continue

            if isinstance(viafPageDataDataObject, dict) and viafPageDataDataObject.get(u'JPG'):
                ulanid = viafPageDataDataObject.get(u'JPG')[0]

                newclaim = pywikibot.Claim(self.repo, u'P245')
                newclaim.setTarget(ulanid)
                pywikibot.output('Adding ULAN %s claim to %s' % (ulanid, item.title(), ))

                # Default text is "‎Created claim: ULAN identifier (P245): 500204732, "
                summary = u'based on VIAF %s' % (viafid,)
                
                item.addClaim(newclaim, summary=summary)

                pywikibot.output('Adding new reference claim to %s' % item)

                refsource = pywikibot.Claim(self.repo, u'P248')
                refsource.setTarget(self.viafitem)
                
                refurl = pywikibot.Claim(self.repo, u'P854')
                refurl.setTarget(viafurl)
                
                refdate = pywikibot.Claim(self.repo, u'P813')
                today = datetime.datetime.today()
                date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
                refdate.setTarget(date)
                
                newclaim.addSources([refsource, refurl, refdate])
        """

def main():
    """

    :return:
    """
    lodCloudBot = LodCloudBot()
    lodCloudBot.run()

if __name__ == "__main__":
    main()
