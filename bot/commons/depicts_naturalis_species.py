#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to depicts statements for species from the Naturalis Leiden collection.

https://commons.wikimedia.org/wiki/Category:Media_donated_by_Naturalis_Biodiversity_Center

"""

import pywikibot
import re
import pywikibot.data.sparql
import datetime
from pywikibot.comms import http
import json
from pywikibot import pagegenerators

class DepictsNaturalisSpeciesBot:
    """
    Bot to add depicts statements on Commons
    """
    def __init__(self):
        """
        Grab generator based on SPARQL to work on.

        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.repo = self.site.data_repository()

        self.search = u'incategory:"Media donated by Naturalis Biodiversity Center" -haswbstatement:P180'

        self.generator = pagegenerators.PreloadingGenerator(pagegenerators.SearchPageGenerator(self.search, namespaces=6, site=self.site))
        self.speciescategories = self.speciesCategoriesOnWikidata()

    def speciesCategoriesOnWikidata(self):
        """"
        Get a list of species names that have categories on Commons and a Wikidata item
        :return: Dict
        """
        result = {}
        sq = pywikibot.data.sparql.SparqlQuery()
        query = u"""SELECT ?item ?commonscat WHERE {
  ?item wdt:P105 wd:Q7432 ; 
        wdt:P31 wd:Q16521 ;
        wdt:P373 ?commonscat .
  } LIMIT 125000"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[resultitem.get('commonscat')] = qid
        return result


    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            self.handleTaxon(filepage)

    def handleTaxon(self, filepage):
        """
        Handle a single taxon image.

        :param filepage: The page of the file to work on.
        :return: Nothing, edit in place
        """
        pywikibot.output(u'Working on %s' % (filepage.title(),))
        if not filepage.exists():
            return

        qid = None
        taxonName = None

        toremove = [u' (museum specimens)', u' (taxidermied)']

        for category in filepage.categories():
            categoryname = category.title(with_ns=False)
            for remove in toremove:
                if categoryname.endswith(categoryname):
                    categoryname = categoryname.replace(remove, u'')
            print (categoryname)
            if categoryname in self.speciescategories:
                qid = self.speciescategories.get(categoryname)
                taxonName = categoryname
                break

        if not qid:
            return

        pywikibot.output(u'Found %s based on %s' % (qid, taxonName,))

        mediaid = u'M%s' % (filepage.pageid,)
        if self.mediaInfoHasStatement(mediaid, u'P180'):
            return

        summary = u'based on Naturalis Leiden image in [[Category:%s]]' % (taxonName, )

        self.addClaim(mediaid, u'P180', qid, summary)

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

    def mediaInfoHasStatement(self, mediaid, property):
        """
        Check if the media info exists or not
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :param property: The property ID to check for (like P180)
        :return: True if it exists, otherwise False
        """
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M72643194
        request = self.site._simple_request(action='wbgetentities',ids=mediaid)
        data = request.submit()
        # No structured data at all is no pageid
        if not data.get(u'entities').get(mediaid).get(u'pageid'):
            return False
        # Has structured data, but the list of statements is empty
        if not data.get(u'entities').get(mediaid).get(u'statements'):
            return False
        if property in data.get(u'entities').get(mediaid).get(u'statements'):
            return True
        return False


def main():
    depictsNaturalisSpeciesBot = DepictsNaturalisSpeciesBot()
    depictsNaturalisSpeciesBot.run()

if __name__ == "__main__":
    main()
