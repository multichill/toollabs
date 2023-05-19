#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
A bot to compare Wikidata with OpenStreetMap for reverse geocoding.

See https://commons.wikimedia.org/wiki/Commons:Reverse_geocoding/Reports

"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import requests
import re
import datetime
import time
import json

class WikidataOsmChecker:
    """
    A bot to compare Wikidata and OpenStreetMap
    """
    def __init__(self, countrycode, report_page, admin_levels, do_edits = False):
        """
        Arguments: None
        """
        self.site = pywikibot.Site('commons', 'commons')
        self.repo = pywikibot.Site().data_repository()
        self.countrycode = countrycode
        self.report_page = report_page
        self.admin_levels = admin_levels
        self.do_edits = do_edits
        self.wd_item_relation = {}
        self.wd_item_id = {}
        self.wd_item_relation_id = {}
        self.wd_item_commons_category = {}
        self.osm_relation_item = {}
        self.osm_relation_id = {}
        self.osm_item_relation = {}
        self.osm_item_relation_id = {}
        for admin_level in admin_levels:
            sparql_query = admin_levels.get(admin_level).get('sparql')
            self.wd_item_relation[admin_level] = set()
            self.wd_item_id[admin_level] = set()
            self.wd_item_commons_category[admin_level] = set()
            self.wd_item_relation_id[admin_level] = set()
            self.do_sparql_query(sparql_query, admin_level)

            overpass_query = admin_levels.get(admin_level).get('overpass')
            id_tag = admin_levels.get(admin_level).get('id_tag')
            id_transform = admin_levels.get(admin_level).get('id_transform')
            self.osm_relation_item[admin_level] = set()
            self.osm_item_relation[admin_level] = set()
            self.osm_relation_id[admin_level] = set()
            self.osm_item_relation_id[admin_level] = set()
            self.do_overpass_query(overpass_query, admin_level, id_tag, id_transform)

    def do_sparql_query(self, query, admin_level):
        """
        Do the sparql query and store the results for an admin_level
        :param query: The sparql query to execute
        :param admin_level: Admin level to store it at
        :return: None
        """
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            osmrelation = resultitem.get('osmrelation')
            commonscategory = resultitem.get('commonscategory')
            id = resultitem.get('id')
            self.wd_item_relation[admin_level].add((qid, osmrelation))
            self.wd_item_id[admin_level].add((qid, id))
            self.wd_item_commons_category[admin_level].add((qid, commonscategory))
            self.wd_item_relation_id[admin_level].add((qid, osmrelation, id))

    def do_overpass_query(self, query, admin_level, id_tag, id_transform):
        """
        Do the overpass query and store it at admin_level
        :param query: The overpass query to execute
        :param admin_level: Admin level to store it at
        :param id_tag: The identifier tag to look for
        :param id_transform: How to transform the identifier tag
        :return:
        """

        url = 'http://overpass-api.de/api/interpreter?data=%s' % (requests.utils.quote(query),)
        #print(url)
        page = requests.get(url)

        json = page.json()
        for element in json.get('elements'):
            osmrelation = '%s' % (element.get('id'),)
            qid = element.get('tags').get('wikidata')
            if id_tag:
                id = element.get('tags').get(id_tag)
                if id_transform:
                    try:
                        id = id_transform % (id, )
                    except TypeError:
                        id = id_transform % (int(id), )
            else:
                id = None
            self.osm_relation_item[admin_level].add((osmrelation, qid))
            self.osm_relation_id[admin_level].add((osmrelation, id))
            self.osm_item_relation[admin_level].add((qid, osmrelation))
            self.osm_item_relation_id[admin_level].add((qid, osmrelation, id))

    def run(self):
        """
        Starts the robot.
        """
        text = 'This is the [[Commons:Reverse geocoding|reverse geocoding]] [[Commons:Reverse geocoding/Reports|report]] for {{SUBPAGENAME}}.\n'
        for admin_level in self.admin_levels:
            text += '== %s ==\n' % (self.admin_levels.get(admin_level).get('label'),)
            item = requests.utils.quote(self.admin_levels.get(admin_level).get('item'))
            text += 'Working on {{Q|%s}} which corresponds to admin level %s on OpenStreetMap\n' % (item, admin_level)

            sparql_query = requests.utils.quote(self.admin_levels.get(admin_level).get('sparql'))
            overpass_query = requests.utils.quote(self.admin_levels.get(admin_level).get('overpass'))
            text += '* [https://query.wikidata.org/#%s SPARQL query]\n' % (sparql_query, )
            text += '* [http://overpass-api.de/api/interpreter?data=%s overpass query]\n' % (overpass_query, )

            id_property = self.admin_levels.get(admin_level).get('id_property')
            id_tag = self.admin_levels.get(admin_level).get('id_tag')
            if id_property and id_tag:
                text += '* {{P|%s}} will be matched with OSM tag "[[openstreetmap:key:%s|%s]]"\n' % (id_property, id_tag, id_tag)
            text += self.check_count(admin_level)

            text += self.check_completeness_links(self.wd_item_relation.get(admin_level), 'Wikidata', 'OpenStreetMap')
            text += self.check_completeness_links(self.osm_relation_item.get(admin_level), 'OpenStreetMap', 'Wikidata')
            text += self.check_interlinks(self.wd_item_relation.get(admin_level), self.osm_item_relation.get(admin_level))

            if not self.admin_levels.get(admin_level).get('no_commons_category'):
                text += self.check_completeness_links(self.wd_item_commons_category.get(admin_level), 'Wikidata', 'Commons category')

            if id_property and id_tag:
                id_property_text = '{{P|%s}}' % (id_property)
                id_tag_text = 'tag "%s"' % (id_tag)
                text += self.check_completeness_links(self.wd_item_id.get(admin_level), 'Wikidata', id_property_text)
                text += self.check_completeness_links(self.osm_relation_id.get(admin_level), 'OpenStreetMap', id_tag_text)
                text += self.check_id_interlinks(self.wd_item_relation_id.get(admin_level), self.osm_item_relation_id.get(admin_level))

        # Might produce very large reports that exceed the max page size
        if len(text) > 2000000:
            text = text[0:800000]
        text += '\n[[Category:Commons reverse geocoding]]\n'

        page = pywikibot.Page(self.site, title=self.report_page)
        summary = 'Updating report'
        page.put(text, summary)
        print(text)


    def check_count(self, admin_level):
        """
        Check the expected count with what we found for an admin_level
        :param admin_level: admin level to work on
        :return: string
        """
        text = '=== Expected count ===\n'
        expected_count = self.admin_levels.get(admin_level).get('count')
        wikidata_count = len(self.wd_item_relation.get(admin_level))
        osm_count = len(self.osm_item_relation.get(admin_level))
        if expected_count == wikidata_count and expected_count == osm_count:
            text += '* {{Done|}} expected %s and found the same on Wikidata and OpenStreetMap\n' % (expected_count,)
        else:
            if expected_count == wikidata_count or expected_count == osm_count:
                text += '* {{Half done|}} expected %s. ' % (expected_count,)
            else:
                text += '* {{Not done|}} expected %s. ' % (expected_count,)
            text += 'Found %s items on Wikidata. ' % (wikidata_count,)
            text += 'Found %s relations on OpenStreetMap.\n' % (osm_count,)

        return text

    def check_completeness_links(self, set_to_check, source_link, target_link):
        """
        """
        text = '=== Link check %s to %s ===\n' % (source_link, target_link)
        found = 0
        complete = 0
        missing_links = []

        for (field, link) in set_to_check:
            found += 1
            if link:
                complete += 1
            else:
                missing_links.append(field)

        if found == complete:
            text += '* {{Done|}} all %s have links\n' % (found,)
            return text

        text += '* {{Not done|}} %s out of %s have links\nDetails:\n' % (complete, found,)

        for missing_link in missing_links:
            if source_link.lower() == 'wikidata':
                text += '* {{Q|%s}} missing link\n' % (missing_link,)
            elif source_link.lower() == 'openstreetmap':
                text += '* [https://www.openstreetmap.org/relation/%s OSM %s] missing link\n' % (missing_link,
                                                                                                 missing_link)
            else:
                text += '* %s (unknown source %s)\n' % (missing_link, source_link)
        return text

    def check_interlinks(self, wikidata_set, openstreetmap_set):
        """
        Check if all Wikidata items link to OpenStreetMap and the other way around

        :param wikidata_set:
        :param openstreetmap_set:
        :return:
        """
        text = '=== Interlinks Wikidata and OpenStreetMap ===\n'
        if wikidata_set == openstreetmap_set:
            text += '* {{Done|}} the links from Wikidata are exactly the same as the links from OpenStreetMap\n'
            return text
        matched = wikidata_set & openstreetmap_set
        wikidata_not_osm = wikidata_set - openstreetmap_set
        osm_not_wikidata = openstreetmap_set - wikidata_set

        text += '* {{Not done|}} %s matched, %s Wikidata not OpenStreetmap and %s OpenStreetmap not Wikidata\n' % (len(matched), len(wikidata_not_osm), len(osm_not_wikidata),)
        text += 'Details:\n'
        for (qid, osm) in wikidata_not_osm:
            if osm:
                text += '* {{Q|%s}} links to https://www.openstreetmap.org/relation/%s, but no backlink\n' % (qid, osm)
            else:
                text += '* {{Q|%s}} is missing link to OpenStreetMap\n' % (qid,)

        for (qid, osm) in osm_not_wikidata:
            if qid:
                if self.do_edits:
                    backlink_added = self.add_missing_osm_backlink(qid, osm)
                    if backlink_added:
                        text += '* https://www.openstreetmap.org/relation/%s links to {{Q|%s}}, added missing backlink\n' % (osm, qid)
                    else:
                        text += '* https://www.openstreetmap.org/relation/%s links to {{Q|%s}}, but that item links to a different relation\n' % (osm, qid)
                else:
                    text += '* https://www.openstreetmap.org/relation/%s links to {{Q|%s}}, might be able to add backlink\n' % (osm, qid)
            else:
                text += '* https://www.openstreetmap.org/relation/%s is missing Wikidata tag\n' % (osm,)
        return text

    def check_id_interlinks(self, wikidata_set, openstreetmap_set):
        """
        Check if all Wikidata items link with ID link to OpenStreetMap and the other way around

        :param wikidata_set:
        :param openstreetmap_set:
        :return:
        """
        text = '=== Identifier comparison Wikidata and OpenStreetMap ===\n'
        if wikidata_set == openstreetmap_set:
            text += '* {{Done|}} the links with identifiers from Wikidata are exactly the same as the links with identifiers from OpenStreetMap\n'
            return text
        matched = wikidata_set & openstreetmap_set
        wikidata_not_osm = wikidata_set - openstreetmap_set
        osm_not_wikidata = openstreetmap_set - wikidata_set

        text += '* {{Not done|}} %s matched, %s Wikidata not OpenStreetmap and %s OpenStreetmap not Wikidata\n' % (len(matched), len(wikidata_not_osm), len(osm_not_wikidata),)
        text += 'Details:\n'
        for (qid, osm, id) in wikidata_not_osm:
            if osm:
                # Only work on items that have OSM, otherwise it will show up in the other report
                if id:
                    text += '* {{Q|%s}} links identier %s, but that doesn\'t match https://www.openstreetmap.org/relation/%s\n' % (qid, id, osm)
                else:
                    text += '* {{Q|%s}} is missing identifier link, but does link to https://www.openstreetmap.org/relation/%s\n' % (qid, osm)

        for (qid, osm, id) in osm_not_wikidata:
            if qid:
                # Only work on items that have Wikidata, otherwise it will show up in the other report
                if id:
                    text += '* https://www.openstreetmap.org/relation/%s links identier %s, but doesn\'t match {{Q|%s}}\n' % (osm, id, qid)
                else:
                    text += '* https://www.openstreetmap.org/relation/%s is missing identifier link, but does link to {{Q|%s}}\n' % (osm, qid)
        return text


    def add_missing_osm_backlink(self, qid, osm):
        """
        Add the missing OSM backlink if it doesn't have a OSM link already

        :param qid: The qid of the Wikidata item to work on
        :param osm: The OSM relation ID
        :return: If it was added or not
        """
        item = pywikibot.ItemPage(self.repo, qid)
        if item.isRedirectPage():
            item = item.getRedirectTarget()
        data = item.get()
        claims = data.get('claims')

        if 'P402' in claims:
            # Already done
            return False

        summary = 'Adding missing link based on Wikidata tag on https://www.openstreetmap.org/relation/%s' % (osm, )
        newclaim = pywikibot.Claim(self.repo, u'P402')
        newclaim.setTarget(osm)
        item.addClaim(newclaim, summary=summary)
        return True

