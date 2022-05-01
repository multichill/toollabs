#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add the main subject to portrait paintings or fall back adding depict.

Also uses the configuration at https://www.wikidata.org/wiki/User:BotMultichillT/portrait_paintings.js

"""
import json
import pywikibot
from pywikibot import pagegenerators
import re
import requests
import csv

class GenreExtractionBot:
    """
    A bot to add main subject to paintings on Wikidata
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields Wikidata items objects.

        """
        self.repo = pywikibot.Site().data_repository()
        self.genres = { u'portrait' : u'Q134307',
                        u'religious_art' : u'Q2864737',
                        u'landscape_art' : u'Q191163',
                        u'genre_art' : u'Q1047337',
                        u'still_life' : u'Q170571',
                        }
        #self.langlabelpairs = self.getConfiguration()
        self.generators = {}
        for genre in self.genres:
            self.generators[genre] = self.getGenerator(self.genres.get(genre))

    def getGenerator(self, genre):
        """
        Build a SPARQL query to get interesting items to work on
        :return: A generator that yields items
        """
        firstfilter = True
        query = """SELECT ?item WHERE {
  ?item wdt:P136 wd:%s .
  ?item wdt:P31 wd:Q3305213 .
  MINUS { ?item wdt:P136 ?genre . FILTER (?genre!=wd:%s) }
  } LIMIT 1000""" % (genre, genre)
        return pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=self.repo))

    def run(self):
        """
        Starts the robot.
        """
        with open('genredatatrain.csv', 'w', newline='', encoding='utf-8') as csv_train:
            trainwriter = csv.writer(csv_train, delimiter=',')
            trainwriter.writerow([u'text', u'genre'])
            with open('genredatatest.csv', 'w', newline='', encoding='utf-8') as csv_test:
                testwriter = csv.writer(csv_test, delimiter=',')
                testwriter.writerow([u'text', u'genre'])
                for genre in self.genres:
                    i = 0
                    for item in self.generators.get(genre):
                        paintingtext = self.extractSinglePainting(item)
                        print (genre)
                        print (paintingtext)
                        # One in 4 to the test set
                        if i % 4 !=0:
                            trainwriter.writerow([paintingtext, genre])
                        else:
                            testwriter.writerow([paintingtext, genre])
                        i += 1

    def extractSinglePainting(self, item):
        """
        Get the data for a single painting
        :param item: The item of the painting
        :return: A string
        """
        result = []
        langs = [u'de', u'en', u'es', u'fr', u'nl', u'sv']
        itemname = item.title()
        pywikibot.output(u'Working on %s' % (itemname,))
        # Could switch this to the Pywikibot http stuff
        #headers = {'Content-type': 'application/ld+json'}
        #page = requests.get(u'http://www.wikidata.org/entity/%s' % (itemname,), headers=headers)
        page = requests.get(u'https://www.wikidata.org/wiki/Special:EntityData?id=%s&format=jsonld' % (itemname,))

        #page = requests.get(u'https://www.wikidata.org/wiki/Special:EntityData/%s.jslonld' % (itemname,))
        #print (page.text)
        graph = page.json().get(u'@graph')

        wantedprops = []
        wanteditems = []

        for entry in graph:
            if entry.get(u'@id')==u'wd:%s' % (itemname,):
                itemfields = [ u'label', u'prefLabel', u'name', u'description'] # Alias?
                for itemfield in itemfields:
                    if entry.get(itemfield):
                        for itementry in entry.get(itemfield):
                            if isinstance(itementry, dict):
                                result.append(itementry.get(u'@value'))
                for entrykey in entry:
                    if entrykey.startswith(u'P') and not entrykey==u'P136':
                        wantedprops.append(entrykey)
                        if isinstance(entry.get(entrykey), str):
                            if entry.get(entrykey).startswith(u'wd:'):
                                wanteditems.append(entry.get(entrykey))
                        elif isinstance(entry.get(entrykey), list):
                            for listentry in entry.get(entrykey):
                                if isinstance(listentry, str) and listentry.startswith(u'wd:'):
                                    wanteditems.append(listentry)
                #print (wantedprops)
                #print (wanteditems)

            elif entry.get(u'@id').startswith(u'wd:Q') and entry.get(u'@id') in wanteditems:
                itemfields = [ u'label']
                for itemfield in itemfields:
                    if entry.get(itemfield):
                        for itementry in entry.get(itemfield):
                            if isinstance(itementry, dict) and itementry.get(u'@language') in langs:
                                result.append(itementry.get(u'@value'))
            elif entry.get(u'@id').startswith(u'wd:P') and entry.get(u'@id').replace(u'wd:', u'') in wantedprops:
                itemfields = [ u'label']
                for itemfield in itemfields:
                    if entry.get(itemfield):
                        for itementry in entry.get(itemfield):
                            if isinstance(itementry, dict) and itementry.get(u'@language') in langs:
                                result.append(itementry.get(u'@value'))
        return u' '.join(result)






    def processPainting(self, item):
        """
        Work on a individual painting.
        """
        data = item.get()
        claims = data.get('claims')
        labels = item.get().get('labels')

        if u'P921' in claims:
            # Already done
            return

        if u'P136' in claims:
            # Check if it's a portrait
            if not claims.get(u'P136')[0].target_equals(u'Q134307'):
                # Found another genre, don't continue
                return

        labelregex = u'^(Portrait of )?(?P<name>.+)\s*\((?P<yob>\d\d\d\d)-(?P<yod>\d\d\d\d)\)(?P<labelend>.*)$'
        labelmatch = re.match(labelregex, labels.get(u'en'))

        if not labelmatch:
            print(u'No match?')
            return

        name = labelmatch.group(u'name').strip()
        yob = labelmatch.group(u'yob')
        yod = labelmatch.group(u'yod')
        labelend = labelmatch.group(u'labelend')

        personitem = self.findPerson(name, yob, yod)
        if not personitem:
            return

        if isinstance(personitem, pywikibot.ItemPage):
            # Labelend is empty so we have an exact match
            if not labelend:
                summary = u'based on %s (%s-%s)' % (name, yob, yod)
                mainsubjectclaim = pywikibot.Claim(self.repo, u'P921')
                mainsubjectclaim.setTarget(personitem)
                pywikibot.output('Adding main subject claim to %s %s' % (item.title(), summary))
                item.addClaim(mainsubjectclaim, summary=summary)
                # Exact match, also add depicts if it's missing
                if u'P180' not in claims:
                    depictsclaim = pywikibot.Claim(self.repo, u'P180')
                    depictsclaim.setTarget(personitem)
                    pywikibot.output('Adding depicts claim to %s %s' % (item.title(), summary))
                    item.addClaim(depictsclaim, summary=summary)
                # Exact match, also add portrait genre if it's missing
                if u'P136' not in claims:
                    genreclaim = pywikibot.Claim(self.repo, u'P136')
                    genreclaim.setTarget(pywikibot.ItemPage(self.repo, u'Q134307'))
                    pywikibot.output('Adding genre claim to %s %s' % (item.title(), summary))
                    item.addClaim(genreclaim, summary=summary)

            # We don't have an exact match, just fall back to adding depicts
            elif labelend and u'P180' not in claims:
                summary = u'based on %s (%s-%s)%s' % (name, yob, yod, labelend)
                depictsclaim = pywikibot.Claim(self.repo, u'P180')
                depictsclaim.setTarget(personitem)
                pywikibot.output('Adding depicts claim to %s %s' % (item.title(), summary))
                item.addClaim(depictsclaim, summary=summary)
        # The name was a valid name, just not the right date of birth/death, but it is a portrait
        elif personitem and not labelend and u'P136' not in claims:
            summary = u'based on the name "%s" in the label' % (name, )
            genreclaim = pywikibot.Claim(self.repo, u'P136')
            genreclaim.setTarget(pywikibot.ItemPage(self.repo, u'Q134307'))
            pywikibot.output('Adding genre claim to %s %s' % (item.title(), summary))
            item.addClaim(genreclaim, summary=summary)

    def findPerson(self, name, yob, yod):
        """
        Find a person.
        :param name: Name of the person
        :param yob: Year of birth of the person
        :param yod: Year of death of the person
        :return: ItemPage if a person is found
        """
        # Search Wikidata for a suitable candidate, tell the search to only return humans
        searchstring = u'"%s" haswbstatement:P31=Q5' % (name,)
        persongen = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataItemGenerator(pagegenerators.SearchPageGenerator(searchstring, step=None, total=50, namespaces=[0], site=self.repo)))

        foundperson = False

        for personitem in persongen:
            #print (u'Possible match %s' % (personitem.title(),))
            if personitem.isRedirectPage():
                personitem = personitem.getRedirectTarget()
            # See if the label or one of the aliases of the creatoritem matches the string we have. Only label is case insensitive.
            #if (personitem.get().get('labels').get('en') and personitem.get().get('labels').get('en').lower() == name.lower()) or (personitem.get().get('aliases').get('en') and name in personitem.get().get('aliases').get('en')):
            #    print (u'Label match for %s' % (personitem.title(),))
            #    # Check of year of birth and year of death match
            if u'P569' in personitem.get().get('claims') and u'P570' in personitem.get().get('claims'):
                dob = personitem.get().get('claims').get('P569')[0].getTarget()
                dod = personitem.get().get('claims').get('P570')[0].getTarget()
                foundperson = True
                if dob and dod:
                    #print (u'Date found dob "%s" "%s" "%s"' % (dob, dob.year, yob))
                    #print (u'Date found dod "%s" "%s" "%s"' % (dod, dod.year, yod))
                    if int(dob.year)==int(yob) and int(dod.year)==int(yod):
                        #print (u'maaaaaaaaaaaaaaaaaaaaaaaatcchhhhh')
                        return personitem
        return foundperson

def main():
    """
    Just a main function to start the robot
    """
    genreExtractionBot = GenreExtractionBot()
    genreExtractionBot.run()

if __name__ == "__main__":
    main()
