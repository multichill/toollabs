#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import missing data from RKDartists ( https://rkd.nl/en/explore/artists/ )

First it does a (SPARQL) query to find wikidata items that miss something relevant.
Bot will try to find the missing info

This should make https://www.wikidata.org/wiki/Wikidata:Database_reports/Constraint_violations/P650 shorter

"""
import pywikibot
from pywikibot import pagegenerators
import requests
import re
import datetime

class RKDArtistsImporterBot:
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
            if u'P650' not in claims:
                pywikibot.output(u'No RKDArtists found, skipping')
                continue

            rkdartistsid = claims.get(u'P650')[0].getTarget()
            rkdartistsurl = u'https://api.rkd.nl/api/record/artists/%s?format=json' % (rkdartistsid,)
            refurl = u'https://rkd.nl/explore/artists/%s' % (rkdartistsid,)

            # Do some checking if it actually exists?
            rkdartistsPage = requests.get(rkdartistsurl, verify=False)
            rkdartistsJson = rkdartistsPage.json()

            if rkdartistsJson.get('content') and rkdartistsJson.get('content').get('message'):
                pywikibot.output(u'Something went wrong, got "%s" for %s, skipping' % (rkdartistsJson.get('content').get('message'),
                                                                                       rkdartistsid))
                continue

            rkdartistsdocs = rkdartistsJson.get(u'response').get(u'docs')[0]

            if u'P21' not in claims:
                self.addGender(itempage, rkdartistsdocs, refurl)
            if u'P106' not in claims:
                self.addOccupation(itempage, rkdartistsdocs, refurl)
            if u'P569' not in claims:
                self.addDateOfBirth(itempage, rkdartistsdocs, refurl)
            if u'P570' not in claims:
                self.addDateOfDeath(itempage, rkdartistsdocs, refurl)
            if u'P19' not in claims:
                self.addPlaceOfBirth(itempage, rkdartistsdocs, refurl)
            if u'P27' not in claims and (u'P569' in claims or u'P570' in claims):
                self.addCountry(itempage, rkdartistsdocs, refurl)


    def addGender(self, itempage, rkdartistsdocs, refurl):
        newclaim = None
        if rkdartistsdocs.get('geslacht'):
            if rkdartistsdocs.get('geslacht')==u'm':
                newclaim = self.addItemStatement(itempage, u'P21', u'Q6581097')
                self.addReference(itempage, newclaim, refurl)
            elif rkdartistsdocs.get('geslacht')==u'v':
                newclaim = self.addItemStatement(itempage, u'P21', u'Q6581072')
                self.addReference(itempage, newclaim, refurl)
            else:
                pywikibot.output(u'Found weird RKD  gender: %s' % (rkdartistsdocs.get('geslacht'),))

    def addOccupation(self, itempage, rkdartistsdocs, refurl):
        occupations = { 2 : u'Q33231', # photographer
                        6 : u'Q1028181', # painter
                        7 : u'Q15296811', # draftsman -> draughtsperson
                        12 : u'Q1281618', # sculptor
                        31 : u'Q644687', # illustrator
                        40 : u'Q329439', # engraver (printmaker) -> engraver
                        43 : u'Q42973', # architect
                        48 : u'Q1925963', # graphic artist
                        95 : u'Q1114448', # cartoonist
                        97 : u'Q10694573', # textile artist
                        126 : u'Q3501317', # fashion designer
                        163 : u'Q16947657', # lithographer
                        232 : u'Q18074503', # installation artist
                        324 : u'Q17505902', # watercolorist
                        363 : u'Q21550646', # glass painter
                        496 : u'Q7541856', # ceramicist
                        597 : u'Q10862983', # etcher
                        1784 : u'Q20857490', # pastelist
                        3115 : u'Q5322166', # designer
                        45116 : u'Q3391743', # artist -> visual artist
                        45297 : u'Q2519376', # jewelry designer
                        }
        for occupationid in rkdartistsdocs.get('kwalificatie_lref'):
            if occupationid in occupations:
                newclaim = self.addItemStatement(itempage, u'P106', occupations.get(occupationid))
                self.addReference(itempage, newclaim, refurl)

    def addDateOfBirth(self, itempage, rkdartistsdocs, refurl):
        '''
        Will add the date of birth if the data is available and not a range
        :param itempage: The ItemPage to update
        :param rkdartistsdocs: The json with the RKD information
        :param refurl: The url to add as reference
        :return:
        '''
        if rkdartistsdocs.get('geboortedatum_begin') and \
           rkdartistsdocs.get('geboortedatum_eind') and \
           rkdartistsdocs.get('geboortedatum_begin')==rkdartistsdocs.get('geboortedatum_eind'):
            datestring = rkdartistsdocs.get('geboortedatum_begin')
            self.addDateProperty(itempage, datestring, u'P569', refurl)

    def addDateOfDeath(self, itempage, rkdartistsdocs, refurl):
        '''
        Will add the date of death if the data is available and not a range
        :param itempage: The ItemPage to update
        :param rkdartistsdocs: The json with the RKD information
        :param refurl: The url to add as reference
        :return:
        '''
        if rkdartistsdocs.get('sterfdatum_begin') and \
                rkdartistsdocs.get('sterfdatum_eind') and \
                        rkdartistsdocs.get('sterfdatum_begin')==rkdartistsdocs.get('sterfdatum_eind'):
            datestring = rkdartistsdocs.get('sterfdatum_begin')
            self.addDateProperty(itempage, datestring, u'P570', refurl)

    def addDateProperty(self, itempage, datestring, property, refurl):
        '''
        Try to find a valid date and add it to the itempage using property
        :param itempage: The ItemPage to update
        :param datestring: The string containing the date
        :param property: The property to add (for example date of birth or date of death)
        :param refurl: The url to add as reference
        :return:
        '''
        dateregex = u'^(?P<year>\d\d\d\d)-(?P<month>\d\d)-(?P<day>\d\d)$'
        monthregex = u'^(?P<year>\d\d\d\d)-(?P<month>\d\d)$'
        yearregex = u'^(?P<year>\d\d\d\d)$'

        datematch = re.match(dateregex, datestring)
        monthmatch = re.match(monthregex, datestring)
        yearmatch = re.match(yearregex, datestring)

        newdate = None
        if datematch:
            newdate = pywikibot.WbTime( year=int(datematch.group(u'year')),
                                        month=int(datematch.group(u'month')),
                                        day=int(datematch.group(u'day')))
        elif monthmatch:
            newdate = pywikibot.WbTime( year=int(monthmatch.group(u'year')),
                                        month=int(monthmatch.group(u'month')))
        elif yearmatch:
            newdate = pywikibot.WbTime( year=int(yearmatch.group(u'year')))
        else:
            return False

        newclaim = pywikibot.Claim(self.repo, property)
        newclaim.setTarget(newdate)
        itempage.addClaim(newclaim)
        self.addReference(itempage, newclaim, refurl)

    def addPlaceOfBirth(self, itempage, rkdartistsdocs, refurl):
        '''
        TODO: Implement
        :param itempage:
        :param rkdartistsdocs:
        :param refurl:
        :return:
        '''
        return

    def addPlaceOfDeath(self, itempage, rkdartistsdocs, refurl):
        '''
        TODO: Implement
        :param itempage:
        :param rkdartistsdocs:
        :param refurl:
        :return:
        '''
        return

    def addCountry(self, itempage, rkdartistsdocs, refurl):
        '''
        Add the country of citizenship.
        Do check if the country already existed based on the inception of the country and dob and dod
        :param itempage: The ItemPage to update
        :param rkdartistsdocs: The json with the RKD information
        :param refurl: The url to add as reference
        :return:
        '''
        nationality = { 104 : u'Q38', # Italian -> Italy
                        174 : u'Q159', # Russian -> Russia
                        184 : u'Q29', # Spanish -> Spain
                        191 : u'Q36', # Polish -> Poland
                        226 : u'Q142', # French -> France
                        262 : u'Q145', # England -> United Kingdom
                        686 : u'Q16', # Canadian -> Canada
                        1143 : u'Q213', # Czech -> Czech Republic
                        92956 : u'Q29999', # Dutch -> Kingdom of the Netherlands
                        #92957 : u'', # North Netherlandish ->
                        #92959 : u'Q6581823', # South Netherlandish -> Southern Netherlands
                        80198 : u'Q30', # American -> United States of America
                        1243 : u'Q408', # Australian -> Australia
                        80684 : u'Q145', # British -> United Kingdom
                        53 : u'Q183', # German -> Germany
                        92958 : u'Q31', # Belgian -> Belgium
                        }
        data = itempage.get()
        claims = data.get('claims')
        dateofbirth = False
        dateofdeath = False
        periodok = False
        if u'P569' in claims:
            dateofbirth = claims.get(u'P569')[0].getTarget()
        if u'P570' in claims:
            dateofdeath = claims.get(u'P570')[0].getTarget()
        if not rkdartistsdocs.get('nationaliteit_lref') or \
                        rkdartistsdocs.get('nationaliteit_lref')[0] not in nationality:
            return False

        countryitemtitle = nationality.get(rkdartistsdocs.get('nationaliteit_lref')[0])
        countryitem = pywikibot.ItemPage(self.repo, countryitemtitle)
        countrydata = countryitem.get()
        countryclaims = countrydata.get('claims')

        # If the country has no inception (like France), country must be ok
        if u'P571' not in countryclaims:
            periodok = True
        else:
            countryinception = countryclaims.get(u'P571')[0].getTarget()
            if dateofbirth and countryinception < dateofbirth:
                periodok = True
            elif dateofdeath and countryinception < dateofdeath:
                periodok = True

        if not periodok:
            pywikibot.output(u'Not adding country')
            return False

        newclaim = self.addItemStatement(itempage, u'P27', countryitemtitle)
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


def main():
    """
    Main function. Grab a generator and pass it to the bot to work on
    """
    query = u"""SELECT DISTINCT ?item {
  {
	?item wdt:P650 ?value .
	?item wdt:P31 wd:Q5 . # Needs to be human
	MINUS { ?item wdt:P21 [] . # No gender
            ?item wdt:P106 [] . # No occupation
            ?item wdt:P569 [] . # No date of birth
           } .
} UNION {
  ?item wdt:P650 [] .
  ?item p:P569 ?birthclaim .
  MINUS { ?item p:P27 [] } # No country of citizenship
  ?birthclaim ps:P569 ?birth .
  FILTER(?birth > "+1900-00-00T00:00:00Z"^^xsd:dateTime) .
} UNION {
  ?item wdt:P650 [] .
  ?item p:P569 ?birthclaim .
  MINUS { ?item p:P570 [] } # No date of death
  ?birthclaim ps:P569 ?birth .
  FILTER(?birth < "+1900-00-15T00:00:00Z"^^xsd:dateTime)
}
}"""
    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    rkdArtistsImporterBot = RKDArtistsImporterBot(generator)
    rkdArtistsImporterBot.run()

if __name__ == "__main__":
    main()