def main(*args):
    """
    Main function.
    """
    regioncode = None
    do_edits = False
    for arg in pywikibot.handle_args(args):
        if arg.startswith('-regioncode:'):
            regioncode = arg[12:]
        elif arg == '-do_edits':
            do_edits = True

    regions = {
        'at': {
            'report_page': 'Commons:Reverse geocoding/Reports/Austria',
            'country_item': 'Q40',
            'admin_levels': {
                4: {'label': 'state',
                    'item': 'Q261543',
                    'count': 9,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      ?instancestatement ps:P31 wd:Q261543 
      MINUS { ?instancestatement pq:P582 [] } .  
      OPTIONAL { ?item wdt:P402 ?osmrelation } .
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P300 ?id } .
      }''',
                    'overpass': '''[timeout:600][out:json];
                area["name:en"="Austria"][admin_level="2"];
                rel(area)[admin_level="4"][boundary="administrative"]["ISO3166-2"];
                out tags;''',
                    'id_property': 'P300',
                    'id_tag': 'ISO3166-2',
                    'id_transform': False,
                    },
                6: {'label': 'district',
                    'item': 'Q871419',
                    'count': 94,  # Have to handle and clean up the  statutory city of Austria (Q262882)
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
          ?item p:P31 ?instancestatement.
          ?instancestatement ps:P31 wd:Q871419 
          MINUS { ?instancestatement pq:P582 [] } .  
          OPTIONAL { ?item wdt:P402 ?osmrelation } .
          OPTIONAL { ?item wdt:P373 ?commonscategory } .
          }''',
                    'overpass': '''[timeout:600][out:json];
                    area["name:en"="Austria"][admin_level="2"];
                    rel(area)[admin_level="6"][boundary="administrative"];
                    out tags;''',
                    'id_property': False,
                    'id_tag': False,  # ref:at:gkz doesn't match with Wikidata
                    'id_transform': False,
                    },
                8: {'label': 'municipality',
                    'item': 'Q667509',
                    'count': 2095,  # Have to handle and clean up the  statutory city of Austria (Q262882)
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
          ?item p:P31 ?instancestatement.
          ?instancestatement ps:P31 wd:Q667509 
          MINUS { ?instancestatement pq:P582 [] } .  
          OPTIONAL { ?item wdt:P402 ?osmrelation } .
          OPTIONAL { ?item wdt:P373 ?commonscategory } .
          OPTIONAL { ?item wdt:P964 ?id } .
          }''',
                    'overpass': '''[timeout:600][out:json];
                    area["name:en"="Austria"][admin_level="2"];
                    rel(area)[admin_level="8"][boundary="administrative"];
                    out tags;''',
                    'id_property': 'P964',
                    'id_tag': 'ref:at:gkz',
                    'id_transform': False,
                    },
                9: {'label': 'city district',
                    'item': 'Q4286337',
                    'count': 40,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
          ?item p:P31 ?instancestatement.
          { ?instancestatement ps:P31 wd:Q261023 } UNION
          { ?instancestatement ps:P31 wd:Q1852119 }
          MINUS { ?instancestatement pq:P582 [] } .  
          OPTIONAL { ?item wdt:P402 ?osmrelation } .
          OPTIONAL { ?item wdt:P373 ?commonscategory } .
          OPTIONAL { ?item wdt:P964 ?id } .
          }''',
                    'overpass': '''[timeout:600][out:json];
                    area["name:en"="Austria"][admin_level="2"];
                    rel(area)[admin_level="9"][boundary="administrative"];
                    out tags;''',
                    'id_property': False,
                    'id_tag': False,
                    'id_transform': False,
                    },
                # Admin_level 10 is cadastral municipality of Austria, missing in OSM
            },
        },
        'be': {
            'report_page': 'Commons:Reverse geocoding/Reports/Belgium',
            'region_item': 'Q31',
            'admin_levels': {
                6: {'label': 'province',
                    'item': 'Q83116',
                    'count': 10,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      ?instancestatement ps:P31 wd:Q83116.
      MINUS { ?instancestatement pq:P582 [] } .  
      OPTIONAL { ?item wdt:P402 ?osmrelation } .
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P300 ?id } .
      }''',
                    'overpass': '''[timeout:600][out:json];
area["name:en"="Belgium"]["admin_level"="2"];
rel(area)[admin_level="6"][boundary="administrative"];
out tags;''',
                    'id_property': 'P300',
                    'id_tag': 'ISO3166-2',
                    'id_transform': False,
                    },
                7: {'label': 'arrondissement',
                    'item': 'Q91028',
                    'count': 43,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
          ?item p:P31 ?instancestatement.
          ?instancestatement ps:P31 wd:Q91028.
          MINUS { ?instancestatement pq:P582 [] } .  
          OPTIONAL { ?item wdt:P402 ?osmrelation } .
          OPTIONAL { ?item wdt:P373 ?commonscategory } .
          OPTIONAL { ?item wdt:P605 ?id } .
          }''',
                    'overpass': '''[timeout:600][out:json];
    area["name:en"="Belgium"]["admin_level"="2"];
    rel(area)[admin_level="7"][boundary="administrative"];
    out tags;''',
                    'id_property': 'P605',
                    'id_tag': 'ref:nuts',
                    'id_transform': False,
                    'no_commons_category': True,
                },
                8: {'label': 'municipality',
                    'item': 'Q493522',
                    'count': 581,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
          ?item p:P31 ?instancestatement.
          ?instancestatement ps:P31 wd:Q493522.
          MINUS { ?instancestatement pq:P582 [] } .  
          OPTIONAL { ?item wdt:P402 ?osmrelation } .
          OPTIONAL { ?item wdt:P373 ?commonscategory } .
          OPTIONAL { ?item wdt:P1567 ?id } .
          }''',
                    'overpass': '''[timeout:600][out:json];
    area["name:en"="Belgium"]["admin_level"="2"];
    rel(area)[admin_level="8"][boundary="administrative"];
    out tags;''',
                    'id_property': 'P1567',
                    'id_tag': 'ref:INS',
                    'id_transform': False,
                    },
                9: {'label': 'municipality section',
                    'item': 'Q2785216',
                    'count': 2500,  # Unable to find how many exactly. 2501 on Wikidata & 1661 on OpenStreetMap.
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
          ?item p:P31 ?instancestatement.
          ?instancestatement ps:P31 wd:Q2785216.
          MINUS { ?instancestatement pq:P582 [] } .  
          OPTIONAL { ?item wdt:P402 ?osmrelation } .
          OPTIONAL { ?item wdt:P373 ?commonscategory } .
          OPTIONAL { ?item wdt:P1567 ?id } .
          }''',
                    'overpass': '''[timeout:600][out:json];
    area["name:en"="Belgium"]["admin_level"="2"];
    rel(area)[admin_level="9"][boundary="administrative"];
    out tags;''',
                    'id_property': 'P1567',
                    'id_tag': 'ref:INS',
                    'id_transform': False,
                    },
            },
        },
        'de': {
            'report_page': 'Commons:Reverse geocoding/Reports/Germany',
            'country_item': 'Q183',
            'admin_levels': {
                8: {'label': 'municipality',
                    'item': 'Q262166',
                    'count': 10773,
                    'sparql': '''SELECT DISTINCT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      ?instancestatement ps:P31/wdt:P279* wd:Q262166.
      MINUS { ?instancestatement pq:P582 [] } .  
      OPTIONAL { ?item wdt:P402 ?osmrelation } .
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P439 ?id } .
      }''',
                    'overpass': '''[timeout:600][out:json];
        area[name="Deutschland"];
        rel(area)[admin_level="8"][boundary="administrative"];
        out tags;''',
                    'id_property': 'P439',
                    'id_tag': 'de:amtlicher_gemeindeschluessel',
                    'id_transform': False,
                    },
            },
        },
        'es': {
            'report_page': 'Commons:Reverse geocoding/Reports/Spain',
            'region_item': 'Q29',
            'admin_levels': {
                4: {'label': 'autonomous community',
                    'item': 'Q10742',
                    'count': 19,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      { ?instancestatement ps:P31 wd:Q10742 } UNION
      { ?instancestatement ps:P31 wd:Q16532593 } 
      MINUS { ?instancestatement pq:P582 [] } .  
      OPTIONAL { ?item wdt:P402 ?osmrelation } .
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P300 ?id } .
      }''',
                    'overpass': '''[timeout:600][out:json];
area["name:en"="Spain"]["admin_level"="2"];
rel(area)[admin_level="4"][boundary="administrative"];
out tags;''',
                    'id_property': 'P300',
                    'id_tag': 'ISO3166-2',
                    'id_transform': False,
                    },
                6: {'label': 'province',
                    'item': 'Q162620',
                    'count': 50,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
          ?item p:P31 ?instancestatement.
          ?instancestatement ps:P31 wd:Q162620 .
          MINUS { ?instancestatement pq:P582 [] } .
          MINUS { ?item wdt:P576 [] } .  
          OPTIONAL { ?item wdt:P402 ?osmrelation } .
          OPTIONAL { ?item wdt:P373 ?commonscategory } .
          OPTIONAL { ?item wdt:P300 ?id } .
          }''',
                    'overpass': '''[timeout:600][out:json];
    area["name:en"="Spain"]["admin_level"="2"];
    rel(area)[admin_level="6"][boundary="administrative"];
    out tags;''',
                    'id_property': 'P300',
                    'id_tag': 'ISO3166-2',
                    'id_transform': False,
                    },
                7: {'label': 'comarca',
                    'item': 'Q1345234',
                    'count': 83,  # Not sure?
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
          ?item p:P31 ?instancestatement.
          ?instancestatement ps:P31/wdt:P279* wd:Q1345234 .
          MINUS { ?instancestatement pq:P582 [] } .
          MINUS { ?item wdt:P576 [] } .  
          OPTIONAL { ?item wdt:P402 ?osmrelation } .
          OPTIONAL { ?item wdt:P373 ?commonscategory } .
          OPTIONAL { ?item wdt:P772 ?id } .
          }''',
                    'overpass': '''[timeout:600][out:json];
    area["name:en"="Spain"]["admin_level"="2"];
    rel(area)[admin_level="7"][boundary="administrative"];
    out tags;''',
                    'id_property': False,
                    'id_tag': False,
                    'id_transform': False,
                    },
                8: {'label': 'municipality',
                    'item': 'Q2074737',
                    'count': 8131,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
          ?item p:P31 ?instancestatement.
          ?instancestatement ps:P31/wdt:P279* wd:Q2074737 .
          MINUS { ?instancestatement pq:P582 [] } .
          MINUS { ?item wdt:P576 [] } .  
          OPTIONAL { ?item p:P402 ?osmstatement . 
            { ?osmstatement ps:P402 ?osmrelation MINUS { ?osmstatement pq:P2868 [] } } UNION
            { ?osmstatement ps:P402 ?osmrelation; pq:P2868 wd:Q2074737 }          
            }   
          OPTIONAL { ?item wdt:P373 ?commonscategory } .
          OPTIONAL { ?item wdt:P772 ?id } .
          }''',
                    'overpass': '''[timeout:600][out:json];
    area["name:en"="Spain"]["admin_level"="2"];
    rel(area)[admin_level="8"][boundary="administrative"];
    out tags;''',
                    'id_property': 'P772',
                    'id_tag': 'ine:municipio',
                    'id_transform': False,
                    },
            },
        },
        'fr': {
            'report_page': 'Commons:Reverse geocoding/Reports/France',
            'region_item': 'Q142',
            'admin_levels': {
                4: {'label': 'region',
                    'item': 'Q36784',
                    'count': 18,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      ?instancestatement ps:P31 wd:Q36784.
      MINUS { ?instancestatement pq:P582 [] } .  
      OPTIONAL { ?item p:P402 ?osmstatement . 
            { ?osmstatement ps:P402 ?osmrelation MINUS { ?osmstatement pq:P2868 [] } } UNION
            { ?osmstatement ps:P402 ?osmrelation; pq:P2868 wd:Q36784 }          
            }   
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P300 ?id } .
      }''',
                    'overpass': '''[timeout:600][out:json];
area["name:en"="France"]["admin_level"="2"];
rel(area)[admin_level="4"][boundary="administrative"];
out tags;''',
                    'id_property': 'P300',
                    'id_tag': 'ISO3166-2',
                    'id_transform': False,
                    },
                6: {'label': 'department',
                    'item': 'Q6465',
                    'count': 101,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      ?instancestatement ps:P31 wd:Q6465.
      MINUS { ?instancestatement pq:P582 [] } .  
      OPTIONAL { ?item p:P402 ?osmstatement . 
            { ?osmstatement ps:P402 ?osmrelation MINUS { ?osmstatement pq:P2868 [] } } UNION
            { ?osmstatement ps:P402 ?osmrelation; pq:P2868 wd:Q6465 }          
            }   
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P300 ?id } .
      }''',
                    'overpass': '''[timeout:600][out:json];
area["name:en"="France"]["admin_level"="2"];
rel(area)[admin_level="6"][boundary="administrative"];
out tags;''',
                    'id_property': 'P300',
                    'id_tag': 'ISO3166-2',
                    'id_transform': False,
                    },
                7: {'label': 'Arrondissement',
                    'item': 'Q194203',
                    'count': 332,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      ?instancestatement ps:P31 wd:Q194203.
      MINUS { ?instancestatement pq:P582 [] } .
      MINUS { ?item wdt:P576 [] } .  
      OPTIONAL { ?item p:P402 ?osmstatement . 
            { ?osmstatement ps:P402 ?osmrelation MINUS { ?osmstatement pq:P2868 [] } } UNION
            { ?osmstatement ps:P402 ?osmrelation; pq:P2868 wd:Q194203 }          
            }   
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P3423 ?id } .
      }''',
                    'overpass': '''[timeout:600][out:json];
