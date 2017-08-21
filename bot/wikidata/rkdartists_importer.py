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
import pywikibot.data.sparql
import requests
import re
import datetime
import time

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
            if u'P20' not in claims:
                self.addPlaceOfDeath(itempage, rkdartistsdocs, refurl)
            # Disabled for now. WbTime comparison seems to contain bugs
            # Can be enabled when https://phabricator.wikimedia.org/T148280 is fixed
            #if u'P27' not in claims and (u'P569' in claims or u'P570' in claims):
            #    self.addCountry(itempage, rkdartistsdocs, refurl)


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
                        31823 : u'Q10732476', # kunstverzamelaar / art collector
                        31824 : u'Q3243461', # verzamelaar / collector
                        44385 : u'Q15472169', # mecenas / patron of the arts
                        45116 : u'Q3391743', # artist -> visual artist
                        45297 : u'Q2519376', # jewelry designer
                        57965 : u'Q16887133', # hoogwaardigheidsbekleder / dignitary
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
        Add the place of birth to the itempage
        :param itempage: The ItemPage to update
        :param rkdartistsdocs: The json with the RKD information
        :param refurl: The url to add as reference
        :return: Nothing, update the itempage in place
        '''
        if rkdartistsdocs.get('geboorteplaats_lref') and \
                rkdartistsdocs.get('geboorteplaats_lref')[0]:
            plaats_lref = rkdartistsdocs.get('geboorteplaats_lref')[0]
            self.addPlaceProperty(itempage, plaats_lref, u'P19', refurl)

    def addPlaceOfDeath(self, itempage, rkdartistsdocs, refurl):
        '''
        Add the place of death to the itempage
        :param itempage: The ItemPage to update
        :param rkdartistsdocs: The json with the RKD information
        :param refurl: The url to add as reference
        :return: Nothing, update the itempage in place
        '''
        if rkdartistsdocs.get('sterfplaats_lref') and \
                rkdartistsdocs.get('sterfplaats_lref')[0]:
            plaats_lref = rkdartistsdocs.get('sterfplaats_lref')[0]
            self.addPlaceProperty(itempage, plaats_lref, u'P20', refurl)

    def addPlaceProperty(self, itempage, plaats_lref, property, refurl):
        '''
        Add the place using property to the itempage
        :param itempage: The ItemPage to update
        :param plaats_lref: The rkd thesaurus id of the place
        :param property: The property to add
        :param refurl: The url to add as reference
        :return: Nothing, update the itempage in place
        '''
        places = { 1 : u'Q55', # Dutch -> Netherlands
                   3 : u'Q36600', # The Hague
                   11 : u'Q43631', # Leiden
                   29 : u'Q727', # Amsterdam
                   30 : u'Q34370', # Rotterdam
                   35 : u'Q749', # Groningen (stad)
                   36 : u'Q2766547', # Den Bosch
                   46 : u'Q1309', # Maastricht
                   52 : u'Q365', # Keulen
                   80 : u'Q803', # Utrecht
                   90 : u'Q10002', # Enschede
                   92 : u'Q52101', # Middelburg
                   100 : u'Q40844', # Breda
                   103 : u'Q9898', # Amstelveen
                   112 : u'Q9920', # Haarlem
                   118 : u'Q26421', # Dordrecht
                   120 : u'Q1199713', # Batavia
                   123 : u'Q1310', # Arnhem
                   134 : u'Q9832', # Eindhoven
                   149 : u'Q9871', # Tilburg
                   129 : u'Q90', # Parijs
                   182 : u'Q495', # Turin
                   193 : u'Q220', # Rome
                   195 : u'Q239', # Brussel
                   204 : u'Q279', # Modena
                   208 : u'Q1891', # Bologna
                   219 : u'Q2634', # Naples
                   220 : u'Q641', # Venice
                   221 : u'Q2044', # Florence
                   225 : u'Q992', # Amersfoort
                   223 : u'Q12892', # Antwerpen
                   236 : u'Q84', # London
                   245 : u'Q490', # Milaan
                   248 : u'Q16977290', # Alkmaar
                   257 : u'Q9799', # Heerlen
                   266 : u'Q134672', # Exeter
                   286 : u'Q1490', # Tokyo
                   287 : u'Q38', # Italië
                   293 : u'Q9783', # Roermond
                   304 : u'Q1741', # Vienna
                   334 : u'Q26296883', # Deventer
                   343 : u'Q1297', # Chicago
                   344 : u'Q23436', # Edinburgh
                   347 : u'Q1726', # München
                   355 : u'Q70', # Bern
                   380 : u'Q25390', # Leeuwarden
                   387 : u'Q1085', # Praag
                   392 : u'Q60', # New York City
                   411 : u'Q656', # Sint-Petersburg
                   424 : u'Q47887', # Nijmegen
                   425 : u'Q8818', # Valencia
                   450 : u'Q8717', # Sevilla
                   454 : u'Q159', # Rusland
                   455 : u'Q142', # Frankrijk
                   462 : u'Q2865', # Kassel
                   475 : u'Q1718', # Düsseldorf
                   480 : u'Q1296', # Gent
                   485 : u'Q78', # Basel
                   490 : u'Q64', # Berlin
                   520 : u'Q1781', # Boedapest
                   533 : u'Q1731', # Dresden
                   541 : u'Q4093', # Glasgow
                   557 : u'Q270', # Warsaw
                   573 : u'Q39121', # Leeds
                   599 : u'Q690', # Delft
                   601 : u'Q10056', # Zeist
                   650 : u'Q506745', # Rijswijk
                   659 : u'Q72', # Zürich
                   684 : u'Q1022', # Stuttgart
                   698 : u'Q1055', # Hamburg
                   714 : u'Q456', # Lyon
                   724 : u'Q3322237', # Venlo
                   750 : u'Q118958', # Leuven
                   754 : u'Q244327', # Gorinchem
                   762 : u'Q12994', # Brugge
                   764 : u'Q162022', # Mechelen
                   786 : u'Q71', # Genève
                   808 : u'Q1486', # Buenos Aires
                   835 : u'Q203312', # Ukkel
                   877 : u'Q2807', # Madrid
                   883 : u'Q33935', # Tel Aviv
                   887 : u'Q1715', # Hannover
                   900 : u'Q36405', # Aberdeen
                   914 : u'Q204709', # Schiedam
                   915 : u'Q62', # San Francisco
                   969 : u'Q9945', # Laren
                   974 : u'Q809821', # Voorburg
                   986 : u'Q9934', # Hilversum
                   1032 : u'Q9909', # Bussum
                   1041 : u'Q18419', # Brooklyn
                   1048 : u'Q2973', # Darmstadt
                   1053 : u'Q1449', # Genua
                   1084 : u'Q2090', # Nuremberg
                   1127 : u'Q2028', # Verona
                   1168 : u'Q131491', # Brighton
                   1173 : u'Q65', # Los Angeles
                   1174 : u'Q505601', # Wassenaar
                   1242 : u'Q3130', # Sydney
                   1276 : u'Q743535', # Chelsea
                   1330 : u'Q13298', # Graz
                   1349 : u'Q1794', # Frankfurt am Main
                   1367 : u'Q1735', # Innsbruck
                   1426 : u'Q1492', # Barcelona
                   1445 : u'Q2749', # Augsburg
                   1506 : u'Q10027', # Baarn
                   1597 : u'Q9908', # Bloemendaal
                   1636 : u'Q9906', # Blaricum
                   1650 : u'Q1754', # Stockholm
                   1729 : u'Q10006', # Hengelo
                   1763 : u'Q24826', # Liverpool
                   1774 : u'Q3992', # Luik
                   1785 : u'Q84125', # Gouda
                   1791 : u'Q192508', # Bergen op Zoom
                   1806 : u'Q18125', # Manchester
                   1901 : u'Q128147', # Hull
                   1993 : u'Q24879', # Bremen
                   2032 : u'Q1761', # Dublin
                   2095 : u'Q12996', # Oostende
                   2102 : u'Q1345', # Philadelphia
                   2124 : u'Q12995', # Kortrijk
                   2138 : u'Q766353', # Hampton
                   2140 : u'Q41262', # Nottingham
                   2431 : u'Q100', # Boston
                   2533 : u'Q211037', # Roeselare
                   2549 : u'Q208713', # Elsene
                   2606 : u'Q1040', # Karlsruhe
                   2637 : u'Q2256', # Birmingham
                   2774 : u'Q12887', # Schaarbeek
                   2812 : u'Q9901', # Bergen (Noord-Holland)
                   2959 : u'Q22889', # Bath
                   2976 : u'Q23154', # Bristol
                   3018 : u'Q130191', # Norwich
                   3399 : u'Q2079', # Leipzig
                   3754 : u'Q585', # Oslo
                   3902 : u'Q5092', # Baltimore
                   3910 : u'Q99', # Californië
                   5080 : u'Q3141', # Melbourne
                   5583 : u'Q288781', # Kensington
                   5671 : u'Q1757',# Helsinki
                   8112 : u'Q25287', # Göteborg
                   14643 : u'Q23666', # Groot-Brittannië
                   30433 : u'Q1425428', # Newcastle upon Tyne
                   32465 : u'Q30096', # Frederiksberg
                   41540 : u'Q1748', # Copenhagen
                   76789 : u'Q793', # Zwolle
                   78789 : u'Q13127', # Sint-Niklaas
                   }

        if not plaats_lref in places:
            return False
        placeitemtitle = places.get(plaats_lref)
        newclaim = self.addItemStatement(itempage, property, placeitemtitle)
        self.addReference(itempage, newclaim, refurl)

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
        start = 0 # 60000
        end = 1800 # 2608 # 361707
        limit = 2
        #baseurl = u'https://api.rkd.nl/api/search/artists?filters[kwalificatie]=painter&fieldset=detail&format=json&rows=%s&start=%s'
        #baseurl = u'https://api.rkd.nl/api/search/artists?fieldset=detail&format=json&rows=%s&start=%s'
        baseurl = u'https://api.rkd.nl/api/search/artists?filters[winnaar_van_prijs]=*&fieldset=detail&format=json&rows=%s&start=%s'

        for i in range(start, end, limit):

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
        # Create remaining people who won something
        if rkdartistsdocs.get('winnaar_van_prijs') and len(rkdartistsdocs.get('winnaar_van_prijs')) > 0:
            if len(rkdartistsdocs.get('winnaar_van_prijs'))==1:
                summary = u'Creating artist based on RKD: Person won the prize "%s"' % (rkdartistsdocs.get('winnaar_van_prijs')[0],)
            elif len(rkdartistsdocs.get('winnaar_van_prijs'))==2:
                summary = u'Creating artist based on RKD: Person won the prizes "%s" & "%s"' % (rkdartistsdocs.get('winnaar_van_prijs')[0],
                                                                                                rkdartistsdocs.get('winnaar_van_prijs')[1],)
            else:
                summary = u'Creating artist based on RKD: Person won %s prizes including "%s" & "%s"' % (len(rkdartistsdocs.get('winnaar_van_prijs')),
                                                                                                         rkdartistsdocs.get('winnaar_van_prijs')[0],
                                                                                                         rkdartistsdocs.get('winnaar_van_prijs')[1],)
            return self.createartist(rkdartistsdocs, summary)
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
        pywikibot.output(u'Going to create new artists!')
        rkdArtistsCreatorBot = RKDArtistsCreatorBot()
        generator = rkdArtistsCreatorBot.run()
    else:
        pywikibot.output(u'Going to try to expand existing artists')

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
