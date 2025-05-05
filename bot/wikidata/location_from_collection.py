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
    def __init__(self, generator, correctlocation=False):
        """
        Arguments:
            * generator    - A generator that yields ItemPage objects.
            * correctlocation - Correct the location with the contents of the collection?

        """
        self.generator = generator
        self.correctlocation = correctlocation
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
            if u'P195' not in claims:
                pywikibot.output(u'No collection found, skipping')
                continue
            if len(claims[u'P195'])!=1:
                pywikibot.output(u'Found multiple collections, skipping')
                continue
            if u'P276' in claims:
                if not self.correctlocation:
                    pywikibot.output(u'Already has a location and not correcting, done')
                    continue
                elif len(claims[u'P276'])!=1:
                    pywikibot.output(u'Found multiple locations to correct, skipping')
                    continue
                else:
                    locationclaim = claims.get('P276')[0]
                    currentlocation = locationclaim.getTarget()
                    collection = claims.get('P195')[0].getTarget()
                    # TODO: Figure out how to get the magic edit summary on Wikidata
                    summary = 'replacing [[Wikidata:WikiProject sum of all paintings/Imprecise location|imprecise location]] [[%s]]' % (currentlocation.title(),)
                    pywikibot.output(u'Adding collection %s as new location' % (collection.title(),))
                    locationclaim.changeTarget(collection, summary=summary)
            else:
                #Get the collection so we can add it later
                collection = claims.get('P195')[0].getTarget()
                summary = u'based on collection (which has coordinates)'
                newclaim = pywikibot.Claim(self.repo, u'P276')
                newclaim.setTarget(collection)
                pywikibot.output(u'Adding collection %s as location' % (collection.title(),))
                itempage.addClaim(newclaim, summary=summary)


def main(*args):
    """
    Main function. Grab a generator and pass it to the bot to work on
    """
    correctlocation = False
    query = """SELECT ?item ?collection  WHERE {
  ?item wdt:P31 wd:Q3305213 ;
        wdt:P195 ?collection .
  MINUS { ?item wdt:P276 [] } .
  ?collection wdt:P625 [] .
} LIMIT 5000"""

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-correctlocation'):
            correctlocation = True
            query = """SELECT ?item ?collection ?location WHERE {
  ?item wdt:P31 wd:Q3305213 ;
        wdt:P276 ?location ;
        wdt:P195 ?collection . 
  ?collection wdt:P131+ ?location ;
              wdt:P625 [] .
  } ORDER BY ?collection
LIMIT 5000"""

    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    locationFromCollectionBot = LocationFromCollectionBot(generator, correctlocation=correctlocation)
    locationFromCollectionBot.run()

if __name__ == "__main__":
    main()
