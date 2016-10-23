#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import missing Biografisch portaal van Nederland ( http://www.biografischportaal.nl ) links
for several properties.

It works by doing a search on the BPN with a certain source, for example:
http://www.biografischportaal.nl/personen?&source_id=rkdartists

First query is done for all items that already have both properties.
Second query is done for all items that have the other property, but not BPN
Third query is done for all items that don't have the other property, but do have BPN

If the id is is in the both properties query, just skip it, all is good.
Retrieve the page.
If the link is in the second query, add the BPN number
If the link is in the third query, add the other property

"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import requests
import re
import datetime

class BPNFinderBot:
    """
    A bot to add missing links based on Biografisch portaal van Nederland
    """
    def __init__(self, generator, otherproperty, idregex, otherbaseurl, report=None):
        """
        Arguments:
        :param generator     - A generator of BPN id's
        :param otherproperty - The other property to work on (for example P650 for RKDartists)
        :param idregex     - The regex to extract the id from a link
        :param reportpage  - Name of the page to report the missing ones on

        """
        self.generator = generator
        self.bpnproperty = u'P651'
        self.bpnbaseurl = u'http://www.biografischportaal.nl/persoon/%s'
        self.otherproperty = otherproperty
        self.idregex = idregex
        self.otherbaseurl = otherbaseurl
        self.report = report

        self.repo = pywikibot.Site().data_repository()
        # Has both BPN and RKDartists
        self.completed = self.buildIdCache(self.bpnproperty, extraproperty=self.otherproperty)
        # Has BPN, but not the other property
        self.missingother = self.buildIdCache(self.bpnproperty, minusproperty=self.otherproperty)
        # Has the other property, but might not have BNP. No filtering because of redirects
        self.missingbpn = self.buildIdCache(self.otherproperty) #, minusproperty=self.bpnproperty)

        self.missingtext = u'This is the report for Biografisch Portaal Nederland and %s\n' % (otherproperty,)

    def buildIdCache(self, property, extraproperty=None, minusproperty=None):
        '''
        Build an ID cache so we can quickly look up the id's for property
        :param property is a string in the form "P650". All items using this property will be returned
        :param extraproperty is an additional filter. Only items that also contain this property will be returned
        :param minusproperty is an additional filter. Only items that do not contain this property will be returned
        :return: Dict with the id of property as key and the Wikidata item qid as value
        '''
        result = {}
        sq = pywikibot.data.sparql.SparqlQuery()
        if extraproperty and minusproperty:
            query = u'SELECT ?item ?id WHERE { ?item wdt:%s ?id . ?item wdt:%s [] . MINUS { ?item wdt:%s [] } }' % (property, extraproperty, minusproperty)
        elif extraproperty:
            query = u'SELECT ?item ?id WHERE { ?item wdt:%s ?id . ?item wdt:%s [] }' % (property, extraproperty)
        elif minusproperty:
            query = u'SELECT ?item ?id WHERE { ?item wdt:%s ?id . MINUS { ?item wdt:%s [] } }' % (property, minusproperty)
        else:
            query = u'SELECT ?item ?id WHERE { ?item wdt:%s ?id}' % (property,)
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[resultitem.get('id')] = qid
        pywikibot.output(u'The query "%s" returned %s items' % (query, len(result)))
        return result

    def run(self):
        """
        Starts the robot.
        """
        for bpnid in self.generator:
            if bpnid in self.completed:
                pywikibot.output(u'BPN id %s is already completed' % (bpnid,))
            elif bpnid in self.missingother:
                pywikibot.output(u'BPN id %s is used on an item, but other property is missing' % (bpnid,))
                self.addOtherProperty(bpnid)
            else:
                self.addBPNProperty(bpnid)

        self.missingtext = self.missingtext + u'\n\n[[Category:User:Multichill]]\n'
        if self.report:
            summary = u'Missing report'
            pywikibot.output(self.missingtext)

            reportpage = pywikibot.Page(self.repo, title=self.report)
            reportpage.put(self.missingtext , summary=summary)


    def getOtherPropertyId(self, bpnid):
        """
        Helper function to retrieve the other property for bpnid
        :param bpnid: The Biografisch Portaal Nederland identifier
        :return: The id of the other property or False if it isn't found
        """

        bpnurl = self.bpnbaseurl % (bpnid,)
        # Do some checking if it actually exists?
        bpnPage = requests.get(bpnurl, verify=False)

        idmatch = re.search(self.idregex, bpnPage.text)
        if idmatch:
            return idmatch.group(1)
        pywikibot.output(u'Other id not found for %s' % (bpnid,))
        self.missingtext = self.missingtext + u'* On page [%s %s] unable to extract other id\n' % (bpnurl, bpnid)
        return False

    def addOtherProperty(self, bpnid):
        """
        We found a Wikidata item qid for the bpnid.
        Try to find the other property and add that id to the Wikidata item
        :param bpnid: The Biografisch Portaal Nederland identifier
        :return: Boolean with True if the otherid is on the Wikidata item (either already there or added)
        """
        otherid = self.getOtherPropertyId(bpnid)
        bpnurl = self.bpnbaseurl % (bpnid,)

        # Do some checking if it actually exists?
        #bpnPage = requests.get(selfbpnurl, verify=False)

        #idmatch = re.search(self.idregex, bpnPage.text)
        if otherid:
            qid = self.missingother.get(bpnid)
            itempage = pywikibot.ItemPage(self.repo, title=qid)
            data = itempage.get()
            claims = data.get('claims')

            if self.otherproperty in claims:
                # Looks like it already has the same property, let's check if it's the same
                if claims.get(self.otherproperty)[0].getTarget() == otherid:
                    # Already complete, if it's another id, add the other one to find duplicates
                    return True
            # Add the id to the item
            newclaim = pywikibot.Claim(self.repo, self.otherproperty)
            newclaim.setTarget(otherid)
            summary = u'Adding link based on link on Biografisch Portaal number %s' % (bpnid,)
            pywikibot.output(summary)
            itempage.addClaim(newclaim, summary=summary)
            self.addReference(itempage, newclaim, bpnurl)
            return True
        return False

    def addBPNProperty(self, bpnid):
        """
        Try to add the bpnid to an existing Wikidata item
        :param bpnid: The Biografisch Portaal Nederland identifier
        :return: boolean with True if the bpnid is on a Wikidata item (either already there or added)
        """
        otherid = self.getOtherPropertyId(bpnid)
        bpnurl = self.bpnbaseurl % (bpnid,)

        if not otherid:
            return False
        if otherid not in self.missingbpn:
            pywikibot.output(u'BPN %s gave other id %s, but nothing found for this id' % (bpnid, otherid))
            otherurl = self.otherbaseurl % (otherid,)
            self.missingtext = self.missingtext + u'* On page [%s %s] found [%s %s] but couldn\'t find Wikidata item\n' % (bpnurl, bpnid, otherurl, otherid)
            return False

        # We found an item that has the other property, but not BPN
        qid = self.missingbpn.get(otherid)
        itempage = pywikibot.ItemPage(self.repo, title=qid)
        data = itempage.get()
        claims = data.get('claims')

        if self.bpnproperty in claims:
            # Looks like it already has the same property, let's check if it's the same
            # FIXME: This only checks the first statement, the same one could be the second.
            if claims.get(self.bpnproperty)[0].getTarget() == bpnid:
                # Already complete, if it's another id, add the other one to find duplicates
                return True
        # Add the id to the item
        newclaim = pywikibot.Claim(self.repo, self.bpnproperty)
        newclaim.setTarget(bpnid)
        summary = u'Adding link based on link to [[Property:%s]] %s on Biografisch Portaal' % (self.otherproperty,otherid)
        pywikibot.output(summary)
        itempage.addClaim(newclaim, summary=summary)
        return True

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


