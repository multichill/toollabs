#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import art data to Wikidata.

"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib2
import re
import pywikibot.data.wikidataquery as wdquery
import datetime
import HTMLParser
import posixpath
from urlparse import urlparse
from urllib import urlopen
import hashlib
import io
import base64
import upload
import tempfile
import os
import time
import itertools

class ArtDataBot:
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
        firstrecord  = dictGenerator.next()
        self.generator = itertools.chain([firstrecord], dictGenerator)
        self.repo = pywikibot.Site().data_repository()
        self.create = create
        
        self.idProperty = firstrecord.get(u'idpid')
        self.collectionqid = firstrecord.get(u'collectionqid')
        self.collectionitem = pywikibot.ItemPage(self.repo, self.collectionqid)
        self.artworkIds = self.fillCache(self.collectionqid, u'217')

        self.artworkIds[u'1']=u'21614077'
        self.artworkIds[u'123']=u'21614244'
        
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
            
        for metadata in self.generator:
            # Buh, for this one I know for sure it's in there
            
            #print metadata[u'id']
            #print metadata[u'url']

            # Do some url magic so that all url fields are always filled
            if not metadata.get('refurl'):
                metadata['refurl']=metadata['url']
            if not metadata.get('idrefurl'):
                metadata['idrefurl']=metadata['refurl']
            if not metadata.get('describedbyurl'):
                metadata['describedbyurl']=metadata['url']

            
            artworkItem = None
            newclaims = []
            if metadata[u'id'] in self.artworkIds:
                artworkItemTitle = u'Q%s' % (self.artworkIds.get(metadata[u'id']),)
                print artworkItemTitle
                artworkItem = pywikibot.ItemPage(self.repo, title=artworkItemTitle)

            elif self.create:
                #Break for now
                #print u'Let us create stuff'
                #continue
                #print u'WTFTFTFTFT???'
                
                #print 'bla'


                data = {'labels': {},
                        'descriptions': {},
                        }

                # loop over stuff
                if metadata.get('title'):
                    for lang, label in metadata['title'].iteritems():
                        data['labels'][lang] = {'language': lang, 'value': label}

                if metadata.get('description'):
                    for lang, description in metadata['description'].iteritems():
                        data['descriptions'][lang] = {'language': lang, 'value': description}
                
                print data
                
                identification = {}
                summary = u'Creating new item with data from %s ' % (metadata[u'url'],)
                pywikibot.output(summary)
                try:
                    result = self.repo.editEntity(identification, data, summary=summary)
                except pywikibot.data.api.APIError:
                    # We got ourselves a duplicate label and description, let's correct that by adding collection and the id
                    pywikibot.output(u'Oops, already had that one. Trying again')
                    for lang, description in metadata['description'].iteritems():
                        data['descriptions'][lang] = {'language': lang, 'value': u'%s (%s %s)' % (description, metadata['collectionshort'], metadata['id'],) }
                    result = self.repo.editEntity(identification, data, summary=summary)
                    pass
                    
                    
                artworkItemTitle = result.get(u'entity').get('id')

                # Wikidata is sometimes lagging. Wait for 10 seconds before trying to actually use the item
                time.sleep(10)
                
                artworkItem = pywikibot.ItemPage(self.repo, title=artworkItemTitle)

                # Add to self.artworkIds so that we don't create dupes
                self.artworkIds[metadata[u'id']]=artworkItemTitle.replace(u'Q', u'')

                # Add the id to the item so we can get back to it later
                newclaim = pywikibot.Claim(self.repo, self.idProperty)
                newclaim.setTarget(metadata[u'id'])
                pywikibot.output('Adding new id claim to %s' % artworkItem)
                artworkItem.addClaim(newclaim)

                self.addReference(artworkItem, newclaim, metadata[u'idrefurl'])
                
                newqualifier = pywikibot.Claim(self.repo, u'P195') #Add collection, isQualifier=True
                newqualifier.setTarget(self.collectionitem)
                pywikibot.output('Adding new qualifier claim to %s' % artworkItem)
                newclaim.addQualifier(newqualifier)

                collectionclaim = pywikibot.Claim(self.repo, u'P195')
                collectionclaim.setTarget(self.collectionitem)
                pywikibot.output('Adding collection claim to %s' % artworkItem)
                artworkItem.addClaim(collectionclaim)

                # Add the date they got it as a qualifier to the collection
                # FIXME: Still have to rewrite this part
                '''
                if metadata.get(u'acquisitiondate'):
                    colqualifier = pywikibot.Claim(self.repo, u'P580')
                    acdate = None
                    if len(painting[u'acquisitiondate'])==4 and painting[u'acquisitiondate'].isnumeric(): # It's a year
                        acdate = pywikibot.WbTime(year=painting[u'acquisitiondate'])
                    elif len(painting[u'acquisitiondate'].split(u'-', 2))==3:
                        (acday, acmonth, acyear) = painting[u'acquisitiondate'].split(u'-', 2)
                        acdate = pywikibot.WbTime(year=int(acyear), month=int(acmonth), day=int(acday))
                    if acdate:
                        colqualifier.setTarget(acdate)
                        pywikibot.output('Adding new acquisition date qualifier claim to collection on %s' % paintingItem)
                        collectionclaim.addQualifier(colqualifier)
                '''
                
                self.addReference(artworkItem, collectionclaim, metadata[u'refurl'])
                
            
            if artworkItem and artworkItem.exists():
                metadata['wikidata'] = artworkItem.title()

                # FIXME: Add logic to add missing labels or aliases (mind dupe exception)

                # FIXME: Add logic to add missing description (mind dupe exception)
                
                data = artworkItem.get()
                claims = data.get('claims')
                #print claims

                # instance of
                self.addItemStatement(artworkItem, u'P31', metadata.get(u'instanceofqid'), metadata.get(u'refurl'))

                # instance of
                self.addItemStatement(artworkItem, u'P276', metadata.get(u'locationqid'), metadata.get(u'refurl'))

                # instance of
                self.addItemStatement(artworkItem, u'P170', metadata.get(u'creatorqid'), metadata.get(u'refurl'))                

                # Inception
                if u'P571' not in claims and metadata.get(u'inception'):
                    if len(metadata[u'inception'])==4 and metadata[u'inception'].isnumeric(): # It's a year
                        newdate = pywikibot.WbTime(year=metadata[u'inception'])
                        newclaim = pywikibot.Claim(self.repo, u'P571')
                        newclaim.setTarget(newdate)
                        pywikibot.output('Adding date of creation claim to %s' % artworkItem)
                        artworkItem.addClaim(newclaim)
                
                        self.addReference(artworkItem, newclaim, metadata[u'refurl'])

                '''
                # material used
                if u'P186' not in claims and painting.get(u'medium'):
                    if painting.get(u'medium')==u'Oil on canvas':
                        olieverf = pywikibot.ItemPage(self.repo, u'Q296955')
                        doek = pywikibot.ItemPage(self.repo, u'Q4259259')
                        oppervlak = pywikibot.ItemPage(self.repo, u'Q861259')
                        
                        newclaim = pywikibot.Claim(self.repo, u'P186')
                        newclaim.setTarget(olieverf)
                        pywikibot.output('Adding new oil paint claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        self.addReference(paintingItem, newclaim, painting[u'url'])

                        newclaim = pywikibot.Claim(self.repo, u'P186')
                        newclaim.setTarget(doek)
                        pywikibot.output('Adding new canvas claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        self.addReference(paintingItem, newclaim, painting[u'url'])
                
                        newqualifier = pywikibot.Claim(self.repo, u'P518') #Applies to part
                        newqualifier.setTarget(oppervlak)
                        pywikibot.output('Adding new qualifier claim to %s' % paintingItem)
                        newclaim.addQualifier(newqualifier)
                '''
                
                # Described at url 
                if u'P973' not in claims:
                    newclaim = pywikibot.Claim(self.repo, u'P973')
                    newclaim.setTarget(metadata[u'describedbyurl'])
                    pywikibot.output('Adding described at claim to %s' % artworkItem)
                    artworkItem.addClaim(newclaim)
                

    def addItemStatement(self, item, pid, qid, url):
        '''
        Helper function to add a statement
        '''
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
        self.addReference(item, newclaim, url)
        
    def addReference(self, item, newclaim, url):
        """
        Add a reference with a retrieval url and todays date
        """
        pywikibot.output('Adding new reference claim to %s' % item)
        refurl = pywikibot.Claim(self.repo, u'P854') # Add url, isReference=True
        refurl.setTarget(url)
        refdate = pywikibot.Claim(self.repo, u'P813')
        today = datetime.datetime.today()
        date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
        refdate.setTarget(date)
        newclaim.addSources([refurl, refdate])
      
        

def main():
    print u'Dude, write your own bot'    
    

if __name__ == "__main__":
    main()
