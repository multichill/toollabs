#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Tool to add creators to painting items of Wikidata that do have an RKDimages (P350) link

See https://www.wikidata.org/wiki/Wikidata:WikiProject_sum_of_all_paintings/Missing_creator_with_RKDimages_link

"""
import pywikibot
from pywikibot import pagegenerators
import requests
import pywikibot.data.sparql
import re

class RKDimagesCreatorRobot():

    """A bot to import artnet ids from Wikipedia"""

    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields ItemPage objects.

        """
        self.generator = generator
        self.currentrkd = self.rkdArtistsOnWikidata()
        self.repo = pywikibot.Site().data_repository()

    def rkdArtistsOnWikidata(self):
        '''
        Just return all the RKD images as a dict
        :return: Dict
        '''
        result = {}
        sq = pywikibot.data.sparql.SparqlQuery()
        query = u'SELECT ?item ?id WHERE { ?item wdt:P650 ?id }'
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[int(resultitem.get('id'))] = qid
        return result

    def run(self):
        """
        Starts the robot.
        """
        for itempage in self.generator:
            pywikibot.output(u'Working on %s' % (itempage.title(),))
            if not itempage.exists():
                pywikibot.output(u'Item does not exist, skipping')
                continue

            data = itempage.get()
            claims = data.get('claims')

            # Do some checks so we are sure we found exactly one inventory number and one collection
            if u'P350' not in claims:
                pywikibot.output(u'No RKDArtists found, skipping')
                continue

            if u'P170' in claims:
                pywikibot.output(u'Already has a creator, done')
                continue

            rkdimagesid = claims.get(u'P350')[0].getTarget()

            imagePage = requests.get('https://api.rkd.nl/api/record/images/%s?format=json' % (rkdimagesid,), verify=False)
            imagejson = imagePage.json()

            if imagejson.get('content') and imagejson.get('content').get('message'):
                pywikibot.output(u'Something went wrong, got "%s" for %s, skipping' % (imagejson.get('content').get('message'),
                                                                                       imagejson))
                continue

            if not imagejson.get(u'response').get(u'docs')[0].get(u'toeschrijving'):
                continue
            toeschrijving = imagejson.get(u'response').get(u'docs')[0].get(u'toeschrijving')[0]
            if not toeschrijving.get(u'status') == u'huidig':
                continue
            if toeschrijving.get(u'kwalificatie'):
                pywikibot.output(u'Kan nog geen kwalificaties aan')
                print toeschrijving
                continue

            #print toeschrijving

            rkdartistsid = int(toeschrijving.get(u'naam_linkref'))
            if rkdartistsid not in self.currentrkd:
                pywikibot.output(u'RKDArtists id %s does not have a Wikidata item yet, skipping' % (rkdartistsid,))
                continue

            creatoritem = pywikibot.ItemPage(self.repo, self.currentrkd.get(rkdartistsid))
            creatordata = creatoritem.get()
            creatorclaims = creatordata.get('claims')
            if not data.get(u'descriptions').get(u'en'):
                # No description
                continue
            if not creatordata.get(u'labels').get(u'en'):
                # No painter label
                continue
            pywikibot.output(u'')
            pywikibot.output(u'Url of painting item http://www.wikidata.org/entity/%s' % (itempage.title(),))
            pywikibot.output(u'RKDimages https://rkd.nl/explore/images/%s' % (rkdimagesid,))
            pywikibot.output(u'Url of creator item http://www.wikidata.org/entity/%s' % (creatoritem.title(),))
            pywikibot.output(u'RKDartists https://rkd.nl/en/explore/artists/%s' % (rkdartistsid,))
            pywikibot.output(u'')
            pywikibot.output(u'Painting item description: "%s"' % (data.get(u'descriptions').get(u'en'),))
            pywikibot.output(u'Creator item label: "%s"' % (creatordata.get(u'labels').get(u'en'),))

            choice = pywikibot.input_choice(u'Do you want to add this creator?', [('Yes', 'y'), ('No', 'n'),], default='N')
            if choice==u'y':
                newclaim = pywikibot.Claim(self.repo, u'P170')
                newclaim.setTarget(creatoritem)
                summary = 'Adding creator based on RKDimages'
                pywikibot.output(summary)
                itempage.addClaim(newclaim, summary=summary)


            #rkdartistsurl = u'https://api.rkd.nl/api/record/artists/%s?format=json' % (rkdartistsid,)

            # Do some checking if it actually exists?
            #rkdartistsPage = requests.get(rkdartistsurl, verify=False)
            #rkdartistsJson = rkdartistsPage.json()

            #if rkdartistsJson.get('content') and rkdartistsJson.get('content').get('message'):
            #    pywikibot.output(u'Something went wrong, got "%s" for %s, skipping' % (rkdartistsJson.get('content').get('message'),
            #                                                                           rkdartistsid))
            #    continue
            #
            #rkdartistsdocs = rkdartistsJson.get(u'response').get(u'docs')[0]
            #print rkdartistsdocs

def getPaintingGenerator():
    '''
    Do a SPARQL query to grab paintings with RKDimages and description to work on
    :return: Dict
    '''
    result = {}
    query = u"""SELECT ?item ?rkdid ?itemdesc WHERE {
  ?item wdt:P31 wd:Q3305213 .
  ?item wdt:P350 ?rkdid .
  MINUS { ?item p:P170 [] }  .
  ?item schema:description ?itemdesc.
  FILTER(LANG(?itemdesc) = "en")
} LIMIT 1000"""
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        paintingitem = {}
        paintingitem[u'item'] = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        paintingitem[u'rkdid'] = resultitem.get('rkdid')
        paintingitem[u'itemdesc'] = resultitem.get('itemdesc')
        yield paintingitem


def processPainting(repo, painting):
    """
    Process on artist and try to add a link
    :param artist:
    :return:
    """
    imagePage = requests.get('https://api.rkd.nl/api/record/images/%s?format=json' % (painting.get('rkdid'),), verify=False)
    imagejson = imagePage.json()

    if imagejson.get(u'response').get(u'docs')[0].get(u'toeschrijving'):
        toeschrijving = imagejson.get(u'response').get(u'docs')[0].get(u'toeschrijving')[0]
        if toeschrijving.get(u'status') == u'huidig':
            if toeschrijving.get(u'kwalificatie'):
                print u'Kan nog geen walificaties aan'
                print toeschrijving
                return
            else:
                print toeschrijving

    """

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
    """


def main(*args):

    gen = getPaintingGenerator()

    repo = pywikibot.Site().data_repository()
    query = u"""SELECT ?item ?rkdid ?itemdesc WHERE {
  ?item wdt:P31 wd:Q3305213 .
  ?item wdt:P350 ?rkdid .
  MINUS { ?item p:P170 [] }  .
  ?item schema:description ?itemdesc.
  FILTER(LANG(?itemdesc) = "en")
} LIMIT 1000"""
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    imagesCreatorRobot = RKDimagesCreatorRobot(generator)
    imagesCreatorRobot.run()
    # Not sure what is wrong with the website, but HTTPS setup is really slow and getting the wrong certificate
    # Just put everything in one session to not have to do that each time
    #session = requests.Session()

    #for painting in  gen:
    #    processPainting(repo, painting)


if __name__ == "__main__":
    main()