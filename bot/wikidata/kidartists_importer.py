#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import missing data from the Kunstindeks Danmark Artist  ( https://www.kulturarv.dk/kid/SoegKunstner.do )

First it does a (SPARQL) query to find wikidata items that miss something relevant.
Bot will try to find the missing info

This should make https://www.wikidata.org/wiki/Wikidata:Database_reports/Constraint_violations/P1138 shorter

"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import requests
import re
import datetime
import time

class KIDArtistsImporterBot:
    """
    A bot to enrich humans on Wikidata
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields ItemPage objects.

        """
        self.generator = generator
        self.repo = pywikibot.Site().data_repository()
        self.missingcountries = {}
        self.missingoccupations = {}

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
            if u'P1138' not in claims:
                pywikibot.output(u'No Kunstindeks Danmark Artist ID (P1138) found, skipping')
                continue

            kidid = claims.get(u'P1138')[0].getTarget()
            kidurl = u'https://www.kulturarv.dk/kid/VisKunstner.do?kunstnerId=%s' % (kidid,)
            kidPage = requests.get(kidurl) # , verify=False)

            if u'P21' not in claims:
                self.addGender(itempage, kidPage.text, kidurl)
            if u'P106' not in claims:
                 self.addOccupation(itempage, kidPage.text, kidurl)
            if u'P569' not in claims:
                self.addDateOfBirth(itempage, kidPage.text, kidurl)
            if u'P570' not in claims:
                self.addDateOfDeath(itempage, kidPage.text, kidurl)
            #if u'P19' not in claims:
            #    self.addPlaceOfBirth(itempage, kidPage.text, kidurl)
            #if u'P20' not in claims:
            #    self.addPlaceOfDeath(itempage, kidPage.text, kidurl)
            if u'P27' not in claims:
                self.addCountry(itempage, kidPage.text, kidurl)
        pywikibot.output(u'The list of missing occupations:')
        pywikibot.output(self.missingoccupations)
        pywikibot.output(u'The list of missing countries:')
        pywikibot.output(self.missingcountries)

    def addGender(self, itempage, text, refurl):
        newclaim = None

        regex = u'\<span class\=\"descr\"\>\<b\>Sex:\s*\<\/b\>[\s\r\n]+(male|female)[\s\r\n]+\<\/span\>'

        match = re.search(regex, text)
        if match:
            if match.group(1) == u'male':
                newclaim = self.addItemStatement(itempage, u'P21', u'Q6581097')
                self.addReference(itempage, newclaim, refurl)
            elif match.group(1) == u'female':
                newclaim = self.addItemStatement(itempage, u'P21', u'Q6581072')
                self.addReference(itempage, newclaim, refurl)


    def addOccupation(self, itempage, text, refurl):
        '''
        Add the occupation of the person
        :param itempage:
        :param text:
        :param refurl:
        :return:
        '''
        occupations = { u'arkitekt' : u'Q42973',
                        u'billedhugger' : u'Q1281618',
                        u'fotograf' : u'Q33231',
                        u'grafiker' : u'Q1925963',
                        u'installationskunstner' : u'Q18074503',
                        u'kobberstikker' : u'Q13365770',
                        u'litograf' : u'Q16947657',
                        u'maler' : u'Q1028181',
                        u'medaljør' : u'Q1708232',
                        u'tegner' : u'Q15296811',
                      }
        regex = u'\<span class\=\"descr\"\>\<b\>Occupation:\s*\<\/b\>([^\<]+)\<\/span\>'
        match = re.search(regex, text)
        if match:
            for occupation in match.group(1).split(','):
                occupation = occupation.strip().lower()
                if occupation:
                    if occupation not in occupations:
                        if not occupation in self.missingoccupations:
                            self.missingoccupations[occupation] = 0
                        self.missingoccupations[occupation] = self.missingoccupations[occupation] + 1
                    else:
                        newclaim = self.addItemStatement(itempage, u'P106', occupations[occupation])
                        self.addReference(itempage, newclaim, refurl)

    def addDateOfBirth(self, itempage, text, refurl):
        regex = u'\<span class\=\"descr\"\>\<b\>Born:\s*\<\/b\>([^\<]+)\<\/span\>'
        match = re.search(regex, text)
        if match:
            self.addDateProperty(itempage, match.group(1), u'P569', refurl)

    def addDateOfDeath(self, itempage, text, refurl):
        regex = u'\<span class\=\"descr\"\>\<b\>Died:\s*\<\/b\>([^\<]+)\<\/span\>'
        match = re.search(regex, text)
        if match:
            self.addDateProperty(itempage, match.group(1), u'P570', refurl)

    def addDateProperty(self, itempage, datestring, property, refurl):
        '''
        Try to find a valid date and add it to the itempage using property
        :param itempage: The ItemPage to update
        :param datestring: The string containing the date
        :param property: The property to add (for example date of birth or date of death)
        :param refurl: The url to add as reference
        :return:
        '''
        datestring = datestring.strip()

        dateregex = u'^(?P<day>\d\d)-(?P<month>\d\d)-(?P<year>\d\d\d\d)$'
        datelocationregex = u'^[^,]+,[\s\t\r\n]*(?P<day>\d\d)-(?P<month>\d\d)-(?P<year>\d\d\d\d)$'
        yearregex = u'^(?P<year>\d\d\d\d)$'
        yearlocationregex = u'^[^,]+,[\s\t\r\n]*(?P<year>\d\d\d\d)$'

        datematch = re.match(dateregex, datestring)
        datelocationmatch = re.match(datelocationregex, datestring)
        yearmatch = re.match(yearregex, datestring)
        yearlocationmatch = re.match(yearlocationregex, datestring)

        newdate = None
        if datematch:
            newdate = pywikibot.WbTime( year=int(datematch.group(u'year')),
                                        month=int(datematch.group(u'month')),
                                        day=int(datematch.group(u'day')))
        elif datelocationmatch:
            newdate = pywikibot.WbTime( year=int(datelocationmatch.group(u'year')),
                                        month=int(datelocationmatch.group(u'month')),
                                        day=int(datelocationmatch.group(u'day')))
        #elif monthmatch:
        #    newdate = pywikibot.WbTime( year=int(monthmatch.group(u'year')),
        #                                month=int(monthmatch.group(u'month')))
        elif yearmatch:
            newdate = pywikibot.WbTime( year=int(yearmatch.group(u'year')))
        elif yearlocationmatch:
            newdate = pywikibot.WbTime( year=int(yearlocationmatch.group(u'year')))
        else:
            #print datestring
            return False

        newclaim = pywikibot.Claim(self.repo, property)
        newclaim.setTarget(newdate)
        itempage.addClaim(newclaim)
        self.addReference(itempage, newclaim, refurl)

    def addCountry(self, itempage, text, refurl):

        countries = { u'American' : u'Q30',
                      u'Argentinian' : u'Q414',
                      u'Austrian' : u'Q30',
                      u'Australian' : u'Q408',
                      u'British' : u'Q145',
                      u'Croatian' : u'Q224',
                      u'Czech' : u'Q213',
                      u'Danish' : u'Q35',
                      u'Dutch' : u'Q29999',
                      u'English' : u'Q145',
                      u'Estonian' : u'Q191',
                      u'Finnish' : u'Q33',
                      u'Flemish' : u'Q31',
                      u'French' : u'Q142',
                      u'German' : u'Q183',
                      u'Irish' : u'Q27',
                      u'Japanese' : u'Q17',
                      u'Italian' : u'Q38',
                      u'Korean' : u'Q884',
                      u'Lithuanian' : u'Q37',
                      u'Netherlands' : u'Q29999',
                      u'New Zealander' : u'Q664',
                      u'Norwegian' : u'Q20',
                      u'Polish' : u'Q36',
                      u'Russian' : u'Q159',
                      u'Spanish' : u'Q29',
                      u'Swedish' : u'Q34',
                      u'Swiss' : u'Q39',
                      u'Turkish' : u'Q43',
                      }

        regex = u'\<span class\=\"descr\"\>\<b\>Nationality:\s*\<\/b\>([^\<]+)\<\/span\>'
        match = re.search(regex, text)
        if match:
            for country in match.group(1).split(','):
                country = country.strip()
                if country:
                    if country not in countries:
                        if not country in self.missingcountries:
                            self.missingcountries[country] = 0
                        self.missingcountries[country] = self.missingcountries[country] + 1
                    else:
                        newclaim = self.addItemStatement(itempage, u'P27', countries[country])
                        self.addReference(itempage, newclaim, refurl)

    def addItemStatement(self, item, pid, qid):
        '''
        Helper function to add a statement
        '''
        if not qid:
            return False

        claims = item.get().get('claims')
        if pid in claims:
            return

        newclaim = pywikibot.Claim(self.repo, pid)
        destitem = pywikibot.ItemPage(self.repo, qid)
        newclaim.setTarget(destitem)
        pywikibot.output(u'Adding %s->%s to %s' % (pid, qid, item))
        item.addClaim(newclaim)
        return newclaim
        #self.addReference(item, newclaim, url)

    def addReference(self, item, newclaim, url):
        """
        Add a reference with a retrieval url and todays date
        """
        pywikibot.output('Adding new reference claim to %s' % item)
        refurl = pywikibot.Claim(self.repo, u'P854') # Add url, isReference=True
        refurl.setTarget(url)
        refdate = pywikibot.Claim(self.repo, u'P813')
        today = datetime.datetime.today()
        date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
        refdate.setTarget(date)
        newclaim.addSources([refurl, refdate])


