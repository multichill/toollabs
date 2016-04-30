#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to match images in one of the subcategories of https://commons.wikimedia.org/wiki/Category:Google_Art_Project_works_by_collection with Wikidata items.

"""
#import artdatabot
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.wikidataquery as wdquery
#import requests
#import urllib2
import re
import HTMLParser
import xml.etree.ElementTree as ET


class ImageFindBot:
    """
    A bot to enrich and create paintings on Wikidata
    """
    def __init__(self, cattitle, collectionqid):
        """
        Arguments:
            * cattitle    - Title of the category to look for images.
            * collectionqid       - The Q number id of the collection

        """
        #firstrecord  = dictGenerator.next()
        #self.generator = itertools.chain([firstrecord], dictGenerator)
        self.repo = pywikibot.Site().data_repository()
        self.site = pywikibot.Site(u'commons', u'commons')
        self.category = pywikibot.Category(self.site, title=cattitle)
        self.generator = pagegenerators.FileGenerator(pagegenerators.PreloadingGenerator(self.category.articles(namespaces=6)))
        #self.create = create
        
        #self.idProperty = firstrecord.get(u'idpid')
        self.collectionqid = collectionqid
        #self.collectionitem = pywikibot.ItemPage(self.repo, self.collectionqid)
        self.artworkIds = self.fillCache(self.collectionqid, u'217')
        
    def fillCache(self, collectionqid, idProperty, queryoverride=u'', cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of items we already have an object for
        '''
        result = {}
        if queryoverride:
            query = queryoverride
        else:
            query = u'CLAIM[195:%s] AND CLAIM[%s]' % (collectionqid.replace(u'Q', u''),
                                                      idProperty,)

        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset, props=[str(idProperty),])

        if data.get('status').get('error')=='OK':
            expectedItems = data.get('status').get('items')
            props = data.get('props').get(str(idProperty))
            for prop in props:
                # FIXME: This will overwrite id's that are used more than once.
                # Use with care and clean up your dataset first
                result[prop[2]] = prop[0]

            if expectedItems==len(result):
                pywikibot.output('I now have %s items in cache' % expectedItems)
            else:
                pywikibot.output('I expected %s items, but I have %s items in cache' % (expectedItems, len(result),))

        return result
                        
    def run(self):
        """
        Starts the robot.
        """

        searchregex = u'\s*\|\s*museum_internal_id\s*=\s*([^\s]+)\s*'
            
        for filepage in self.generator:
            text = filepage.get()
            match = re.search(searchregex, text)
            if not match:
                pywikibot.output(u'No match found')
                continue

            invnum = match.group(1)
            
            artworkItem = None

            if invnum in self.artworkIds:
                artworkItemTitle = u'Q%s' % (self.artworkIds.get(invnum),)
                print artworkItemTitle
                artworkItem = pywikibot.ItemPage(self.repo, title=artworkItemTitle)
            else:
                pywikibot.output(u'No artwork item found for id %s' % (invnum,))
                continue
            data = artworkItem.get()
            claims = data.get('claims')
                                 
            if u'P18' not in claims:
                newclaim = pywikibot.Claim(self.repo, u'P18')
                newclaim.setTarget(filepage)
                pywikibot.output('Adding %s --> %s based on inventory number %s' % (newclaim.getID(), newclaim.getTarget(), invnum))
                artworkItem.addClaim(newclaim)

def main(*args):

    # Process global args and prepare generator args parser
    local_args = pywikibot.handle_args(args)
    googlecat = False
    collectionid = False
    for arg in local_args:
        if arg.startswith('-googlecat'):
            if len(arg) == 10:
                googlecat = pywikibot.input(
                    u'Please enter the category you want to work on:')
            else:
                googlecat = arg[11:]
        elif arg.startswith('-collectionid'):
            if len(arg) == 13:
                collectionid = pywikibot.input(
                    u'Please enter the collectionid you want to work on:')
            else:
                collectionid = arg[14:]
        #else:
        #    generator_factory.handleArg(arg)

    if googlecat and collectionid:
        imageFindBot = ImageFindBot(googlecat, collectionid)
        imageFindBot.run()
    else:
        pywikibot.output(u'Usage: pwb.py add_google_images.py -googlecat:<category name> -collectionid:Q<123>')
    
    

if __name__ == "__main__":
    main()
