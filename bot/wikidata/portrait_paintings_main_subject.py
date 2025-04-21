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

class PortraitPaintingsBot:
    """
    A bot to add main subject to paintings on Wikidata
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields Wikidata items objects.

        """
        self.repo = pywikibot.Site().data_repository()
        self.langlabelpairs = self.getConfiguration()
        self.generator = self.getGenerator()

    def getConfiguration(self):
        """
        Grab the configuration of tuples to work on
        :return: List of tuples
        """
        result = []
        configpage = pywikibot.Page(self.repo, title=u'User:BotMultichillT/portrait paintings.js')
        (comments, sep, jsondata) = configpage.get().partition(u'[')
        jsondata = u'[' + jsondata
        configjson = json.loads(jsondata)
        for workitem in configjson:
            langlabelpair = (workitem.get('lang'), workitem.get('labelstart'))
            result.append(langlabelpair)
        return result

    def getGenerator(self):
        """
        Build a SPARQL query to get interesting items to work on
        :return: A generator that yields items
        """
        query = """SELECT DISTINCT ?item ?itemlabel WHERE {
  ?item wdt:P31 wd:Q3305213 ;
        wdt:P136 wd:Q134307 ;
        schema:dateModified ?date .
  MINUS { ?item wdt:P921 [] } .
  MINUS { ?item wdt:P180 [] } .
  MINUS { ?item wdt:P136 ?genre. FILTER(?genre!=wd:Q134307) } 
  ?item rdfs:label ?itemlabel .
  FILTER(LANG(?itemlabel)="en" && REGEX(STR(?itemlabel), "^.+\\\\(\\\\d\\\\d\\\\d\\\\d[-–]\\\\d\\\\d\\\\d\\\\d\\\\).*$"))
} LIMIT 25000"""
        return pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=self.repo))

    def run(self):
        """
        Starts the robot.
        """
        for item in self.generator:
            self.processPainting(item)

    def processPainting(self, item):
        """
        Work on a individual painting.
        """
        data = item.get()
        claims = data.get('claims')
        labels = item.get().get('labels')

        pywikibot.output('Working on %s' % (item.title(),))

        if 'P921' in claims:
            pywikibot.output('Already has a main subject, done')
            return

        if 'P136' in claims:
            # Check if it's a portrait
            if not claims.get(u'P136')[0].target_equals('Q134307'):
                # Found another genre, don't continue
                return

        labelregex = u'^(Portrait of )?(?P<name>.+)\s*\((?P<yob>\d\d\d\d)[-–](?P<yod>\d\d\d\d)\)(?P<labelend>.*)$'
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

        pywikibot.output(f'Search for "{name}" ({yob}-{yod})')
        persongen = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikibaseItemGenerator(pagegenerators.SearchPageGenerator(searchstring, total=50, namespaces=[0], site=self.repo)))

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
    portraitPaintingsBot = PortraitPaintingsBot()
    portraitPaintingsBot.run()

if __name__ == "__main__":
    main()
