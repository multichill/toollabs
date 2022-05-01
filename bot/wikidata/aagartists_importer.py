#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import missing data from the Auckland Art Gallery ( http://www.aucklandartgallery.com/ )

First it does a (SPARQL) query to find wikidata items that miss something relevant.
Bot will try to find the missing info

This should make https://www.wikidata.org/wiki/Wikidata:Database_reports/Constraint_violations/P3372 shorter

"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import requests
import re
import datetime
import time

class AAGArtistsImporterBot:
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
            if u'P3372' not in claims:
                pywikibot.output(u'No  Auckland Art Gallery artist ID (P3372) found, skipping')
                continue

            aucklandid = claims.get(u'P3372')[0].getTarget()
            aucklandurl = u'http://www.aucklandartgallery.com/explore-art-and-ideas/artist/%s/' % (aucklandid,)
            aucklandPage = requests.get(aucklandurl, verify=False)

            if u'P21' not in claims:
                self.addGender(itempage, aucklandPage.text, aucklandurl)
            # Occupation is not available
            # if u'P106' not in claims:
            #     self.addOccupation(itempage, rkdartistsdocs, refurl)
            if u'P569' not in claims:
                self.addDateOfBirth(itempage, aucklandPage.text, aucklandurl)
            if u'P570' not in claims:
                self.addDateOfDeath(itempage, aucklandPage.text, aucklandurl)
            #if u'P19' not in claims:
            #    self.addPlaceOfBirth(itempage, aucklandPage.text, aucklandurl)
            #if u'P20' not in claims:
            #    self.addPlaceOfDeath(itempage, aucklandPage.text, aucklandurl)

            if u'P27' not in claims:
                self.addCountry(itempage, aucklandPage.text, aucklandurl)
        print self.missingcountries


    def addGender(self, itempage, text, refurl):
        newclaim = None

        regex = u'\<dt\>Gender\<\/dt\>\s*\n\s*\<dd\>(Male|Female)\<\/dd\>'

        match = re.search(regex, text)
        if match:
            if match.group(1) == u'Male':
                newclaim = self.addItemStatement(itempage, u'P21', u'Q6581097')
                self.addReference(itempage, newclaim, refurl)
            elif match.group(1) == u'Female':
                newclaim = self.addItemStatement(itempage, u'P21', u'Q6581072')
                self.addReference(itempage, newclaim, refurl)


    def addDateOfBirth(self, itempage, text, refurl):
        newclaim = None
        regex = u'\<dt\>Date of birth\<\/dt\>\s*\n\s*\<dd\>(\d{4,4})\<\/dd\>'
        match = re.search(regex, text)
        if match:
            self.addDateProperty(itempage, match.group(1), u'P569', refurl)

    def addDateOfDeath(self, itempage, text, refurl):
        newclaim = None
        regex = u'\<dt\>Date of death\<\/dt\>\s*\n\s*\<dd\>(\d{4,4})\<\/dd\>'
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

    def addCountry(self, itempage, text, refurl):

        countries = { u'American' : u'Q30',
                      u'Argentinian' : u'Q414',
                      u'Austrian' : u'Q30',
                      u'Australian' : u'Q408',
                      u'British' : u'Q145',
                      u'Croatian' : u'Q224',
                      u'Czech' : u'Q213',
                      u'Dutch' : u'Q29999',
                      u'English' : u'Q145',
                      u'Estonian' : u'Q191',
                      u'Flemish' : u'Q31',
                      u'French' : u'Q142',
                      u'German' : u'Q183',
                      u'Irish' : u'Q27',
                      u'Japanese' : u'Q17',
                      u'Italian' : u'Q38',
                      u'Korean' : u'Q884',
                      u'Lithuanian' : u'Q37',
                      u'New Zealander' : u'Q664',
                      u'Polish' : u'Q36',
                      u'Russian' : u'Q159',
                      u'Spanish' : u'Q29',
                      u'Swedish' : u'Q34',
                      u'Swiss' : u'Q39',
                      u'Turkish' : u'Q43',
                      }
        newclaim = None
        regex = u'\<dt\>Nationality\<\/dt\>\s*\n\s*\<dd\>([^\<]+)\<\/dd\>'
        match = re.search(regex, text)
        if match:
            for country in match.group(1).split(','):
                country = country.strip()
                if country not in countries:
                    print u'NOT FOUND COUNTRY!'
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


