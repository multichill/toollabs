#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to depicts statements for monuments. Start with Rijksmonumenten and maybe later more (3M images probably).

"""

import pywikibot
import re
import pywikibot.data.sparql
import datetime
from pywikibot.comms import http
import json
from pywikibot import pagegenerators

class DepictsMonumentsBot:
    """
    Bot to add depicts statements on Commons
    """
    def __init__(self):
        """
        Grab generator based on SPARQL to work on.

        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.repo = self.site.data_repository()

        monumentcat = pywikibot.Category(self.site, title=u'Category:Rijksmonumenten_with_known_IDs')

        self.generator = pagegenerators.PreloadingGenerator(pagegenerators.CategorizedPageGenerator(monumentcat, namespaces=6))
        self.monuments = self.getMonumentsOnWikidata()

    def getMonumentsOnWikidata(self):
        """
        Get the monuments currently on Wikidata
        :return:
        """
        result = {}
        query = u'''SELECT ?item ?id WHERE {
  ?item wdt:P1435 wd:Q916333 .
  ?item wdt:P359 ?id .
  } ORDER BY xsd:integer(?id)'''
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[resultitem.get('id')] = qid
        return result

    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            self.handleMonument(filepage)

    def handleMonument(self, filepage):
        """

        :param item:
        :return:
        """
        if not filepage.exists():
            return

        regex = u'\{\{[rR]ijksmonument\|(\d+)\}\}'
        matches = list(re.finditer(regex, filepage.text))
        monumentid = None
        qid = None

        # Only work if you find exactly one template
        if matches and len(matches)==1:
            monumentid = matches[0].group(1)
            if monumentid in self.monuments:
                qid = self.monuments.get(monumentid)

        if not monumentid or not qid:
            return

        mediaid = u'M%s' % (filepage.pageid,)
        if self.mediaInfoExists(mediaid):
            return

        summary = u'based on [[Template:Rijksmonument]] with id %s, which is the same id as [[:d:Property:P359| Rijksmonument ID (P359)]] on [[:d:%s]]' % (monumentid, qid,)

        self.addClaim(mediaid, u'P180', qid, summary)

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
                    u'summary' : summary
                    }
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
    depictsMonumentsBot = DepictsMonumentsBot()
    depictsMonumentsBot.run()

if __name__ == "__main__":
    main()