area["name:en"="France"]["admin_level"="2"];
rel(area)[admin_level="7"][boundary="administrative"];
out tags;''',
                    'id_property': 'P3423',
                    'id_tag': 'ref:INSEE',
                    'id_transform': False,
                    'no_commons_category': True,
                    },
                8: {'label': 'commune',
                    'item': 'Q484170',
                    'count': 34965,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      { ?instancestatement ps:P31 wd:Q484170 } UNION
      { ?instancestatement ps:P31 wd:Q84669937 } UNION
      { ?instancestatement ps:P31 wd:Q84598477 } 
      MINUS { ?instancestatement pq:P582 [] } .
      MINUS { ?item wdt:P576 [] } .  
      OPTIONAL { ?item p:P402 ?osmstatement . 
            { ?osmstatement ps:P402 ?osmrelation MINUS { ?osmstatement pq:P2868 [] } } UNION
            { ?osmstatement ps:P402 ?osmrelation; pq:P2868 wd:Q484170 }          
            }   
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P374 ?id } .
      }''',
                    'overpass': '''[timeout:600][out:json];
area["name:en"="France"]["admin_level"="2"];
rel(area)[admin_level="8"][boundary="administrative"];
out tags;''',
                    'id_property': 'P374',
                    'id_tag': 'ref:INSEE',
                    'id_transform': False,
                    },
                9: {'label': 'municipal arrondissement',
                    'item': 'Q702842',
                    'count': 45,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      ?instancestatement ps:P31 wd:Q702842 .
      MINUS { ?instancestatement pq:P582 [] } .
      MINUS { ?item wdt:P576 [] } .  
      OPTIONAL { ?item wdt:P402 ?osmrelation } . 
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P374 ?id } .
      }''',
                    'overpass': '''[timeout:600][out:json];
