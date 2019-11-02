#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add the Wikidata item id to a monuments list. Start with Rijksmonumenten.

Grab configuration from a file like https://github.com/wikimedia/labs-tools-heritage/blob/master/erfgoedbot/monuments_config/nl_nl.json

"""

import pywikibot
import re
import requests
import pywikibot.data.sparql
import datetime
from pywikibot.comms import http
import json
from pywikibot import pagegenerators

class WikidataToMonumentsListBot:
    """
    Bot to add depicts statements on Commons
    """
    def __init__(self, configurl=u'https://raw.githubusercontent.com/wikimedia/labs-tools-heritage/master/erfgoedbot/monuments_config/nl_nl.json'):
        """
        Grab generator based on search to work on.

        """
        page = requests.get(configurl)
        self.monumentsconfig = page.json()
        #print (self.monumentsconfig)
        self.site = pywikibot.Site(self.monumentsconfig.get(u'lang'), self.monumentsconfig.get(u'project'))
        self.repo = self.site.data_repository()

        self.wikidatafield = None
        for field in self.monumentsconfig.get('fields'):
            if field.get(u'dest') and field.get(u'dest')=='wd_item':
                self.wikidatafield = field.get(u'source')

        self.property = u'P359'
        self.designation = u'Q916333'
        self.monuments = self.getMonumentsOnWikidata(self.property, self.designation)

        row_template = pywikibot.Page(self.site, '{0}:{1}'.format(self.site.namespace(10),
                                                             self.monumentsconfig.get('rowTemplate')))

        trans_gen = pagegenerators.ReferringPageGenerator(row_template,
                                                                                   onlyTemplateInclusion=True)
        self.generator = pagegenerators.NamespaceFilterPageGenerator(trans_gen, self.monumentsconfig.get('namespaces'),
                                                                     site=self.site)

    def getMonumentsOnWikidata(self, property, designation=None):
        """
        Get the monuments currently on Wikidata. Keep the id as a string.
        :return:
        """
        result = {}
        if designation:
            query = u'''SELECT ?item ?id WHERE {
  ?item wdt:P1435 wd:%s .
  ?item wdt:%s ?id .
  } ORDER BY ?id''' % (designation, property, )
        else:
            query = u'''SELECT ?item ?id WHERE {
  ?item wdt:%s ?id .
  } ORDER BY ?id''' % (property, )
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[resultitem.get('id')] = qid
        return result

    def run(self):
        """
        Run on the items
        """
        for page in self.generator:
            self.process_page(page)

    def process_page(self, page):
        """

        :param page:
        :return:
        """

        templates = page.templatesWithParams()
        text = page.text
        newtext = text

        total_templates = 0
        total_added = 0

        for (template, params) in templates:
            template_name = template.title(with_ns=False)
            if template_name == self.monumentsconfig.get('rowTemplate'):
                total_templates +=1
                monumentid = None
                wditem = None
                for param in params:
                    (field, sep, value) = param.partition(u'=')
                    field = field.strip()
                    value = value.strip()
                    if field == self.monumentsconfig.get('primkey'):
                        monumentid = value
                    if field == self.wikidatafield:
                        if value:
                            wditem = value
                        else:
                            wditem = True
                if monumentid and not wditem:
                    if monumentid in self.monuments:
                        qid = self.monuments.get(monumentid)

                        regex = u'(%s\s*\=\s*%s\s*\|)' % (self.monumentsconfig.get('primkey'), monumentid)
                        replace = u'\\1%s=%s|' % (self.wikidatafield, qid)

                        newtext = re.sub(regex, replace, newtext)
                        total_added +=1
        if total_added > 0:
            if total_added == total_templates:
                summary = u'Toevoegen Wikidata item ID aan alle %s monumenten op deze lijst' % (total_added,)
            else:
                summary = u'Toevoegen Wikidata item ID aan %s van de %s monumenten op deze lijst' % (total_added, total_templates)
            pywikibot.showDiff(text, newtext)
            pywikibot.output (summary)
            page.put(newtext, summary)




    def handleMonument(self, filepage):
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

        toadd = []

        # First collect the matches to add
        for match in matches:
            monumentid = match.group(u'id')
            if monumentid not in self.monuments:
                pywikibot.output(u'Found unknown monument id %s on %s, skipping' % (monumentid, filepage.title(),))
                return
            qid = self.monuments.get(monumentid)
            # Some cases the template is in the file text multiple times
            if (monumentid, qid) not in toadd:
                toadd.append((monumentid, qid))

        mediaid = u'M%s' % (filepage.pageid,)
        if self.mediaInfoHasStatement(mediaid, u'P180'):
            return
        i = 1
        for (monumentid, qid) in toadd:
            if len(toadd)==1:
                summary = u'based on [[Template:%s]] with id %s, which is the same id as [[:d:Property:%s|%s (%s)]] on [[:d:%s]]' % (self.template,
                                                                                                                                     monumentid,
                                                                                                                                     self.property,
                                                                                                                                     self.propertyname,
                                                                                                                                     self.property,
                                                                                                                                     qid, )
            else:
                summary = u'based on [[Template:%s]] with id %s, which is the same id as [[:d:Property:%s|%s (%s)]] on [[:d:%s]] (%s/%s)' % (self.template,
                                                                                                                                             monumentid,
                                                                                                                                             self.property,
                                                                                                                                             self.propertyname,
                                                                                                                                             self.property,
                                                                                                                                             qid,
                                                                                                                                             i,
                                                                                                                                             len(toadd))
            self.addClaim(mediaid, u'P180', qid, summary)
            i +=1

    def addClaim(self, mediaid, pid, qid, summary=''):
        """
        Add a claim to a mediaid

        :param mediaid: The mediaid to add it to
        :param pid: The property P id (including the P)
        :param qid: The item Q id (including the Q)
        :param summary: The summary to add in the edit
        :return: Nothing, edit in place
        """
        pywikibot.output(u'Adding %s->%s to %s. %s' % (pid, qid, mediaid, summary))

        tokenrequest = http.fetch(u'https://commons.wikimedia.org/w/api.php?action=query&meta=tokens&type=csrf&format=json')

        tokendata = json.loads(tokenrequest.text)
        token = tokendata.get(u'query').get(u'tokens').get(u'csrftoken')

        postvalue = {"entity-type":"item","numeric-id": qid.replace(u'Q', u'')}

        postdata = {u'action' : u'wbcreateclaim',
                    u'format' : u'json',
                    u'entity' : mediaid,
                    u'property' : pid,
                    u'snaktype' : u'value',
                    u'value' : json.dumps(postvalue),
                    u'token' : token,
                    u'summary' : summary,
                    u'bot' : True,
                    }
        apipage = http.fetch(u'https://commons.wikimedia.org/w/api.php', method='POST', data=postdata)

    def mediaInfoExists(self, mediaid):
        """
        Check if the media info exists or not
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :return: True if it exists, otherwise False
        """
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M72643194
        request = self.site._simple_request(action='wbgetentities',ids=mediaid)
        data = request.submit()
        if data.get(u'entities').get(mediaid).get(u'pageid'):
            return True
        return False

    def mediaInfoHasStatement(self, mediaid, property):
        """
        Check if the media info exists or not
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :param property: The property ID to check for (like P180)
        :return: True if it exists, otherwise False
        """
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M72643194
        request = self.site._simple_request(action='wbgetentities',ids=mediaid)
        data = request.submit()
        # No structured data at all is no pageid
        if not data.get(u'entities').get(mediaid).get(u'pageid'):
            return False
        # Has structured data, but the list of statements is empty
        if not data.get(u'entities').get(mediaid).get(u'statements'):
            return False
        if property in data.get(u'entities').get(mediaid).get(u'statements'):
            return True
        return False

def getDepictsMonumentsConfig():
    """
    Load the configuration from https://commons.wikimedia.org/wiki/User:ErfgoedBot/Depicts_monuments.js
    :return: Dict with the configuration
    """
    site = pywikibot.Site(u'commons', u'commons')
    pageTitle = u'User:ErfgoedBot/Depicts monuments.js'
    page = pywikibot.Page(site, title=pageTitle)

    jsonregex = u'^\/\*.+\n( \*.*\n)+(?P<json>(.+\n?)+)$'
    match = re.match (jsonregex, page.text)
    result = json.loads(match.group('json'))
    return result


def main(*args):
    wikidataToMonumentsListBot = WikidataToMonumentsListBot()
    wikidataToMonumentsListBot.run()
    """
    monumentproperty = None
    for arg in pywikibot.handle_args(args):
        if arg.startswith('-monumentproperty:'):
            if len(arg) == 18:
                monumentproperty = pywikibot.input(
                        u'Please enter the property you want to work on:')
            else:
                monumentproperty = arg[18:]
    config = getDepictsMonumentsConfig()
    if monumentproperty:
        if monumentproperty not in config.keys():
            pywikibot.output(u'%s is not a valid property to work on!' % (monumentproperty,))
            pywikibot.output(u'See https://commons.wikimedia.org/wiki/User:ErfgoedBot/Depicts_monuments.js')
            return
        depictsMonumentsBot = DepictsMonumentsBot(config.get(monumentproperty))
        depictsMonumentsBot.run()
    else:
        for monumentproperty in config.keys():
            depictsMonumentsBot = DepictsMonumentsBot(config.get(monumentproperty))
            depictsMonumentsBot.run()
    """

if __name__ == "__main__":
    main()
