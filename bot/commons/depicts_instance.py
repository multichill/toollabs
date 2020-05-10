#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to replace depicts statements of classes with specific instances based on the category

For example a lot of church buildings are tagged as such, but are in a category for
the specific church. This bot will pick that up and replace it.

Should be switched to a more general Pywikibot implementation.
"""

import pywikibot
import pywikibot.data.sparql
from pywikibot.comms import http
import json
from pywikibot import pagegenerators

class DepictsInstanceBot:
    """
    """
    def __init__(self, depictsclass, gen):
        """
        Make the bot ready to run
        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()
        self.depictsclass = depictsclass
        self.depictssubclasses = self.getDepictsSubclasses(depictsclass)
        self.generator = gen

    def getDepictsSubclasses(self, depictsclass):
        """
        Get the subclasses of the depictsclass
        :return:
        """
        result = []
        query = '''SELECT ?item WHERE { ?item wdt:P279+ wd:Q16970 } LIMIT 2500'''

        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result.append(qid)
        return result

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
            self.processFile(filepage, mediaid, currentdata)

    def getCurrentMediaInfo(self, mediaid):
        """
        Check if the media info exists. If that's the case, return that so we can check against it
        Otherwise return an empty dict
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :return: dict
        """
        request = self.site._simple_request(action='wbgetentities',ids=mediaid)
        data = request.submit()
        if data.get(u'entities').get(mediaid).get(u'pageid'):
            return data.get(u'entities').get(mediaid)
        return {}

    def processFile(self, filepage, mediaid, currentdata):
        """
        Handle a file.
        Get the better item based on the category and do the replacement.

        :param filepage: The page of the file to work on.
        :param mediaid: The mediaid of the file (like M12345)
        :param currentdata: Dict with the current structured data
        :return: Nothing, edit in place
        """
        pywikibot.output(u'Working on %s' % (filepage.title(),))
        if not filepage.exists():
            return

        if not currentdata.get('statements'):
            return

        if not currentdata.get('statements').get('P180'):
            return

        # I need the id of the existing statement to replace it later on
        foundClassStatementId = False

        for statement in currentdata.get('statements').get('P180'):
            if statement.get('mainsnak').get('datavalue'):
                if statement.get('mainsnak').get('datavalue').get('value').get('id')==self.depictsclass:
                    foundClassStatementId = statement.get('id')
                    if statement.get('qualifiers'):
                        # I can't handle qualifiers, skip it.
                        return
                    break

        instanceqid = self.getInstanceFromCategories(filepage)

        if not instanceqid:
            return

        # Check to make sure that the statement isn't already on the file
        for statement in currentdata.get('statements').get('P180'):
            if statement.get('mainsnak').get('datavalue'):
                if statement.get('mainsnak').get('datavalue').get('value').get('id')==instanceqid:
                    return

        summary = 'adding specific instance for [[d:Special:EntityPage/%s]] based on category' % (self.depictsclass,)

        token = self.site.tokens['csrf']
        postdata = {'action' : 'wbsetclaimvalue',
                    'format' : 'json',
                    'claim' : foundClassStatementId,
                    'snaktype' : 'value',
                    'value' : json.dumps({'entity-type' : 'item',
                                'numeric-id' : int(instanceqid.replace('Q', ''))}),
                    'token' : token,
                    'summary' : summary,
                    'bot' : True,
                    }
        pywikibot.output('Replacing %s with %s' % (self.depictsclass, instanceqid))
        request = self.site._simple_request(**postdata)
        data = request.submit()

    def getInstanceFromCategories(self, filepage):
        """
        Get the specific instance based on the categories on the file
        :param filepage: The page of the file to work on.
        :return: The id of the instance or None
        """
        for category in filepage.categories():
            if not category.isHiddenCategory():
                instance = self.getInstanceFromCategory(category)
                if instance:
                    return instance
        return None

    def getInstanceFromCategory(self, category):
        """
        Try to get the instance from one category
        :param category: The category page to work on
        :return: The id of the instance or None
        """
        try:
            item = category.data_item()
        except pywikibot.exceptions.NoPage:
            return None

        data = item.get()
        claims = data.get('claims')
        if not 'P31' in claims:
            return None

        foundcategory = False
        for claim in claims.get('P31'):
            if claim.getTarget().getID() == self.depictsclass:
                return item.getID()
            elif claim.getTarget().getID() in self.depictssubclasses:
                return item.getID()
            elif claim.getTarget().getID() == 'Q4167836':
                foundcategory = True
                break

        # Handle category items
        if foundcategory and 'P301' in claims:
            item = claims.get('P301')[0].getTarget()
            data = item.get()
            claims = data.get('claims')
            if not 'P31' in claims:
                return None

            for claim in claims.get('P31'):
                if claim.getTarget().getID()==self.depictsclass:
                    return item.getID()
        return None


def main(*args):
    gen = None
    genFactory = pagegenerators.GeneratorFactory()
    depictsclass = None

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-depictsclass:'):
            depictsclass = arg[14:]
        elif genFactory.handleArg(arg):
            continue
    gen = genFactory.getCombinedGenerator(gen, preload=True)

    if not depictsclass or not gen:
        pywikibot.output('Usage example: depicts_instance.py -depictsclass:Q16970 -lang:commons -family:commons -namespace:6 -search:"haswbstatement:P180=Q16970"')
        return

    depictsInstanceBot = DepictsInstanceBot(depictsclass, gen)
    depictsInstanceBot.run()

if __name__ == "__main__":
    main()
