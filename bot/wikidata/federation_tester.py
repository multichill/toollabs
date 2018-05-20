#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Check if all the links at:
* https://raw.githubusercontent.com/wikimedia/wikidata-query-deploy/master/whitelist.txt
* https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual/SPARQL_Federation_endpoints
all work using a simple query and report the results at:
https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service/Federation_report

"""
import pywikibot
import pywikibot.data.sparql
import requests
import re

class FederationBot:
    """
    Simple federation reporting bot
    """
    def __init__(self):
        """

        """
        self.site =  pywikibot.Site(u'mediawiki', u'mediawiki')
        self.repo = self.site.data_repository()
        self.gitlist = self.getGitList()
        self.wikilist = self.getWikiList()

    def getGitList(self):
        result = []
        page = requests.get(u'https://raw.githubusercontent.com/wikimedia/wikidata-query-deploy/master/whitelist.txt')
        for line in page.text.splitlines():
            result.append(line)
        return result

    def getWikiList(self):
        result = []
        page = pywikibot.Page(self.site, title=u'Wikidata Query Service/User Manual/SPARQL Federation endpoints')
        regex = u'\s*\|-\s*\n\s*\|\s*(http.+)'
        matches = re.finditer(regex, page.text)
        for match in matches:
            result.append(match.group(1))
        return result

    def run(self):
        """
        Starts the robot.
        """
        reportpage = pywikibot.Page(self.repo, title=u'Wikidata:SPARQL query service/Federation report')
        newtext = u'Testing the different SPARQL endpoints. Taking the links from '
        newtext += u'[https://raw.githubusercontent.com/wikimedia/wikidata-query-deploy/master/whitelist.txt git] and '
        newtext += u'[[:mw:Wikidata Query Service/User Manual/SPARQL Federation endpoints|the manual]] and doing a '
        newtext += u'[https://query.wikidata.org/#SELECT%20%3Fa%20%3Fb%20%3Fc%20WHERE%20%7B%20%0A%20%20SERVICE%20%3Chttp%3A%2F%2Fdata.bibliotheken.nl%2Fsparql%3E%20%7B%0A%20%20%20%20SELECT%20%3Fa%20%3Fb%20%3Fc%20WHERE%20%7B%20%3Fa%20%3Fb%20%3Fc%20%7D%20LIMIT%201%0A%20%20%7D%0A%7D%20LIMIT%201 very simple federated query]\n\n'
        newtext += u'{| class="wikitable sortable"\n! Link !! Git !! Wiki !! Query works?\n'
        alllist = sorted(set(self.gitlist) | set(self.wikilist))
        for link in alllist:
            newtext += u'|-\n'
            newtext += u'| %s\n' % (link,)
            if link in self.gitlist:
                newtext += u'| OK\n' # FIXME: Add pretty icon
            else:
                newtext += u'| Missing\n'
            if link in self.wikilist:
                newtext += u'| OK\n' # FIXME: Add pretty icon
            else:
                newtext += u'| Missing\n'
            queryworks = self.testSparql(link)
            if queryworks:
                newtext += u'| OK\n' # FIXME: Add pretty icon
            else:
                newtext += u'| Query failed\n'
        newtext += u'|}\n[[Category:Wikidata:SPARQL query service]]'
        print newtext
        reportpage.put(newtext, summary=u'Updating federation report')

    def testSparql(self, link):
        query = u"""SELECT ?a ?b ?c WHERE { 
  SERVICE <%s> {
    SELECT ?a ?b ?c WHERE { ?a ?b ?c } LIMIT 1
  }
} LIMIT 1""" % (link,)
        sq = pywikibot.data.sparql.SparqlQuery(max_retries=1, retry_wait=1)
        try:
            queryresult = sq.select(query)
            if queryresult:
                return True
            print queryresult
            #for resultitem in queryresult:
            #    qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            #    result[resultitem.get('id')] = qid
        except pywikibot.exceptions.TimeoutError:
            return False
        return False


def main(*args):
    federationBot = FederationBot()
    federationBot.run()

if __name__ == "__main__":
    main()
