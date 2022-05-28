#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to fix some of the Rijksmonument templates on Commons. Fixing two things:
* Replace old ID with new ID
* Replace Rijksmonument template with Rijksmonumentcomplex template

"""

import pywikibot
import re
import pywikibot.data.sparql
import time
import json
import random
from pywikibot import pagegenerators

class FixRijksmonumentenBot:
    """
    Bot to add depicts statements on Commons
    """
    def __init__(self, gen):
        """
        Grab generator based on search to work on.

        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()

        self.rijksmonumenten = self.getMonumentsOnWikidata('Q916333', 'P359')
        self.rijksmonumentcomplexen = self.getMonumentsOnWikidata('Q13423591', 'P7135')
        self.oldrijksmonumenten = self.getOldMonumentsOnWikidata()

        self.lostrijksmonumenten = {}

        self.generator = gen

    def getMonumentsOnWikidata(self, designation, property):
        """
        Get the monuments currently on Wikidata. Keep the id as a string.
        :return:
        """
        result = {}
        query = u'''SELECT ?item ?id WHERE {
?item wdt:P1435 wd:%s .
?item wdt:%s ?id .
} ORDER BY ?id''' % (designation, property, )
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[resultitem.get('id')] = qid
        return result

    def getOldMonumentsOnWikidata(self):
        """
        Get the old and new id's for Rijksmonumenten from Wikidata
        :return:
        """
        result = {}
        query = u'''SELECT ?item ?newid ?oldid {
  ?item wdt:P1435 wd:Q916333 ;
        p:P359 ?newstatement .
  ?newstatement wikibase:rank wikibase:PreferredRank ;
                ps:P359 ?newid .
  ?item p:P359 ?oldstatement .  
  ?oldstatement wikibase:rank wikibase:DeprecatedRank ;
                ps:P359 ?oldid ;
                pq:P2241 wd:Q21441764 .
  }'''
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            data = {}
            data['qid'] = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            data['oldid'] = resultitem.get('id')
            data['newid'] = resultitem.get('newid')
            result[resultitem.get('oldid')] = data
        return result

    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            if not filepage.exists():
                continue
            self.handleMonument(filepage)

        for monumentid in sorted(self.lostrijksmonumenten, key=self.lostrijksmonumenten.get, reverse=True)[:150]:
            pywikibot.output('* %s - %s' % (monumentid, self.lostrijksmonumenten.get(monumentid), ))

    def handleMonument(self, filepage):
        """
        Handle a single monument. Try to extract the template, look up the id and add the Q if no mediainfo is present.

        :param filepage: The page of the file to work on.
        :return: Nothing, edit in place
        """
        pywikibot.output(u'Working on %s' % (filepage.title(),))
        if not filepage.exists():
            return

        templateregex = '\{\{\s*[rR]ijksmonument\s*\|(1=)?\s*(?P<id>\d+)\s*\}\}'

        matches = list(re.finditer(templateregex, filepage.text))

        if not matches:
            pywikibot.output(u'No matches found on %s, skipping' % (filepage.title(),))
            return

        #summarytoadd = []
        #depictstoadd = []
        #locationstoadd = []

        newtext = filepage.text

        # First collect the matches to add
        for match in matches:
            monumentid = match.group(u'id')
            if monumentid in self.rijksmonumenten:
                # This one has a valid id
                qid = self.rijksmonumenten.get(monumentid)
                pywikibot.output('Found valid id %s on %s. Not replacing' % (monumentid, qid,))
                continue
            elif monumentid in self.rijksmonumentcomplexen:
                # Get Wikidata
                qid = self.rijksmonumentcomplexen.get(monumentid)
                oldstring = '{{Rijksmonument|%s}}' % (monumentid,)
                newstring = '{{Rijksmonumentcomplex|%s}}' % (monumentid,)
                summary = 'Found rijksmonumentcomplex id %s on [[d:Special:EntityPage/%s]]. Replacing template' % (monumentid, qid )
                pywikibot.output(summary)
                newtext = newtext.replace(oldstring, newstring)
                if filepage.text!=newtext:
                    pywikibot.showDiff(filepage.text, newtext)
                    filepage.put(newtext, summary=summary)
                return
            elif monumentid in self.oldrijksmonumenten:
                qid = self.oldrijksmonumenten.get(monumentid).get('qid')
                newid = self.oldrijksmonumenten.get(monumentid).get('newid')
                oldstring = '{{Rijksmonument|%s}}' % (monumentid,)
                newstring = '{{Rijksmonument|%s}}' % (newid,)
                summary = 'Found old id %s and new id %s on [[d:Special:EntityPage/%s]]. Replacing id' % (monumentid, newid, qid )
                pywikibot.output(summary)
                newtext = newtext.replace(oldstring, newstring)
                if filepage.text!=newtext:
                    pywikibot.showDiff(filepage.text, newtext)
                    filepage.put(newtext, summary=summary)
            else:
                pywikibot.output('The id %s wasn\'t found anywhere. Skipping it' % (monumentid,))
                if monumentid not in self.lostrijksmonumenten:
                    self.lostrijksmonumenten[monumentid] = 0
                self.lostrijksmonumenten[monumentid] +=1
                continue


def main(*args):
    gen = None
    genFactory = pagegenerators.GeneratorFactory()
    for arg in pywikibot.handle_args(args):
        if genFactory.handleArg(arg):
            continue

    gen = genFactory.getCombinedGenerator(gen, preload=True)
    if gen:
        fixRijksmonumentenBot = FixRijksmonumentenBot(gen)
        fixRijksmonumentenBot.run()

if __name__ == "__main__":
    main()
