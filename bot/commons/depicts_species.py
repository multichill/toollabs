#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to depicts statements for species.

This is just a proof of concept to show that this is possible. When we're actually going to import,
I should probably optimize it.
"""

import pywikibot
import re
import pywikibot.data.sparql
import datetime
from pywikibot.comms import http
import json
from pywikibot import pagegenerators

class DepictsSpeciesBot:
    """
    Bot to add depicts statements on Commons
    """
    def __init__(self):
        """
        Grab generator based on SPARQL to work on.

        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.repo = self.site.data_repository()

        query = u"""SELECT ?item ?image WHERE {
  ?item wdt:P105 wd:Q7432 .
  ?item wdt:P18 ?image .
  ?item wdt:P31 wd:Q16521 .
  } LIMIT 200000"""

        self.generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=self.repo))

    def run(self):
        """
        Run on the items
        """
        for item in self.generator:
            self.handleTaxonItem(item)

    def handleTaxonItem(self, item):
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

        mediaid = u'M%s' % (filepage.pageid,)
        if self.mediaInfoExists(mediaid):
            return

        self.addDepicts(mediaid, item.title())

    def addDepicts(self, mediaid, qid):
        """

        :param mediaid:
        :param qid:
        :return:
        """
        pywikibot.output(u'Adding %s to %s' % (qid, mediaid))

        # I hate tokens
        tokenrequest = http.fetch(u'https://commons.wikimedia.org/w/api.php?action=query&meta=tokens&type=csrf&format=json')

        tokendata = json.loads(tokenrequest.text)
        token = tokendata.get(u'query').get(u'tokens').get(u'csrftoken')

        # https://commons.wikimedia.org/w/api.php?action=wbcreateclaim&entity=Q42&property=P9003&snaktype=value&value=%7B%22entity-type%22:%22item%22,%22numeric-id%22:1%7D

        postvalue = {"entity-type":"item","numeric-id": qid.replace(u'Q', u'')}
        summary = u'Adding [[:d:Property:P180]] based on usage on [[:d:%s]]' % (qid,)

        postdata = {u'action' : u'wbcreateclaim',
                    u'format' : u'json',
                    u'entity' : mediaid,
                    u'property' : u'P180',
                    u'snaktype' : u'value',
                    u'value' : json.dumps(postvalue),
                    u'token' : token,
                    u'summary' : summary,
                    u'bot' : True,
                    }

        pywikibot.output(summary)
        apipage = http.fetch(u'https://commons.wikimedia.org/w/api.php', method='POST', data=postdata)

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
    depictsSpeciesBot = DepictsSpeciesBot()
    depictsSpeciesBot.run()

if __name__ == "__main__":
    main()
