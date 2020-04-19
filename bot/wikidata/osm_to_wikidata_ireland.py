#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import missing OSM relation links to Wikidata for parishes in Ireland

It uses a dump from overpass ( http://overpass-turbo.eu/s/T15 ) and logainm:ref or wikidata to make the match

Could easily be adapted to work on another subset.
"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import requests
import re
import datetime
import time
import json

class OsmToWikidataBot:
    """
    A bot to add missing OSM links
    """
    def __init__(self):
        """
        Arguments: None
        """
        self.wikidata_parishes = None
        self.logainm_to_wikidata = None
        self.osm_to_wikidata = None
        self.wikidata_to_osm = None
        self.getWikidataLookupTables()

        self.generator = self.getOsmRelationGenerator()
        self.repo = pywikibot.Site().data_repository()

    def getWikidataLookupTables(self):
        """
        Fill the lookup tables
        """
        wikidata_parishes = []
        logainm_to_wikidata = {}
        osm_to_wikidata = {}
        wikidata_to_osm = {}

        query = u"""SELECT ?item ?logainm ?osm WHERE {
  ?instance ps:P31 wd:Q3910694 .
  ?item p:P31 ?instance .
  MINUS { ?instance pq:P582 [] } . 
  OPTIONAL { ?item wdt:P5097 ?logainm }.
  OPTIONAL { ?item wdt:P402 ?osm } 
} LIMIT 20000"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            logainm = resultitem.get('logainm')
            osm = resultitem.get('osm')
            wikidata_parishes.append(qid)
            if logainm:
                logainm_to_wikidata[logainm] = qid
            if osm:
                osm_to_wikidata[osm] = qid
                wikidata_to_osm[qid] = osm

        self.wikidata_parishes = wikidata_parishes
        self.logainm_to_wikidata = logainm_to_wikidata
        self.osm_to_wikidata = osm_to_wikidata
        self.wikidata_to_osm = wikidata_to_osm

    def getOsmRelationGenerator(self):
        """
        Get a generator returning relation objects
        :yield: Element
        """
        with open('/home/mdammers/temp/Ireland_all_parishes_OSM_rel.json') as json_file:
            data = json.load(json_file)
            for element in data.get('elements'):
                yield element

    def run(self):
        """
        Starts the robot.
        """
        foundit = True
        for osm_relation in self.generator:
            if osm_relation.get('id')==7013627:
                foundit = True
            if foundit:
                self.processRelation(osm_relation)

    def processRelation(self, osm_relation):
        """
        Work on one relation.

        :param osm_relation: A dict as returned by overpass
        :return: Edit in place if needed
        """
        osmid = str(osm_relation.get('id'))
        logainmid = None
        qid = None
        if osm_relation.get('tags').get('logainm:ref'):
            logainmid = osm_relation.get('tags').get('logainm:ref')
        if osm_relation.get('tags').get('wikidata'):
            qid = osm_relation.get('tags').get('wikidata')
        osmname = osm_relation.get('tags').get('name')

        if self.osm_to_wikidata.get(osmid):
            # Too verbose
            return
            if self.osm_to_wikidata.get(osmid)==qid:
                pywikibot.output('Wikidata %s and OSM %s already link to each other' % (qid, osmid))
            else:
                pywikibot.output('Wikidata %s already links to OSM %s' % (self.osm_to_wikidata.get(osmid), osmid))
            return
        elif qid:
            if qid in self.wikidata_to_osm:
                if self.wikidata_to_osm.get(qid)==osmid:
                    pywikibot.output('Wikidata %s and OSM %s already link to each other' % (qid, osmid))
                else:
                    pywikibot.output('OSM %s links to Wikidata %s, but Wikidata links to %s' % (osmid, qid, self.wikidata_to_osm.get(qid)))
            if qid in self.wikidata_parishes:
                if logainmid:
                    if logainmid in self.logainm_to_wikidata:
                        if self.logainm_to_wikidata.get(logainmid)==qid:
                            summary = u'based on backlink from OSM %s with name "%s" and same Logainm ID %s' % (osmid, osmname, logainmid)
                            self.addOsmRelation(qid, osmid, summary)
                else:
                    summary = u'based on backlink from OSM %s with name "%s"' % (osmid, osmname)
                    self.addOsmRelation(qid, osmid, summary)
            else:
                print('OSM %s links to Wikidata %s, but I don\'t have that item' % (osmid,qid))
            return

        if logainmid:
            if logainmid in self.logainm_to_wikidata:
                qid = self.logainm_to_wikidata.get(logainmid)
                summary = u'based on same Logainm ID %s on Wikidata and OSM %s with name "%s"' % (logainmid, osmid, osmname)
                self.addOsmRelation(qid, osmid, summary)
            else:
                pywikibot.output('No match found for OSM %s and Logainm ID %s with name "%s"' % (osmid, logainmid, osmname))
            return


        pywikibot.output('No match found for OSM %s with name "%s"' % (osmid, osmname))

    def addOsmRelation(self, qid, osmid, summary):
        """
        Add the actual OSM relation

        :param qid: The qid of the Wikidata item to work on
        :param osmid: The OSM relation ID
        :param summary: The summary to use
        :return: Edit in place
        """
        item  = pywikibot.ItemPage(self.repo, qid)
        data = item.get()
        claims = data.get('claims')

        if 'P402' in claims:
            # Already done
            pywikibot.output('Wikidata %s already has OSM %s, no edit needed' % (qid, osmid))
            return

        newclaim = pywikibot.Claim(self.repo, u'P402')
        newclaim.setTarget(osmid)
        pywikibot.output('Adding %s to %s %s' % (osmid, qid, summary))
        item.addClaim(newclaim, summary=summary)


def main(*args):
    """
    Main function. Grab a generator and pass it to the bot to work on
    """
    osmToWikidataBot = OsmToWikidataBot()
    osmToWikidataBot.run()

if __name__ == "__main__":
    main()
