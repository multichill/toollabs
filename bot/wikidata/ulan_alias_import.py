#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import missing labels and aliases from ULAN.
For labels it works on German, English, Spanish, French and Dutch. For aliases only on English.
Suggestions that are not Latin1 (for example Russian or Arabic) get filtered out.
"""
import json
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import requests

class UlanImportBot:
    """
    
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields wikidata item objects.

        """
        self.repo = pywikibot.Site().data_repository()
        self.generator = pagegenerators.PreloadingItemGenerator(generator)

    def run (self):
        """
        Work on all items
        """

        for item in self.generator:
            if not item.exists():
                continue

            if item.isRedirectPage():
                item = item.getRedirectTarget()

            data = item.get()
            claims = data.get('claims')

            if not u'P245' in claims:
                pywikibot.output(u'No ULAN  found, skipping')
                continue

            ulanid = claims.get(u'P245')[0].getTarget()
            #ulanurl = u'http://www.getty.edu/vow/ULANFullDisplay?find=&role=&nation=&subjectid=%s' % (ulanid,)
            ulanvocaburl = u'http://vocab.getty.edu/ulan/%s' % (ulanid,)
            ulanurljson = u'http://vocab.getty.edu/download/json?uri=http://vocab.getty.edu/ulan/%s.json' % (ulanid,)
            ulanPage = requests.get(ulanurljson)

            try:
                ulanPageDataDataObject = ulanPage.json()
            except ValueError:
                pywikibot.output('On %s I got a json error while working on %s, skipping it' % (item.title(), ulanurljson))
                continue

            # We have everything in JSON. We loop over it and grab the preferred label (=~Wikidata label) and the labels (=~Wikidata aliases)
            if ulanPageDataDataObject.get(u'results'):
                if ulanPageDataDataObject.get(u'results').get(u'bindings'):
                    (prefLabel, allLabels) = self.getLabels(ulanPageDataDataObject.get(u'results').get(u'bindings'),
                                                            ulanvocaburl)
                    #pywikibot.output(prefLabel)
                    #pywikibot.output(allLabels)

                    if not prefLabel:
                        pywikibot.output(u'No preferred label found, skipping this one')
                        continue
                    currentlabel = self.updateLabels(item, prefLabel, ulanid)
                    aliaseschanged = self.updateEnglishAliases(item, currentlabel, allLabels, ulanid)

    def getLabels(self, bindings, ulanvocaburl):
        """
        Loop over a bunch of bindings and return the prefered label
        :param bindings:
        :return:
        """
        prefLabel = u''
        allLabels = [] # Should probably be a set

        for binding in bindings:
            # We only care about this item and literals
            if binding.get(u'Subject').get(u'type')==u'uri' and binding.get(u'Subject').get(u'value')==ulanvocaburl and binding.get(u'Object').get(u'type')==u'literal':
                if binding.get(u'Predicate').get(u'type')==u'uri' and binding.get(u'Predicate').get(u'value')==u'http://www.w3.org/2004/02/skos/core#prefLabel':
                    templabel = binding.get(u'Object').get(u'value')
                    if self.checkLatin(templabel):
                        prefLabel = self.normalizeName(templabel)
                elif binding.get(u'Predicate').get(u'type')==u'uri' and binding.get(u'Predicate').get(u'value')==u'http://www.w3.org/2000/01/rdf-schema#label':
                    templabel = binding.get(u'Object').get(u'value')
                    if not binding.get(u'Object').get(u'xml:lang'):
                        if self.checkLatin(templabel):
                            allLabels.append(self.normalizeName(templabel))
                    elif binding.get(u'Object').get(u'xml:lang') and binding.get(u'Object').get(u'xml:lang')=='en':
                        allLabels.append(self.normalizeName(templabel))

        return (prefLabel, allLabels)

    def checkLatin(self, label):
        """
        Check if a label is Latin1 or Latin2.
        Latin1 covers most of Western Europe, Latin2 covers most of Eastern Europe
        Full table is at https://docs.python.org/2/library/codecs.html
        """
        try:
            label.encode(u'latin1')
            return True
        except UnicodeEncodeError:
            pywikibot.output(u'Encoding it as latin1 did not work. Trying latin2 for label %s' % (label, ))
            try:
                label.encode(u'latin2')
                return True
            except UnicodeEncodeError:
                pywikibot.output(u'That did not work either. Filtering out non-Latin1/2 label %s' % (label, ))
                return False

    def normalizeName(self, name):
        """
        Helper function to normalize the name
        """
        if u',' in name:
            (surname, sep, firstname) = name.partition(u',')
            name = u'%s %s' % (firstname.strip(), surname.strip(),)
        return name

    def updateLabels(self, item, prefLabel, ulanid):
        """
        Update the Wikidata labels on the item based on prefLabel
        Return the English label (can be an empty string)
        """
        data = item.get()
        wdlabels = data.get('labels')
        # The item doesn't have a label in my languages. Let's fix that!
        mylangs = [u'ca', u'da', u'de', u'en', u'es', u'fr', u'it', u'nl', u'pt', u'sv']
        if wdlabels:
            currentlabel = wdlabels.get(u'en')
        else:
            pywikibot.output(u'This item doesn\'t have any labels!')
            wdlabels = {}
            currentlabel = u''

        labelschanged = 0
        for mylang in mylangs:
            if not wdlabels.get(mylang):
                wdlabels[mylang] = prefLabel
                labelschanged = labelschanged + 1
                if mylang==u'en':
                    currentlabel=prefLabel

        if labelschanged:
            summary = u'Added missing labels in %s languages based on ULAN %s' % (labelschanged, ulanid)
            pywikibot.output(summary)
            try:
                pywikibot.output(summary)
                item.editLabels(wdlabels, summary=summary)
            except pywikibot.data.api.APIError:
                pywikibot.output(u'Couldn\'t update the labels, conflicts with another item')
            except pywikibot.exceptions.OtherPageSaveError:
                pywikibot.output(u'Couldn\'t update the labels, conflicts with another item')
        return currentlabel

    def updateEnglishAliases(self, item, currentlabel, allLabels, ulanid):
        """
        Update the Wikidata aliases on the item based on allLabels. Will skip the currentlabel.
        Returns the number of updated aliases
        """
        # Only do this in English
        data = item.get()
        aliases = data.get('aliases').get(u'en')

        if not aliases:
            #pywikibot.output(u'This item doesn\'t have any English aliases!')
            aliases = []
        aliaseschanged = 0

        for newalias in set(allLabels):
            if newalias!=currentlabel and not newalias in aliases:
                aliases.append(newalias)
                aliaseschanged = aliaseschanged + 1

        if aliaseschanged:
            summary = u'Added %s missing aliases in English based on ULAN %s' % (aliaseschanged,ulanid)
            pywikibot.output(summary)
            try:
                item.editAliases({u'en' : aliases}, summary=summary)
            except pywikibot.data.api.APIError:
                pywikibot.output(u'Couldn\'t update the aliases, item is probably already in conflicted state')
            except pywikibot.exceptions.OtherPageSaveError:
                pywikibot.output(u'Couldn\'t update the aliases, item is probably already in conflicted state')
        return aliaseschanged

def main(*args):
    """
    Run the bot. By default it only runs on the items changed in the last 14 days.
    """
    fullrun = False
    days = u'14'
    for arg in pywikibot.handle_args(args):
        if arg=='-full':
            fullrun = True
        elif arg.startswith('-days:'):
            if len(arg) == 6:
                days = pywikibot.input(
                    u'Please enter the number of days you want to work on:')
            else:
                days = arg[6:]

    if fullrun:
        pywikibot.output(u'Doing a full run')
        query = u"""SELECT DISTINCT ?item WHERE { 
  ?item wdt:P245 [] . 
  ?item wdt:P31 wd:Q5 .
  ?item wdt:P106/wdt:P279* wd:Q3391743  . 
}"""
    else:
        pywikibot.output(u'Doing a run on the items modified in the last %s days' % (days,) )
        query = u"""SELECT DISTINCT ?item {
  ?item wdt:P245 [] . ?item wdt:P31 wd:Q5 .
  ?item schema:dateModified ?date_modified .
  BIND (now() - ?date_modified as ?date_range)
  FILTER (?date_range < %s) .
  ?item wdt:P106/wdt:P279* wd:Q3391743 
}""" % (days,)

    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))
    
    ulanImportBot = UlanImportBot(generator)
    ulanImportBot.run()

if __name__ == "__main__":
    main()
