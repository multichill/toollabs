#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add the collection qualifer to the inventory numbers.
It will work on all items with an inventory number, but no collection qualifier

This will reduce down the list on https://www.wikidata.org/wiki/Wikidata:Database_reports/Constraint_violations/P217#.22Qualifiers.22_violations

Just the paintings in this list are available at https://www.wikidata.org/wiki/User:Multichill/Paintings_inventory_numbers_missing_collection

"""
import pywikibot
from pywikibot import pagegenerators

class FixInventoryCollectionBot:
    """
    A bot to enrich and create paintings on Wikidata
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields ItemPage objects.

        """
        self.generator = generator
        self.repo = pywikibot.Site().data_repository()
                
    def run(self):
        """
        Starts the robot.
        """
        for itempage in self.generator:
            pywikibot.output(u'Working on %s' % (itempage.title(),))
            data = itempage.get()
            claims = data.get('claims')

            # Do some checks so we are sure we found exactly one inventory number and one collection
            if u'P217' not in claims:
                pywikibot.output(u'No inventory number found, skipping')
                continue                
            if len(claims[u'P217'])!=1:
                pywikibot.output(u'Found multiple inventory numbers, skipping')
                continue
            if u'P195' not in claims:
                pywikibot.output(u'No collection found, skipping')
                continue                
            if len(claims[u'P195'])!=1:
                pywikibot.output(u'Found multiple collections, skipping')
                continue

            #Get the collection so we can add it later
            collection = claims.get('P195')[0].getTarget()
            summary = u'Adding [[%s]] as a qualifier to the inventory number' % collection.title()

            # Get the claim and make sure the qualifier is missing
            claim = claims.get('P217')[0]
            if not u'P195' in claim.qualifiers:
                newqualifier = pywikibot.Claim(self.repo, u'P195')
                newqualifier.setTarget(collection)
                pywikibot.output('Adding new qualifier claim to %s' % itempage)
                pywikibot.output(summary)
                claim.addQualifier(newqualifier, summary=summary)

def main():
    """
    Main function. Grab a generator and pass it to the bot to work on
    """
    
    query = u"""SELECT DISTINCT ?item
WHERE 
{
	?item p:P217 ?inventory .  # with an inventory number and we want the statement
  	?item wdt:P195 ?collection .  # with a collection set
	FILTER NOT EXISTS { ?inventory pq:P195 ?somecollection }  # and the inventory statement is missing the collection qualifier
}
LIMIT 1000"""
    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    fixInventoryCollectionBot = FixInventoryCollectionBot(generator)
    fixInventoryCollectionBot.run() 

if __name__ == "__main__":
    main()