class RKDArtistsCreatorBot:
    """
    A bot to enrich humans on Wikidata
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields ItemPage objects.

        """
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

    def getArtistsGenerator(self):
        '''
        Generate a bunch of artists from RKD.
        '''
        limit = 2
        #baseurl = u'https://api.rkd.nl/api/search/artists?filters[kwalificatie]=painter&fieldset=detail&format=json&rows=%s&start=%s'
        baseurl = u'https://api.rkd.nl/api/search/artists?fieldset=detail&format=json&rows=%s&start=%s'


        for i in range(60000, 361707, limit):

            url = baseurl % (limit, i)
            #print url
            rkdartistsApiPage = requests.get(url, verify=False)
            rkdartistsApiPageJson = rkdartistsApiPage.json()
            #print rkdartistsApiPageJson
            if rkdartistsApiPageJson.get('content') and rkdartistsApiPageJson.get('content').get('message'):
                pywikibot.output(u'Something went wrong')
                continue

            for rkdartistsdocs in rkdartistsApiPageJson.get('response').get('docs'):
                yield rkdartistsdocs

    def filterArtists(self, generator):
        """
        Starts the robot.
        """
        for rkdartistsdocs in generator:
            if rkdartistsdocs.get('priref') in self.currentrkd:
                pywikibot.output(u'Already got %s on %s' % (rkdartistsdocs.get('priref'),
                                                            self.currentrkd.get(rkdartistsdocs.get('priref'))))
                continue
            if rkdartistsdocs.get(u'results_in_other_databases') and \
                rkdartistsdocs.get(u'results_in_other_databases').get(u'images_kunstenaar'):
                number = rkdartistsdocs.get(u'results_in_other_databases').get(u'images_kunstenaar').get('count')
                if number > 0:
                    print rkdartistsdocs.get('kwalificatie')
                    if u'schilder' in rkdartistsdocs.get('kwalificatie'):
                        yield rkdartistsdocs

    def procesArtist(self, rkdartistsdocs):
        """
        Process a single artist. If it hits one of the creator criteria, create it
        :param rkdartistsdocs:
        :return:
        """
        summary = u''
        if rkdartistsdocs.get('priref') in self.currentrkd:
            pywikibot.output(u'Already got %s on %s' % (rkdartistsdocs.get('priref'),
                                                        self.currentrkd.get(rkdartistsdocs.get('priref'))))
            return False
        print rkdartistsdocs.get('priref')
        number = -1
        if rkdartistsdocs.get(u'results_in_other_databases') and \
                rkdartistsdocs.get(u'results_in_other_databases').get(u'images_kunstenaar').get('count'):
            number = rkdartistsdocs.get(u'results_in_other_databases').get(u'images_kunstenaar').get('count')
        if number > 25:
            summary = u'Creating artist based on RKD: Artist has more than 25 works in RKDimages'
            return self.createartist(rkdartistsdocs, summary)
        # Focus on painters here
        if 'schilder' in rkdartistsdocs.get('kwalificatie'):
            if 'Koninklijke subsidie voor vrije schilderkunst' in rkdartistsdocs.get('winnaar_van_prijs'):
                summary = u'Creating artist based on RKD: Painter won the Royal Prize for Painting'
                return self.createartist(rkdartistsdocs, summary)
            # Could add more prizes here
            if number > 5:
                summary = u'Creating artist based on RKD: Painter has more than 5 works in RKDimages'
                return self.createartist(rkdartistsdocs, summary)
            if number > 0 and rkdartistsdocs.get('geboortedatum_begin') and rkdartistsdocs.get('geboorteplaats'):
                summary = u'Creating artist based on RKD: Painter with works in RKDimages and date and place of birth known'
                return self.createartist(rkdartistsdocs, summary)
            #summary = u'Stresstest'
            #return self.createartist(rkdartistsdocs, summary)
        return None

    def createartist(self, rkdartistsdocs, summary):
        """
        The magic create function
        :param rkdartistsdocs:
        :param summary:
        :return:
        """

        langs = [u'de', u'en', u'es', u'fr', u'nl']

        data = {'labels': {},
                'aliases': {},
                }
        kunstenaarsnaam = rkdartistsdocs.get('virtualFields').get('hoofdTitel').get('kunstenaarsnaam')
        if kunstenaarsnaam.get('label') == u'Voorkeursnaam':
            for lang in langs:
                data['labels'][lang] = {'language': lang, 'value': kunstenaarsnaam.get('contents')}

            spellingsvarianten = rkdartistsdocs.get('virtualFields').get('naamsvarianten').get('contents').get('spellingsvarianten').get('contents')
            aliases = []
            for spellingsvariant in spellingsvarianten:
                name = spellingsvariant
                if u',' in name:
                    (surname, sep, firstname) = name.partition(u',')
                    name = u'%s %s' % (firstname.strip(), surname.strip(),)
                aliases.append(name)
            if aliases:
                for lang in langs:
                    data['aliases'][lang]=[]
                    for alias in aliases:
                        data['aliases'][lang].append({'language': lang, 'value': alias})

            print data

        priref = rkdartistsdocs.get('priref')

        identification = {}
        pywikibot.output(summary)

        # No need for duplicate checking
        result = self.repo.editEntity(identification, data, summary=summary)
        artistTitle = result.get(u'entity').get('id')

        # Wikidata is sometimes lagging. Wait for 10 seconds before trying to actually use the item
        time.sleep(10)

        artistItem = pywikibot.ItemPage(self.repo, title=artistTitle)

        # Add to self.artworkIds so that we don't create dupes
        self.currentrkd[priref]=artistTitle

        # Add human
        humanitem = pywikibot.ItemPage(self.repo,u'Q5')
        instanceclaim = pywikibot.Claim(self.repo, u'P31')
        instanceclaim.setTarget(humanitem)
        artistItem.addClaim(instanceclaim)

        # Add the id to the item so we can get back to it later
        newclaim = pywikibot.Claim(self.repo, u'P650')
        newclaim.setTarget(unicode(priref))
        pywikibot.output('Adding new RKDartists ID claim to %s' % artistItem)
        artistItem.addClaim(newclaim)

        # Force an update so everything is available for the next step
        artistItem.get(force=True)

        return artistItem

    def run(self):
        """
        Starts the robot.
        """
        for rkdartistsdocs in self.getArtistsGenerator():
            artist = self.procesArtist(rkdartistsdocs)
            if artist:
                yield artist


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
            ?item wdt:P3372 ?value .
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
        generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    aagArtistsImporterBot = AAGArtistsImporterBot(generator)
    aagArtistsImporterBot.run()

if __name__ == "__main__":
    main()
