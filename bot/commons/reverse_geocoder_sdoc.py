#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add the location of creation (P1071) based on coordinates.

Should be switched to a more general Pywikibot implementation.

"""

import pywikibot
# import re
import pywikibot.data.sparql
import time
import json
import requests
from pywikibot import pagegenerators

class ReverseGeocodingBot:
    """
    Bot to add structured data statements on Commons
    """
    def __init__(self, generator):
        """
        Grab generator based on search to work on.
        """
        self.site = pywikibot.Site('commons', 'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()
        self.generator = generator

    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            print(filepage.title())
            self.add_location(filepage)

    def add_location(self, filepage):
        """

        :param mediainfo:
        :return:
        """

        #summary = 'Fix [[Commons:Structured data/Modeling/Location|location]]:'
        #claims = []
        #location_of_creation = None
        #location_of_creation_source = None
        #location = None
        #location_snak = None
        #admin_location = None
        #admin_location_snak = None
        #country = None
        #country_snak = None
        mediainfo = filepage.data_item()
        if not mediainfo:
            return

        try:
            statements = mediainfo.statements
        except KeyError:
            # Bug in Pywikibot, no statements
            return

        # Check if we already have location of creation
        if 'P1071' in statements:
            return

        coordinates = None

        if 'P1259' in statements:
            coordinates = statements.get('P1259')[0].getTarget()
        elif 'P9149' in statements:
            coordinates = statements.get('P9149')[0].getTarget()

        if not coordinates:
            return

        location_of_creation = self.lookup_location(coordinates.lat, coordinates.lon)

        if not location_of_creation:
            return
        print(location_of_creation)

        summary = '[[d:Special:EntityPage/P1071]]→[[d:Special:EntityPage/%s]]' % (location_of_creation, )
        summary += ' based on [[Commons:Reverse geocoding|reverse geocoding]] %s° N %s° E' % (coordinates.lat, coordinates.lon)

        location_of_creation_item = pywikibot.ItemPage(self.repo, title=location_of_creation)
        newclaim = pywikibot.Claim(self.repo, 'P1071')
        newclaim.setTarget(location_of_creation_item)

        data = {'claims': [newclaim.toJSON(), ]}
        try:
            print(data)
            response = self.site.editEntity(mediainfo, data, summary=summary)
            filepage.touch()
        except pywikibot.exceptions.APIError as e:
            print(e)




    def lookup_location(self, lat, lon, tries=3):
        """
        Do reverse geocoding based on latitude & longitude and return Wikidata item
        :param lat: The latitude
        :parim lon: The longitude
        :return: Wikidata item
        """
        qid = None
        url = 'http://edwardbetts.com/geocode/?lat=%s&lon=%s' % (lat, lon)
        print(url)
        try:
            page = requests.get(url)
            jsondata = page.json()
            print(jsondata)
        except ValueError:
            # Either json.decoder.JSONDecodeError or simplejson.scanner.JSONDecodeError, both subclass of ValueError
            pywikibot.output('Got invalid json at %s' % (url,))
            time.sleep(60)
            if tries > 0:
                return self.lookup_location(lat, lon, tries=tries-1)
            return qid
        except IOError:
            # RequestExceptions was thrown
            pywikibot.output('Got an IOError at %s' % (url,))
            time.sleep(60)
            if tries > 0:
                return self.lookup_location(lat, lon, tries=tries-1)
            return qid

        if not jsondata.get('missing'):
            if jsondata.get('wikidata') and jsondata.get('admin_level'):
                if jsondata.get('admin_level') > 9:
                    qid = jsondata.get('wikidata')
                else:
                    print('admin_level too low')
        return qid


def mediainfo_to_fix_generator():
    site = pywikibot.Site('commons', 'commons')
    search_strings = ['File: haswbstatement:P17 -haswbstatement:P276 -haswbstatement:P131 -haswbstatement:P1071',
                      'File: haswbstatement:P131 -haswbstatement:P1071',
                      'File: haswbstatement:P276 -haswbstatement:P1071',
                      'File: haswbstatement:P276 haswbstatement:P131 haswbstatement:P17',
                      'File: haswbstatement:P276 haswbstatement:P131 -haswbstatement:P17',
                      'File: haswbstatement:P276 -haswbstatement:P131 -haswbstatement:P17',
                      'File: -haswbstatement:P276 haswbstatement:P131 haswbstatement:P17',
                      'File: -haswbstatement:P276 haswbstatement:P131 -haswbstatement:P17',
                      'File: -haswbstatement:P276 -haswbstatement:P131 haswbstatement:P17',
                      ]
    for search in search_strings:
        print(search)
        # Do something with preloading here?
        gen = pagegenerators.PageClassGenerator(pagegenerators.SearchPageGenerator(search, namespaces=[6], site=site))
        for filepage in gen:
            print(filepage.title())
            yield filepage.data_item()



def main(*args):
    """

    :param args:
    :return:
    """
    #site = pywikibot.Site('commons', 'commons')
    gen = None

    genFactory = pagegenerators.GeneratorFactory()

    for arg in pywikibot.handle_args(args):
        if arg == '-loose':
            pass
        elif genFactory.handle_arg(arg):
            continue


    gen = pagegenerators.PageClassGenerator(genFactory.getCombinedGenerator(gen, preload=True))

    reverse_geocoding_bot = ReverseGeocodingBot(gen)
    reverse_geocoding_bot.run()


if __name__ == "__main__":
    main()
