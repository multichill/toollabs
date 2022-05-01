#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import  National Thesaurus for Author Names ID (P1006) statements from viaf.

See https://www.wikidata.org/wiki/Property:P1006

Viaf contains some broken links so check that the entry at http://data.bibliotheken.nl/ actually exists
and links back to the same viaf item.

"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import requests
import datetime
import re

class ViafImportBot:
    """
    Bot to import NTA links from VIAF
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields wikidata item objects.
        """
        self.repo = pywikibot.Site().data_repository()
        self.generator = pagegenerators.PreloadingEntityGenerator(generator)
        self.viafitem = pywikibot.ItemPage(self.repo, u'Q54919')
    
    def run (self):
        '''
        Work on all items
        '''
        validlinks = 0
        brokenlinks = 0

        for item in self.generator:
            if not item.exists():
                continue

            if item.isRedirectPage():
                item = item.getRedirectTarget()

            data = item.get()
            claims = data.get('claims')

            if not u'P214' in claims:
                pywikibot.output(u'No viaf found, skipping')
                continue

            if u'P1006' in claims:
                # Already has National Thesaurus for Author Names ID, great!
                continue

            viafid = claims.get(u'P214')[0].getTarget()

            if not viafid:
                pywikibot.output(u'Viaf is set to novalue, skipping')
                continue
            
            viafurl = u'http://viaf.org/viaf/%s' % (viafid,)
            viafurljson = u'%s/justlinks.json' % (viafurl,)
            try:
                viafPage = requests.get(viafurljson)
            except requests.HTTPError as e:
                pywikibot.output('On %s the VIAF link %s returned this HTTPError %s: %s' % (item.title(), viafurljson, e.errno, e.strerror))
            except requests.exceptions.ConnectionError as e:
                pywikibot.output('On %s the VIAF link %s returned this HTTPError %s: %s' % (item.title(), viafurljson, e.errno, e.strerror))

            try:
                viafPageDataDataObject = viafPage.json()
            except ValueError:
                pywikibot.output('On %s the VIAF link %s returned this junk:\n %s' % (item.title(), viafurljson, viafPage.text))
                continue

            if not isinstance(viafPageDataDataObject, dict):
                pywikibot.output('On %s the VIAF link %s did not return a dict:\n %s' % (item.title(), viafurljson, viafPage.text))
                continue

            if viafPageDataDataObject.get(u'NTA'):
                ntaid = viafPageDataDataObject.get(u'NTA')[0]

                ntaurl = u'http://data.bibliotheken.nl/id/thes/p%s' % (ntaid,)
                ntapage = requests.get(ntaurl)
                if not ntapage.status_code==200:
                    pywikibot.output(u'Viaf %s points to broken NTA url: %s' % (viafurljson, ntaurl,))
                    brokenlinks = brokenlinks + 1
                    continue

                validviaffound = False

                if viafurl in ntapage.text:
                    validviaffound = True
                    pywikibot.output('Adding National Thesaurus for Author Names ID %s claim to %s (based on bidirectional viaf<->nta links)' % (ntaid, item.title(),) )
                    summary = u'based on VIAF %s (with bidirectional viaf<->nta links)' % (viafid,)
                else:
                    pywikibot.output(u'No backlink found on %s to viaf %s. Will try to find another link and resolve redirect' % (ntaurl, viafurl, ))
                    ntajsonpage = requests.get(ntaurl + u'.json')
                    ntajson = ntajsonpage.json()

                    ntaviafurl = None
                    if ntajson.get(u'@graph')[1].get('sameAs'):
                        for sameAs in ntajson.get(u'@graph')[1].get('sameAs'):
                            if sameAs.startswith(u'http://viaf.org/viaf/'):
                                ntaviafurl = sameAs
                                break
                    if ntaviafurl:
                        pywikibot.output(u'The NTA item has a link to the viaf url %s' % (ntaviafurl,))
                        ntaviafpage = requests.get(ntaviafurl)
                        if ntaviafpage.url==u'https://viaf.org/viaf/%s/' % (viafid,):
                            print (ntaviafpage.url)
                            validviaffound = True
                            pywikibot.output('Adding National Thesaurus for Author Names ID %s claim to %s (based on bidirectional viaf<->nta links, with a NTA redirect to viaf)' % (ntaid, item.title(),) )
                            summary = u'based on VIAF %s (with bidirectional viaf<->nta links (NTA links to redirected viaf %s)' % (viafid, ntaviafurl)

                if not validviaffound:
                    continue

                newclaim = pywikibot.Claim(self.repo, u'P1006')
                newclaim.setTarget(ntaid)

                item.addClaim(newclaim, summary=summary)

                pywikibot.output('Adding new reference claim to %s' % item)

                refurl = pywikibot.Claim(self.repo, u'P214')
                refurl.setTarget(viafid)

                refsource = pywikibot.Claim(self.repo, u'P248')
                refsource.setTarget(self.viafitem)

                refdate = pywikibot.Claim(self.repo, u'P813')
                today = datetime.datetime.today()
                date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
                refdate.setTarget(date)
                
                newclaim.addSources([refurl, refsource, refdate])
                validlinks = validlinks + 1

        pywikibot.output(u'I found %s valid links and %s broken links' % (validlinks, brokenlinks,))

