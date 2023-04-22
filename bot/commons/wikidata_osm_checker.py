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
                    # TODO: Add transformations
                    pass
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
            sparql_query = requests.utils.quote(self.admin_levels.get(admin_level).get('sparql'))
            overpass_query = requests.utils.quote(self.admin_levels.get(admin_level).get('overpass'))
            text += '* [https://query.wikidata.org/#%s SPARQL query]\n' % (sparql_query, )
            text += '* [http://overpass-api.de/api/interpreter?data=%s overpass query]\n' % (overpass_query, )
            text += self.check_count(admin_level)

            text += self.check_completeness_links(self.wd_item_relation.get(admin_level), 'Wikidata', 'OpenStreetMap')
            text += self.check_completeness_links(self.osm_relation_item.get(admin_level), 'OpenStreetMap', 'Wikidata')

            id_property = self.admin_levels.get(admin_level).get('id_property')
            id_tag = self.admin_levels.get(admin_level).get('id_tag')

            if id_property and id_tag:
                id_property_text = '{{P|%s}}' % (id_property)
                id_tag_text = 'tag "%s"' % (id_tag)
                text += self.check_completeness_links(self.wd_item_id.get(admin_level), 'Wikidata', id_property_text)
                text += self.check_completeness_links(self.osm_relation_id.get(admin_level), 'OpenStreetMap', id_tag_text)

            text += self.check_completeness_links(self.wd_item_commons_category.get(admin_level), 'Wikidata', 'Commons category')
            text += self.check_interlinks(self.wd_item_relation.get(admin_level), self.osm_item_relation.get(admin_level))

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


    def add_missing_osm_backlink(self, qid, osm):
        """
        Add the missing OSM backlink if it doesn't have a OSM link already

        :param qid: The qid of the Wikidata item to work on
        :param osm: The OSM relation ID
        :return: If it was added or not
        """
        item = pywikibot.ItemPage(self.repo, qid)
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
                    'id_transform': False,
                    },
                10: {'label': 'cadastral populated place',
                     'item': 'Q1852859',
                     'count': 2501,
                     'sparql': '''SELECT ?item ?osmrelation ?commonscategory ?id WHERE {
  ?item wdt:P981 ?id ;
        p:P31 ?instancestatement.
  ?instancestatement ps:P31 wd:Q1852859.  
  OPTIONAL { ?item wdt:P373 ?commonscategory } .
  OPTIONAL { ?item p:P402 ?osmstatement . 
            { ?osmstatement ps:P402 ?osmrelation MINUS { ?osmstatement pq:P2868 [] } } UNION
            { ?osmstatement ps:P402 ?osmrelation; pq:P2868 wd:Q1852859 }          
            }  
  }''',
                     'overpass': '''[timeout:600][out:json];
    area[name="Nederland"];
    rel(area)[admin_level="10"][boundary="administrative"]["ref:woonplaatscode"];
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
