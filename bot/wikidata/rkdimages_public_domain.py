#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
RKDimages started providing public domain images and marking them as such.
See for example https://rkd.nl/nl/explore/images/249868 / https://api.rkd.nl/api/record/images/249868?format=json&language=nl

Loop over all the items on Wikidata with RKDimages, but without an image (and some additional filter).
If a public domain image is found, add the suggestion link.

"""
import pywikibot
from pywikibot import pagegenerators
import requests
import pywikibot.data.sparql
import re

class RKDimagesPublicDomain():

    """A bot to import artnet ids from Wikipedia"""

    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields ItemPage objects.

        """
        self.generator = generator
        #self.currentrkd = self.rkdArtistsOnWikidata()
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

            if u'P18' in claims:
                pywikibot.output(u'Already has an image, done')
                continue

            if u'P4765' in claims:
                pywikibot.output(u'Already has an image suggestion, done')
                continue

            rkdimagesid = claims.get(u'P350')[0].getTarget()
            rkdimagesurl = u'https://rkd.nl/nl/explore/images/%s' % (rkdimagesid,)

            imagePage = requests.get('https://api.rkd.nl/api/record/images/%s?format=json&language=nl' % (rkdimagesid,), verify=False)
            try:
                imagejson = imagePage.json()
            except ValueError:
                pywikibot.output(u'No valid json found for %s' % (rkdimagesurl,))
                continue

            if imagejson.get('content') and imagejson.get('content').get('message'):
                pywikibot.output(u'Something went wrong, got "%s" for %s, skipping' % (imagejson.get('content').get('message'),
                                                                                       imagejson))
                continue

            if not imagejson.get(u'response').get(u'docs')[0].get(u'standplaats'):
                continue
            # Just get the first one
            standplaats = imagejson.get(u'response').get(u'docs')[0].get(u'standplaats')[0]
            if not standplaats.get('licence') or not standplaats.get('licence')==u'pub-dom':
                pywikibot.output(u'No valid license found, skipping')
                continue
            afbeeldingsnummer = standplaats.get('afbeeldingsnummer')

            if not imagejson.get(u'response').get(u'docs')[0].get(u'afbeeldingsnummer_rkd_picturae_mapping'):
                continue
            picturae_id = imagejson.get(u'response').get(u'docs')[0].get(u'afbeeldingsnummer_rkd_picturae_mapping').get(afbeeldingsnummer)

            if not picturae_id:
                continue

            imageurl = u'https://images.rkd.nl/rkd/thumb/fullsize/%s.jpg' % (picturae_id,)

            print (imageurl)

            descriptioncontents = imagejson.get(u'response').get(u'docs')[0].get(u'virtualFields').get(u'introduction').get(u'contents')
            title = descriptioncontents.get(u'benaming').strip()
            creator = descriptioncontents.get(u'toeschrijving').strip()
            print (title)
            print (creator)

            newclaim = pywikibot.Claim(self.repo, u'P4765')
            newclaim.setTarget(imageurl)
            pywikibot.output('Adding commons compatible image available at URL claim to %s' % (itempage.title(),))
            itempage.addClaim(newclaim)

            # JPEG
            newqualifier = pywikibot.Claim(self.repo, u'P2701')
            newqualifier.setTarget(pywikibot.ItemPage(self.repo, u'Q2195'))
            newclaim.addQualifier(newqualifier)

            # Source link
            newqualifier = pywikibot.Claim(self.repo, u'P2699')
            newqualifier.setTarget(rkdimagesurl)
            newclaim.addQualifier(newqualifier)

            # Operated by link
            newqualifier = pywikibot.Claim(self.repo, u'P137')
            newqualifier.setTarget(pywikibot.ItemPage(self.repo, u'Q758610'))
            newclaim.addQualifier(newqualifier)

            # Title qualifier
            if title:
                nltitle = pywikibot.WbMonolingualText(title, u'nl')
                newqualifier = pywikibot.Claim(self.repo, u'P1476')
                newqualifier.setTarget(nltitle)
                newclaim.addQualifier(newqualifier)

            # Author name string qualifier
            if creator:
                newqualifier = pywikibot.Claim(self.repo, u'P2093')
                newqualifier.setTarget(creator)
                newclaim.addQualifier(newqualifier)


def main(*args):


    repo = pywikibot.Site().data_repository()
    query = u"""SELECT ?item WHERE {
  ?item wdt:P350 ?rkdimage .
  MINUS { ?item wdt:P18 ?image } .
  MINUS { ?item wdt:P4765 ?ccimage } .
  ?item wdt:P31 wd:Q3305213 .
  MINUS { ?item wdt:P170 ?creator . ?creator wdt:P570 ?dod . FILTER(YEAR(?dod) > 1923) }
  MINUS { ?item wdt:P170 ?creator . ?creator wdt:P569 ?dob . FILTER(YEAR(?dob) > 1900) }
  MINUS { ?item wdt:P170 wd:Q4233718 . ?item wdt:P571 ?inception . FILTER(YEAR(?inception) > 1850) }
  ?item schema:dateModified ?modified
  } ORDER BY DESC(?modified)"""
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    imagesPublicDomainRobot = RKDimagesPublicDomain(generator)
    imagesPublicDomainRobot.run()

if __name__ == "__main__":
    main()