area["name:en"="France"]["admin_level"="2"];
rel(area)[admin_level="9"][boundary="administrative"]["admin_type:FR"="arrondissement municipal"];
out tags;''',
                    'id_property': 'P374',
                    'id_tag': 'ref:INSEE',
                    'id_transform': False,
                    },
                19: {'label': 'delegated commune',  # FIXME: Change into list
                    'item': 'Q21869758',
                    'count': 2245,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      ?instancestatement ps:P31 wd:Q21869758 .
      MINUS { ?instancestatement pq:P582 [] } .
      OPTIONAL { ?item wdt:P402 ?osmrelation } . 
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P374 ?id } .
      }''',
                    'overpass': '''[timeout:600][out:json];
area["name:en"="France"]["admin_level"="2"];
rel(area)[admin_level="9"][boundary="administrative"]["admin_type:FR"="commune déléguée"];
out tags;''',
                    'id_property': 'P374',
                    'id_tag': 'ref:INSEE',
                    'id_transform': False,
                    },
                10: {'label': 'administrative quarter',
                     'item': 'Q22575704',
                     'count': 194,  # Not sure
                     'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item wdt:P31/wdt:P279 wd:Q22575704 ;
            wdt:P17 wd:Q142 .
      OPTIONAL { ?item wdt:P402 ?osmrelation } . 
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      }''',
                     'overpass': '''[timeout:600][out:json];
