#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to depicts statements for monuments. Start with Rijksmonumenten and maybe later more (3M images probably).

Should be switched to a more general Pywikibot implementation.

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
        Grab generator based on search to work on.

        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.repo = self.site.data_repository()

        # This was everything in the category. Search is only the ones we still need to work on
        # monumentcat = pywikibot.Category(self.site, title=u'Category:Rijksmonumenten_with_known_IDs')
        # self.generator = pagegenerators.PreloadingGenerator(pagegenerators.CategorizedPageGenerator(monumentcat, namespaces=6))

        query = u'incategory:Rijksmonumenten_with_known_IDs -haswbstatement:P180'
        self.generator = pagegenerators.PreloadingGenerator(pagegenerators.SearchPageGenerator(query, namespaces=6, site=self.site))

        self.monuments = self.getMonumentsOnWikidata()

    def getMonumentsOnWikidata(self):
        """
        Get the monuments currently on Wikidata. Keep the id as a string.
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
        Handle a single monument. Try to extract the template, look up the id and add the Q if no mediawinfo is present.

        :param filepage: The page of the file to work on.
        :return: Nothing, edit in place
        """
        pywikibot.output(u'Working on %s' % (filepage.title(),))
        if not filepage.exists():
            return

        regex = u'\{\{[rR]ijksmonument\|(1=)?\s*(?P<id>\d+)\}\}'
        matches = list(re.finditer(regex, filepage.text))

        if not matches:
            pywikibot.output(u'No matches found on %s, skipping' % (filepage.title(),))
            return

        toadd = []

        # First collect the matches to add
        for match in matches:
            monumentid = match.group(u'id')
            if monumentid not in self.monuments:
                pywikibot.output(u'Found unknown monument id %s on %s, skipping' % (monumentid, filepage.title(),))
                return
            qid = self.monuments.get(monumentid)
            toadd.append((monumentid, qid))

        mediaid = u'M%s' % (filepage.pageid,)
        if self.mediaInfoExists(mediaid):
            return
        i = 1
        for (monumentid, qid) in toadd:
            if len(toadd)==1:
                summary = u'based on [[Template:Rijksmonument]] with id %s, which is the same id as [[:d:Property:P359|Rijksmonument ID (P359)]] on [[:d:%s]]' % (monumentid, qid,)
            else:
                summary = u'based on [[Template:Rijksmonument]] with id %s, which is the same id as [[:d:Property:P359|Rijksmonument ID (P359)]] on [[:d:%s]] (%s/%s)' % (monumentid, qid, i, len(toadd))
            self.addClaim(mediaid, u'P180', qid, summary)
            i +=1

    def addClaim(self, mediaid, pid, qid, summary=''):
        """
        Add a claim to a mediaid

        :param mediaid: The mediaid to add it to
        :param pid: The property P id (including the P)
        :param qid: The item Q id (including the Q)
        :param summary: The summary to add in the edit
        :return: Nothing, edit in place
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
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M72643194
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