def main(*args):
    """
    Main function. Grab a generator and pass it to the bot to work on
    """
    create = False
    for arg in pywikibot.handle_args(args):
        if arg=='-create':
            create = True

    if create:
        pywikibot.output(u'Not implemented yet!')
        #rkdArtistsCreatorBot = RKDArtistsCreatorBot()
        #generator = rkdArtistsCreatorBot.run()
        return
    else:
        pywikibot.output(u'Going to try to expand existing artists')

        query = u"""SELECT DISTINCT ?item {
        {
            ?item wdt:P1138 ?value .
            ?item wdt:P31 wd:Q5 . # Needs to be human
            MINUS { ?item wdt:P21 [] . # No gender
                    ?item wdt:P27 [] . # No country of citizenship
                    ?item wdt:P106 [] . # No occupation
                    ?item wdt:P569 [] . # No date of birth
                   } .
        } UNION {
          ?item wdt:P3372 [] .
          ?item p:P569 ?birthclaim .
          MINUS { ?item p:P570 [] } # No date of death
          ?birthclaim ps:P569 ?birth .
          FILTER(?birth < "+1900-00-15T00:00:00Z"^^xsd:dateTime)
        }
        }"""
        repo = pywikibot.Site().data_repository()
        generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    kidArtistsImporterBot = KIDArtistsImporterBot(generator)
    kidArtistsImporterBot.run()

if __name__ == "__main__":
    main()
