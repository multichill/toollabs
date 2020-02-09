#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to process Muziekweg performers so these can be added to mix'n'match and to Wikidata

Loop over all performers and insert it into a dict based on the unique key. Output it as a tsv

For the quality hits, edit Wikidata.

Not working properly at the moment. No good way to confirm the suggestion is actually the correct link.
"""

import pywikibot
import pywikibot.data.sparql
import requests
import re
import time
import csv
import io

def getMuziekwebMedewerkersGenerator():
    """
    Generator to return Auckland Art Gallery paintings

    """
    with open('/home/mdammers/temp/MuziekwebMedewerkers_inclExternalIdentifers.tsv', 'r') as medewerkersFile:
        #data = medewerkersFile.read().decode("utf-8-sig").encode("utf-8")
        #for line in medewerkersFile:
        #    print line
        #print medewerkersFile
        reader = csv.DictReader(medewerkersFile, delimiter='\t')
        for medewerker in reader:
            yield medewerker

def getMetadata(medewerker):

    print (medewerker)
    if not medewerker.get('MEDEWERKERLINK'):
        return False
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

    if medewerker.get(u'MUSICBRAINZ'):
        metadata[u'musicbrainz'] = u'%s' % (medewerker.get(u'MUSICBRAINZ').decode(u'utf-8').replace(u'https://musicbrainz.org/artist/', u''),)

    if medewerker.get(u'DISCOGS'):
        metadata[u'discogs'] = u'%s' % (medewerker.get(u'DISCOGS').decode(u'utf-8').replace(u'https://www.discogs.com/artist/', u''),)

    isniregex = u'(\d\d\d\d)\s*(\d\d\d\d)\s*(\d\d\d\d)\s*(\d\d\d\d)'
    if medewerker.get(u'ISNI'):
        isnimatch = re.match(isniregex, medewerker.get(u'ISNI').decode(u'utf-8'))
        if isnimatch:
            metadata[u'isni'] = u'%s %s %s %s' % (isnimatch.group(1),
                                                  isnimatch.group(2),
                                                  isnimatch.group(3),
                                                  isnimatch.group(4),)

    metadata[u'type'] = u''

    metadata[u'suggestion'] = u''
    if qid:
        metadata[u'suggestion'] = qid.title()

    return metadata

def getLookupTabel(property):
    """
    Make a lookupt table "id" -> "qid" for the property
    :param property: Property to make the lookup table for
    :return: Dict with strings in it
    """
    result = {}
    query = u'SELECT ?item ?id WHERE { ?item wdt:%s ?id }' % (property, )
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = qid
    return result

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

def addWikidata(metadata, muziekWebLookup, musicBrainzLookup, discogsLookup, isniLookup, repo):
    """
    The to add the suggestion in the metadata if it's good enough
    :param metadata:
    :param muziekWebLookup:
    :param musicBrainzLookup:
    :param discogsLookup:
    :return:
    """
    if metadata.get('id') in muziekWebLookup:
        # It's already linked!
        return True

    qid = metadata.get('suggestion')
    print (u'Working on %s' % (qid,))
    musicbrainz = None
    musicbrainzqid = None
    discogs = None
    discogsqid = None
    isni = None
    isniqid = None

    if metadata.get('musicbrainz'):
        musicbrainz = metadata.get('musicbrainz')
        musicbrainzqid = musicBrainzLookup.get(musicbrainz)
    if metadata.get('discogsLookup'):
        discogs = metadata.get('discogsLookup')
        discogsqid = discogsLookup.get(discogs)
    if metadata.get('isniLookup'):
        isni = metadata.get('isniLookup')
        isniqid = isniLookup.get(isni)

    print (u'Suggestions found: %s->%s %s->%s %s->%s' % (musicbrainz, musicbrainzqid, discogs, discogsqid, isni, isniqid, ))

    if not musicbrainzqid and not discogsqid and not isniqid:
        # Nothing to match against
        return False

    # Mismatches
    if musicbrainzqid and musicbrainzqid!=qid:
        return False
    if discogsqid and discogsqid!=qid:
        return False
    if isniqid and isniqid!=qid:
        return False

    # Basic checks done, let's grab the item to check it.
    itempage = pywikibot.ItemPage(repo, qid)
    data = itempage.get()
    claims = data.get('claims')

    if u'P5882' in claims:
        # Already done
        return True

    summary = u'based on linkback'

    # Check MusicBrainz
    if u'P434' in claims:
        if claims.get(u'P434')[0].getTarget()!=musicbrainz:
            return False
        summary += u' / MusicBrainz artist ID %s' % (musicbrainz,)
    # Check Discogs
    if u'P1953' in claims:
        if claims.get(u'P1953')[0].getTarget()!=discogs:
            return False
        summary += u' / Discogs artist ID %s' % (discogs,)
    # Check ISNI
    if u'P213' in claims:
        if claims.get(u'P213')[0].getTarget()!=isni:
            return False
        summary += u' / ISNI %s' % (isni,)

    print (summary)
    print (summary)
    print (summary)
    print (summary)
    print (summary)
    newclaim = pywikibot.Claim(repo, u'P5882')
    newclaim.setTarget(metadata.get('id'))
    itempage.addClaim(newclaim, summary=summary)


def main():
    medewerkerDict = getMuziekwebMedewerkersGenerator()
    muziekWebLookup = getLookupTabel('P5882')
    musicBrainzLookup = getLookupTabel('P434')
    discogsLookup = getLookupTabel('P1953')
    isniLookup = getLookupTabel('P213')
    repo = pywikibot.Site().data_repository()

    with open('/tmp/muziekweb_performers.tsv', 'wb') as tsvfile:
        fieldnames = [u'Entry ID', # (your alphanumeric identifier; must be unique within the catalog)
                      u'Entry name', # (will also be used for the search in mix'n'match later)
                      u'Entry description', #
                      u'Entry type', # (short string, e.g. "person" or "location"; recommended)
                      u'Entry URL', # if omitted, it will be constructed from the URL pattern and the entry ID. Either a URL pattern or a URL column are required!
                      u'Entry suggestion'
                      ]

        #writer = csv.DictWriter(tsvfile, fieldnames, dialect='excel-tab')

        #No header!
        #writer.writeheader()

        for medewerker in medewerkerDict:
            metadata = getMetadata(medewerker)
            if not metadata:
                continue
            print (metadata)

            artistdict = {u'Entry ID' : metadata[u'id'].encode(u'utf-8'),
                          u'Entry name' : metadata[u'name'].encode(u'utf-8'),
                          u'Entry description' : metadata[u'description'].encode(u'utf-8'),
                          u'Entry type' : metadata[u'type'].encode(u'utf-8'),
                          u'Entry URL': metadata[u'url'].encode(u'utf-8'),
                          u'Entry suggestion': metadata[u'suggestion'].encode(u'utf-8'),
                          }
            #print (artistdict)
            #writer.writerow(artistdict)

            print (u'heeeelpup')
            if metadata.get('suggestion'):
                print (u'blaaaaldie bla')
                addWikidata(metadata, muziekWebLookup, musicBrainzLookup, discogsLookup, isniLookup, repo)

if __name__ == "__main__":
    main()
