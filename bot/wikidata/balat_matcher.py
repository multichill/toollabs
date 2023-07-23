#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Tool to match RKDimages on Wikidata with RKDimages and make some sort of easy result

"""
import pywikibot
#import requests
import pywikibot.data.sparql
#import re
import json
#import urllib.parse


class BalatMatcher:
    """
    Program to do the matching of RKDimages with Wikidata
    """
    def __init__(self, collection_name, collection_qid, collection_json):
        """
        Setup the bot
        """
        self.repo = pywikibot.Site().data_repository()
        self.collection_name = collection_name
        self.collection_qid = collection_qid

        with open(collection_json, 'r') as jsonfile:
            self.balat_paintings = json.load(jsonfile)

        self.wikidata_paintings = self.collection_on_wikidata(collection_qid)

        self.balat_on_wikidata = self.get_balat_on_wikidata()
        #for painting in self.wikidata_paintings:
        #    if painting.get('balatid'):
        #        self.balat_on_wikidata[painting.get('balatid')] = painting

    def collection_on_wikidata(self, collection_qid):
        """

        """
        result = []

        query = """SELECT DISTINCT ?item ?itemLabel ?itemDescription ?inv ?balatid ?inception WHERE {
  ?item p:P195/ps:P195 wd:%s;
        wdt:P31 wd:Q3305213 .
  OPTIONAL { ?item p:P217 [ ps:P217 ?inv; pq:P195 wd:%s]}
  OPTIONAL { ?item wdt:P3293 ?balatid }
  OPTIONAL { ?item wdt:P571 ?date . BIND(YEAR(?date) AS ?inception) }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "nl,en,fr". }
  }""" % (collection_qid, collection_qid)

        sq = pywikibot.data.sparql.SparqlQuery()
        query_result = sq.select(query)

        for result_item in query_result:
            result_item['qid'] = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
            if result_item.get('itemLabel'):
                result_item['title'] = result_item.get('itemLabel')
            if result_item.get('itemDescription'):
                creatorname = result_item.get('itemDescription').replace('olieverfschildering van ', '')
                creatorname = creatorname.replace('olieverfschilderij van ', '')
                creatorname = creatorname.replace('schildering van ', '')
                creatorname = creatorname.replace('schilderij van ', '')
                creatorname = creatorname.replace('schilderij door ', '')
                result_item['creatorname'] = creatorname
            result.append(result_item)
        return result

    def get_balat_on_wikidata(self):
        """
        Get all Balat links on Wikidata
        :return:
        """
        result = {}
        query = """SELECT ?item ?id WHERE {
        ?item wdt:P3293 ?id .
        }"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            identifier = resultitem.get('id')
            result[identifier] = qid
        return result

    def run(self):
        """
        Do the actual run
        :return:
        """
        report_page = 'Wikidata:WikiProject sum of all paintings/Balat to match/%s' % (self.collection_name,)

        text = 'This page gives an overview of Balat images to match in {{Q|%s}} (%s).\n' % (self.collection_qid, self.collection_name, )
        text += 'You can help by connecting these two lists.\n'
        text += '{| style=\'width:100%\'\n| style=\'width:50%;vertical-align: top;\' |\n'
        text += '== Balat with no link to Wikidata ==\n'

        text += '{| class=\'wikitable sortable\' style=\'width:100%\'\n'
        text += '! Balat\n'
        text += '! Title\n'
        text += '! Painter\n'
        text += '! Inception\n'
        text += '! Inv.\n'

        balat_to_do = {}
        wikidata_to_do = {}

        for painting in self.balat_paintings:
            if painting.get('artworkid') not in self.balat_on_wikidata:
                if painting.get('id'):
                    painting_id = painting.get('id').replace(' ', '-').replace('Inv. ', '').replace('MSKG ', '')
                    painting['id'] = painting_id

                text += '|-\n'
                text += '| [%s %s] \n| %s \n| %s \n|%s \n| %s\n' % (painting.get('url'),
                                                                    painting.get('artworkid'),
                                                                    painting.get('orginal_title'),
                                                                    painting.get('creatorname'),
                                                                    painting.get('date_raw'),
                                                                    painting.get('id'),
                                                                    )
                if painting.get('orginal_title') and painting.get('creatorname') and painting.get('id'):
                    #balat_to_do[(painting.get('orginal_title'), painting.get('creatorname'), painting.get('id'))] = painting
                    balat_to_do[(painting.get('creatorname'), painting.get('id'))] = painting


        text += '|}\n| style=\'width:50%;vertical-align: top;\' |\n'
        text += '== Wikidata with no link to Balat ==\n'
        text += '{| class=\'wikitable sortable\' style=\'width:100%\'\n'
        text += '! Painting\n'
        text += '! Painter\n'
        text += '! Inception\n'
        text += '! Inv.\n'

        for painting in self.wikidata_paintings:
            if not painting.get('balatid'):
                text += '|-\n'
                text += '| [[%s|%s]] \n| %s \n| %s \n| %s\n' % (painting.get('qid'),
                                                                painting.get('title'),
                                                                painting.get('creatorname'),
                                                                painting.get('inception'),
                                                                painting.get('inv'),
                                                                )
                if painting.get('title') and painting.get('creatorname') and painting.get('inv'):
                    #wikidata_to_do[(painting.get('title'), painting.get('creatorname'), painting.get('inv'))] = painting
                    wikidata_to_do[(painting.get('creatorname'), painting.get('inv'))] = painting

        text += '|}\n\n|}\n\n'
        balat_keys = set(balat_to_do.keys())
        wikidata_keys = set(wikidata_to_do.keys())

        both_keys = balat_keys.intersection(wikidata_keys)
        if both_keys:
            text += '== Balat and Wikidata matches ==\n'
            text += 'Matches based on same title, painter and inventory number.\n'

            text += '{| class=\'wikitable sortable\' style=\'width:100%\'\n'
            text += '! Balat\n'
            text += '! Wikidata\n'
            text += '! Title\n'
            text += '! Painter\n'
            text += '! Inv.\n'

            for key in both_keys:
                #(title, creatorname, inv) = key
                (creatorname, inv) = key
                balat_painting = balat_to_do.get(key)
                wikidata_painting = wikidata_to_do.get(key)
                title = balat_painting.get('orginal_title')
                text += '|-\n'
                text += '| [%s %s] \n| {{Q|%s}} \n| %s \n| %s \n| %s\n' % (balat_painting.get('url'),
                                                                           balat_painting.get('artworkid'),
                                                                           wikidata_painting.get('qid'),
                                                                           title,
                                                                           creatorname,
                                                                           inv,
                                                                           )
            text += '|}\n\n'


        text += '\n[[Category:WikiProject sum of all paintings Balat to match|%s]]' % (self.collection_name, )

        page = pywikibot.Page(self.repo, title=report_page)
        summary = 'Updating Balat collection page'
        page.put(text, summary)

