#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to get all the artists from the  Museum of New Zealand Te Papa Tongarewa website so these can be added to mix'n'match.

Loop over all works and insert it into a dict based on the unique key. Output it as a tsv


"""
import artdatabot
import pywikibot
import requests
import re
import time
import csv

def getTePagaArtistsGenerator():
    """
    Generator to return Auckland Art Gallery paintings

    """
    session = requests.session()
    baseurl=u'http://collections.tepapa.govt.nz/Person/%s'

    # Just loop over the pages
    for i in range(1, 50000):
        url = baseurl % (i,)
        print url
        page = session.get(url)
        fieldregex = u'\<tr\>[\s\t\r\n]*\<td class\=\"heading\">([^\<]+)\<\/td\>[\s\t\r\n]*\<td\>([^\<]+)\<\/td\>'
        gettyregex = u'\<li\>\<a href\=\"http\:\/\/www\.getty\.edu\/vow\/ULANFullDisplay[^\"]*subjectid\=(\d+)\"\>www\.getty\.edu\<\/a\>\<\/li\>'

        expectedfields = [u'Name',
                          u'Party Type',
                          u'Date of Birth',
                          u'Date of Death',
                          u'Nationality',
                          u'Place of Activity']
        parseddata = {}

        matches = re.finditer(fieldregex, page.text)
        for match in matches:
            fieldkey = match.group(1).strip()
            fieldvalue = match.group(2).strip()
            parseddata[fieldkey] = fieldvalue
            if not fieldkey in expectedfields:
                print u'Got unexpected key %s with value %s' % (fieldkey, fieldvalue)
        print parseddata

        name = parseddata.get('Name')
        if name:
            if u',' in name:
                (surname, sep, firstname) = name.partition(u',')
                name = u'%s %s' % (firstname.strip(), surname.strip(),)

            description = u''
            if parseddata.get('Nationality'):
                description = description + parseddata.get('Nationality') + u' '

            if parseddata.get('Place of Activity'):
                description = description + u'active: ' + parseddata.get('Place of Activity') + u' '

            if parseddata.get('Date of Birth'):
                if parseddata.get('Date of Death'):
                    description = description + u'(%s-%s)' % (parseddata.get('Date of Birth'),
                                                              parseddata.get('Date of Death'))
                else:
                    description = description + u'(%s)' % (parseddata.get('Date of Birth'),)

            if parseddata.get('Party Type'):
                partytype = parseddata.get('Party Type')
                metadata = { u'id' : u'%s' % (i,),
                             u'name' : name,
                             u'description' : description,
                             u'url' : url,
                             u'partytype' : partytype.lower(),
                         }
                gettymatch = re.search(gettyregex, page.text)
                if gettymatch:
                    metadata[u'ulan'] = gettymatch.group(1)

                yield metadata

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


def main():
    repo = pywikibot.Site().data_repository()
    artistsGen= getTePagaArtistsGenerator()
    tepapawd = linkOnWikidata(u'P3544')
    pywikibot.output(u'Number of Te Papa items on Wikidata is %s' % (len(tepapawd),))
    ulanwd = linkOnWikidata(u'P245')
    pywikibot.output(u'Number of ULAN items on Wikidata is %s' % (len(ulanwd),))
    #for artist in artistsDict:
    #    print artist

    with open('/tmp/tepapa_artists.tsv', 'wb') as tsvfile:
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
                          u'Entry type' : artist[u'partytype'].encode(u'utf-8'),
                          u'Entry URL': artist[u'url'].encode(u'utf-8'),
                          }
            print artist
            writer.writerow(artistdict)
            if artist[u'id'] not in tepapawd and artist.get(u'ulan') and artist.get(u'ulan') in ulanwd:
                itemTitle = ulanwd.get(artist.get(u'ulan')).get('qid')
                pywikibot.output(u'Found %s as the Wikidata item to link to' % (itemTitle,))
                item = pywikibot.ItemPage(repo, title=itemTitle)
                if not item.exists():
                    return False
                if item.isRedirectPage():
                    item = item.getRedirectTarget()

                data = item.get()
                claims = data.get('claims')

                if u'P3544' not in claims:

                    newclaim = pywikibot.Claim(repo, u'P3544')
                    newclaim.setTarget(artist.get('id'))
                    pywikibot.output('Adding Te Papa %s claim to %s' % (artist.get('id'), item.title(), ))

                    # Default text is "‎Created claim: Te Papa identifier (P3544): 123, "
                    summary = u'based on link to ULAN %s on entry "%s" on Te Papa website' % (artist.get(u'ulan'),
                                                                                              artist.get(u'name'), )

                    item.addClaim(newclaim, summary=summary)

if __name__ == "__main__":
    main()
