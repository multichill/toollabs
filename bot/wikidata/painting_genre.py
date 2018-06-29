#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Painting genre classifier

"""
#import json
import pywikibot
from pywikibot import pagegenerators
import re
#import datetime
import requests
import pywikibot.data.sparql
import pandas

class PaintingGenreBot:
    """
    
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields wikidata item objects.

        """
        
        self.repo = pywikibot.Site().data_repository()
        # Split up in, training, test and validation
        self.workdata = []
        self.workdata = self.workdata + self.getWorkData(u'Q134307') # portrait
        self.workdata = self.workdata + self.getWorkData(u'Q2864737') # religious art
        self.workdata = self.workdata + self.getWorkData(u'Q191163') # landscape art
        self.dataframe = pandas.DataFrame(self.workdata)
        print self.dataframe.head()

        cat_features = []
        scalar_features = []
        binary_features = []

        for feat in cat_features:
            self.dataframe[feat] = self.dataframe[feat].astype('category')
        for feat in scalar_features:
            self.dataframe[feat] = self.dataframe[feat].astype('scalar')
        for feat in binary_features:
            self.dataframe[feat] = self.dataframe[feat].astype('binary')


        #self.viafitem = pywikibot.ItemPage(self.repo, u'Q54919')

    def getWorkData(self, genreid, limit=100):
        """
        Get the generator of items to consider
        """
        query = u"""SELECT ?item ?label ?description YEAR(?inception) ?movementLabel ?locationLabel ?collectionLabel ?creatorLabel (MD5(CONCAT(str(?item),str(RAND()))) as ?random) WHERE {
  ?item wdt:P31 wd:Q3305213 .  
  ?item wdt:P136 wd:Q134307 . 
  OPTIONAL { ?item rdfs:label ?label FILTER (LANG (?label) = "en") . }
  OPTIONAL { ?item schema:description ?description FILTER (LANG (?description) = "en") .}
  OPTIONAL { ?item wdt:P571 ?inception } .
  OPTIONAL { ?item wdt:P135 ?movement } .
  OPTIONAL { ?item wdt:P276 ?location } .
  OPTIONAL { ?item wdt:P195 ?collection } .
  OPTIONAL { ?item wdt:P170 ?creator } .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
} ORDER BY ?random
LIMIT %s"""
        query = u"""
        SELECT ?item ?genreLabel ?paintingLabel ?description (YEAR(?inception) as ?year) ?movementLabel ?locationLabel ?collectionLabel ?creatorLabel WHERE {
  ?item wdt:P31 wd:Q3305213 .  
  ?item wdt:P136 ?genre .
  FILTER(?genre=wd:%s) . 
  BIND(wd:Q134307 AS ?genre) . 
  OPTIONAL { ?item rdfs:label ?paintingLabel FILTER (LANG (?paintingLabel) = "en") . }
  OPTIONAL { ?item schema:description ?description FILTER (LANG (?description) = "en") .}
  OPTIONAL { ?item wdt:P571 ?inception } .
  OPTIONAL { ?item wdt:P135 ?movement } .
  OPTIONAL { ?item wdt:P276 ?location } .
  OPTIONAL { ?item wdt:P195 ?collection } .
  OPTIONAL { ?item wdt:P170 ?creator } .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
LIMIT %s""" % (genreid, limit)
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)
        #print queryresult


        return queryresult

        #for resultitem in queryresult:
        #    resultitem['item'] = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        #    yield resultitem

    def run(self):
        """
        Work on all items
        """

        for item in self.generator:
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


def main():
    """
    Do a query for items that do have RKDartists (P650) and VIAF (P214), but no ULAN (P245)
    :return:
    """
    paintingGenreBot = PaintingGenreBot()
    paintingGenreBot.run()

if __name__ == "__main__":
    main()
