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
import random
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer


class GenreTfidBot:
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

        # Load training data
        f = open('genredatatrain.csv')
        train_rows = [row for row in csv.reader(f)][1:]  # discard the first row
        random.shuffle(train_rows)
        genre_train = [row[0].decode('utf8') for row in train_rows]
        classes_train = [row[1] for row in train_rows]

        # Load testing data
        f = open('genredatatest.csv') # _2020-01-01.csv')
        test_rows = [row for row in csv.reader(f)][1:]  # discard the first row
        genre_test = [row[0].decode('utf8') for row in test_rows]
        classes_test = [row[1] for row in test_rows]

        self.pipeline_tfidf = Pipeline(steps=[('vectorizer', TfidfVectorizer(ngram_range=(1, 2))),
                                              ('classifier', LogisticRegression())])

        self.pipeline_tfidf.fit(genre_train, classes_train)
        pywikibot.output('Success score for this set: %s' % (self.pipeline_tfidf.score(genre_test, classes_test),))

        #self.langlabelpairs = self.getConfiguration()
        self.generator = self.getGenerator()

    def getGenerator(self):
        """
        Build a SPARQL query to get interesting items to work on
        :return: A generator that yields items
        """
        query = """SELECT ?item WHERE {
  ?item wdt:P31 wd:Q3305213 .
  MINUS { ?item wdt:P136 [] } .
  #?item wdt:P18 [] .
  ?item wdt:P195 wd:Q1459037 . 
  } LIMIT 1000"""
        return pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=self.repo))

    def run(self):
        """
        Starts the robot.
        """
        for item in self.generator:
            paintingtext = self.extractSinglePainting(item)

            topredict = [paintingtext,]
            proba = self.pipeline_tfidf.predict_proba(topredict)

            highproba = False
            for p in proba[0]:
                if p > 0.50:
                    highproba = True
            if highproba:
                pywikibot.output (paintingtext)
                pywikibot.output (u'https://www.wikidata.org/wiki/%s' % (item.title(),))
                pywikibot.output (proba)
                pywikibot.output (self.pipeline_tfidf.predict(topredict))

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


def main():
    """
    Just a main function to start the robot
    """
    genreTfidBot = GenreTfidBot()
    genreTfidBot.run()

    return

    # Load training data
    f = open('genredatatrain.csv') #_2020-01-01.csv')
    train_rows = [row for row in csv.reader(f)][1:]  # discard the first row
    random.shuffle(train_rows)
    genre_train = [row[0].decode('utf8') for row in train_rows]
    classes_train = [row[1] for row in train_rows]

    # Load testing data
    f = open('genredatatest.csv') # _2020-01-01.csv')
    test_rows = [row for row in csv.reader(f)][1:]  # discard the first row
    genre_test = [row[0].decode('utf8') for row in test_rows]
    classes_test = [row[1] for row in test_rows]

    vectorizer = TfidfVectorizer(ngram_range=(1, 2))

    pipeline_tfidf = Pipeline(steps=[('vectorizer', vectorizer),
                                     ('classifier', LogisticRegression())])

    pipeline_tfidf.fit(genre_train, classes_train)

    #print genre_test[10:14]
    #print (pipeline_tfidf.predict_proba(genre_test))
    #print (pipeline_tfidf.predict(genre_test))
    #print (vectorizer.get_feature_names())

    #return
    for train_size in (20, 50, 100, 200, 500, 1000, 2000, 3000, len(genre_train)):
        print(train_size, '--------------------------------------')

        # tfidf
        pipeline_tfidf.fit(genre_train[:train_size], classes_train[:train_size])
        print('tfidf', pipeline_tfidf.score(genre_test, classes_test))


if __name__ == "__main__":
    main()
