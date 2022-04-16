#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to depicts statements for monuments. Start with Rijksmonumenten and maybe later more (3M images probably).

Should be switched to a more general Pywikibot implementation.

"""

import pywikibot
import re
import pywikibot.data.sparql
import time
import json
import random
from pywikibot import pagegenerators

class DepictsMonumentsBot:
    """
    Bot to add depicts statements on Commons
    """
    def __init__(self, config, gen=None):
        """
        Grab generator based on search to work on.

        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()

        # From the config at https://commons.wikimedia.org/wiki/User:ErfgoedBot/Depicts_monuments.js
        self.description = config.get('description')
        self.property = config.get('property')
        self.propertyname = config.get('propertyname')
        self.template = config.get('template')
        self.trackercategory = config.get('trackercategory')
        self.search = config.get('search')
        self.designation = config.get('designation')
        self.templateregex = config.get('templateregex')

        # This was everything in the category. Search is only the ones we still need to work on
        # monumentcat = pywikibot.Category(self.site, title=u'Category:Rijksmonumenten_with_known_IDs')

        if gen:
            self.generator = gen
        else:
            self.generator = pagegenerators.PreloadingGenerator(pagegenerators.SearchPageGenerator(self.search, namespaces=6, site=self.site))
        (self.monuments, self.monumentsLocations) = self.getMonumentsOnWikidata(self.property, self.designation)

    def getMonumentsOnWikidata(self, property, designation=None):
        """
        Get the monuments currently on Wikidata. Keep the id as a string.
        :return:
        """
        resultMonuments = {}
        resultLocations = {}
        if designation:
            query = u'''SELECT ?item ?id ?location WHERE {
  ?item wdt:P1435 wd:%s .
  ?item wdt:%s ?id .
  OPTIONAL { ?item wdt:P131 ?location } . 
  } ORDER BY ?id''' % (designation, property, )
        else:
            query = u'''SELECT ?item ?id ?location WHERE {
  ?item wdt:%s ?id .
  OPTIONAL { ?item wdt:P131 ?location } .
  } ORDER BY ?id''' % (property, )
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            resultMonuments[resultitem.get('id')] = qid
            if resultitem.get('location'):
                locationqid = resultitem.get('location').replace(u'http://www.wikidata.org/entity/', u'')
                resultLocations [resultitem.get('id')] = locationqid

        return (resultMonuments, resultLocations)

    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            if not filepage.exists():
                continue
            # Probably want to get this all in a preloading generator to make it faster
            mediaid = u'M%s' % (filepage.pageid,)
            currentdata = self.getCurrentMediaInfo(mediaid)
            self.handleMonument(filepage, mediaid, currentdata)

    def getCurrentMediaInfo(self, mediaid):
        """
        Check if the media info exists. If that's the case, return that so we can expand it.
        Otherwise return an empty dict
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :return: json
            """
        request = self.site._simple_request(action='wbgetentities',ids=mediaid)
        data = request.submit()
        if data.get(u'entities').get(mediaid).get(u'pageid'):
            return data.get(u'entities').get(mediaid)
        return {}

    def handleMonument(self, filepage, mediaid, currentdata):
        """
        Handle a single monument. Try to extract the template, look up the id and add the Q if no mediainfo is present.

        :param filepage: The page of the file to work on.
        :return: Nothing, edit in place
        """
        pywikibot.output(u'Working on %s' % (filepage.title(),))
        if not filepage.exists():
            return

        matches = list(re.finditer(self.templateregex, filepage.text))

        if not matches:
            pywikibot.output(u'No matches found on %s, skipping' % (filepage.title(),))
            return

        summarytoadd = []
        depictstoadd = []
        locationstoadd = []

        # First collect the matches to add
        for match in matches:
            monumentid = match.group(u'id')
            if monumentid not in self.monuments:
                pywikibot.output(u'Found unknown monument id %s on %s, skipping' % (monumentid, filepage.title(),))
                return
            qid = self.monuments.get(monumentid)
            # Some cases the template is in the file text multiple times
            if (monumentid, qid) not in summarytoadd:
                summarytoadd.append((monumentid, qid))
                depictstoadd.append(qid)
            if monumentid in self.monumentsLocations:
                locationstoadd.append(self.monumentsLocations.get(monumentid))

        # Here we're collecting
        newclaims = {}

        newclaims['depicts'] = self.addDepicts(mediaid, currentdata, depictstoadd)
        newclaims['location'] = self.addLocation(mediaid, currentdata, locationstoadd)

        for (monumentid, qid) in summarytoadd:
            if len(summarytoadd)==1:
                summary = u'based on [[Template:%s]] with id %s, which is the same id as [[:d:Property:%s|%s (%s)]] on [[d:Special:EntityPage/%s]]' % (self.template,
                                                                                                                                     monumentid,
                                                                                                                                     self.property,
                                                                                                                                     self.propertyname,
                                                                                                                                     self.property,
                                                                                                                                     qid, )
            else:
                summary = u'based on [[Template:%s]] with id %s, which is the same id as [[:d:Property:%s|%s (%s)]] on [[d:Special:EntityPage/%s]] (and %s more)' % (self.template,
                                                                                                                                             monumentid,
                                                                                                                                             self.property,
                                                                                                                                             self.propertyname,
                                                                                                                                             self.property,
                                                                                                                                             qid,
                                                                                                                                             len(summarytoadd)-1)
        addedclaims = []

        itemdata = {u'claims' : [] }

        for newclaim in newclaims:
            if newclaims.get(newclaim):
                itemdata['claims'].extend(newclaims.get(newclaim))
                addedclaims.append(newclaim)

        if len(addedclaims) > 0:
            # Flush it
            pywikibot.output(summary)

            token = self.site.tokens['csrf']
            postdata = {'action' : u'wbeditentity',
                        'format' : u'json',
                        'id' : mediaid,
                        'data' : json.dumps(itemdata),
                        'token' : token,
                        'summary' : summary,
                        'bot' : True,
                        }
            if currentdata:
                # This only works when the entity has been created
                postdata['baserevid'] = currentdata.get('lastrevid')

            request = self.site._simple_request(**postdata)
            try:
                data = request.submit()
                # Always touch the page to flush it
                filepage.touch()
            except (pywikibot.exceptions.APIError, pywikibot.exceptions.OtherPageSaveError):
                pywikibot.output('Got an API error while saving page. Sleeping, getting a new token and skipping')
                time.sleep(30)
                self. site.tokens.load_tokens(['csrf'])

    def addDepicts(self, mediaid, currentdata, depictstoadd):
        """
        Add the author info to filepage
        :param mediaid: Media ID of the file
        :param currentdata: What's currently on the fiel
        :param depictstoadd: List of Q id's to add
        :return:
        """
        if currentdata.get('statements'):
            if currentdata.get('statements').get('P180'):
                return False

        result = []

        # Add the different licenses
        for depicts in depictstoadd:
            result.extend(self.addClaimJson(mediaid, u'P180', depicts))
        return result

    def addLocation(self, mediaid, currentdata, locationstoadd):
        """
        Add the author info to filepage
        :param mediaid: Media ID of the file
        :param currentdata: What's currently on the fiel
        :param depictstoadd: List of Q id's to add
        :return:
        """
        if currentdata.get('statements'):
            if currentdata.get('statements').get('P1071'):
                return False

        locationstoadd = list(set(locationstoadd))
        if len(locationstoadd) !=1:
            return False
        return self.addClaimJson(mediaid, u'P1071', locationstoadd[0])

    def addClaimJson(self, mediaid, pid, qid):
        """
        Add a claim to a mediaid

        :param mediaid: The mediaid to add it to
        :param pid: The property P id (including the P)
        :param qid: The item Q id (including the Q)
        :param summary: The summary to add in the edit
        :return: Nothing, edit in place
        """
        toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': pid,
                                 'datavalue': { 'value': { 'numeric-id': qid.replace(u'Q', u''),
                                                           'id' : qid,
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        return [toclaim,]

def getDepictsMonumentsConfig():
    """
    Load the configuration from https://commons.wikimedia.org/wiki/User:ErfgoedBot/Depicts_monuments.js
    :return: Dict with the configuration
    """
    site = pywikibot.Site('commons', 'commons')
    pageTitle = 'User:ErfgoedBot/Depicts monuments.js'
    page = pywikibot.Page(site, title=pageTitle)

    jsonregex = u'^\/\*.+\n( \*.*\n)+(?P<json>(.+\n?)+)$'
    match = re.match (jsonregex, page.text)
    result = json.loads(match.group('json'))
    return result


def main(*args):
    monumentproperty = None
    gen = None
    genFactory = pagegenerators.GeneratorFactory()
    for arg in pywikibot.handle_args(args):
        if arg.startswith('-monumentproperty:'):
            if len(arg) == 18:
                monumentproperty = pywikibot.input(
                        u'Please enter the property you want to work on:')
            else:
                monumentproperty = arg[18:]
        elif genFactory.handleArg(arg):
            continue

    config = getDepictsMonumentsConfig()
    gen = genFactory.getCombinedGenerator(gen, preload=True)
    if monumentproperty:
        if monumentproperty not in config.keys():
            pywikibot.output(u'%s is not a valid property to work on!' % (monumentproperty,))
            pywikibot.output(u'See https://commons.wikimedia.org/wiki/User:ErfgoedBot/Depicts_monuments.js')
            return
        depictsMonumentsBot = DepictsMonumentsBot(config.get(monumentproperty), gen=gen)
        depictsMonumentsBot.run()
    else:
        # Work on all configured properties, but each time in a different order
        monkeys = list(config.keys())
        random.shuffle(monkeys)
        pywikibot.output('Working on all %s configured monument properties' % (len(monkeys),))
        for monumentproperty in monkeys:
            pywikibot.output('Working on %s: "%s"' % (monumentproperty,config.get(monumentproperty).get('description')))
            depictsMonumentsBot = DepictsMonumentsBot(config.get(monumentproperty))
            depictsMonumentsBot.run()

if __name__ == "__main__":
    main()
