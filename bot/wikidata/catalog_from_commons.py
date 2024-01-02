#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Tool to match catalog on Commons with Wikidata items
"""
import pywikibot
import requests
import pywikibot.data.sparql
import time
import re
import json
import datetime
#import urllib.parse
import os.path


class CatalogFromCommons:
    """

    """
    def __init__(self, catalogid):
        """
        Setup the bot
        """
        self.commons_site = pywikibot.Site('commons', 'commons')
        self.repo = pywikibot.Site().data_repository()
        self.catalogid = catalogid
        self.catalog = pywikibot.ItemPage(self.repo, title=catalogid)
        self.catalog_on_wikidata = self.get_catalog_on_wikidata(catalogid)
        self.commons_gallery = list(self.catalog.iterlinks(family='commons'))[0]
        self.catalog_on_commons = self.parse_gallery()
        #self.catalog.getSitelink(self.commons_site)
        #self.friedlander_on_wikidata = self.get_usage_on_wikidata('P11918')  # self.get_friedlander_on_wikidata()
        #self.balat_on_wikidata = self.get_usage_on_wikidata('P3293')
        #self.rkd_on_wikidata = self.get_usage_on_wikidata('P350')
        #self.data_session = requests.Session()

    def get_catalog_on_wikidata(self, catalogid):
        """
        Get the entries for a single catalog on Wikidata
        """
        result = {}
        query = """SELECT ?item ?catalog_code  WHERE { 
  ?item p:P528 [ps:P528 ?catalog_code ; pq:P972 wd:%s ] .
  } 
LIMIT 10000""" % (catalogid, )

        sq = pywikibot.data.sparql.SparqlQuery()
        query_result = sq.select(query)

        for result_item in query_result:
            qid = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
            identifier = result_item.get('catalog_code')
            result[identifier] = qid
        return result

    def parse_gallery(self):
        """
        Parse the gallery on Commons
        :return:
        """
        result = {}

        gallery_regex = '(<gallery.+</gallery>)'
        gallery_match = re.search(gallery_regex, self.commons_gallery.text, flags=re.DOTALL)
        if gallery_match:
            gallery_text = gallery_match.group(1)

            tile_regex = '^([^\|]+\.[^\|]+)\|([^\|]+)$'
            tile_regex = '^(.+)\|(.+)$'
            for match in re.finditer(tile_regex, gallery_text, flags=re.MULTILINE):
                if 'Category:' not in match.group(1):
                    #print(match.group(1))
                    #print(match.group(2))
                    result[match.group(2)] = match.group(1)
            return result

    def run(self):
        """

        :return:
        """
        #self.parse_gallery
        #print(self.catalog_on_commons)
        self.add_missing_wikidata_links()
    def add_missing_wikidata_links(self):
        """
        Loop over all the images and see if we need to add a missing Wikidata link
        :return:
        """
        for catalog_code in self.catalog_on_commons:
            commons_image = self.catalog_on_commons.get(catalog_code)
            if catalog_code in self.catalog_on_wikidata:
                wikidata_item = self.catalog_on_wikidata.get(catalog_code)
                #print(catalog_code)
                #print(commons_image)
                #print(wikidata_item)
                self.add_missing_wikidata_link(catalog_code, commons_image, wikidata_item)
            else:
                self.add_missing_catalog_code(catalog_code, commons_image)

    def add_missing_wikidata_link(self, catalog_code, commons_image, wikidata_item):
        """

        :param catalog_code:
        :param commons_image:
        :param wikidata_item:
        :return:
        """
        file = pywikibot.FilePage(self.commons_site, title=commons_image)
        item = pywikibot.ItemPage(self.repo, title=wikidata_item)

        mediainfo = file.data_item()

        try:
            data = mediainfo.get()
            claims = data.get('statements')
            if 'P6243' in claims or 'P921' in claims:
                #print('already linked')
                return
        except pywikibot.exceptions.NoWikibaseEntityError:
            # No MediaInfo yet
            pass
        print('Based on catalog code %s' % (catalog_code, ))
        print('The file %s' % (file,))
        print('Should be linked with the Wikidata item %s' % (item,))

        summary = 'based on catalog code "%s" on %s' % (catalog_code,
                                                        self.commons_gallery.title(as_link=True,
                                                                                   insite=self.commons_site),
                                                        )
        newclaim = pywikibot.Claim(self.repo, 'P6243')
        newclaim.setTarget(item)
        mediainfo.addClaim(newclaim, summary=summary)

        # FIXME: Figure out the editEntity

        #statements_queue = []

        #for pid in 'P180', 'P921', 'P6243':
        #    newclaim = pywikibot.Claim(self.repo, pid)
        #    newclaim.setTarget(item)
        #    statements_queue.append(newclaim.toJSON())
        #mediainfo.editEntity(data={'statements': statements_queue}, summary=summary)

    def add_missing_catalog_code(self, catalog_code, commons_image):
        """
        Found a catalog code on a Commons image that is not in use
        :return:
        """
        file = pywikibot.FilePage(self.commons_site, title=commons_image)

        mediainfo = file.data_item()

        try:
            data = mediainfo.get()
        except pywikibot.exceptions.NoWikibaseEntityError:
            # No mediainfo, just return
            return

        claims = data.get('statements')
        if 'P6243' not in claims: # or 'P921' in claims:
            #print('already linked')
            return

        item = claims.get('P6243')[0].getTarget()

        summary = 'based on %s with catalog code "%s" on %s' % (file.title(as_link=True,
                                                                           insite=self.repo),
                                                                catalog_code,
                                                                self.commons_gallery.title(as_link=True,
                                                                                           insite=self.repo),
                                                                )

        print('Based on catalog code %s' % (catalog_code, ))
        print('On the file %s' % (file,))
        print('Catalog code should a added on the Wikidata item %s' % (item,))

        wikidata_claims = item.get().get('claims')
        if 'P528' in wikidata_claims:
            print('Already has catalog code')
            for claim in wikidata_claims.get('P528'):
                if claim.qualifiers.get('P972'):
                    qualifier = claim.qualifiers.get('P972')[0]
                    if qualifier.getTarget() == self.catalog:
                        print('Already has catalog code in same catalog, skipping')
                        return

        newclaim = pywikibot.Claim(self.repo, 'P528')
        newclaim.setTarget(catalog_code)

        newqualifier = pywikibot.Claim(self.repo, 'P972')
        newqualifier.setTarget(self.catalog)

        refimported = pywikibot.Claim(self.repo, u'P143')
        refimported.setTarget(pywikibot.ItemPage(self.repo, title='Q565'))

        refurl = pywikibot.Claim(self.repo, u'P854')
        refurl.setTarget(file.full_url())

        refdate = pywikibot.Claim(self.repo, u'P813')
        today = datetime.datetime.today()
        date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
        refdate.setTarget(date)

        item.addClaim(newclaim, summary=summary)
        newclaim.addQualifier(newqualifier)
        newclaim.addSources([refimported, refurl, refdate])


def main(*args):
    """
    :param args:
    :return:
    """
    catalogid = None

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-catalogid:'):
            if len(arg) == 11:
                catalogid = pywikibot.input(
                        u'Please enter the catalogid you want to work on:')
            else:
                catalogid = arg[11:]


    catalog_from_commons = CatalogFromCommons(catalogid)
    catalog_from_commons.run()


if __name__ == "__main__":
    main()
