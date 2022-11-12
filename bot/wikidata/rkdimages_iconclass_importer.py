#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import iconclass for RKDimages ( https://rkd.nl/en/explore/images/ )

Got a dataset in tsv format to process

This is a fork of the RKDartists importer.

First it does a (SPARQL) query to find wikidata items that miss something relevant.
Bot will try to find the missing info

This should make https://www.wikidata.org/wiki/Wikidata:Database_reports/Constraint_violations/P350 shorter

"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import requests
import re
import datetime
import time
import json
import artdatabot
import csv



class RKDImagesIconclassImporter():
    """
    A generator for data from RKDimages
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields ItemPage objects.
        """
        self.repo = pywikibot.Site().data_repository()
        self.rkd_images = self.get_id_lookup_table('P350')
        self.generator = self.get_iconclass_generator()

    def get_id_lookup_table(self, id_property):
        """
        Make a lookup table for provided id property
        :param id_property: String like P350
        :return: The lookup table as a dict
        """
        result = {}
        query = """SELECT ?item ?id WHERE { ?item wdt:%s ?id }""" % (id_property,)
        sq = pywikibot.data.sparql.SparqlQuery()
        query_result = sq.select(query)

        for result_item in query_result:
            qid = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
            result[result_item.get('id')] = qid
        return result

    def get_iconclass_generator(self):
        """
        Get the generator that returns Wikidata items and list of iconlass items to add
        :return:
        """
        with open('../Downloads/rkd_iconclass.tsv', 'r') as tsvfile:
            reader = csv.DictReader(tsvfile, delimiter='\t', fieldnames=['rkdimage', 'iconclass'])
            current_rkdimage = None
            current_iconclass = []
            for possible_match in reader:
                if not current_rkdimage:
                    current_rkdimage = possible_match.get('rkdimage')
                    current_iconclass.append(possible_match.get('iconclass'))
                elif current_rkdimage and current_rkdimage == possible_match.get('rkdimage'):
                    current_iconclass.append(possible_match.get('iconclass'))
                elif current_rkdimage:
                    if current_rkdimage in self.rkd_images:
                        qid = self.rkd_images.get(current_rkdimage)
                        yield { 'qid' : qid,
                                'rkdimage' : current_rkdimage,
                                'depictsiconclass' : current_iconclass,
                                }
                    current_rkdimage = possible_match.get('rkdimage')
                    current_iconclass = [possible_match.get('iconclass'),]

    def run(self):
        """
        """
        for metadata in self.generator:
            item = pywikibot.ItemPage(self.repo, metadata.get('qid'))
            self.add_iconclass(item, metadata)

    def add_iconclass(self, item, metadata):
        """
        Add depicts iconclass to item
        :param item:
        :param metadata:
        :return:
        """
        claims = item.get().get('claims')

        if metadata.get('depictsiconclass'):
            current_iconclass = []
            if claims.get('P1257'):
                for claim in claims.get('P1257'):
                    current_iconclass.append(claim.getTarget())

            for depictsiconclass in set(metadata.get('depictsiconclass')):
                if depictsiconclass not in current_iconclass:
                    newclaim = pywikibot.Claim(self.repo, 'P1257')
                    newclaim.setTarget(depictsiconclass)
                    summary = 'Based on data provided by Iconclass derived from RKDimages %s' % (metadata.get('rkdimage'),)
                    pywikibot.output('Adding depicts Iconclass notation claim to %s' % item)
                    item.addClaim(newclaim, summary=summary)


def main(*args):
    """
    Main function. Grab a generator and pass it to the bot to work on
    """
    rkdimages_iconclass_importer = RKDImagesIconclassImporter()
    rkdimages_iconclass_importer.run()


if __name__ == "__main__":
    main()
