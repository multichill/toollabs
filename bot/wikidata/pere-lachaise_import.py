#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Robot to import missing graves from Commons to Wikidata so that we can move the data there.

Focus on Père-Lachaise, but also some other places.

Worked on https://commons.wikimedia.org/wiki/Category:Graves_without_Wikidata_item
"""

import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import time
import re

def pere_lachaise_divisions():
    """
    Get a lookup table for the divisions
    :return:
    """
    result = {}
    query = """SELECT ?item ?label WHERE {
  { ?item wdt:P31 wd:Q50064469 } UNION { ?item wdt:P31 wd:Q112390525 } .
    ?item rdfs:label ?label .
  FILTER (LANG(?label)="en")
  }"""
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        try:
            result[resultitem.get('label')] = qid
        except ValueError:
            # Unknown value will trigger this
            pass
    return result

def get_pere_lachaise_generator(category_generator):
    """
    Loop over the categories and return the relevant data
    :return:
    """
    divisions = pere_lachaise_divisions()
    for category in category_generator:
        metadata = { 'category_page' : category,
                     'commons_category' : category.title(underscore=False, with_ns=False),
                     }
        title = category.title(underscore=False, with_ns=False)
        if '(' in title:
            (title, title_sep, title_junk) = title.partition('(')
        metadata['title'] = title.strip()
        try:
            metadata['wikidata'] = category.data_item().title()
        except pywikibot.exceptions.NoPageError:
            # No linked page yet
            pass
        # Do Wikidata lookup here?
        for (template, params) in category.templatesWithParams():
            if template.title(underscore=False, with_ns=False) in [ 'Category definition: Object', 'Artwork']:
                for param in params:
                    (field, sep, value) = param.partition('=')
                    if field == 'image':
                        metadata['image'] = value
                    elif field == 'object type':
                        if value.lower() == 'grave':
                            metadata['instanceofqid'] = 'Q173387'
                        elif value.lower() == 'funeral chapel':
                            metadata['instanceofqid'] = 'Q1424583'
                        elif value.lower() == 'funeral niche':
                            metadata['instanceofqid'] = 'Q56054867'
                    elif field == 'gallery' or field == 'institution':
                        if value == '{{institution:Cimetière du Père-Lachaise}}':
                            metadata['collectionqid'] = 'Q311'
                            metadata['countryqid'] = 'Q142'
                            metadata['administrativeqid'] = 'Q210720'
                        elif value =='{{institution:Highgate Cemetery}}':
                            metadata['collectionqid'] = 'Q533697'
                            metadata['countryqid'] = 'Q145'
                            metadata['administrativeqid'] = 'Q202088'
                            metadata['locationqid'] = 'Q533697'
                        if value == '{{institution:Cimetière de Passy}}':
                            metadata['collectionqid'] = 'Q1092107'
                            metadata['countryqid'] = 'Q142'
                            metadata['administrativeqid'] = 'Q194420'
                        elif value =='{{institution:Cimetière de l\'église Sainte-Marie-Madeleine d\'Aiglun}}':
                            metadata['collectionqid'] = 'Q26760299'
                            metadata['countryqid'] = 'Q145'
                            metadata['administrativeqid'] = 'Q404474'
                            metadata['locationqid'] = 'Q26760299'
                        elif value =='{{institution:Cimetière du Calvaire}}':
                            metadata['collectionqid'] = 'Q2750701'
                            metadata['countryqid'] = 'Q145'
                            metadata['administrativeqid'] = 'Q200126'
                            metadata['locationqid'] = 'Q2750701'
                        elif value =='{{institution:Cimetière de Charonne}}':
                            metadata['collectionqid'] = 'Q781858'
                            metadata['countryqid'] = 'Q145'
                            metadata['administrativeqid'] = 'Q210720'
                            metadata['locationqid'] = 'Q781858'
                        elif value =='{{institution:Cimetière communal de Massiac}}':
                            metadata['collectionqid'] = 'Q29358821'
                            metadata['countryqid'] = 'Q145'
                            metadata['administrativeqid'] = 'Q470686'
                            metadata['locationqid'] = 'Q29358821'
                        elif value =='{{institution:Cimetière Saint-Martin de Miribel}}':
                            metadata['collectionqid'] = 'Q26960618'
                            metadata['countryqid'] = 'Q145'
                            metadata['administrativeqid'] = 'Q363100'
                            metadata['locationqid'] = 'Q26960618'
                        elif value =='{{institution:Cemetery Saint-Pierre, Brignoles}}':
                            metadata['collectionqid'] = 'Q47515029'
                            metadata['countryqid'] = 'Q145'
                            metadata['administrativeqid'] = 'Q207584'
                            metadata['locationqid'] = 'Q47515029'
                    #print (field)
                    #print (value)
            elif template.title(underscore=False, with_ns=False) == 'Object location':
                if len (params) >= 2:
                    metadata['lat'] = params[0]
                    metadata['lon'] = params[1]
        for parent_category in category.categories():
            division = parent_category.title(underscore=False, with_ns=False)
            if division.startswith('Père-Lachaise Cemetery - Division ') or division.startswith('Passy Cemetery - Division '):
                if division in divisions:
                    metadata['locationqid'] = divisions.get(division)
            elif division=='Père-Lachaise Cemetery - Unknown division':
                metadata['locationqid'] = 'Q311'
        if metadata.get('instanceofqid') and metadata.get('administrativeqid') and metadata.get('locationqid'):
            yield metadata

class GraveBot:
    """
    A bot to enrich and create paintings on Wikidata
    """
    def __init__(self, dictGenerator, create=False):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.
            The dict in this generator needs to contain 'idpid' and 'collectionqid'
            * create       - Boolean to say if you want to create new items or just update existing

        """
        self.generator = dictGenerator
        self.site = pywikibot.Site('commons', 'commons')
        self.repo = pywikibot.Site().data_repository()
        self.create = create

    def run(self):
        """
        Starts the robot.
        """
        for metadata in self.generator:
            grave_item = None
            if metadata.get('wikidata'):
                grave_item = pywikibot.ItemPage(self.repo, title=metadata.get('wikidata'))
            elif self.create:
                grave_item = self.create_grave_item(metadata)
            if grave_item and grave_item.exists():
                metadata['wikidata'] = grave_item.title()
                self.update_grave_item(grave_item, metadata)

    def create_grave_item(self, metadata):
        """
        Create a new grave item based on the metadata

        :param metadata: All the metadata for this new grave
        :return: The newly created grave item
        """
        category_page = metadata.get('category_page')
        # data['labels'][lang] = {'language': lang, 'value': label}
        data = {'labels': {'en' : { 'language' : 'en', 'value' : metadata.get('title')} },
                'descriptions': {},
                'sitelinks' : [{'site' : 'commonswiki',
                                'title' : category_page.title(),
                                },],
                }
        #print (data)

        identification = {}
        summary = 'Creating new item with data from [[:Commons:%s]]' % (category_page.title(),)
        pywikibot.output(summary)

        result = self.repo.editEntity(identification, data, summary=summary)

        grave_item_title = result.get(u'entity').get('id')

        # Wikidata is sometimes lagging. Wait for additional 5 seconds before trying to actually use the item
        time.sleep(5)

        wikidata_regex = '(\|\s*wikidata\s*\=)([\s\r\n]+)'
        repl = '\\1%s\\2' % (grave_item_title,)
        newtext = re.sub(wikidata_regex, repl, category_page.text, count=1)
        category_page.put(newtext, summary='Wikidata item created')

        grave_item = pywikibot.ItemPage(self.repo, title=grave_item_title)
        #grave_item.setSitelink(category_page)

        return grave_item

    def update_grave_item(self, grave_item, metadata):
        """
        Add statements and other data to the artworkItem
        :param grave_item: The artwork item to work on
        :param metadata: All the metadata about this artwork.
        :return: Nothing, updates item in place
        """

        ## Add the (missing) labels to the item based on the title.
        #self.addLabels(artworkItem, metadata)

        ## Add the (missing) descriptions to the item.
        #self.addDescriptions(artworkItem, metadata)

        # Add instance of (P31) to the item.
        self.addItemStatement(grave_item, 'P31', metadata.get('instanceofqid'))

        # Add collection (P195) to the item.
        self.addItemStatement(grave_item, 'P195', metadata.get('collectionqid'))

        # Add country (P17) to the item.
        self.addItemStatement(grave_item, 'P17', metadata.get('countryqid'))

        # Add located in the administrative territorial entity (P131) to the item.
        self.addItemStatement(grave_item, u'P131', metadata.get('administrativeqid'))

        # Add location (P276) to the item.
        self.addItemStatement(grave_item, 'P276', metadata.get('locationqid'))

        data = grave_item.get()
        claims = data.get('claims')

        if metadata.get('image') and not 'P18' in claims:
            imagefile = pywikibot.FilePage(self.site, title=metadata.get('image'))
            if imagefile.exists():
                newclaim = pywikibot.Claim(self.repo, 'P18')
                newclaim.setTarget(imagefile)

                pywikibot.output('Adding %s --> %s' % (newclaim.getID(), newclaim.getTarget()))
                try:
                    grave_item.addClaim(newclaim)
                except pywikibot.exceptions.OtherPageSaveError:
                    # Sometimes this trips up?
                    pass

        if metadata.get('commons_category') and not 'P373' in claims:
            newclaim = pywikibot.Claim(self.repo, 'P373')
            newclaim.setTarget(metadata.get('commons_category'))

            pywikibot.output('Adding %s --> %s' % (newclaim.getID(), newclaim.getTarget()))
            grave_item.addClaim(newclaim)

        ## Add creator (P170) to the item.
        #self.addItemStatement(artworkItem, u'P170', metadata.get(u'creatorqid'), metadata.get(u'refurl'))

        ## Add inception (P571) to the item.
        #self.addInception(artworkItem, metadata)

    def addItemStatement(self, item, pid, qid):
        """
        Helper function to add a statement
        """
        if not qid:
            return False

        claims = item.get().get('claims')
        if pid in claims:
            return

        newclaim = pywikibot.Claim(self.repo, pid)
        destitem = pywikibot.ItemPage(self.repo, qid)
        if destitem.isRedirectPage():
            destitem = destitem.getRedirectTarget()

        newclaim.setTarget(destitem)
        pywikibot.output(u'Adding %s->%s to %s' % (pid, qid, item))
        item.addClaim(newclaim)


def main(*args):
    gen = None
    dryrun = False
    create = False
    genFactory = pagegenerators.GeneratorFactory()

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True
        elif genFactory.handle_arg(arg):
            continue

    gen = pagegenerators.PageClassGenerator(genFactory.getCombinedGenerator(gen, preload=True))
    dict_gen = get_pere_lachaise_generator(gen)

    if dryrun:
        for grave in dict_gen:
            print (grave)
    else:
        grave_bot = GraveBot(dict_gen, create=create)
        grave_bot.run()

if __name__ == "__main__":
    main()

