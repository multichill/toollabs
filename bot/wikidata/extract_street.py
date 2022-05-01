#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Tool to extract the street from the address.
* Loop over a bunch of items
* Check if it doesn't already contain a street (P669)
* Get P969 (if available)
* Get the is in the administrative-territorial entity('s) (P131)
* If multiple, get the most specific
* Do a regex to get everything before the first number
* Based on the name, get a bunch of items (beware: English by default)
* For each item check if it's in the same administrative-territorial entity
* If that's the case, add the street claim


"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib
import re
import pywikibot.data.wikidataquery as wdquery
from pywikibot.data import api

class StreetBot:
    """
    A bot to add streets on Wikidata
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields itempage objects.

        """
        self.generator = generator
        self.repo = pywikibot.Site().data_repository()

                        
    def run(self):
        """
        Starts the robot.
        """
        for item in self.generator:
            pywikibot.output(u'Working on %s' % (item.title(),))
             
            if item.exists():
                item.get()
                if not u'P669' in item.claims and u'P969' in item.claims and u'P131' in item.claims:
                    # We have no street, but we do have address and administrative thingie
                    admItem = None
                    if len(item.claims.get('P131'))==1:
                        admItem = item.claims.get('P131')[0].getTarget()
                    elif len(item.claims.get('P131'))==2:
                        admItemA = item.claims.get('P131')[0].getTarget()
                        admItemA.get()
                        admItemB = item.claims.get('P131')[1].getTarget()
                        admItemB.get()
                        if admItemA.claims.get('P131'):
                            if admItemA.claims.get('P131')[0].getTarget()== admItemB:
                                admItem = admItemA
                        if admItemB.claims.get('P131'):
                            if admItemB.claims.get('P131')[0].getTarget()== admItemA:
                                admItem = admItemB

                    if admItem:
                        streetItem = None
                        address = item.claims.get('P969')[0].getTarget()
                        #print address
                        regex = u'^([^\d]+)\s\d+.*$'
                        match = re.search(regex, address)
                        if match:
                            streetname = match.group(1).strip()
                            #print streetname
                            request = api.Request(site=self.repo,
                                                  action='wbsearchentities',
                                                  search=streetname,
                                                  language='en')
                            data = request.submit()
                            if data.get('success')==1:
                                for hit in data.get('search'):
                                    hitItem = pywikibot.ItemPage(self.repo, hit.get('id'))
                                    hitItem.get()
                                    # We got a hit, now test if it's a street and if it's in the same administrative location
                                    isStreet = False
                                    sameAdmin = False
                                    if hitItem.claims.get('P31'):
                                        for istanceHit in hitItem.claims.get('P31'):
                                            if istanceHit.getTarget().title()==u'Q79007':
                                                isStreet=True
                                                continue

                                    if hitItem.claims.get('P131'):
                                        for adminHit in hitItem.claims.get('P131'):
                                            if adminHit.getTarget()==admItem:
                                                sameAdmin=True
                                                continue
                                    if isStreet and sameAdmin:
                                        streetItem = hitItem
                                        continue
                            if streetItem:
                                pywikibot.output(u'Found street item for %s' % (streetname,))
                                newclaim = pywikibot.Claim(self.repo, u'P669')

                                summary = u'Adding street claim to %s ([[%s]]) based on address %s' % (streetname,
                                                                                                   streetItem.title(),
                                                                                                   address,)

                                newclaim.setTarget(streetItem)
                                pywikibot.output('Adding instance claim to %s' % item)
                                item.addClaim(newclaim, summary=summary)
                            else:
                                pywikibot.output(u'Did not find a street item for %s' % (streetname,))
                        

def WikidataQueryItemPageGenerator(query, site=None):
    """Generate pages that result from the given WikidataQuery.

    @param query: the WikidataQuery query string.

    """
    if site is None:
        site = pywikibot.Site()
    repo = site.data_repository()

    wd_queryset = wdquery.QuerySet(query)

    wd_query = wdquery.WikidataQuery(cacheMaxAge=0)
    data = wd_query.query(wd_queryset)

    pywikibot.output(u'retrieved %d items' % data[u'status'][u'items'])
    for item in data[u'items']:
        yield pywikibot.ItemPage(repo, u'Q' + unicode(item))


def main():

    query = u'CLAIM[359] AND CLAIM[131:9899] AND CLAIM[969] AND NOCLAIM[669]'
    pigenerator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataItemGenerator(WikidataQueryItemPageGenerator(query)))
    
    streetBot = StreetBot(pigenerator)
    streetBot.run()
    
if __name__ == "__main__":
    main()
