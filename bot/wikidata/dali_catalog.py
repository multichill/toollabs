#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to get all the paintings in the Dali catalog matched with Wikidata.

See https://www.salvador-dali.org/en/artwork/catalogue-raisonne-paintings/obres/ for the paintings.

Should generate mix'n'match output and maybe more.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import csv
import string
from html.parser import HTMLParser


def getDaliCatalogPaintingsGenerator():
    """
    Generator to get the paintings from https://www.salvador-dali.org/en/artwork/catalogue-raisonne-paintings/obres/

    I'm just going to be lazy and loop from 1 to 1200 and work on it if I don't get a 404
    :return:
    """
    htmlparser = HTMLParser()
    urlpattern = 'https://www.salvador-dali.org/en/artwork/catalogue-raisonne-paintings/obra/%s/'
    caurlpattern = 'https://www.salvador-dali.org/en/artwork/catalogue-raisonne-paintings/obra/%s/'
    esurlpattern = 'https://www.salvador-dali.org/en/artwork/catalogue-raisonne-paintings/obra/%s/'
    frurlpattern = 'https://www.salvador-dali.org/en/artwork/catalogue-raisonne-paintings/obra/%s/'
    session = requests.Session()


    for i in range(1,1220):
        metadata = {}
        metadata['instance'] = 'Q3305213'
        metadata['id'] = '%s' % (i,)
        url = urlpattern % (i,)
        metadata['url'] = url
        page = session.get(url)
        if page.status_code == 404:
            # Ok, that one didn't exist
            print('No painting found for %s at %s' % (i, url))
            continue
        titleregex = '\<title\>([^\|]+)\s*\| Fundació Gala - Salvador Dalí\<\/title\>'
        titlematch = re.search(titleregex, page.text)
        metadata['title'] = htmlparser.unescape(titlematch.group(1)).strip()

        dateregex = '\<dt\>Date\:\<\/dt\>[\s\r\n\t]*\<dd\>\<a href\=\"[^\"]*\"\>([^\<]+)\<\/a\>\<\/dd\>'
        datematch = re.search(dateregex, page.text)
        metadata['date'] = htmlparser.unescape(datematch.group(1)).strip()

        mediumregex = '\<dt\>Technique\:\<\/dt\>[\s\r\n\t]*\<dd\>([^\<]+)\<\/dd\>'
        mediummatch = re.search(mediumregex, page.text)
        metadata['medium'] = htmlparser.unescape(mediummatch.group(1)).strip()

        dimensionregex = '\<dt\>Dimensions\:\<\/dt\>[\s\r\n\t]*\<dd\>([^\<]+)\<'
        dimensionmatch = re.search(dimensionregex, page.text)
        if dimensionmatch:
            metadata['dimension'] = htmlparser.unescape(dimensionmatch.group(1)).strip()

        locationregex = '\<dt\>Location\:\<\/dt\>[\s\r\n\t]*\<dd\>\<a href\=\"[^\"]*\"\>([^\<]+)\<\/a\>\<\/dd\>'
        locationmatch = re.search(locationregex, page.text)
        if locationmatch:
            metadata['location'] = htmlparser.unescape(locationmatch.group(1)).strip()

        metadata['description'] = 'Date: %s Technique: %s Dimensions: %s Location: %s' % (metadata.get('date'),
                                                                                          metadata.get('medium'),
                                                                                          metadata.get('dimension'),
                                                                                          metadata.get('location'),)
        yield metadata
        #time.sleep(1)







def linkOnWikidata(property):
    '''
    Make a dict for ULAN -> qid
    :return: Dict
    '''
    result = {}
    # Need to use the long version here to get all ranks
    query = u"""SELECT ?item ?id WHERE { ?item wdt:%s ?id }""" % (property,)
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = { u'qid' : qid }

    return result

def processArtist(artist, ulanwd, gndwd, repo):
    """
    Get the artist info, look for ULAN, if
    """
    itemPage = requests.get(artist.get('url'))
    ulanregex = u'\<a href\=\"http\:\/\/vocab\.getty\.edu\/page\/ulan\/(\d+)\"\>ULAN\<\/a\>'
    gndregex = u'\<a href\=\"http\:\/\/d-nb\.info\/gnd\/([^\"]+)\"\>GND\<\/a\>'
    wikiregex = u'\<a href\=\"https\:\/\/de\.wikipedia\.org\/wiki\/([^\"]+)">Wikipedia</a>'

    ulanmatch = re.search(ulanregex, itemPage.text)
    gndmatch = re.search(gndregex, itemPage.text)
    wikimatch = re.search(wikiregex, itemPage.text)
    if ulanmatch:
        ulanid = ulanmatch.group(1).encode(u'utf-8') # Force it to string
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
            return True

    if gndmatch:
        gndid = gndmatch.group(1).encode(u'utf-8') # Force it to string
        pywikibot.output(u'Found an GND match on %s to %s' % (artist.get('url'), gndid))
        if gndid in gndwd:
            itemTitle = gndwd.get(gndid).get('qid')
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
            summary = u'based on link to GND %s on entry "%s" on Belvedere website' % (gndid, artist.get(u'name'), )

            item.addClaim(newclaim, summary=summary)
            return True

    if wikimatch:
        articleTitle = u':de:%s' % (wikimatch.group(1),)
        page = pywikibot.Page(pywikibot.Link(articleTitle))
        if not page.exists():
            return False
        if page.isRedirectPage():
            page = page.getRedirectTarget()
        item = page.data_item()

        if not item or not item.exists():
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
        summary = u'based on link to [[%s]] on entry "%s" on Belvedere website' % (articleTitle, artist.get(u'name'), )

        item.addClaim(newclaim, summary=summary)
        return True

def main():
    repo = pywikibot.Site().data_repository()
    paintingGenerator = getDaliCatalogPaintingsGenerator()

    with open('/tmp/dali_cat_paintings.tsv', 'w') as tsvfile:
        fieldnames = [u'Entry ID', # (your alphanumeric identifier; must be unique within the catalog)
                      u'Entry name', # (will also be used for the search in mix'n'match later)
                      u'Entry description', #
                      u'Entry type', # (short string, e.g. "person" or "location"; recommended)
                      u'Entry URL', # if omitted, it will be constructed from the URL pattern and the entry ID. Either a URL pattern or a URL column are required!
                      ]

        writer = csv.DictWriter(tsvfile, fieldnames, dialect='excel-tab')

        #No header!
        #writer.writeheader()

        for painting in paintingGenerator:
            print (painting)
            paintingdict = {'Entry ID' : painting['id'].encode(u'utf-8'),
                            'Entry name' : painting[u'title'].encode(u'utf-8'),
                            'Entry description' : painting[u'description'].encode(u'utf-8'),
                            'Entry type' : u'artwork'.encode(u'utf-8'),
                            'Entry URL': painting[u'url'].encode(u'utf-8'),
                          }
            paintingdict = {'Entry ID' : painting['id'],
                            'Entry name' : painting['title'],
                            'Entry description' : painting['description'],
                            'Entry type' : painting['instance'],
                            'Entry URL': painting['url'],
                            }
            writer.writerow(paintingdict)
            #if artist[u'id'] not in belvederewd:
            #    processArtist(artist, ulanwd, gndwd, repo)


if __name__ == "__main__":
    main()
