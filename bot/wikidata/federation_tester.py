#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Check if all the links at:
* https://gerrit.wikimedia.org/r/plugins/gitiles/operations/puppet/+/refs/heads/production/modules/query_service/templates/allowlist.txt.epp
* https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual/SPARQL_Federation_endpoints
all work using a simple query and report the results at:
https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service/Federation_report

"""
import base64
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
        self.site =  pywikibot.Site('mediawiki', 'mediawiki')
        self.repo = self.site.data_repository()
        self.gitlist = self.getGitList()
        self.wikilist = self.getWikiList()

    def getGitList(self):
        result = []
        allowlist_base64 = requests.get('https://gerrit.wikimedia.org/r/plugins/gitiles/operations/puppet/+/refs/heads/production/modules/query_service/templates/allowlist.txt.epp?format=TEXT').text
        allowlist_epp = base64.b64decode(allowlist_base64).decode('utf8')
        for line in allowlist_epp.splitlines():
            # note: the allowlist is in puppet syntax, not quite plain text
            if line.startswith('http') and '<' not in line and '>' not in line:
                # this looks like a real URL line, hope for the best and just add it
                result.append(line)
        return result

    def getWikiList(self):
        result = []
        page = pywikibot.Page(self.site, title='Wikidata Query Service/User Manual/SPARQL Federation endpoints')
        regex = r'\s*\|-\s*\n\s*\|\s*(http.+)'
        matches = re.finditer(regex, page.text)
        for match in matches:
            result.append(match.group(1))
        return result

    def run(self):
        """
        Starts the robot.
        """
        reportpage = pywikibot.Page(self.repo, title='Wikidata:SPARQL query service/Federation report')
        newtext = 'Testing the different SPARQL endpoints. Taking the links from '
        newtext += '[https://gerrit.wikimedia.org/r/plugins/gitiles/operations/puppet/+/refs/heads/production/modules/query_service/templates/allowlist.txt.epp git] and '
        newtext += '[[:mw:Wikidata Query Service/User Manual/SPARQL Federation endpoints|the manual]] and doing a '
        newtext += '[https://query.wikidata.org/#SELECT%20%3Fa%20%3Fb%20%3Fc%20WHERE%20%7B%20%0A%20%20SERVICE%20%3Chttp%3A%2F%2Fdata.bibliotheken.nl%2Fsparql%3E%20%7B%0A%20%20%20%20SELECT%20%3Fa%20%3Fb%20%3Fc%20WHERE%20%7B%20%3Fa%20%3Fb%20%3Fc%20%7D%20LIMIT%201%0A%20%20%7D%0A%7D%20LIMIT%201 very simple federated query] ([https://github.com/multichill/toollabs/blob/master/bot/wikidata/federation_tester.py bot source code]).\n\n'
        newtext += '{| class="wikitable sortable"\n! Link !! Git !! Wiki !! Query works?\n'
        alllist = sorted(set(self.gitlist) | set(self.wikilist))
        for link in alllist:
            newtext += '|-\n'
            newtext += '| %s\n' % (link,)
            if link in self.gitlist:
                newtext += '| OK\n' # FIXME: Add pretty icon
            else:
                newtext += '| Missing\n'
            if link in self.wikilist:
                newtext += '| OK\n' # FIXME: Add pretty icon
            else:
                newtext += '| Missing\n'
            queryworks = self.testSparql(link)
            if queryworks:
                newtext += '| OK\n' # FIXME: Add pretty icon
            else:
                newtext += '| Query failed\n'
        newtext += '|}\n[[Category:Wikidata:SPARQL query service]]'
        print(newtext)
        reportpage.put(newtext, summary='Updating federation report')

    def testSparql(self, link):
        query = """SELECT ?a ?b ?c WHERE { 
  SERVICE <%s> {
    SELECT ?a ?b ?c WHERE { ?a ?b ?c } LIMIT 1
  }
} LIMIT 1""" % (link,)
        sq = pywikibot.data.sparql.SparqlQuery(max_retries=1, retry_wait=1)
        try:
            queryresult = sq.select(query)
            if queryresult:
                return True
            print(queryresult)
        except (pywikibot.exceptions.TimeoutError, pywikibot.exceptions.ServerError):
            return False
        return False


def main(*args):
    federationBot = FederationBot()
    federationBot.run()

if __name__ == "__main__":
    main()