area["name:en"="France"]["admin_level"="2"];
rel(area)[admin_level="10"][boundary="administrative"]["admin_type:FR"="quartier administratif"]; 
out tags;''',  #
                     'id_property': False,
                     'id_tag': False,
                     'id_transform': False,
                     },
            },  # It's possible to add admin level 11 too
        },
        'gb-eng': {
            'report_page': 'Commons:Reverse geocoding/Reports/England',
            'region_item': 'Q21',
            'admin_levels': {
                8: {'label': 'district',
                     'item': 'Q349084',
                     'count': 309,
                     'sparql': '''SELECT DISTINCT ?item ?osmrelation ?commonscategory ?id WHERE {
  ?item p:P31 ?instancestatement .
  ?instancestatement ps:P31/wdt:P279* wd:Q349084 .
      MINUS { ?instancestatement pq:P582 [] } .  
      OPTIONAL { ?item wdt:P402 ?osmrelation } .
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P836 ?id } .
      }''',
                     'overpass': '''[timeout:600][out:json];
area["name"="England"]["admin_level"="4"];
rel(area)[admin_level="8"][boundary="administrative"];
out tags;''',
                     'id_property': 'P836',
                     'id_tag': 'ref:gss',
                     'id_transform': False,
                     },
                10: {'label': 'civil parish',
                     'item': 'Q1115575',
                     'count': 10449,
                     'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      ?instancestatement ps:P31 wd:Q1115575.
      MINUS { ?instancestatement pq:P582 [] } .  
      OPTIONAL { ?item wdt:P402 ?osmrelation } .
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P836 ?id } .
      }''',
                     'overpass': '''[timeout:600][out:json];
area["name"="England"]["admin_level"="4"];
rel(area)[admin_level="10"][designation="civil_parish"];
out tags;''',
                     'id_property': 'P836',
                     'id_tag': 'ref:gss',
                     'id_transform': False,
                     },
            }
        },
        'gb-wls': {
            'report_page': 'Commons:Reverse geocoding/Reports/Wales',
            'region_item': 'Q25',
            'admin_levels': {
                6: {'label': 'principal area',
                    'item': 'Q15979307',
                    'count': 22,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      ?instancestatement ps:P31 wd:Q15979307.
      MINUS { ?instancestatement pq:P582 [] } .  
      OPTIONAL { ?item wdt:P402 ?osmrelation } .
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P836 ?id } .
      }''',
                    'overpass': '''[timeout:600][out:json];
area["name:en"="Wales"];
rel(area)[admin_level="6"][designation="principal_area"];
out tags;''',
                    'id_property': 'P836',
                    'id_tag': 'ref:gss',
                    'id_transform': False,
                    },
                10: {'label': 'community',
                    'item': 'Q2630741',
                    'count': 878,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      ?instancestatement ps:P31 wd:Q2630741.
      MINUS { ?instancestatement pq:P582 [] } .  
      OPTIONAL { ?item wdt:P402 ?osmrelation } .
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P836 ?id } .
      }''',
                    'overpass': '''[timeout:600][out:json];
area["name:en"="Wales"];
rel(area)[admin_level="10"][designation="community"];
out tags;''',
                    'id_property': 'P836',
                    'id_tag': 'ref:gss',
                    'id_transform': False,
                    },
            }
        },
        'ie': {
            'report_page': 'Commons:Reverse geocoding/Reports/Ireland',
            'country_item': 'Q27',
            'admin_levels': {
                6: {'label': 'county',
                    'item': 'Q179872',
                    'count': 24,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      ?instancestatement ps:P31 wd:Q179872.
      MINUS { ?instancestatement pq:P582 [] } .  
      OPTIONAL { ?item wdt:P402 ?osmrelation } .
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P300 ?id } .
      }''',
                    'overpass': '''[timeout:600][out:json];
        area["name:en"="Ireland"];
        rel(area)[admin_level="6"][boundary="administrative"]["ISO3166-2"];
        out tags;''',
                    'id_property': 'P300',
                    'id_tag': 'ISO3166-2',
                    'id_transform': False,
                    },
                8: {'label': 'civil parish ',  # Not really admin_level 8
                    'item': 'Q3910694',
                    'count': 2508,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      ?instancestatement ps:P31 wd:Q3910694.
      ?item wdt:P17 wd:Q27.
      MINUS { ?instancestatement pq:P582 [] } .  
      OPTIONAL { ?item wdt:P402 ?osmrelation } .
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P5097 ?id } .
      }''',
                    'overpass': '''[timeout:600][out:json];
        area["name:en"="Ireland"][admin_level="2"];
        rel(area)[type="boundary"][boundary="civil_parish"];
        out tags;''',
                    'id_property': 'P5097',
                    'id_tag': 'logainm:ref',
                    'id_transform': False,
                    },
            },
        },
        'lu': {
            'report_page': 'Commons:Reverse geocoding/Reports/Luxembourg',
            'country_item': 'Q32',
            'admin_levels': {
                6: {'label': 'canton',
                    'item': 'Q1146429',
                    'count': 12,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      ?instancestatement ps:P31 wd:Q1146429.
      MINUS { ?instancestatement pq:P582 [] } .  
      OPTIONAL { ?item wdt:P402 ?osmrelation } .
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P300 ?id } .
      }''',
                    'overpass': '''[timeout:600][out:json];
        area[name="Lëtzebuerg"];
        rel(area)[admin_level="6"][boundary="administrative"]["ISO3166-2"];
        out tags;''',
                    'id_property': 'P300',
                    'id_tag': 'ISO3166-2',
                    'id_transform': False,
                    },
                8: {'label': 'municipality',
                    'item': 'Q2919801',
                    'count': 102,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      ?instancestatement ps:P31 wd:Q2919801.
      MINUS { ?instancestatement pq:P582 [] } .  
      OPTIONAL { ?item wdt:P402 ?osmrelation } .
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      }''',
                    'overpass': '''[timeout:600][out:json];
        area[name="Lëtzebuerg"];
        rel(area)[admin_level="8"][boundary="administrative"];
        out tags;''',
                    'id_property': False,
                    'id_tag': False,
                    'id_transform': False,
                    },
            }
        },
        'nl': {
            'report_page': 'Commons:Reverse geocoding/Reports/Netherlands',
            'country_item': 'Q55',
            'admin_levels': {
                4: {'label': 'province',
                    'item': 'Q134390',
                    'count': 12,
                    'sparql': """SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
      ?item p:P31 ?instancestatement.
      ?instancestatement ps:P31 wd:Q134390.
      MINUS { ?instancestatement pq:P582 [] } .  
      OPTIONAL { ?item wdt:P402 ?osmrelation } .
      OPTIONAL { ?item wdt:P373 ?commonscategory } .
      OPTIONAL { ?item wdt:P300 ?id } .
      }""",
                    'overpass': '''[timeout:600][out:json];
        area[name="Nederland"];
        rel(area)[admin_level="4"][boundary="administrative"]["ISO3166-2"]["ref:nuts"]["ref:provinciecode"];
        out tags;''',
                    'id_property': 'P300',
                    'id_tag': 'ISO3166-2',
                    'id_transform': False,
                    },
                8: {'label': 'municipality',
                    'item': 'Q2039348',
                    'count': 342,
                    'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
  ?item wdt:P382 ?id ;
        p:P31 ?instancestatement.
  ?instancestatement ps:P31 wd:Q2039348.
  MINUS { ?instancestatement pq:P582 [] } .
  OPTIONAL { ?item wdt:P373 ?commonscategory } .  
  OPTIONAL { ?item p:P402 ?osmstatement . 
            { ?osmstatement ps:P402 ?osmrelation MINUS { ?osmstatement pq:P2868 [] } } UNION
            { ?osmstatement ps:P402 ?osmrelation; pq:P2868 wd:Q2039348 }          
            } 
}''',
                    'overpass': '''[timeout:600][out:json];
        area[name="Nederland"];
        rel(area)[admin_level="8"][boundary="administrative"]["ref:gemeentecode"];
        out tags;''',
                    'id_property': 'P382',
                    'id_tag': 'ref:gemeentecode',
                    'id_transform': '%04d',
                    },
                10: {'label': 'cadastral populated place',
                     'item': 'Q1852859',
                     'count': 2501,
                     'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
  ?item p:P31 ?instancestatement.
  ?instancestatement ps:P31 wd:Q1852859. 
  MINUS { ?instancestatement pq:P582 [] } .
  OPTIONAL { ?item wdt:P373 ?commonscategory } .
  OPTIONAL { ?item p:P981 [ps:P981 ?id ; pq:P518 ?part]; p:P402 [ps:P402 ?osmrelation; pq:P518 ?part] } 
  OPTIONAL { ?item wdt:P981 ?id ;
                   p:P402 ?osmstatement . 
            { ?osmstatement ps:P402 ?osmrelation MINUS { ?osmstatement pq:P2868 [] } } UNION
            { ?osmstatement ps:P402 ?osmrelation; pq:P2868 wd:Q1852859 }          
            }  
  }''',
                     'overpass': '''[timeout:600][out:json];
    area[name="Nederland"];
    rel(area)[admin_level="10"][boundary="administrative"];
    out tags;''',
                     'id_property': 'P981',
                     'id_tag': 'ref:woonplaatscode',
                     'id_transform': False,
                     },
            }
        }
    }
    if regioncode:
        if regioncode in regions:
            report_page = regions.get(regioncode).get('report_page')
            admin_levels = regions.get(regioncode).get('admin_levels')
            wikidata_osm_checker = WikidataOsmChecker(regioncode, report_page, admin_levels, do_edits=do_edits)
            wikidata_osm_checker.run()
        else:
            pywikibot.output('Unknown region code %s' % (regioncode,))
    else:
        for regioncode in regions:
            report_page = regions.get(regioncode).get('report_page')
            admin_levels = regions.get(regioncode).get('admin_levels')
            wikidata_osm_checker = WikidataOsmChecker(regioncode, report_page, admin_levels, do_edits=do_edits)
            wikidata_osm_checker.run()

if __name__ == "__main__":
    main()
