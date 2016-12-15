#!/usr/bin/python
# -*- coding: utf-8 -*-
"""


"""
import artdatabot
import pywikibot
import requests
import re
import time

def getKidWorkGenerator(museumid, museumqid):
    """
    Generator to return KID paintings
    """
    basesearchurl = u'https://www.kulturarv.dk/kid/SoegMuseumVaerker.do?orderBy=asc:titel&action=SoegMuseumVaerker&listeviewtype=museumvaerkliste&museumId=%s&page=%s'

    apiurl = u'https://api.royalcollection.org.uk/collection/search-api'
    postjson = u'{"searchTerm":"","hasImages":false,"orderBy":"relevancy","orderDirection":"desc","page":%s,"searchType":{"who":[],"what":{"object_category":[[{"id":"18","name":"Object category","type":"object_category"},{"id":"49367","name":"Paintings"}]]},"where":[],"when":[],"more":{}},"themeSubject":[],"themePeople":[],"themeType":"","whatsOn":[],"whatsOnDate":"","whatsOnEndDateIsPast":false,"whatsOnAccess":"","excludeNode":"","conservationProcesses":[],"conservationTypes":[],"exhibitionReference":[],"residenceReference":[],"itemsPerPage":8}'

    firstpage = requests.get(basesearchurl % (museumid, 1,))
    lastregex = u'\<a href\=\"\/kid\/SoegMuseumVaerker\.do\?page=(\d+)&[^\"]+"\>Last&nbsp;&gt;&gt;\<\/a\>'

    lastmatch = re.search(lastregex, firstpage.text)

    lastpage = int(lastmatch.group(1))
    print (u'Number of pages to work on is %s' % (lastpage,))

    for i in range(1, lastpage+1):
        searchurl = basesearchurl % (museumid, i,)
        print (searchurl)
        searchpage = requests.get(searchurl)

        #print searchpage.text
        idregex = u'\<td class\=\"light\"\>[\s\t\r\n]+Painting[\s\t\r\n]+\<\/td\>[\s\t\r\n]+\<td class\=\"light\"\>[\s\t\r\n]+\<form [^\>]+\>[\s\t\r\n]+\<input type[^\>]+\>[\s\t\r\n]+\<a href\=\"VisVaerk\.do\?vaerkId\=(\d+)\"'
        idregex = u'\<td class\=\"light\"\>([^\<]+)\<\/td\>[\s\t\r\n]+\<td class\=\"light\"\>[\s\t\r\n]+\<form [^\>]+\>[\s\t\r\n]+\<input type[^\>]+\>[\s\t\r\n]+\<a href\=\"VisVaerk\.do\?vaerkId\=(\d+)\"'
        idregex = u'\<a href\=\"VisVaerk\.do\?vaerkId\=(\d+)\"'

        ids = []

        for match in re.finditer(idregex, searchpage.text):
            if not match.group(1) in ids:
                ids.append(match.group(1))


        for kidid in ids:
            url = u'https://www.kulturarv.dk/kid/VisVaerk.do?vaerkId=%s' % (kidid,)
            itempage = requests.get(url)
            invregex = u'\<\/a\>,\s*inv\. nr\.\s*([^\<]+)[\s\t\r\n]+\<\/form\>'
            invmatch = re.search(invregex, itempage.text)
            invid = invmatch.group(1).strip()
            metadata = {u'invnum' : invid,
                        u'kidid' : kidid,
                        u'url' : url}
            yield metadata


def fillCache(collectionqid):
    '''
    Build an ID cache so we can quickly look up the id's for property.
    Only return items for which we don't already have the  Kunstindeks Danmark artwork ID (P2108) link
    '''
    result = {}
    sq = pywikibot.data.sparql.SparqlQuery()

    # FIXME: Do something with the collection qualifier
    query = u'SELECT ?item ?id WHERE { ?item wdt:P195 wd:%s . ?item wdt:P217 ?id . MINUS { ?item wdt:P2108 [] } } ' % (collectionqid,)
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = qid
    pywikibot.output(u'The query "%s" returned %s items' % (query, len(result)))
    return result

def main():
    museumid = u'583'
    museumqid = u'Q671384'
    cache = fillCache(museumqid)
    dictGen = getKidWorkGenerator(museumid, museumqid)
    repo = pywikibot.Site().data_repository()

    for work in dictGen:
        print(work)
        if work.get(u'invnum') in cache:
            artworkItemTitle = cache.get(work.get(u'invnum'))
            pywikibot.output(u'Found an artwork to add a link to: %s' % (artworkItemTitle,))
            artworkItem = pywikibot.ItemPage(repo, title=artworkItemTitle)
            data = artworkItem.get()
            claims = data.get('claims')
            if not u'P2108' in claims:
                newclaim = pywikibot.Claim(repo, u'P2108')
                newclaim.setTarget(work[u'kidid'])
                #pywikibot.output('Adding link based on described at claim to %s' % artworkItem)
                summary = u'adding link based on inventory number %s' % (work.get(u'invnum'),)
                pywikibot.output(summary)
                artworkItem.addClaim(newclaim, summary=summary)


    #artDataBot = artdatabot.ArtDataBot(dictGen, create=False)
    #artDataBot.run()

if __name__ == "__main__":
    main()
