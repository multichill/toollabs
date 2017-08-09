#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import Rijksmonumenten to Wikidata.
The data is coming from the monuments database, see https://commons.wikimedia.org/wiki/Commons:Monuments_database

Code is quite messy, but should be easy to reuse it for other countries.

* Get all the items that don't have an image, but do have an id
* Get all the heritage sites that have an id and have an image from the Monuments database

"""
import json
import pywikibot
from pywikibot import pagegenerators
import requests
import re

class MonumentsImageBot:
    """
    A bot to enrich and create monuments on Wikidata
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields Wikidata items objects.

        """
        self.generator = generator
        self.repo = pywikibot.Site().data_repository()
        self.monumentImages = self.imagesMonumentsDatabase()
        
    def imagesMonumentsDatabase(self, country=u'nl', lang=u'nl'):

        result =  {}
        baseurl = u'https://tools.wmflabs.org/heritage/api/api.php?action=search&srcountry=%s&srlang=%s&format=json&srwithimage=1&limit=1000'
        searchurl = baseurl % (country, lang)
        sourceregex = u'^(\/\/.+\.wikipedia\.org\/w\/index\.php\?).+&(oldid\=\d+)$'
        url = searchurl
        srcontinue = True
        while srcontinue:
            monumentsPage = requests.get(url)
            monumentsJson = monumentsPage.json()
            for monument in monumentsJson.get('monuments'):
                sourcematch = re.match(sourceregex, monument.get('source'))
                source = u'%s%s' % (sourcematch.group(1), sourcematch.group(2))
                                       
                monumentinfo = { u'id' : monument.get('id'),
                                 u'image' : monument.get('image'),
                                 u'source' : source,
                                 }
                result[monument.get('id')]=monumentinfo            
            if monumentsJson.get('continue'):
                srcontinue = monumentsJson.get('continue').get('srcontinue')
                url = searchurl + u'&srcontinue=' + srcontinue
            else:
                srcontinue = False
        return result

    def run(self):
        """
        Starts the robot.
        """
        for item in self.generator:
            data = item.get()
            claims = data.get('claims')

            if u'P359' in claims:
                heritageid = claims.get(u'P359')[0].getTarget()

            # Hardcoded to Rijksmonument. Could do something with SPARQL query
            if u'P18' not in claims and heritageid in self.monumentImages:
                imagename = self.monumentImages.get(heritageid).get('image')
                sourceurl = self.monumentImages.get(heritageid).get('source')
                
                print u'no image found'
                # Construct
                newclaim = pywikibot.Claim(self.repo, u'P18')
                commonssite = pywikibot.Site("commons", "commons")
                imagelink = pywikibot.Link(imagename, source=commonssite, defaultNamespace=6)
                image = pywikibot.ImagePage(imagelink)
                if image.isRedirectPage():
                    image = pywikibot.ImagePage(image.getRedirectTarget())
                if not image.exists():
                    pywikibot.output('[[%s]] doesn\'t exist so I can\'t link to it' % (image.title(),))
                else:
                    newclaim.setTarget(image)
                    pywikibot.output('Adding %s --> %s based on %s' % (newclaim.getID(), newclaim.getTarget(), sourceurl))
                    summary = 'based on usage in list https%s' % (sourceurl,)
                    item.addClaim(newclaim, summary=summary)
                
def main():
    query = u"""SELECT ?item WHERE {
  ?item wdt:P1435 wd:Q916333 .
  MINUS { ?item wdt:P18 ?image.} .
}"""
    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    monumentsImageBot = MonumentsImageBot(generator)
    monumentsImageBot.run()
    

if __name__ == "__main__":
    main()
