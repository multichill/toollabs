#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to get all the artists from the Auckland Art Gallery website so these can be added to mix'n'match.

They seem to provide json:

http://www.aucklandartgallery.com/search/artworks?section=collection&undated=undated&objectType[0]=Painting&reference=artworks&page=2

Loop over all works and insert it into a dict based on the unique key. Output it as a tsv


"""
import artdatabot
import pywikibot
import requests
import re
import time
import csv
import io

def getMuziekwebMedewerkersGenerator():
    """
    Generator to return Auckland Art Gallery paintings

    """
    with open('/home/mdammers/temp/MuziekwebMedewerkers.tsv', 'rb') as medewerkersFile:
        #data = medewerkersFile.read().decode("utf-8-sig").encode("utf-8")
        #for line in medewerkersFile:
        #    print line
        #print medewerkersFile
        reader = csv.DictReader(medewerkersFile, delimiter='\t')
        for medewerker in reader:
            yield medewerker

    """


    basesearchurl=u'http://www.aucklandartgallery.com/search/artworks?section=collection&undated=undated&reference=artworks&page=%s'

    #basesearchurl = u'http://www.aucklandartgallery.com/search/artworks?section=collection&undated=undated&objectType[0]=Painting&reference=artworks&page=%s'
    origin = u'http://www.aucklandartgallery.com'
    referer = u'http://www.aucklandartgallery.com/search/artworks?section=collection&undated=undated&objectType%5B0%5D=Painting'

    result = {}
    notdone = []



    # Just loop over the pages
    for i in range(1, 1341):
        print i
        searchurl = basesearchurl % (i,)
        searchPage = requests.get(searchurl, headers={'X-Requested-With' : 'XMLHttpRequest',
                                                      'referer' : referer,
                                                      'origin' : origin} )

        # This might bork evey once in a while, we'll see
        try:
            searchJson = searchPage.json()
        except ValueError:
            print u'Oh, noes, no JSON. Wait and try again'
            time.sleep(15)
            searchPage = requests.get(searchurl, headers={'X-Requested-With' : 'XMLHttpRequest',
                                                          'referer' : referer,
                                                          'origin' : origin} )
            searchJson = searchPage.json()

        for record in searchJson.get('data'):

            entryid = record.get('user_sym_91')
            if not isinstance(entryid, list):
                result = processEntry(entryid, record.get('user_sym_32'),record.get('classification'), result)
            else:
                i = 0
                for ndentry in entryid:
                    result = processEntry(ndentry, record.get('user_sym_32')[i],record.get('classification'), result)
                    i = i + 1
                    #notdone.append(ndentry)
                #print u'No idea how to process this one'

            #yield
    for entrynum in result:
        result[entrynum][u'description'] =  result[entrynum]['shortdescription'] + u' (field of work: ' + u'/'.join(result[entrynum]['classification']) + u')'

    return result
    """

def processEntry(entryid, user_sym_32, classification, result):
    descregex = u'^([^\)]+)\s*\((.+)\)'
    if int(entryid) not in result:
        metadata = { u'id' : entryid,
                     u'name' : u'',
                     u'shortdescription' : u'',
                     u'url' : u'http://www.aucklandartgallery.com/explore-art-and-ideas/artist/%s/' % (entryid,),
                     u'classification' : [classification,]
                     }
        match = re.match(descregex, user_sym_32)
        if match:
            metadata[u'name'] = match.group(1).strip()
            metadata[u'shortdescription'] = match.group(2)
        else:
            metadata[u'name'] =  user_sym_32
            metadata[u'shortdescription'] = user_sym_32
        result[int(entryid)]=metadata
    else:
        if classification not in result[int(entryid)][u'classification']:
            result[int(entryid)][u'classification'].append(classification)
    return result


def getMetadata(medewerker):

    metadata = {}
    metadata[u'id'] = medewerker.get(u'MEDEWERKERLINK').decode(u'utf-8')
    metadata[u'url'] = u'https://www.muziekweb.nl/Link/%s/' % (medewerker.get(u'MEDEWERKERLINK').decode(u'utf-8'),)
    metadata[u'name'] = medewerker.get(u'MEDEWERKER').decode(u'utf-8')
    metadata[u'description'] = u''
    if medewerker.get(u'ANNOTATIE') and medewerker.get(u'LEEFJAAR'):
        metadata[u'description'] = u'%s (%s)' % (medewerker.get(u'ANNOTATIE').decode(u'utf-8'),
                                                 medewerker.get(u'LEEFJAAR').decode(u'utf-8'))
    elif medewerker.get(u'ANNOTATIE'):
        metadata[u'description'] = u'%s' % (medewerker.get(u'ANNOTATIE').decode(u'utf-8'))
    elif medewerker.get(u'LEEFJAAR'):
        metadata[u'description'] = u'%s' % (medewerker.get(u'LEEFJAAR').decode(u'utf-8'),)

    qid = None
    if medewerker.get(u'WIKI_NL_KEY'):
        qid = getWikidataId(medewerker.get(u'WIKI_NL_KEY').decode(u'utf-8'), u'nl')
    elif medewerker.get(u'WIKI_EN_KEY'):
        qid = getWikidataId(medewerker.get(u'WIKI_EN_KEY').decode(u'utf-8'), u'en')

    metadata[u'type'] = u''

    metadata[u'suggestion'] = u''
    if qid:
        metadata[u'suggestion'] = qid.title()

    return metadata


def getWikidataId(page_title, lang):
    try:
        site = pywikibot.Site(lang, u'wikipedia')
        performerlink = pywikibot.Link(page_title, source=site, defaultNamespace=0)

        page = pywikibot.Page(performerlink)
        if page.isRedirectPage():
            page = pywikibot.Page(page.getRedirectTarget())
        if not page.exists():
            pywikibot.output('[[%s]] doesn\'t exist so I can\'t link to it' % (page.title(),))
        elif page.isDisambig():
            pywikibot.output('[[%s]] is a disambiguation page so I can\'t link to it' % (page.title(),))
        else:
            item = pywikibot.ItemPage.fromPage(page)
            if item.exists():
                return item
    except pywikibot.exceptions.NoPage:
        return


def main():
    medewerkerDict = getMuziekwebMedewerkersGenerator()

    with open('/tmp/muziekweb_performers.tsv', 'wb') as tsvfile:
        fieldnames = [u'Entry ID', # (your alphanumeric identifier; must be unique within the catalog)
                      u'Entry name', # (will also be used for the search in mix'n'match later)
                      u'Entry description', #
                      u'Entry type', # (short string, e.g. "person" or "location"; recommended)
                      u'Entry URL', # if omitted, it will be constructed from the URL pattern and the entry ID. Either a URL pattern or a URL column are required!
                      u'Entry suggestion'
                      ]

        writer = csv.DictWriter(tsvfile, fieldnames, dialect='excel-tab')

        #No header!
        #writer.writeheader()

        for medewerker in medewerkerDict:
            metadata = getMetadata(medewerker)
            print metadata

            artistdict = {u'Entry ID' : metadata[u'id'].encode(u'utf-8'),
                          u'Entry name' : metadata[u'name'].encode(u'utf-8'),
                          u'Entry description' : metadata[u'description'].encode(u'utf-8'),
                          u'Entry type' : metadata[u'type'].encode(u'utf-8'),
                          u'Entry URL': metadata[u'url'].encode(u'utf-8'),
                          u'Entry suggestion': metadata[u'suggestion'].encode(u'utf-8'),
                          }
            print artistdict
            writer.writerow(artistdict)

if __name__ == "__main__":
    main()