def getCurrentNTA():
    '''
    Build a cache so we can easility skip Qid's
    '''
    result = {}

    query = u'SELECT ?item ?id { ?item wdt:P1006 ?id }'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        if resultitem.get('artukid'):
            result[qid] = resultitem.get('id')
    pywikibot.output(u'The query "%s" returned %s items with a NTA links' % (query, len(result),))
    return result

def ntaBacklinksGenerator():
    """
    Do a SPARQL query at the NTA to get backlinks to Wikidata
    :return:
    """
    basequery = u"""SELECT ?item ?person {
      SERVICE <http://data.bibliotheken.nl/sparql> {
  SELECT ?item ?person WHERE {
  ?person rdf:type <http://schema.org/Person> .
 ?person owl:sameAs ?item .
 FILTER REGEX(STR(?item), "http://www.wikidata.org/entity/") .
} OFFSET %s
LIMIT %s
      }
  # The URI (wdtn) links don't seem to be fully populated
  #MINUS { ?item wdtn:P1006 ?person } .
  MINUS { ?item wdt:P1006 [] } .
  #MINUS { ?item owl:sameAs ?item2 . ?item2 wdtn:P1006 ?person }
  MINUS { ?item owl:sameAs ?item2 . ?item2 wdt:P1006 [] }
}"""
    repo = pywikibot.Site().data_repository()
    step = 10000
    limit = 122000
    for i in range(0, limit, step):
        query = basequery % (i, limit)
        gen = pagegenerators.WikidataSPARQLPageGenerator(query, site=repo)
        for item in gen:
            # Add filtering
            yield item

def viafDumpGenerator(filename=u'../Downloads/viaf-20180807-links.txt'):
    """
    Use a viaf dump to find Wikidata items to check.
    It will filter out the Wikidata items that already have a link
    :return:
    """
    repo = pywikibot.Site().data_repository()
    currentNTAitems = getCurrentNTA()
    wdregex = re.compile(u'^http\:\/\/viaf\.org\/viaf\/(\d+)\tWKP\|(Q\d+)$')
    ntaregex = re.compile(u'^http\:\/\/viaf\.org\/viaf\/(\d+)\tNTA\|([^\s]+)$')
    currentviaf = None
    currentwikidata = None
    currentnta = None
    with open(filename, 'rb') as f:
        for line in f:
            wdmatch = wdregex.match(line)
            ntamatch = ntaregex.match(line)
            if not (wdmatch or ntamatch):
                continue
            if not currentviaf:
                if wdmatch:
                    currentviaf = wdmatch.group(1)
                    currentwikidata = wdmatch.group(2)
                elif ntamatch:
                    currentviaf = ntamatch.group(1)
                    currentnta = ntamatch.group(2)
            elif currentviaf:
                if wdmatch and currentviaf!=wdmatch.group(1):
                    currentviaf = wdmatch.group(1)
                    currentwikidata = wdmatch.group(2)
                    currentnta = None
                elif ntamatch and currentviaf!=ntamatch.group(1):
                    currentviaf = ntamatch.group(1)
                    currentwikidata = None
                    currentnta = ntamatch.group(2)
                elif wdmatch and currentviaf==wdmatch.group(1) and currentnta:
                    currentwikidata = wdmatch.group(2)
                    print(u'Viaf: %s, Wikidata: %s, NTA: %s' % (currentviaf, currentwikidata, currentnta))
                    if not currentwikidata in currentNTAitems:
                        yield pywikibot.ItemPage(repo, title=currentwikidata)
                    currentviaf = None
                    currentwikidata = None
                    currentnta = None
                elif ntamatch and currentviaf==ntamatch.group(1) and currentwikidata:
                    currentnta = ntamatch.group(2)
                    print(u'Viaf: %s, Wikidata: %s, NTA: %s' % (currentviaf, currentwikidata, currentnta))
                    if not currentwikidata in currentNTAitems:
                        yield pywikibot.ItemPage(repo, title=currentwikidata)
                    currentviaf = None
                    currentwikidata = None
                    currentnta = None



def main():
    repo = pywikibot.Site().data_repository()
    query = u"""SELECT ?item WHERE {
  ?item wdt:P214 ?viafid .
  { ?item wdt:P27 wd:Q31 } UNION { ?item wdt:P27 wd:Q29999 } .
  ?item wdt:P31 wd:Q5 .
  MINUS { ?item wdt:P1006 [] } .
  } LIMIT 400000"""

    # This query will get all the Qid's for which NTA has a link, but the Qid doesn't have a link
    # The commented out lines will also make mismatched links visible. Too much for this bot now.

    query = u"""SELECT ?item ?person {
      SERVICE <http://data.bibliotheken.nl/sparql> {
  SELECT ?item ?person WHERE {
  ?person rdf:type <http://schema.org/Person> .
 ?person owl:sameAs ?item .
 FILTER REGEX(STR(?item), "http://www.wikidata.org/entity/") .
}
      }
  # The URI (wdtn) links don't seem to be fully populated
  #MINUS { ?item wdtn:P1006 ?person } .
  MINUS { ?item wdt:P1006 [] } .
  #MINUS { ?item owl:sameAs ?item2 . ?item2 wdtn:P1006 ?person }
  MINUS { ?item owl:sameAs ?item2 . ?item2 wdt:P1006 [] }
}"""

    #generator = pagegenerators.PreloadingEntityGenerator(viafDumpGenerator())

    generator = pagegenerators.PreloadingEntityGenerator(ntaBacklinksGenerator())
    #generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    viafImportBot = ViafImportBot(generator)
    viafImportBot.run()

if __name__ == "__main__":
    main()
