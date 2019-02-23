#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
I'm tired of all the damn links that keep breaking on paintings and are not in the Wayback Machine
Let's add a ton of links to https://archive.org/web/
The bot will take a SPARQL query that will return a bunch of links.
Bot will run over these links and if needed, add them to the Wayback machine.
This is part of https://www.wikidata.org/wiki/Wikidata:WikiProject_sum_of_all_paintings/Link_rot
"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import requests
import re
import datetime
import time
import urllib

class WaybackPaintingsBot:
    """
    A bot to enrich humans on Wikidata
    """
    def __init__(self, query):
        """
        Arguments:
            * query    - A valid SPARQL query with url's in the ?url field

        """
        self.generator = self.getUrlGenerator(query)
        self.repo = pywikibot.Site().data_repository()


    def getUrlGenerator(self, query):
        '''
        :param query: A valid SPARQL query with ?url in the result
        :return: Generator with url's to work on
        '''
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            yield resultitem.get('url')
            #qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            #result[int(resultitem.get('id'))] = qid
            #return result


    def run(self):
        """
        Starts the robot.
        """
        for url in self.generator:
            self.processUrl(url)

    def processUrl(self, url):
        """
        Process a single url

        :param url: Url to possibly archive
        :return: Nothing
        """
        try:
            print (url)
            url = self.resolveRedirect(url)
            print (url)
            available = self.getWaybackAvailability(url)
            print (available)
            if not available:
                self.submitWayback(url)
        except requests.exceptions.RequestException:
            print (u'Ran into an exception')
            pass

    def resolveRedirect(self, url):
        """
        Try to resolve redirect, otherwise just return the url
        :param url:
        :return:
        """
        # FIXME: We want html, not rdf
        page = requests.head(url, verify=False)
        if page.status_code in [301, 302]:
            page = requests.get(url, verify=False)
            if page.url!=url:
                return page.url
        # Do something with error status codes
        return url

    def getWaybackAvailability(self, url):
        """
        Check at https://archive.org/help/wayback_api.php if an url is already available or not

        TODO: Might have to do something with resolving redirects

        :param url: The url to check
        :return: Something if availab,e False if not available,
        """
        waybackUrl = u'http://archive.org/wayback/available?url=%s' % (urllib.parse.quote(url),)
        print (waybackUrl)
        waybackPage = requests.get(waybackUrl)
        waybackPageJson = waybackPage.json()

        if waybackPageJson.get('archived_snapshots'):
            return True
        return False

    def submitWayback(self, url):
        """
        Submit an url to the Wayback Machine for indexing

        :param url: The url to index
        :return:
        """
        waybackUrl = u'https://web.archive.org/save/%s' % (url,)
        print (waybackUrl)
        waybackPage = requests.get(waybackUrl)
        return


def main(*args):
    """
    Main function. Grab a query and pass it to the bot to work on
    """
    queryname = u''
    query = u''
    queryvariable = u''
    for arg in pywikibot.handle_args(args):
        if arg=='-allurl':
            queryname = u'allurl'
        elif arg=='-allid':
            queryname = u'allid'
        elif arg=='-newesturl':
            queryname = u'newesturl'
        elif arg=='-newestid':
            queryname = u'newestid'
        elif arg=='-testquery':
            queryname = u'testquery'
        elif arg=='-periodurl':
            queryname = u'periodurl'
        elif arg.startswith(u'-artistid:'):
            queryname = u'artist'
            queryvariable = arg.replace(u'-artistid:', u'')
        elif arg.startswith(u'-collectionid:'):
            queryname = u'collection'
            queryvariable = arg.replace(u'-collectionid:', u'')

    if queryname==u'allurl':
        query = u"""SELECT DISTINCT ?url WHERE {
  ?item wdt:P31 wd:Q3305213 .
  ?item wdt:P973 ?url .
  }"""
    elif queryname==u'allid':
        query = u"""SELECT DISTINCT ?formatter ?identifier ?url WHERE {
  ?item wdt:P31 wd:Q3305213 .
  ?property wikibase:propertyType wikibase:ExternalId .
  ?property wdt:P31 wd:Q44847669 .
  ?property wdt:P1630 ?formatter .
  ?property wikibase:directClaim ?propertyclaim .
  ?item ?propertyclaim ?identifier .
  BIND(IRI(REPLACE(?identifier, '^(.+)$', ?formatter)) AS ?url).
}"""
    elif queryname==u'newesturl':
        query = u"""SELECT DISTINCT ?url WHERE {
  ?item wdt:P31 wd:Q3305213.
  ?item schema:dateModified ?modified.
  BIND((NOW()) - ?modified AS ?distance)
  ?item wdt:P973 ?url.
  FILTER(?distance < 2)
}
ORDER BY DESC(?modified)
LIMIT 15000"""
    elif queryname==u'newestid':
        query = u"""SELECT DISTINCT ?url WHERE {
  ?item wdt:P31 wd:Q3305213.
  ?item schema:dateModified ?modified.
  BIND((NOW()) - ?modified AS ?distance)
  ?property wikibase:propertyType wikibase:ExternalId.
  ?property wdt:P31 wd:Q44847669.
  ?property wdt:P1630 ?formatter.
  ?property wikibase:directClaim ?propertyclaim.
  ?item ?propertyclaim ?identifier.
  BIND(IRI(REPLACE(?identifier, "^(.+)$", ?formatter)) AS ?url)
  FILTER(?distance < 2)
}
ORDER BY DESC(?modified)
LIMIT 15000"""
    elif queryname==u'testquery':
        query = u"""SELECT DISTINCT ?url WHERE {
  ?item wdt:P31 wd:Q3305213 .
  ?item wdt:P973 ?url .
  } LIMIT 100"""
    elif queryname==u'periodurl':
        query = u"""SELECT DISTINCT ?item ?url WHERE {
  ?item wdt:P31 wd:Q3305213.
  ?item schema:dateModified ?modified.
  FILTER(YEAR(?modified)=2015) . #&&MONTH(?modified)=12) .
  ?item wdt:P973 ?url.
}
ORDER BY ASC(?modified)
LIMIT 200000"""

    elif queryname==u'artist':
        query = u"""SELECT DISTINCT ?url WHERE {
  ?item wdt:P31 wd:Q3305213 .
  ?item p:P170/ps:P170 wd:%s .
  ?item wdt:P973 ?url .
  }""" % (queryvariable,)

    elif queryname==u'collection':
        query = u"""SELECT DISTINCT ?url WHERE {
  ?item wdt:P31 wd:Q3305213 .
  ?item p:P195/ps:P195 wd:%s .
  ?item wdt:P973 ?url .
  }""" % (queryvariable,)

    else:
        pywikibot.output(u'No valid query option found. Please use -query:<option>')

    if query:
        waybackPaintingsBot = WaybackPaintingsBot(query)
        waybackPaintingsBot.run()

if __name__ == "__main__":
    main()
