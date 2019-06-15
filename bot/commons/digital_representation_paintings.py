#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to digital representation of ... to paintings

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
  ?item wdt:P31 wd:Q3305213 .
  ?item wdt:P18 ?image.
} LIMIT 200000"""

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

        mediaid = u'M%s' % (filepage.pageid,)
        if self.mediaInfoExists(mediaid):
            return

        qid = item.title()
        summary = u'this file depicts and is a digital representation of [[:d:%s]] (based on image usage)' % (qid,)
        self.addClaim(mediaid, u'P180', qid, summary)
        self.addClaim(mediaid, u'P6243', qid, summary)

    def addClaim(self, mediaid, pid, qid, summary=''):
        """

        :param mediaid:
        :param pid:
        :param qid:
        :param summary:
        :return:
        """
        pywikibot.output(u'Adding %s->%s to %s. %s' % (pid, qid, mediaid, summary))

        tokenrequest = http.fetch(u'https://commons.wikimedia.org/w/api.php?action=query&meta=tokens&type=csrf&format=json')

        tokendata = json.loads(tokenrequest.text)
        token = tokendata.get(u'query').get(u'tokens').get(u'csrftoken')

        postvalue = {"entity-type":"item","numeric-id": qid.replace(u'Q', u'')}

        postdata = {u'action' : u'wbcreateclaim',
                    u'format' : u'json',
                    u'entity' : mediaid,
                    u'property' : pid,
                    u'snaktype' : u'value',
                    u'value' : json.dumps(postvalue),
                    u'token' : token,
                    u'summary' : summary,
                    u'bot' : True,
                    }
        apipage = http.fetch(u'https://commons.wikimedia.org/w/api.php', method='POST', data=postdata)

    def mediaInfoExists(self, mediaid):
        """
        Check if the media info exists or not
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :return: True if it exists, otherwise False
        """
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
