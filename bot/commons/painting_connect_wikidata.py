#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This bot adds the Wikidata id to the Artwork template for files that are in use.

"""
import pywikibot
import requests
import re
import pywikibot.data.sparql

class PaintingsMatchBot:
    """
    A bot to add missing links to Wikidata on Commons
    """
    def __init__(self):
        """
        Build all the lookup tables to work on
        """
        self.commons = pywikibot.Site(u'commons', u'commons')
        self.repo = pywikibot.Site().data_repository()


        self.commonsNoLink = self.getCommonsWithoutWikidataSimple()
        self.wikidataImages = self.getWikidataWithImages()

    def run(self):
        """
        Starts the robot.
        """
        self.addMissingCommonsWikidataLinks()

    def getCommonsWithoutWikidataSimple(self):
        """
        Get the list of images on Commons that don't have a Wikidata identifier.
        """
        result = []
        url = u'http://tools.wmflabs.org/multichill/queries2/commons/paintings_without_wikidata_simple.txt'
        regex = u'^\* \[\[:File:(?P<image>[^\]]+)\]\]$'
        queryPage = requests.get(url)
        for match in re.finditer(regex, queryPage.text, flags=re.M):
            image = match.group("image")
            result.append(image)
        return result

    def getWikidataWithImages(self):
        """
        Query to get all the paintings on Wikidata that have an image.
        """
        result = {}
        query = u"""SELECT ?item ?image WHERE {
        ?item wdt:P31 wd:Q3305213 .
        ?item wdt:P18 ?image .
}"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            item = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            image = pywikibot.FilePage(pywikibot.Site('commons', 'commons'),resultitem.get('image').replace(u'http://commons.wikimedia.org/wiki/Special:FilePath/', u'')).title(underscore=True, with_ns=False)
            result[image] = item
        return result

    def addMissingCommonsWikidataLinks(self):
        '''
        Add missing links from Commons to Wikidata and report for which files it didn't work
        '''
        addedfiles = {}
        missedfiles = {}
        pageTitle = u'Commons:WikiProject sum of all paintings/Unable to add Wikidata link'
        page = pywikibot.Page(self.commons, title=pageTitle)
        text = u'{{/header}}\n'

        missingCommonsLinks = set(self.wikidataImages.keys()) & set(self.commonsNoLink)
        for filename in missingCommonsLinks:
            wikidataitem = self.wikidataImages.get(filename)
            success = self.addMissingCommonsWikidataLink(filename, wikidataitem)
            if success:
                # Add it to the list of files we updated so we have some statistcs
                addedfiles[filename] = wikidataitem
            else:
                missedfiles[filename] = wikidataitem
                text = text + u'* [[:File:%s]] - <nowiki>|</nowiki> wikidata = %s\n' % (filename, wikidataitem)

        text = text + u'\n[[Category:WikiProject sum of all paintings]]\n'

        summary = u'Updating list of images to which to bot was unable to add a link (added %s, missed %s)' % (len(addedfiles), len(missedfiles))
        pywikibot.output(summary)
        page.put(text, summary)

    def addMissingCommonsWikidataLink(self, filename, wikidataitem):
        """
        Try to add a missing link to Commons. Returns True if it worked and False if it failed
        """
        filepage = pywikibot.FilePage(self.commons, title=filename)

        text = filepage.get()
        replaceregex = u'\{\{(Artwork|Painting|Art Photo|Google Art Project|Google Cultural Institute|Walters Art Museum artwork|NARA-image-full)'
        emptywikidataregex = u'(\s*\|\s*wikidata\s*=)\s*\n'
        wikidataregex = u'[wW]ikidata\s*=\s*(Q\d+)\s*'

        pywikibot.output(u'Working on %s' % (filepage.title(),))

        wdmatch = re.search(wikidataregex, text)

        if wdmatch:
            # Template with duplicate template problems might hit this one or when database query is a bit stale
            pywikibot.output(u'Seems to already link to Wikidata %s' % (wdmatch.group(1),))
            return False

        # First try to update an existing field
        newtext = re.sub(emptywikidataregex, u'\\1%s\n' % (wikidataitem,), text, count=1)

        if text==newtext:
            #Ok, that didn't work, just slap it at the top
            newtext = re.sub(replaceregex, u'{{\\1\n|wikidata=%s' % (wikidataitem,), text, count=1, flags=re.I)
            if text==newtext:
                pywikibot.output(u'Unable to add Wikidata link to %s' % (filename,))
                return False

        pywikibot.showDiff(text, newtext)
        summary = u'Adding link to [[:d:%s]] based on usage on that item' % (wikidataitem,)
        pywikibot.output(summary)
        filepage.put(newtext, summary=summary)
        return True


def main():
    paintingsMatchBot = PaintingsMatchBot()
    paintingsMatchBot.run()

if __name__ == "__main__":
    main()