def biografischportaalGenerator(source_id):
    """

    :param searchstring:
    :return:
    """
    baseurl = u'http://www.biografischportaal.nl/personen?&source_id=%s&start=%s'
    firstPage = requests.get(baseurl % (source_id, 0), verify=False)

    numregex = u'Er zijn\s*\n\s*([\d\.]+)\s*\n\s*personen gevonden\.'
    bpnidregex = u'\<a href\=\"http:\/\/www\.biografischportaal\.nl\/persoon\/(\d+)\"\>'

    nummatch =  re.search(numregex, firstPage.text)
    total = int(nummatch.group(1).replace('.', u''))
    step = 30
    for i in range(0, total+step, step):
        searchPage = requests.get(baseurl % (source_id, i), verify=False)
        for bpnid in re.finditer(bpnidregex, searchPage.text):
            yield bpnid.group(1)

def main(*args):
    """
    Main function. Grab a generator and pass it to the bot to work on
    """
    sources = {u'P650' : { u'property' : u'P650', # RKDartists ID
                           u'source_id' : u'rkdartists',
                           u'idregex' : u'href\=\"http:\/\/www\.rkd\.nl\/rkddb\/dispatcher\.aspx\?action=search\&amp;database\=ChoiceArtists\&amp;search\=priref\=(\d+)\"\>',
                           u'baseurl' : u'https://rkd.nl/en/artists/%s',
                           },
               u'P723' : { u'property' : u'P723',# DBNL author ID
                           u'source_id' : u'dbnl',
                           u'idregex' : u'href\=\"http\:\/\/www.dbnl.org\/auteurs\/auteur.php\?id\=([a-z_]{4}[0-9]{3})\"\>',
                           u'baseurl' : u'http://www.dbnl.org/auteurs/auteur.php?id=%s',
                           },
               u'P1749' : { u'property' : u'P1749',# Parlement & Politiek ID
                            u'source_id' : u'pdc',
                            u'idregex' : u'href\=\"http:\/\/www\.parlementairdocumentatiecentrum\.nl\/id\/([^\"]+)\"\>',
                            u'baseurl' : u'http://www.parlement.com/id/%s',
                            },
               }

    source = None
    report = None
    for arg in pywikibot.handle_args(args):
        if arg.startswith('-source:'):
            if len(arg) == 8:
                source = pywikibot.input(
                        u'Please enter the source property you want to work on:')
            else:
                source = arg[8:]
        elif arg.startswith('-report:'):
            if len(arg) == 8:
                report = pywikibot.input(
                        u'Please enter the name of the page to report on:')
            else:
                report = arg[8:]
    repo = pywikibot.Site().data_repository()

    # Source was passed on the commandline. Only work on that one
    if source and source in sources:
        idgenerator = biografischportaalGenerator(sources.get(source).get(u'source_id'))
        bpnFinderBot = BPNFinderBot(idgenerator,
                                    otherproperty=source,
                                    idregex=sources.get(source).get(u'idregex'),
                                    otherbaseurl=sources.get(source).get(u'baseurl'),
                                    report=report)
        bpnFinderBot.run()
    else:
        # Let's work on all of them
        for source in sources:
            idgenerator = biografischportaalGenerator(sources.get(source).get(u'source_id'))
            bpnFinderBot = BPNFinderBot(idgenerator,
                                        otherproperty=source,
                                        idregex=sources.get(source).get(u'idregex'),
                                        otherbaseurl=sources.get(source).get(u'baseurl'))
            bpnFinderBot.run()

if __name__ == "__main__":
    main()
