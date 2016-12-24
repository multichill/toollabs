#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to get all the artists from the Österreichische Galerie Belvedere website so these can be added to mix'n'match.

They provide ULAN links so might as well match and import these right away.


http://digital.belvedere.at/people/ (append a-z)

Loop over all works and insert it into a dict based on the unique key. Output it as a tsv

Added some quick & dirty code to make matches based on ULAN, GND and the German Wikipedia

"""
import artdatabot
import pywikibot
import requests
import re
import time
import csv
import string
import HTMLParser

def getBelvedereArtistsGenerator():
    """
    Generator to return Auckland Art Gallery paintings

    """
    htmlparser = HTMLParser.HTMLParser()

    basesearchurl=u'http://digital.belvedere.at/people/%s'
    urlregex = u'\<h3\>\<a href\=\"\/people\/(?P<id>\d+)\/[^\"]+\"\>(?P<name>[^\<]+)\<\/a\>\<\/h3\>\<div\>(?P<description>[^\<]+)\<\/div\>'

    # Just loop over the pages
    for i in string.ascii_lowercase:
        searchurl = basesearchurl % (i,)
        print searchurl
        searchPage = requests.get(searchurl)

        matches = re.finditer(urlregex, searchPage.text)
        for match in matches:
            artist = {}
            artist[u'id'] = match.group(u'id')
            artist[u'name'] = htmlparser.unescape(match.group(u'name'))
            artist[u'description'] = htmlparser.unescape(match.group(u'description'))
            artist[u'url'] = u'http://digital.belvedere.at/people/%s/' % (match.group(u'id'),)
            yield artist


def ULANOnWikidata():
    '''
    Make a dict for ULAN -> qid
    :return: Dict
    '''
    result = {}
    # Need to use the long version here to get all ranks
    query = u"""SELECT ?item ?id WHERE { ?item wdt:P245 ?id }"""
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = { u'qid' : qid }

    return result


def BelvedereOnWikidata():
    '''
    Make a dict for Belvedere -> qid
    :return: Dict
    '''
    result = {}
    # Need to use the long version here to get all ranks
    query = u"""SELECT ?item ?id WHERE { ?item wdt:P3421 ?id }"""
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = { u'qid' : qid }

    return result

def processUlan(artist, ulanwd, repo):
    """
    Get the artist info, look for ULAN, if
    """
    itemPage = requests.get(artist.get('url'))
    ulanregex = u'\<a href\=\"http\:\/\/vocab\.getty\.edu\/page\/ulan\/(\d+)\"\>ULAN\<\/a\>'

    match = re.search(ulanregex, itemPage.text)
    if match:
        ulanid = match.group(1).encode(u'utf-8') # Force it to string
        pywikibot.output(u'Found an ULAN match on %s to %s' % (artist.get('url'), ulanid))
        if ulanid in ulanwd:
            itemTitle = ulanwd.get(ulanid).get('qid')
            pywikibot.output(u'Found %s as the Wikidata item to link to' % (itemTitle,))
            item = pywikibot.ItemPage(repo, title=itemTitle)
            if not item.exists():
                return False

            if item.isRedirectPage():
                item = item.getRedirectTarget()

            data = item.get()
            claims = data.get('claims')

            if u'P3421' in claims:
                # Already has Belvedere, great!
                return True

            newclaim = pywikibot.Claim(repo, u'P3421')
            newclaim.setTarget(artist.get('id'))
            pywikibot.output('Adding Belvedere %s claim to %s' % (artist.get('id'), item.title(), ))

            # Default text is "‎Created claim: Belvedere identifier (P3421): 123, "
            summary = u'based on link to ULAN %s on entry "%s" on Belvedere website' % (ulanid, artist.get(u'name'), )

            item.addClaim(newclaim, summary=summary)

def main():
    repo = pywikibot.Site().data_repository()
    artistsGen = getBelvedereArtistsGenerator()
    ulanwd = ULANOnWikidata()
    belvederewd = BelvedereOnWikidata()

    with open('/tmp/belvedere_artists.tsv', 'wb') as tsvfile:
        fieldnames = [u'Entry ID', # (your alphanumeric identifier; must be unique within the catalog)
                      u'Entry name', # (will also be used for the search in mix'n'match later)
                      u'Entry description', #
                      u'Entry type', # (short string, e.g. "person" or "location"; recommended)
                      u'Entry URL', # if omitted, it will be constructed from the URL pattern and the entry ID. Either a URL pattern or a URL column are required!
                      ]

        writer = csv.DictWriter(tsvfile, fieldnames, dialect='excel-tab')

        #No header!
        #writer.writeheader()

        for artist in artistsGen:
            artistdict = {u'Entry ID' : artist[u'id'].encode(u'utf-8'),
                          u'Entry name' : artist[u'name'].encode(u'utf-8'),
                          u'Entry description' : artist[u'description'].encode(u'utf-8'),
                          u'Entry type' : u'person'.encode(u'utf-8'),
                          u'Entry URL': artist[u'url'].encode(u'utf-8'),
                          }
            print artist
            writer.writerow(artistdict)
            if artist[u'id'] not in belvederewd:
                processUlan(artist, ulanwd, repo)


if __name__ == "__main__":
    main()
