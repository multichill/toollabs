#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add missing Art UK Work links. It will do this based on the collection / inventory number combination.

To run:

python pwb.py /path/to/art_uk_works_link.py -collectionid:Q180788

This will make the bot run on https://www.wikidata.org/wiki/Q180788 . The item needs to have a  Art UK venue ID (P1602)

In this case: http://artuk.org/visit/venues/the-national-gallery-london-2030

Bot will loop over http://artuk.org/discover/artworks/search/venue:the-national-gallery-london-2030/


"""
import artdatabot
import pywikibot
import requests
import re
import time

def getVenue(collectionid):
    repo = pywikibot.Site().data_repository()
    item = pywikibot.ItemPage(repo, title=collectionid)
    data = item.get()

    claims = data.get('claims')
    if u'P1602' in claims:
        result = claims.get(u'P1602')[0].getTarget()
        return result
    else:
        pywikibot.output(u'No venue claim found')

def getArtUKWorkGenerator(venuid):
    """
    Generator to return KID paintings
    """
    i = 1
    load_more = True
    basesearchurl = u'http://artuk.org/discover/artworks/search/venue:%s/page/%s?_ajax=1'
    while load_more:
        searchurl = basesearchurl % (venuid, i)
        searchpage = requests.get(searchurl, headers={'X-Requested-With' : 'XMLHttpRequest',} )
        searchjson = searchpage.json()
        load_more = searchjson.get('load_more')
        i = i + 1
        searchtext = searchjson.get('html')

        idregex = u'\"http\:\/\/artuk\.org\/discover\/artworks\/([^\/]+)/search\/venue:[^\"]+/page/\d+\"'
        for match in re.finditer(idregex, searchtext):
            artukid = match.group(1)
            url = u'http://artuk.org/discover/artworks/%s' % (artukid,)
            itempage = requests.get(url)
            invregex = u'\<li\>[\s\t\r\n]+\<h5\>Accession number\<\/h5\>[\s\t\r\n]+\<p\>([^\<]+)\<\/p\>[\s\t\r\n]+\<\/li\>'
            invmatch = re.search(invregex, itempage.text)
            if invmatch:
                invid = invmatch.group(1).strip()
                metadata = {u'invnum' : invid,
                            u'artukid' : artukid,
                            u'url' : url}
                yield metadata

def fillCache(collectionqid):
    '''
    Build an ID cache so we can quickly look up the id's for property.
    Only return items for which we don't already have the Art UK artwork ID (P1679) link
    '''
    result = {}
    sq = pywikibot.data.sparql.SparqlQuery()

    # FIXME: Do something with the collection qualifier
    query = u'SELECT ?item ?id WHERE { ?item wdt:P195 wd:%s . ?item wdt:P217 ?id . MINUS { ?item wdt:P1679 [] } } ' % (collectionqid,)
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = qid
    pywikibot.output(u'The query "%s" returned %s items without an ART UK work link' % (query, len(result)))
    return result

def main(*args):
    collectionid = None

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-collectionid:'):
            if len(arg) == 14:
                collectionid = pywikibot.input(
                        u'Please enter the collectionid you want to work on:')
            else:
                collectionid = arg[14:]

    if not collectionid:
        pywikibot.output(u'Usage: python pwb.py /path/to/art_uk_works_link.py -collectionid:Q180788')
        return

    venueid = getVenue(collectionid)
    if not venueid:
        pywikibot.output(u'No valid venue found')
        return

    cache = fillCache(collectionid)
    dictGen = getArtUKWorkGenerator(venueid)
    repo = pywikibot.Site().data_repository()

    for work in dictGen:
        print(work)
        if work.get(u'invnum') in cache:
            artworkItemTitle = cache.get(work.get(u'invnum'))
            pywikibot.output(u'Found an artwork to add a link to: %s' % (artworkItemTitle,))
            artworkItem = pywikibot.ItemPage(repo, title=artworkItemTitle)
            data = artworkItem.get()
            claims = data.get('claims')
            if not u'P1679' in claims:
                newclaim = pywikibot.Claim(repo, u'P1679')
                newclaim.setTarget(work[u'artukid'])
                summary = u'adding link based on [[%s]] with inventory number %s' % (collectionid, work.get(u'invnum'),)
                pywikibot.output(summary)
                artworkItem.addClaim(newclaim, summary=summary)

if __name__ == "__main__":
    main()
