#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add the missing location based on collection with coordinates

It works on all items without a location and only one collection. The collection has to has coordinates.

Just the paintings in this list are available at xxx

"""
import pywikibot
from pywikibot import pagegenerators

class LocationFromCollectionBot:
    """
    A bot to add locations to paintings on Wikidata
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

            # Do some checks
            if u'P276' in claims:
                pywikibot.output(u'Already has a location, done')
                continue
            if u'P195' not in claims:
                pywikibot.output(u'No collection found, skipping')
                continue
            if len(claims[u'P195'])!=1:
                pywikibot.output(u'Found multiple collections, skipping')
                continue

            #Get the collection so we can add it later
            collection = claims.get('P195')[0].getTarget()
            summary = u'based on collection (which has coordinates)'
            newclaim = pywikibot.Claim(self.repo, u'P276')
            newclaim.setTarget(collection)
            pywikibot.output(u'Adding collection %s as location' % (collection.title(),))
            itempage.addClaim(newclaim, summary=summary)


def main():
    """
    Main function. Grab a generator and pass it to the bot to work on
    """
    
    query = u"""SELECT ?item ?collection  WHERE {
  ?item wdt:P31 wd:Q3305213 .
  ?item wdt:P195 ?collection .
  MINUS { ?item wdt:P276 [] } .
  MINUS { ?item wdt:P195 wd:Q842858 } . # Skipping Nationalmuseum for now
  MINUS { ?item wdt:P195 wd:Q18600731 } . # And RCE art collection, don't like that as location
  ?collection wdt:P625 [] .
} ORDER BY ?collection"""
    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    locationFromCollectionBot = LocationFromCollectionBot(generator)
    locationFromCollectionBot.run()

if __name__ == "__main__":
    main()
