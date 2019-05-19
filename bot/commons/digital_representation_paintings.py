#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to digital representation of ... to paintings

This is just a proof of concept to show that this is possible. When we're actually going to import,
I should probably optimize it.

TODO: Fix authentication, currently editing as IP(v6)

"""

import pywikibot
import re
import pywikibot.data.sparql
import datetime
import requests
import json
from pywikibot import pagegenerators

class DigitalRepresentationBot:
    """
    Bot to add digital representation of statements on Commons
    """
    def __init__(self):
        """
        Grab generator based on SPARQL to work on.

        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.repo = self.site.data_repository()

        query = u"""SELECT DISTINCT ?item ?image WHERE {
  ?item p:P195/ps:P195 wd:Q303139 .
  ?item wdt:P31 wd:Q3305213 .   
  ?item wdt:P18 ?image
  } 
 LIMIT 4000"""

        self.generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=self.repo))

    def run(self):
        """
        Run on the items
        """
        for item in self.generator:
            self.handlePaintingItem(item)

    def handlePaintingItem(self, item):
        """

        :param item:
        :return:
        """
        data = item.get()
        claims = data.get('claims')

        if u'P18' not in claims:
            return

        filepage = claims.get('P18')[0].getTarget()

        if not filepage.exists():
            return

        if u'{{Licensed-PD-Art|PD-old-auto-1923|' not in filepage.text:
            return

        mediaid = u'M%s' % (filepage.pageid,)
        if self.mediaInfoExists(mediaid):
            return

        self.addDigitalRepresentation(mediaid, item.title())

    def addDigitalRepresentation(self, mediaid, qid):
        """

        :param mediaid:
        :param qid:
        :return:
        """
        pywikibot.output(u'Adding %s to %s' % (qid, mediaid))

        # I hate tokens
        #tokenrequest = self.site._simple_request(action='query', meta='tokens', type='csrf')
        tokenrequest = requests.get(u'https://commons.wikimedia.org/w/api.php?action=query&meta=tokens&type=csrf&format=json')
        #tokendata = tokenrequest.submit()
        tokendata = tokenrequest.json()
        token = tokendata.get(u'query').get(u'tokens').get(u'csrftoken')

        # https://commons.wikimedia.org/w/api.php?action=wbcreateclaim&entity=Q42&property=P9003&snaktype=value&value=%7B%22entity-type%22:%22item%22,%22numeric-id%22:1%7D

        postvalue = {"entity-type":"item","numeric-id": qid.replace(u'Q', u'')}
        summary = u'Adding [[:d:Property:P6243]] based on usage on [[:d:%s]]' % (qid,)

        postdata = {u'action' : u'wbcreateclaim',
                    u'format' : u'json',
                    u'entity' : mediaid,
                    u'property' : u'P6243',
                    u'snaktype' : u'value',
                    u'value' : json.dumps(postvalue),
                    u'token' : token,
                    u'summary' : summary
                    }

        userinfo = tokendata.get(u'query').get(u'tokens').get(u'userinfo')
        #print tokendata

        print postdata

        #apipage = requests.post(u'https://commons.wikimedia.org/w/api.php?action=wbeditentity&format=json&data=, data=postdata)
        apipage = requests.post(u'https://commons.wikimedia.org/w/api.php', data=postdata)
        print apipage.text

    def mediaInfoExists(self, mediaid):
        """
        Check if the media info exists or not
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :return: True if it exists, otherwise False
        """
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M52611909
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M10038
        request = self.site._simple_request(action='wbgetentities',ids=mediaid)
        data = request.submit()
        if data.get(u'entities').get(mediaid).get(u'pageid'):
            return True
        return False


def main():
    digitalRepresentationBot = DigitalRepresentationBot()
    digitalRepresentationBot.run()

if __name__ == "__main__":
    main()