def main(*args):
    """
    :param args:
    :return:
    """
    collection = None
    collections = {'Q938154': {'name': 'Sint-Baafskathedraal',
                               'qid': 'Q938154',
                               'completed': True,
                               'json_file': 'balat_objects_baaf.json'},
                   'Q1948674': {'name': 'Groeningemuseum',
                                'qid': 'Q1948674',
                                'completed': True,
                                'json_file': 'balat_objects_groeningemuseum.json'},
                   'Q1471477': {'name': 'KMSKA',
                                'qid': 'Q1471477',
                                'completed': True,
                                'json_file': 'balat_objects_kmska.json'},
                   'Q2362660': {'name': 'M Leuven',
                                'qid': 'Q2362660',
                                'json_file': 'balat_objects_m_leuven.json'},
                   'Q1699233': {'name': 'Museum Mayer van den Bergh',
                                'qid': 'Q1699233',
                                'completed': True,
                                'json_file': 'balat_objects_mmb.json'},
                   'Q2365880': {'name': 'MSK Gent',
                                'qid': 'Q2365880',
                                'json_file': 'balat_objects_msk_gent.json'},
                   'Q5901': {'name': 'Onze-Lieve-Vrouwekathedraal',
                             'qid': 'Q5901',
                             'completed': True,
                             'json_file': 'balat_objects_onze-lieve-vrouwe.json'},
                   'Q2272511': {'name': 'Sint-Pauluskerk',
                                'qid': 'Q2272511',
                                'completed': True,
                                'json_file': 'balat_objects_paulus.json'},
                   'Q2662909': {'name': 'Rockoxhuis',
                                'qid': 'Q2662909',
                                'completed': True,
                                'json_file': 'balat_objects_rockox.json'},
                   'Q775644': {'name': 'Rubenshuis',
                               'qid': 'Q775644',
                               'completed': True,
                               'json_file': 'balat_objects_rubenshuis.json'},
                   'Q1378149': {'name': 'Sint-Salvatorskathedraal',
                                'qid': 'Q1378149',
                                'completed': True,
                                'json_file': 'balat_objects_salvator.json'},
                   'Q377500': {'name': 'Koninklijke Musea voor Schone Kunsten',
                               'qid': 'Q377500',
                               'json_file': 'balat_objects_schone_kunsten_brussel.json'},
                   'Q1778179': {'name': 'Museum voor Schone Kunsten Doornik',
                                'qid': 'Q1778179',
                                'completed': True,
                                'json_file': 'balat_objects_schone_kunsten_doornik.json'},
                   'Q80784': {'name': 'Museum voor Schone Kunsten Luik',
                              'qid': 'Q80784',
                              'completed': True,
                              'json_file': 'balat_objects_schone_kunsten_luik.json'},
                   'Q2893370': {'name': 'Museum voor Schone Kunsten Mons',
                                'qid': 'Q2893370',
                                'completed': True,
                                'json_file': 'balat_objects_schone_kunsten_mons.json'},
                   'Q1540707': {'name': 'Stedelijk Museum voor Actuele Kunst',
                                'qid': 'Q1540707',
                                'completed': True,
                                'json_file': 'balat_objects_smak.json'},
                   'Q49425918': {'name': 'Groot Seminarie',
                                'qid': 'Q49425918',
                                'completed': True,
                                'json_file': 'balat_objects_groot_seminarie.json'},
                   'Q3044768': {'name': 'Musée du Louvre',
                                'qid': 'Q3044768',
                                'completed': True,
                                'json_file': 'balat_objects_louvre.json'},
                   'Q2628596': {'name': 'Palais des Beaux-Arts de Lille',
                                'qid': 'Q2628596',
                                'completed': True,
                                'json_file': 'balat_objects_schone_kunsten_lille.json'},
                   'Q2536986': {'name': 'Koninklijke Collectie',
                                'qid': 'Q2536986',
                                'completed': True,
                                'json_file': 'balat_objects_koninklijke_collectie.json'},
                   'Q595802': {'name': 'Museum Plantin-Moretus',
                                'qid': 'Q595802',
                                'completed': True,
                                'json_file': 'balat_objects_plantin-moretus.json'},
                   }


    for arg in pywikibot.handle_args(args):
        if arg.startswith('-collectionid:'):
            if len(arg) == 14:
                collection = pywikibot.input(
                        u'Please enter the collectionid you want to work on:')
            else:
                collection = arg[14:]

    if collection:
        collection_name = collections.get(collection).get('name')
        collection_qid = collections.get(collection).get('qid')
        collection_json = '../balat_bende/%s' % (collections.get(collection).get('json_file'),)
        balat_matcher = BalatMatcher(collection_name, collection_qid, collection_json)
        balat_matcher.run()
    else:
        for collection in collections:
            if not collections.get(collection).get('completed'):
                collection_name = collections.get(collection).get('name')
                collection_qid = collections.get(collection).get('qid')
                collection_json = '../balat_bende/%s' % (collections.get(collection).get('json_file'),)
                balat_matcher = BalatMatcher(collection_name, collection_qid, collection_json)
                balat_matcher.run()


if __name__ == "__main__":
    main()
