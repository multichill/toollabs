#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to fix Structured Data location statements:
* location (P276)
* located in the administrative territorial entity (P131)
* country (P17)
and replace with location of creation (P1071)

Should be switched to a more general Pywikibot implementation.

"""

import pywikibot
# import re
import pywikibot.data.sparql
# import time
# import json
from pywikibot import pagegenerators

class FixLocationBot:
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
        for mediainfo in self.generator:
            self.fix_location(mediainfo)

    def fix_location(self, mediainfo):
        """

        :param mediainfo:
        :return:
        """
        summary = 'Fix [[Commons:Structured data/Modeling/Location|location]]:'
        claims = []
        location_of_creation = None
        location_of_creation_source = None
        location = None
        location_snak = None
        admin_location = None
        admin_location_snak = None
        country = None
        country_snak = None
        statements = mediainfo.statements

        # Check if we already have location of creation
        if 'P1071' in statements:
            if len(statements.get('P1071')) == 1:
                location_of_creation = statements.get('P1071')[0].getTarget()
                if not location_of_creation:
                    return
                elif location_of_creation.isRedirectPage():
                    location_of_creation = location_of_creation.getRedirectTarget()
                    newclaim = statements.get('P1071')[0]
                    newclaim.setTarget(location_of_creation)
                    summary += ' resolve redirect [[d:Special:EntityPage/P1071]]'
                    claims.append(newclaim.toJSON())
                location_of_creation_source = 'location_of_creation'
            else:
                return
        #print(location_of_creation)

        # Check if we already have location
        if 'P276' in statements:
            if len(statements.get('P276')) == 1:
                location = statements.get('P276')[0].getTarget()
                if location.isRedirectPage():
                    location = location.getRedirectTarget()
                location_snak = statements.get('P276')[0].snak
            else:
                return
        #print(location)

        if 'P131' in statements:
            if len(statements.get('P131')) == 1:
                admin_location = statements.get('P131')[0].getTarget()
                if admin_location.isRedirectPage():
                    admin_location = admin_location.getRedirectTarget()
                admin_location_snak = statements.get('P131')[0].snak
            else:
                return
        #print(admin_location)

        if 'P17' in statements:
            if len(statements.get('P17')) == 1:
                country = statements.get('P17')[0].getTarget()
                if country.isRedirectPage():
                    country = country.getRedirectTarget()
                country_snak = statements.get('P17')[0].snak
            else:
                return
        #print(admin_location)


        if not location_of_creation:
            if location:
                summary += ' move [[d:Special:EntityPage/P276]] to [[d:Special:EntityPage/P1071]]'
                location_of_creation = location
                location_of_creation_source = 'location'
            elif admin_location:
                summary += ' move [[d:Special:EntityPage/P131]] to [[d:Special:EntityPage/P1071]]'
                location_of_creation = admin_location
                location_of_creation_source = 'admin_location'
            elif country:
                summary += ' move [[d:Special:EntityPage/P17]] to [[d:Special:EntityPage/P1071]]'
                location_of_creation = country
                location_of_creation_source = 'country'
            if location_of_creation:
                newclaim = pywikibot.Claim(self.repo, 'P1071')
                newclaim.setTarget(location_of_creation)
                claims.append(newclaim.toJSON())

        if not location_of_creation:
            return

        if location_of_creation == location:
            if not location_of_creation_source == 'location':
                summary += ' remove [[d:Special:EntityPage/P276]] (same as [[d:Special:EntityPage/P1071]])'
            claims.append({'id': location_snak, 'remove': ''})

        if location_of_creation == admin_location:
            if not location_of_creation_source == 'admin_location':
                summary += ' remove [[d:Special:EntityPage/P131]] (same as [[d:Special:EntityPage/P1071]])'
            claims.append({'id': admin_location_snak, 'remove': ''})

        if location_of_creation == country:
            if not location_of_creation_source == 'country':
                summary += ' remove [[d:Special:EntityPage/P17]] (same as [[d:Special:EntityPage/P1071]])'
            claims.append({'id': country_snak, 'remove': ''})

        if admin_location or country:
            #location_of_creation_item = pywikibot.ItemPage(self.repo, title=location_of_creation)
            item_claims = location_of_creation.get('data').get('claims')
            if 'P131' in item_claims:
                if item_claims.get('P131')[0].getTarget() == admin_location:
                    summary += ' remove [[d:Special:EntityPage/P131]] (it\'s on [[d:Special:EntityPage/P1071]])'
                    claims.append({'id': admin_location_snak, 'remove': ''})
            if 'P17' in item_claims and location_of_creation_source != 'country':
                if item_claims.get('P17')[0].getTarget() == country:
                    summary += ' remove [[d:Special:EntityPage/P17]] (it\'s on [[d:Special:EntityPage/P1071]])'
                    claims.append({'id': country_snak, 'remove': ''})

        if claims:
            #print('claim stuff')
            print(summary)
            print(claims)
            data = {'claims': claims}
            #print(data)
            try:
                response = self.site.editEntity(mediainfo, data, summary=summary)
            except pywikibot.exceptions.APIError as e:
                print(e)

            #response = mediainfo.editEntity(data, summary=summary)
            #print(response)


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
    generator = mediainfo_to_fix_generator()

    fix_location_bot = FixLocationBot(generator)
    fix_location_bot.run()


if __name__ == "__main__":
    main()
