#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import RKD thesaurus and to create a mix and match set.


"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import requests
import re
import datetime
import time

class RKDThesaurusImporterBot:
    """
    A bot to enrich humans on Wikidata
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields ItemPage objects.

        """
        self.repo = pywikibot.Site().data_repository()
        self.generator = self.getSparqlGenerator()
        self.rkdThesaurusLookup = self.getIntLookupTable('P8519')
        self.aatLookup = self.getIntLookupTable('P1014')
        self.tgnLookup = self.getIntLookupTable('P1667')
        self.geonamesLookup = self.getIntLookupTable('P1566')

    def getSparqlGenerator(self):
        """
        Get the generator based on the external SPARQL endpoint.
        :return:
        """
        endpoint = 'https://data.netwerkdigitaalerfgoed.nl/_api/datasets/ivo/VGWW-RKD/services/VGWW-RKD/sparql'
        basequery = """PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?sub ?id ?enlabel ?nllabel ?description ?aaturi ?tgnuri ?geouri WHERE {
  ?sub rdf:type skos:Concept .
  BIND ( xsd:integer(REPLACE(STR(?sub), "https://data.rkd.nl/thesau/", "")) AS ?id ) 
  OPTIONAL { ?sub skos:prefLabel ?enlabel .  FILTER(LANG(?enlabel)="en-us") } .
  OPTIONAL { ?sub skos:prefLabel ?nllabel .  FILTER(LANG(?nllabel)="nl-nl") } .
  OPTIONAL { ?sub skos:scopeNote ?description } . 
  OPTIONAL { ?sub skos:exactMatch ?aaturi .  FILTER(REGEX(STR(?aaturi), "http://vocab.getty.edu/aat/")) } .
  OPTIONAL { ?sub skos:exactMatch ?tgnuri .  FILTER(REGEX(STR(?tgnuri), "http://vocab.getty.edu/tgn/")) } .
  OPTIONAL { ?sub skos:exactMatch ?geouri .  FILTER(REGEX(STR(?geouri), "https://sws.geonames.org/")) } .
  
  FILTER ( ?id > %s && ?id < %s )
  
} 
ORDER BY ?id 
LIMIT 10000""" # FIXME: Do range stuff

        for i in range(0, 110000, 10000):
            query = basequery % (i, i+10000)

            sq = pywikibot.data.sparql.SparqlQuery(endpoint=endpoint, entity_url='https://data.rkd.nl/thesau/')
            queryresult = sq.select(query)

            for resultitem in queryresult:
                result = { 'url' : resultitem.get('sub'),
                           'id' : int(resultitem.get('id')),
                           }
                if resultitem.get('enlabel') and resultitem.get('nllabel'):
                    if resultitem.get('enlabel')==resultitem.get('nllabel'):
                        result['label'] = resultitem.get('nllabel')
                    else:
                        result['label'] = '%s / %s' % (resultitem.get('enlabel'), resultitem.get('nllabel'))
                if resultitem.get('description'):
                    result['description'] = resultitem.get('description')

                uriintregex = '^http[^\d]+(\d+)[^\d]*$'
                if resultitem.get('aaturi'):
                    aatmatch = re.match(uriintregex, resultitem.get('aaturi'))
                    if aatmatch:
                        result['aat'] = int(aatmatch.group(1))

                if resultitem.get('tgnuri'):
                    result['tgn'] = int(re.match(uriintregex, resultitem.get('tgnuri')).group(1))

                if resultitem.get('geouri'):
                    result['geonames'] = int(re.match(uriintregex, resultitem.get('geouri')).group(1))

                yield result

    def getIntLookupTable(self, pid):
        """
        Make a lookup table for some identifier. Only works with integers
        :return: Dict
        """
        result = {}
        query = u'SELECT ?item ?id WHERE { ?item wdt:%s ?id }' % (pid,)
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)
        print (query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            try:
                result[int(resultitem.get('id'))] = qid
            except ValueError:
                pass
        return result

    def run(self):
        """
        Starts the robot.
        """
        for thesaurusentry in self.generator:
            #print (thesaurusentry)
            self.handleEntry(thesaurusentry)
        return

    def handleEntry(self, thesaurusentry):
        """
        Handle one entry in the RKD thesaurus
        :param thesaurusentry:
        :return:
        """
        if thesaurusentry.get('id') in self.rkdThesaurusLookup:
            print ('Already matched')
            return True

        if thesaurusentry.get('aat') and thesaurusentry.get('aat') in self.aatLookup:
            qid = self.aatLookup.get(thesaurusentry.get('aat'))
            pywikibot.output('AAT match for %s to %s' % (thesaurusentry.get('id'), qid))
            summary = '"%s" based on AAT match' % (thesaurusentry.get('label'))
            self.addLink(qid, thesaurusentry.get('id'), summary)

        if thesaurusentry.get('tgn') and thesaurusentry.get('geonames'):
            if thesaurusentry.get('tgn') in self.tgnLookup and thesaurusentry.get('geonames') in self.geonamesLookup:
                qid = self.tgnLookup.get(thesaurusentry.get('tgn'))
                if self.geonamesLookup.get(thesaurusentry.get('geonames'))==qid:
                    pywikibot.output('TGN and Geonames match for %s to %s' % (thesaurusentry.get('id'), qid))
                    summary = '"%s" based on TGN and Geonames match' % (thesaurusentry.get('label'))
                    self.addLink(qid, thesaurusentry.get('id'), summary)
        elif thesaurusentry.get('tgn') and thesaurusentry.get('tgn') in self.tgnLookup:
            qid = self.tgnLookup.get(thesaurusentry.get('tgn'))
            pywikibot.output('TGN match for %s to %s' % (thesaurusentry.get('id'), qid))
            summary = '"%s" based on TGN match' % (thesaurusentry.get('label'))
            self.addLink(qid, thesaurusentry.get('id'), summary)
        elif thesaurusentry.get('geonames') and thesaurusentry.get('geonames') in self.geonamesLookup:
            qid = self.geonamesLookup.get(thesaurusentry.get('geonames'))
            pywikibot.output('Geonames match for %s to %s' % (thesaurusentry.get('id'), qid))
            summary = '"%s" based on Geonames match' % (thesaurusentry.get('label'))
            self.addLink(qid, thesaurusentry.get('id'), summary)

    def addLink(self, qid, id, summary):
        """
        Add the actual link
        :param qid: The id of the Wikidata item
        :param id: The RKD thesaurus id to add
        :param summary: The edit summary
        :return: Nothing
        """
        itempage = pywikibot.ItemPage(self.repo, qid)
        claims = itempage.get().get('claims')

        if 'P8519' in claims:
            return

        newclaim = pywikibot.Claim(self.repo, 'P8519')

        newclaim.setTarget('%s' % (id,))
        pywikibot.output(u'Adding P8519->%s %s' % (id, summary))
        itempage.addClaim(newclaim, summary=summary)

    def bladieblas(self):
        while True:
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

            # Check if instance of (P31) -> human (Q5) is set
            if u'P31' not in claims:
                pywikibot.output(u'No instance of (P31) found, skipping')
                continue
            if not claims.get(u'P31')[0].getTarget():
                pywikibot.output(u'Weird instance of (P31) found, skipping')
                continue
            if claims.get(u'P31')[0].getTarget().title()!=u'Q5':
                pywikibot.output(u'Instance of (P31) is not set to human (Q5), skipping')
                continue

            rkdartistsid = claims.get(u'P650')[0].getTarget()
            rkdartistsurl = u'https://api.rkd.nl/api/record/artists/%s?format=json' % (rkdartistsid,)
            refurl = u'https://rkd.nl/explore/artists/%s' % (rkdartistsid,)

            # Do some checking if it actually exists
            rkdartistsPage = requests.get(rkdartistsurl, verify=False)

            # Check if we got json
            if not rkdartistsPage.headers.get('content-type')=='application/json':
                pywikibot.output(u'I did not get JSON back from RKD api, skipping')
                continue
            rkdartistsJson = rkdartistsPage.json()

            if rkdartistsJson.get('content') and rkdartistsJson.get('content').get('message'):
                pywikibot.output(u'Something went wrong, got "%s" for %s, skipping' % (rkdartistsJson.get('content').get('message'),
                                                                                       rkdartistsid))
                continue

            rkdartistsdocs = rkdartistsJson.get(u'response').get(u'docs')[0]

            self.addLabels(itempage, rkdartistsdocs, refurl)
            if u'P21' not in claims:
                self.addGender(itempage, rkdartistsdocs, refurl)
            elif len(claims.get(u'P21'))==1:
                self.addGender(itempage, rkdartistsdocs, refurl, claim=claims.get(u'P21')[0])
            if u'P106' not in claims:
                self.addOccupation(itempage, rkdartistsdocs, refurl)
            if u'P569' not in claims:
                self.addDateOfBirth(itempage, rkdartistsdocs, refurl)
            elif len(claims.get(u'P569'))==1:
                self.addDateOfBirth(itempage, rkdartistsdocs, refurl, claim=claims.get(u'P569')[0])
            if u'P570' not in claims:
                self.addDateOfDeath(itempage, rkdartistsdocs, refurl)
            elif len(claims.get(u'P570'))==1:
                self.addDateOfDeath(itempage, rkdartistsdocs, refurl, claim=claims.get(u'P570')[0])
            if u'P2031' not in claims:
                self.addWorkPeriodStart(itempage, rkdartistsdocs, refurl)
            elif len(claims.get(u'P2031'))==1:
                self.addWorkPeriodStart(itempage, rkdartistsdocs, refurl, claim=claims.get(u'P2031')[0])
            if u'P2032' not in claims:
                self.addWorkPeriodEnd(itempage, rkdartistsdocs, refurl)
            elif len(claims.get(u'P2032'))==1:
                self.addWorkPeriodEnd(itempage, rkdartistsdocs, refurl, claim=claims.get(u'P2032')[0])
            if u'P1317' not in claims:
                self.addFloruit(itempage, rkdartistsdocs, refurl)
            elif len(claims.get(u'P1317'))==1:
                self.addFloruit(itempage, rkdartistsdocs, refurl, claim=claims.get(u'P1317')[0])
            if u'P19' not in claims:
                self.addPlaceOfBirth(itempage, rkdartistsdocs, refurl)
            if u'P20' not in claims:
                self.addPlaceOfDeath(itempage, rkdartistsdocs, refurl)
            if u'P937' not in claims:
                self.addWorklocation(itempage, rkdartistsdocs, refurl)
            # Disabled for now. WbTime comparison seems to contain bugs
            # Can be enabled when https://phabricator.wikimedia.org/T148280 is fixed
            #if u'P27' not in claims and (u'P569' in claims or u'P570' in claims):
            #    self.addCountry(itempage, rkdartistsdocs, refurl)
            if u'P1343' not in claims:
                self.addDescribedBySource(itempage, rkdartistsdocs, refurl)

        self.reportMissingPlaces()
        self.reportMissingBooks()

    def addLabels(self, itempage, rkdartistsdocs, refurl):
        """
        Add any missing labels in one of the key languages
        """
        mylangs = [u'ca', u'da', u'de', u'en', u'es', u'fr', u'it', u'nl', u'pt', u'sv']
        kunstenaarsnaam = rkdartistsdocs.get('virtualFields').get('hoofdTitel').get('kunstenaarsnaam')
        if kunstenaarsnaam.get('label') == u'Voorkeursnaam':
            data = itempage.get()
            wdlabels = data.get('labels')
            prefLabel = kunstenaarsnaam.get('contents')
            labelschanged = 0
            for mylang in mylangs:
                if not wdlabels.get(mylang):
                    wdlabels[mylang] = prefLabel
                    labelschanged = labelschanged + 1

            if labelschanged:
                summary = u'Added missing labels in %s languages based on RKDartists %s' % (labelschanged, refurl)
                pywikibot.output(summary)
                try:
                    pywikibot.output(summary)
                    itempage.editLabels(wdlabels, summary=summary)
                except pywikibot.data.api.APIError:
                    pywikibot.output(u'Couldn\'t update the labels, conflicts with another item')

    def addGender(self, itempage, rkdartistsdocs, refurl, claim=None):
        newclaim = None
        claimid = None
        removesource = False
        if claim:
            if not claim.getTarget():
                pywikibot.output(u'Current claim doesn\'t seem to contain a gender, skipping')
                return
            claimid = claim.getTarget().title()
            if len(claim.getSources())==0:
                removesource = False
            elif len(claim.getSources())==1:
                removesource = self.isRemovableSource(claim.getSources()[0])
                if not removesource:
                    pywikibot.output(u'Not a source I can replace for gender, skipping')
                    return
            else:
                pywikibot.output(u'More sources than I can handle, skipping')
                return
        if rkdartistsdocs.get('geslacht'):
            if rkdartistsdocs.get('geslacht')==u'm':
                if claim:
                    if not claimid==u'Q6581097':
                        pywikibot.output(u'Current claim is not male, skipping')
                        return
                    if removesource:
                        claim.removeSource(removesource, summary=u'Removing to add better source')
                    self.addReference(itempage, claim, refurl)
                else:
                    newclaim = self.addItemStatement(itempage, u'P21', u'Q6581097')
                    self.addReference(itempage, newclaim, refurl)
            elif rkdartistsdocs.get('geslacht')==u'v':
                if claim:
                    if not claimid==u'Q6581072':
                        pywikibot.output(u'Current claim is not female, skipping')
                        return
                    if removesource:
                        claim.removeSource(removesource, summary=u'Removing to add better source')
                    self.addReference(itempage, claim, refurl)
                else:
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
                        33 : u'Q627325', # grafisch ontwerper
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
                        2909 : u'Q2519376', # edelsmid
                        3115 : u'Q5322166', # designer
                        3342 : u'Q173950', # kunsthandelaar
                        28583 : u'Q2216340', # zilversmid
                        28617 : u'Q11569986', # prentkunstenaar
                        31823 : u'Q10732476', # kunstverzamelaar / art collector
                        31824 : u'Q3243461', # verzamelaar / collector
                        44385 : u'Q15472169', # mecenas / patron of the arts
                        45116 : u'Q3391743', # artist -> visual artist
                        45297 : u'Q2519376', # jewelry designer
                        46436 : u'Q1028181', # amateurschilder
                        57618 : u'Q10732476', # schilderijenverzamelaar
                        57965 : u'Q16887133', # hoogwaardigheidsbekleder / dignitary
                        60862 : u'Q10732476', # verzamelaar van Hollandse en Vlaamse schilderkunst
                        63026 : u'Q43845', # koopman
                        63714 : u'Q211423', # goudsmid
                        }
        for occupationid in rkdartistsdocs.get('kwalificatie_lref'):
            if occupationid in occupations:
                newclaim = self.addItemStatement(itempage, u'P106', occupations.get(occupationid))
                self.addReference(itempage, newclaim, refurl)

    def addDateOfBirth(self, itempage, rkdartistsdocs, refurl, claim=None):
        '''
        Will add the date of birth if the data is available and not a range
        :param itempage: The ItemPage to update
        :param rkdartistsdocs: The json with the RKD information
        :param refurl: The url to add as reference
        :param clams: Existing claim to update (more precise and/or source it)
        :return:
        '''
        if rkdartistsdocs.get('geboortedatum_begin') and \
                rkdartistsdocs.get('geboortedatum_eind') and \
                        rkdartistsdocs.get('geboortedatum_begin')==rkdartistsdocs.get('geboortedatum_eind'):
            datestring = rkdartistsdocs.get('geboortedatum_begin')
            if claim:
                if len(claim.getSources())==0:
                    self.addDateProperty(itempage, datestring, u'P569', refurl, claim=claim)
                if len(claim.getSources())==1:
                    removesource = self.isRemovableSource(claim.getSources()[0])
                    if removesource:
                        self.addDateProperty(itempage,
                                             datestring,
                                             u'P569',
                                             refurl,
                                             claim=claim,
                                             removesource=removesource)
            else:
                self.addDateProperty(itempage, datestring, u'P569', refurl)


    def addDateOfDeath(self, itempage, rkdartistsdocs, refurl, claim=None):
        '''
        Will add the date of death if the data is available and not a range
        :param itempage: The ItemPage to update
        :param rkdartistsdocs: The json with the RKD information
        :param refurl: The url to add as reference
        :param clams: Existing claim to update (more precise and/or source it)
        :return:
        '''
        if rkdartistsdocs.get('sterfdatum_begin') and \
                rkdartistsdocs.get('sterfdatum_eind') and \
                        rkdartistsdocs.get('sterfdatum_begin')==rkdartistsdocs.get('sterfdatum_eind'):
            datestring = rkdartistsdocs.get('sterfdatum_begin')
            if claim:
                if len(claim.getSources())==0:
                    self.addDateProperty(itempage, datestring, u'P570', refurl, claim=claim)
                if len(claim.getSources())==1:
                    removesource = self.isRemovableSource(claim.getSources()[0])
                    if removesource:
                        self.addDateProperty(itempage,
                                             datestring,
                                             u'P570',
                                             refurl,
                                             claim=claim,
                                             removesource=removesource)
            else:
                self.addDateProperty(itempage, datestring, u'P570', refurl)

    def addWorkPeriodStart(self, itempage, rkdartistsdocs, refurl, claim=None):
        '''
        Will add the work period start date
        :param itempage: The ItemPage to update
        :param rkdartistsdocs: The json with the RKD information
        :param refurl: The url to add as reference
        :param clams: Existing claim to update (more precise and/or source it)
        :return:
        '''
        if rkdartistsdocs.get('werkzame_periode_begin'):
            if rkdartistsdocs.get('werkzame_periode_eind') and \
                    rkdartistsdocs.get('werkzame_periode_begin')[0]==rkdartistsdocs.get('werkzame_periode_eind')[0]:
                # Use floruit instead
                return
            datestring = rkdartistsdocs.get('werkzame_periode_begin')[0]
            if claim:
                if len(claim.getSources())==0:
                    self.addDateProperty(itempage, datestring, u'P2031', refurl, claim=claim)
                if len(claim.getSources())==1:
                    removesource = self.isRemovableSource(claim.getSources()[0])
                    if removesource:
                        self.addDateProperty(itempage,
                                             datestring,
                                             u'P2031',
                                             refurl,
                                             claim=claim,
                                             removesource=removesource)
            else:
                self.addDateProperty(itempage, datestring, u'P2031', refurl)

    def addWorkPeriodEnd(self, itempage, rkdartistsdocs, refurl, claim=None):
        '''
        Will add the work period end date
        :param itempage: The ItemPage to update
        :param rkdartistsdocs: The json with the RKD information
        :param refurl: The url to add as reference
        :param clams: Existing claim to update (more precise and/or source it)
        :return:
        '''
        if rkdartistsdocs.get('werkzame_periode_eind'):
            if rkdartistsdocs.get('werkzame_periode_begin') and \
                    rkdartistsdocs.get('werkzame_periode_begin')[0]==rkdartistsdocs.get('werkzame_periode_eind')[0]:
                # Use floruit instead
                return
            datestring = rkdartistsdocs.get('werkzame_periode_eind')[0]
            if claim:
                if len(claim.getSources())==0:
                    self.addDateProperty(itempage, datestring, u'P2032', refurl, claim=claim)
                if len(claim.getSources())==1:
                    removesource = self.isRemovableSource(claim.getSources()[0])
                    if removesource:
                        self.addDateProperty(itempage,
                                             datestring,
                                             u'P2032',
                                             refurl,
                                             claim=claim,
                                             removesource=removesource)
            else:
                self.addDateProperty(itempage, datestring, u'P2032', refurl)

    def addFloruit(self, itempage, rkdartistsdocs, refurl, claim=None):
        '''
        Will add the floruit date (point in time when someone was active)
        :param itempage: The ItemPage to update
        :param rkdartistsdocs: The json with the RKD information
        :param refurl: The url to add as reference
        :param clams: Existing claim to update (more precise and/or source it)
        :return:
        '''
        if rkdartistsdocs.get('werkzame_periode_begin') and \
                rkdartistsdocs.get('werkzame_periode_eind') and \
                rkdartistsdocs.get('werkzame_periode_begin')[0]==rkdartistsdocs.get('werkzame_periode_eind')[0]:
            datestring = rkdartistsdocs.get('werkzame_periode_begin')[0]
            if claim:
                if len(claim.getSources())==0:
                    self.addDateProperty(itempage, datestring, u'P1317', refurl, claim=claim)
                if len(claim.getSources())==1:
                    removesource = self.isRemovableSource(claim.getSources()[0])
                    if removesource:
                        self.addDateProperty(itempage,
                                             datestring,
                                             u'P1317',
                                             refurl,
                                             claim=claim,
                                             removesource=removesource)
            else:
                self.addDateProperty(itempage, datestring, u'P1317', refurl)

    def isRemovableSource(self, source):
        '''
        Will return the source claim if the source is imported from and nothing else
        :param source: The source
        :return:
        '''
        if not len(source)==1:
            return False
        if not u'P143' in source:
            return False
        return source.get('P143')[0]

    def addDateProperty(self, itempage, datestring, property, refurl, claim=None, removesource=False):
        '''
        Try to find a valid date and add it to the itempage using property
        :param itempage: The ItemPage to update
        :param datestring: The string containing the date
        :param property: The property to add (for example date of birth or date of death)
        :param refurl: The url to add as reference
        :return:
        '''
        newdate = self.parseDatestring(datestring)
        if not newdate:
            return False

        if claim:
            date = claim.getTarget()
            # If date is set to unknown, date will be None
            if date:
                if date.precision==newdate.precision:
                    if not date.year==newdate.year:
                        pywikibot.output(u'Different year, skipping')
                        return
                    if not (date.precision==9 or date.month==newdate.month):
                        pywikibot.output(u'Different month and precision is not set to 9 (year), skipping')
                        return
                    if not (date.precision==9 or date.precision==10 or date.day==newdate.day):
                        pywikibot.output(u'Different day and precision is not set to 9 (year) or 10 (month), skipping')
                        return
                    if not (date.timezone==newdate.timezone or date.calendarmodel==newdate.calendarmodel):
                        pywikibot.output(u'Different timezone or calendarmodel, skipping')
                        return
                else:
                    if not date.year==newdate.year:
                        pywikibot.output(u'Different precision and year, skipping')
                        return
                    if not (date.precision==9 and (newdate.precision==10 or newdate.precision==11)):
                        # FIXME: Add better message
                        pywikibot.output(u'Current precision is not 9 (year) or new precision is not 10 or 11, skipping')
                        return
                    summary = u'Replacing date with more precise date sourced from RKDartists'
                    pywikibot.output(summary)
                    claim.changeTarget(newdate, summary=summary)
                if removesource:
                    claim.removeSource(removesource, summary=u'Removing to add better source')
                self.addReference(itempage, claim, refurl)
        else:

            newclaim = pywikibot.Claim(self.repo, property)
            newclaim.setTarget(newdate)
            itempage.addClaim(newclaim)
            self.addReference(itempage, newclaim, refurl)

    def parseDatestring(self, datestring):
        '''
        Try to parse the date string. Returns
        :param datestring: String that might be a date
        :return:  pywikibot.WbTime
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
        return newdate

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

    def addWorklocation(self, itempage, rkdartistsdocs, refurl):
        '''
        Add the worklocation(s) to the itempage.
        Only work on items for which all the locations can be added
        :param itempage: The ItemPage to update
        :param rkdartistsdocs: The json with the RKD information
        :param refurl: The url to add as reference
        :return: Nothing, update the itempage in place
        '''
        if rkdartistsdocs.get('werkzaamheid'):
            for worklocation in rkdartistsdocs.get('werkzaamheid'):
                plaats_lref = worklocation.get('plaats_van_werkzaamheid_linkref')
                if not plaats_lref:
                    return False
                elif int(plaats_lref) not in self.places:
                    pywikibot.output(u'The work location "%s" with name "%s" is unknown' % (worklocation.get('plaats_van_werkzaamheid_linkref'),
                                                                                            worklocation.get('plaats_van_werkzaamheid')))
                    plaats_lref = int(plaats_lref)
                    if plaats_lref not in self.missingPlaces:
                        self.missingPlaces[plaats_lref] = 0
                    self.missingPlaces[plaats_lref] = self.missingPlaces[plaats_lref] + 1
                    return False
            # All the work locations were found so now we can actually add them.
            for worklocation in rkdartistsdocs.get('werkzaamheid'):
                placeitemtitle = self.places.get(int(worklocation.get('plaats_van_werkzaamheid_linkref')))
                newclaim = self.addItemStatement(itempage, u'P937', placeitemtitle)

                beginDate = None
                if worklocation.get('plaats_v_werkzh_begindatum'):
                    beginDate = self.parseDatestring(worklocation.get('plaats_v_werkzh_begindatum'))

                endDate = None
                if worklocation.get('plaats_v_werkzh_einddatum'):
                    endDate = self.parseDatestring(worklocation.get('plaats_v_werkzh_einddatum'))

                # Point in time
                if beginDate and endDate and beginDate==endDate:
                    newqualifier = pywikibot.Claim(self.repo, u'P585')
                    newqualifier.setTarget(beginDate)
                    newclaim.addQualifier(newqualifier)
                else:
                    if beginDate:
                        newqualifier = pywikibot.Claim(self.repo, u'P580')
                        newqualifier.setTarget(beginDate)
                        newclaim.addQualifier(newqualifier)
                    if endDate:
                        newqualifier = pywikibot.Claim(self.repo, u'P582')
                        newqualifier.setTarget(endDate)
                        newclaim.addQualifier(newqualifier)
                self.addReference(itempage, newclaim, refurl)

    def addPlaceProperty(self, itempage, plaats_lref, property, refurl):
        '''
        Add the place using property to the itempage
        :param itempage: The ItemPage to update
        :param plaats_lref: The rkd thesaurus id of the place
        :param property: The property to add
        :param refurl: The url to add as reference
        :return: Nothing, update the itempage in place
        '''
        if not plaats_lref in self.places:
            if plaats_lref not in self.missingPlaces:
                self.missingPlaces[plaats_lref] = 0
            self.missingPlaces[plaats_lref] = self.missingPlaces[plaats_lref] + 1
            return False
        placeitemtitle = self.places.get(plaats_lref)
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

    def addDescribedBySource(self, itempage, rkdartistsdocs, refurl):
        '''
        Add the described by source(s) to the itempage based on RKDlibrary books being used.
        Only work on items for which all the books can be added
        :param itempage: The ItemPage to update
        :param rkdartistsdocs: The json with the RKD information
        :param refurl: The url to add as reference
        :return: Nothing, update the itempage in place
        '''
        if not rkdartistsdocs.get('bronnen'):
            return False

        for bron in rkdartistsdocs.get('bronnen'):
            bron_literatuur_linkref = bron.get('bron_literatuur_linkref')
            if not bron_literatuur_linkref:
                return False
            elif int(bron_literatuur_linkref) not in self.rkdLibrary:
                pywikibot.output(u'The book "%s" with name "%s" is unknown' % (bron.get('bron_literatuur_linkref'),
                                                                               bron.get('bron_literatuur')))
                bron_literatuur_linkref = int(bron_literatuur_linkref)
                if bron_literatuur_linkref not in self.missingRkdLibrary:
                    self.missingRkdLibrary[bron_literatuur_linkref] = 0
                self.missingRkdLibrary[bron_literatuur_linkref] += 1
                return False
        # All the books were found so now we can actually add them.
        for bron in rkdartistsdocs.get('bronnen'):
            bookitemtitle = self.rkdLibrary.get((int(bron.get('bron_literatuur_linkref'))))
            newclaim = self.addItemStatement(itempage, u'P1343', bookitemtitle)

            volume = None
            page = None
            if bron.get('bron_deel_pag'):
                volumePageRegex = u'^vol\.\s*(\d+)\s*,?\s*p\.\s*(.+)$'
                pageRegex = u'^p\.\s*(.+)$'
                volumePageRegexMatch = re.match(volumePageRegex, bron.get('bron_deel_pag'))
                pageMatch = re.match(pageRegex, bron.get('bron_deel_pag'))
                if volumePageRegexMatch:
                    volume = volumePageRegexMatch.group(1)
                    page = volumePageRegexMatch.group(2)
                elif pageMatch:
                    page = pageMatch.group(1)
                else:
                    page = bron.get('bron_deel_pag')

            namedas = None
            if bron.get('bron_opmerking'):
                asregex = u'^as\:\s*(.+)$'
                asmatch = re.match(asregex, bron.get('bron_opmerking'))
                if asmatch:
                    namedas = asmatch.group(1)

            # Add the qualifiers for the things we found
            if volume:
                newqualifier = pywikibot.Claim(self.repo, u'P478')
                newqualifier.setTarget(volume)
                newclaim.addQualifier(newqualifier)
            if page:
                newqualifier = pywikibot.Claim(self.repo, u'P304')
                newqualifier.setTarget(page)
                newclaim.addQualifier(newqualifier)
            if namedas:
                newqualifier = pywikibot.Claim(self.repo, u'P1810')
                newqualifier.setTarget(namedas)
                newclaim.addQualifier(newqualifier)
            self.addReference(itempage, newclaim, refurl)

    def reportMissingPlaces(self):
        """

        :return:
        """
        print ('The top 50 places that are missing in this run:')
        for identifier in sorted(self.missingPlaces, key=self.missingPlaces.get, reverse=True)[:50]:
            print ('* https://rkd.nl/en/explore/thesaurus?term=%s - %s' % (identifier, self.missingPlaces[identifier]))

    def reportMissingBooks(self):
        """

        :return:
        """
        print ('The top 50 books that are missing in this run:')
        for identifier in sorted(self.missingRkdLibrary, key=self.missingRkdLibrary.get, reverse=True)[:50]:
            print ('* https://rkd.nl/explore/library/%s - %s'  % (identifier, self.missingRkdLibrary[identifier]))


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
        statedin = pywikibot.Claim(self.repo, u'P248')
        rkdartistsitem = pywikibot.ItemPage(self.repo,u'Q17299517')
        statedin.setTarget(rkdartistsitem)
        refurl = pywikibot.Claim(self.repo, u'P854') # Add url, isReference=True
        refurl.setTarget(url)
        refdate = pywikibot.Claim(self.repo, u'P813')
        today = datetime.datetime.today()
        date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
        refdate.setTarget(date)

        newclaim.addSources([statedin, refurl, refdate])


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
        Just return all the RKD artists as a dict
        :return: Dict
        '''
        result = {}
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
        start = 0 # 20000 # 60000
        end = 101232 # 101232 # 2608 # 361707
        limit = 2

        start = 0
        end = 3246
        baseurl = u'https://api.rkd.nl/api/search/artists?query=+Wachlin&fieldset=detail&format=json&rows=%s&start=%s'
        #baseurl = u'https://api.rkd.nl/api/search/artists?filters[kwalificatie]=schilder&fieldset=detail&format=json&rows=%s&start=%s'
        #baseurl = u'https://api.rkd.nl/api/search/artists?fieldset=detail&format=json&rows=%s&start=%s'
        #baseurl = u'https://api.rkd.nl/api/search/artists?filters[winnaar_van_prijs]=*&fieldset=detail&format=json&rows=%s&start=%s'

        for i in range(start, end, limit):

            url = baseurl % (limit, i)
            #print (url)
            rkdartistsApiPage = requests.get(url, verify=False)
            rkdartistsApiPageJson = rkdartistsApiPage.json()
            #print (rkdartistsApiPageJson)
            if rkdartistsApiPageJson.get('content') and rkdartistsApiPageJson.get('content').get('message'):
                pywikibot.output(u'Something went wrong')
                continue

            for rkdartistsdocs in rkdartistsApiPageJson.get('response').get('docs'):
                yield rkdartistsdocs

    def filterArtists(self, generator):
        """
        Unused function I think
        """
        for rkdartistsdocs in generator:
            if rkdartistsdocs.get('priref') in self.currentrkd:
                pywikibot.output(u'Already got %s on %s' % (rkdartistsdocs.get('priref'),
                                                            self.currentrkd.get(rkdartistsdocs.get('priref'))))
                continue
            if rkdartistsdocs.get('priref')==452514:
                pywikibot.output(u'Skipping favorite test item at https://rkd.nl/explore/artists/452514')
                continue
            if rkdartistsdocs.get(u'results_in_other_databases') and \
                rkdartistsdocs.get(u'results_in_other_databases').get(u'images_kunstenaar'):
                number = rkdartistsdocs.get(u'results_in_other_databases').get(u'images_kunstenaar').get('count')
                if number > 0:
                    print (rkdartistsdocs.get('kwalificatie'))
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
        print (rkdartistsdocs.get('priref'))
        number = -1
        if rkdartistsdocs.get(u'results_in_other_databases') and \
                rkdartistsdocs.get(u'results_in_other_databases').get(u'images_kunstenaar').get('count'):
            number = rkdartistsdocs.get(u'results_in_other_databases').get(u'images_kunstenaar').get('count')
        if number > 10:
            summary = u'Creating artist based on RKD: Artist has more than 10 works in RKDimages'
            return self.createartist(rkdartistsdocs, summary)
        # Focus on painters here
        if 'schilder' in rkdartistsdocs.get('kwalificatie'):
            if 'Koninklijke subsidie voor vrije schilderkunst' in rkdartistsdocs.get('winnaar_van_prijs'):
                summary = u'Creating artist based on RKD: Painter won the Royal Prize for Painting'
                return self.createartist(rkdartistsdocs, summary)
            # Could add more prizes here
            if number > 2:
                summary = u'Creating artist based on RKD: Painter has more than 2 works in RKDimages'
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
        # Wachlin 2011 photographers for Hanno
        if 'fotograaf' in rkdartistsdocs.get('kwalificatie'):
            wachlinfound = False
            for bron in rkdartistsdocs.get('bronnen'):
                if bron.get('bron_literatuur')=='Wachlin 2011' and bron.get('bron_literatuur_linkref')=='211864':
                    wachlinfound = True
            if wachlinfound:
                summary = u'Creating artist based on RKD: Photographer documented in [[Q15880691]]'
                return self.createartist(rkdartistsdocs, summary)
        return None

    def createartist(self, rkdartistsdocs, summary):
        """
        The magic create function
        :param rkdartistsdocs:
        :param summary:
        :return:
        """

        langs = [u'ca', u'da', u'de', u'en', u'es', u'fr', u'it', u'nl', u'pt', u'sv']

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

            print (data)

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
    """

    rkdThesaurusImporterBot = RKDThesaurusImporterBot()
    rkdThesaurusImporterBot.run()

if __name__ == "__main__":
    main()
