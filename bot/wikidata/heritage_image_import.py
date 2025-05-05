#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import heritage images from the Monuments database to Wikidata.
The data is coming from the monuments database, see https://commons.wikimedia.org/wiki/Commons:Monuments_database

Configure sources to work on at https://www.wikidata.org/wiki/User:BotMultichillT/heritage_images.js

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
    def __init__(self, generator, country=u'nl', lang=u'nl', wdproperty=u'P359'):
        """
        Arguments:
            * generator    - A generator that yields Wikidata items objects.

        """
        self.generator = generator
        self.repo = pywikibot.Site().data_repository()
        self.monumentImages = self.imagesMonumentsDatabase(country=country, lang=lang)
        self.wdproperty = wdproperty
        
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

            heritageid = None
            if self.wdproperty in claims:
                heritageid = claims.get(self.wdproperty)[0].getTarget()

            # Hardcoded to Rijksmonument. Could do something with SPARQL query
            if u'P18' not in claims and heritageid in self.monumentImages:
                imagename = self.monumentImages.get(heritageid).get('image')
                sourceurl = self.monumentImages.get(heritageid).get('source')

                # Construct
                newclaim = pywikibot.Claim(self.repo, u'P18')
                commonssite = pywikibot.Site("commons", "commons")
                imagelink = pywikibot.Link(imagename, source=commonssite, default_namespace=6)
                image = pywikibot.FilePage(imagelink)
                if image.isRedirectPage():
                    image = pywikibot.FilePage(image.getRedirectTarget())
                if not image.exists():
                    pywikibot.output('[[%s]] doesn\'t exist so I can\'t link to it' % (image.title(),))
                else:
                    newclaim.setTarget(image)
                    pywikibot.output('Adding %s --> %s based on %s' % (newclaim.getID(), newclaim.getTarget(), sourceurl))
                    summary = 'based on usage in list https%s' % (sourceurl,)
                    try:
                        item.addClaim(newclaim, summary=summary)
                    except pywikibot.exceptions.Error:
                        pywikibot.output('Got an error while saving, skipping')

                
def main():
    repo = pywikibot.Site().data_repository()
    configpage = pywikibot.Page(repo, title=u'User:BotMultichillT/heritage images.js')
    (comments, sep, jsondata) = configpage.get().partition(u'[')
    jsondata = u'[' + jsondata
    configjson = json.loads(jsondata)
    for workitem in configjson:
        print (workitem)
    
        query = u"""SELECT ?item WHERE {
  ?item wdt:P1435 wd:%s .
  MINUS { ?item wdt:P18 ?image.} .
}""" % (workitem.get('item'),)
        generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

        monumentsImageBot = MonumentsImageBot(generator,
                                              lang=workitem.get('lang'),
                                              country=workitem.get('country'),
                                              wdproperty=workitem.get('property'),
                                              )
        monumentsImageBot.run()

if __name__ == "__main__":
    main()
