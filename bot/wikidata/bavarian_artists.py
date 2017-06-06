#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Tool to match pinakothek artists with items on Wikidata.

See https://www.wikidata.org/wiki/Property:P4025 and talk page for more information about this property

Bot does a quite complicated SPARQL query to get suggestions. Checks those with the pinakothek website

"""
import pywikibot
import requests
import pywikibot.data.sparql
import re


def getPossibleArtistsGenerator():
    '''
    Do a SPARQL query to grab artists to work on
    :return: Dict
    '''
    result = {}
    # Need to use the long version here to get all ranks
    query = u"""SELECT (SAMPLE(?item) AS ?item) ?creator ?creatorLabel ?creatorurl ?creatorid ?yob ?yod
{
	?item wdt:P195 wd:Q812285 .
	?item wdt:P170 ?creator .
	MINUS { ?item wdt:P170 wd:Q4233718 } . # Filter out anonymous
	MINUS { ?creator wdt:P4025 [] } .
    ?item p:P31 ?instancestatement .
    ?instancestatement prov:wasDerivedFrom/pr:P854 ?referenceurl .
    BIND(IRI(REPLACE(STR(?referenceurl), '^(.+)\\\\/([^\\\\/]+)$', '$1')) AS ?creatorurl) .
    BIND(REPLACE(STR(?referenceurl), '^(.+)\\\\/([^\\\\/]+)\\\\/([^\\\\/]+)$', '$2') AS ?creatorid) .
    ?creator wdt:P569 ?dob .
    BIND(YEAR(?dob) AS ?yob) .
    ?creator wdt:P570 ?dod .
    BIND(YEAR(?dod) AS ?yod) .
	SERVICE wikibase:label { bd:serviceParam wikibase:language "en,de" }
} GROUP BY ?creator ?creatorLabel ?creatorurl ?creatorid ?yob ?yod
ORDER BY ?creatorLabel"""
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        artistitem = {}
        artistitem[u'item'] = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        artistitem[u'creator'] = resultitem.get('creator').replace(u'http://www.wikidata.org/entity/', u'')
        artistitem[u'creatorurl'] = resultitem.get('creatorurl')
        artistitem[u'creatorid'] = resultitem.get('creatorid')
        artistitem[u'yob'] = resultitem.get('yob')
        artistitem[u'yod'] = resultitem.get('yod')
        yield artistitem


def processArtist(repo, session, artist):
    """
    Process on artist and try to add a link
    :param artist:
    :return:
    """
    artistPage = session.get(artist.get(u'creatorurl'),
                             verify=False) # For some reason I'm getting certificate errors?

    yobregex = u'\<p class\=\"artist__birthday\"\>[\s\t\r\n]*Born[\s\t\r\n]*\<span\>[\s\t\r\n]*\<a href\=\"https\:\/\/www\.sammlung\.pinakothek\.de\/en\/year\/(\d\d\d\d)\"\>'
    yodregex = u'\<p class\=\"artist__death\"\>[\s\t\r\n]*Deceased[\s\t\r\n]*\<span\>[\s\t\r\n]*\<a href\=\"https\:\/\/www\.sammlung\.pinakothek\.de\/en\/year\/(\d\d\d\d)\"\>'

    yobmatch = re.search(yobregex, artistPage.text)
    yodmatch = re.search(yodregex, artistPage.text)

    if yobmatch and yodmatch:
        yobpinakothek = yobmatch.group(1)
        yodpinakothek = yodmatch.group(1)

        print u'Found yob %s on Wikidata and %s on pinakothek' % (artist.get(u'yob'), yobpinakothek, )
        print u'Found yod %s on Wikidata and %s on pinakothek' % (artist.get(u'yod'), yodpinakothek, )

        item = pywikibot.ItemPage(repo, title=artist.get(u'creator'))
        if not item.exists():
            return False
        if item.isRedirectPage():
            return False
        data = item.get()
        claims = data.get('claims')
        if u'P4025' not in claims:
            if int(artist.get(u'yob'))==int(yobpinakothek) and int(artist.get(u'yod'))==int(yodpinakothek):
                newclaim = pywikibot.Claim(repo, u'P4025')
                newclaim.setTarget(artist.get(u'creatorid'))
                pywikibot.output('Adding %(creatorid)s claim to %(creator)s' % artist)

                summary = u'based on [[%(item)s]]: year of birth %(yob)s and year of death %(yod)s are the same' % artist
                item.addClaim(newclaim, summary=summary)
            elif int(artist.get(u'yob'))==int(yobpinakothek) and abs(int(artist.get(u'yod')) - int(yodpinakothek))==1:
                newclaim = pywikibot.Claim(repo, u'P4025')
                newclaim.setTarget(artist.get(u'creatorid'))
                pywikibot.output('Adding %(creatorid)s claim to %(creator)s' % artist)

                summary = u'based on [[%(item)s]]: year of birth %(yob)s is the same and year of death %(yod)s has just a one year difference' % artist
                item.addClaim(newclaim, summary=summary)
            elif int(artist.get(u'yod'))==int(yodpinakothek) and abs(int(artist.get(u'yob')) - int(yobpinakothek))==1:
                newclaim = pywikibot.Claim(repo, u'P4025')
                newclaim.setTarget(artist.get(u'creatorid'))
                pywikibot.output('Adding %(creatorid)s claim to %(creator)s' % artist)

                summary = u'based on [[%(item)s]]: year of birth %(yob)s has just a one year difference and year of death %(yod)s is the same' % artist
                item.addClaim(newclaim, summary=summary)

            else:
                if int(artist.get(u'yob'))==int(yobpinakothek):
                    pywikibot.output(u'The year of birth is the same (%s), but the year of death is different (%s / %s)' % (yobpinakothek,
                                                                                                                    artist.get(u'yod'),
                                                                                                                    yodpinakothek,))
                    summary = u'based on [[%s]]: year of birth (%s) the same and year of death (%s / %s) confirmed by user' % (artist.get(u'item'),
                                                                                                                             yobpinakothek,
                                                                                                                             artist.get(u'yod'),
                                                                                                                             yodpinakothek,)
                elif int(artist.get(u'yod'))==int(yodpinakothek):
                    pywikibot.output(u'The year of birth is different (%s / %s), but the year of death is the same ( %s )' % (artist.get(u'yob'),
                                                                                                                       yobpinakothek,
                                                                                                                       yodpinakothek,))
                    summary = u'based on [[%s]]: year of birth  (%s / %s) confirmed by user and year of death (%s) the same' % (artist.get(u'item'),
                                                                                                                                artist.get(u'yob'),
                                                                                                                                yobpinakothek,
                                                                                                                                yodpinakothek,)
                else:
                    pywikibot.output(u'The year of birth is different (%s / %s) and the year of death is different (%s / %s)' % (artist.get(u'yob'),
                                                                                                                                 yobpinakothek,
                                                                                                                                 artist.get(u'yod'),
                                                                                                                                 yodpinakothek,))
                    summary = u'based on [[%s]]: both year of birth  (%s / %s) and year of death (%s / %s) confirmed by user' % (artist.get(u'item'),
                                                                                                                                 artist.get(u'yob'),
                                                                                                                                 yobpinakothek,
                                                                                                                                 artist.get(u'yod'),
                                                                                                                                 yodpinakothek,)
                choice = pywikibot.input_choice(u'Do you add it anyway?', [('Yes', 'y'), ('No', 'n'),], default='N')
                if choice==u'y':
                    newclaim = pywikibot.Claim(repo, u'P4025')
                    newclaim.setTarget(artist.get(u'creatorid'))
                    pywikibot.output('Adding %(creatorid)s claim to %(creator)s' % artist)
                    item.addClaim(newclaim, summary=summary)

    else:
        print u'No match'
        print artist


def main(*args):

    gen = getPossibleArtistsGenerator()

    repo = pywikibot.Site().data_repository()
    # Not sure what is wrong with the website, but HTTPS setup is really slow and getting the wrong certificate
    # Just put everything in one session to not have to do that each time
    session = requests.Session()

    for artist in  gen:
        processArtist(repo, session, artist)


if __name__ == "__main__":
    main()