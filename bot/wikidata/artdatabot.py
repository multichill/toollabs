#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import art data to Wikidata.

"""
import pywikibot
from pywikibot import pagegenerators
import re
import pywikibot.data.sparql
import datetime
import posixpath
import hashlib
import io
import base64
import tempfile
import os
import time
import itertools
import copy

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
        firstrecord = next(dictGenerator)
        self.generator = itertools.chain([firstrecord], dictGenerator)
        self.repo = pywikibot.Site().data_repository()
        self.create = create
        
        self.idProperty = firstrecord.get(u'idpid')
        self.collectionqid = firstrecord.get(u'collectionqid')
        self.collectionitem = pywikibot.ItemPage(self.repo, self.collectionqid)
        self.artworkIds = self.fillCache(self.collectionqid,self.idProperty)

    def fillCache(self, collectionqid, idProperty):
        '''
        Build an ID cache so we can quickly look up the id's for property

        '''
        result = {}
        sq = pywikibot.data.sparql.SparqlQuery()

        # FIXME: Do something with the collection qualifier
        query = u'SELECT ?item ?id WHERE { ?item wdt:P195 wd:%s . ?item wdt:%s ?id }' % (collectionqid,
                                                                                                idProperty)
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[resultitem.get('id')] = qid
        pywikibot.output(u'The query "%s" returned %s items' % (query, len(result)))
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
                artworkItemTitle = self.artworkIds.get(metadata[u'id'])
                print (artworkItemTitle)
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
                    for lang, label in metadata['title'].items():
                        data['labels'][lang] = {'language': lang, 'value': label}

                if metadata.get('description'):
                    for lang, description in metadata['description'].items():
                        data['descriptions'][lang] = {'language': lang, 'value': description}
                
                identification = {}
                summary = u'Creating new item with data from %s ' % (metadata[u'url'],)
                pywikibot.output(summary)
                try:
                    result = self.repo.editEntity(identification, data, summary=summary)
                except pywikibot.data.api.APIError:
                    # TODO: Check if this is pywikibot.OtherPageSaveError too
                    # We got ourselves a duplicate label and description, let's correct that by adding collection and the id
                    pywikibot.output(u'Oops, already had that one. Trying again')
                    for lang, description in metadata['description'].items():
                        data['descriptions'][lang] = {'language': lang, 'value': u'%s (%s %s)' % (description, metadata['collectionshort'], metadata['id'],) }
                    result = self.repo.editEntity(identification, data, summary=summary)
                    pass

                artworkItemTitle = result.get(u'entity').get('id')

                # Wikidata is sometimes lagging. Wait for 10 seconds before trying to actually use the item
                time.sleep(10)
                
                artworkItem = pywikibot.ItemPage(self.repo, title=artworkItemTitle)

                # Add to self.artworkIds so that we don't create dupes
                self.artworkIds[metadata[u'id']]=artworkItemTitle

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
                if metadata.get(u'acquisitiondate'):
                    if type(metadata[u'acquisitiondate']) is int or (len(metadata[u'acquisitiondate'])==4 and \
                                                                   metadata[u'acquisitiondate'].isnumeric()): # It's a year
                        acdate = pywikibot.WbTime(year=metadata[u'acquisitiondate'])
                        colqualifier = pywikibot.Claim(self.repo, u'P580')
                        colqualifier.setTarget(acdate)
                        pywikibot.output('Adding new acquisition date qualifier claim to collection on %s' % artworkItem)
                        collectionclaim.addQualifier(colqualifier)
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

                '''
                
                self.addReference(artworkItem, collectionclaim, metadata[u'refurl'])

                # For the meta collections the option to add extra inventory number and extra collections
                if metadata.get(u'extracollectionqid'):
                    extracollectionitem = pywikibot.ItemPage(self.repo, metadata.get(u'extracollectionqid'))
                    collectionclaim = pywikibot.Claim(self.repo, u'P195')
                    collectionclaim.setTarget(extracollectionitem)
                    pywikibot.output('Adding collection claim to %s' % artworkItem)
                    artworkItem.addClaim(collectionclaim)

                    if metadata.get(u'extraid'):
                        newclaim = pywikibot.Claim(self.repo, self.idProperty)
                        newclaim.setTarget(metadata[u'extraid'])
                        pywikibot.output('Adding extra new id claim to %s' % artworkItem)
                        artworkItem.addClaim(newclaim)

                        self.addReference(artworkItem, newclaim, metadata[u'idrefurl'])

                        newqualifier = pywikibot.Claim(self.repo, u'P195') #Add collection, isQualifier=True
                        newqualifier.setTarget(extracollectionitem)
                        pywikibot.output('Adding new qualifier claim to %s' % artworkItem)
                        newclaim.addQualifier(newqualifier)

                # And in some cases we need this one
                if metadata.get(u'extracollectionqid2'):
                    extracollectionitem = pywikibot.ItemPage(self.repo, metadata.get(u'extracollectionqid2'))
                    collectionclaim = pywikibot.Claim(self.repo, u'P195')
                    collectionclaim.setTarget(extracollectionitem)
                    pywikibot.output('Adding collection claim to %s' % artworkItem)
                    artworkItem.addClaim(collectionclaim)

            
            if artworkItem and artworkItem.exists():
                metadata['wikidata'] = artworkItem.title()

                data = artworkItem.get()
                claims = data.get('claims')

                # Add missing labels
                # FIXME: Move to a function
                # FIXME Do something with aliases too
                labels = data.get('labels')
                if metadata.get('title'):
                    labelschanged = False
                    for lang, label in metadata['title'].items():
                        if lang not in labels:
                            labels[lang] = label
                            labelschanged = True
                    if labelschanged:
                        summary = u'Adding missing label(s) from %s' % (metadata.get(u'refurl'),)
                        try:
                            artworkItem.editLabels(labels, summary=summary)
                        except pywikibot.OtherPageSaveError:
                            # Just skip it for no
                            pywikibot.output(u'Oops, already had that label/description combination. Skipping')
                            pass

                # Add missing descriptions
                # FIXME Move to a function
                descriptions = copy.deepcopy(data.get('descriptions'))
                if metadata.get('description'):
                    descriptionschanged = False
                    for lang, description in metadata['description'].items():
                        if lang not in descriptions:
                            descriptions[lang] = description
                            descriptionschanged = True
                    if descriptionschanged:
                        summary = u'Adding missing description(s) from %s' % (metadata.get(u'refurl'),)
                        try:
                            artworkItem.editDescriptions(descriptions, summary=summary)
                        except pywikibot.exceptions.OtherPageSaveError: # pywikibot.data.api.APIError:
                            # We got ourselves a duplicate label and description, let's correct that by adding collection and the id
                            descriptions = copy.deepcopy(data.get('descriptions'))
                            pywikibot.output(u'Oops, already had that label/description combination. Trying again')
                            for lang, description in metadata['description'].items():
                                if lang not in descriptions:
                                    descriptions[lang] = u'%s (%s %s)' % (description,
                                                                             metadata['collectionshort'],
                                                                             metadata['id'],)
                            artworkItem.editDescriptions(descriptions, summary=summary)
                            pass
                #print claims

                # instance of
                self.addItemStatement(artworkItem, u'P31', metadata.get(u'instanceofqid'), metadata.get(u'refurl'))

                # instance of
                self.addItemStatement(artworkItem, u'P276', metadata.get(u'locationqid'), metadata.get(u'refurl'))

                # instance of
                self.addItemStatement(artworkItem, u'P170', metadata.get(u'creatorqid'), metadata.get(u'refurl'))                

                # Inception
                if u'P571' not in claims and metadata.get(u'inception'):
                    if type(metadata[u'inception']) is int or (len(metadata[u'inception'])==4 and \
                                                                   metadata[u'inception'].isnumeric()): # It's a year
                        newdate = pywikibot.WbTime(year=metadata[u'inception'])
                        newclaim = pywikibot.Claim(self.repo, u'P571')
                        newclaim.setTarget(newdate)
                        pywikibot.output('Adding date of creation claim to %s' % artworkItem)
                        artworkItem.addClaim(newclaim)
                
                        self.addReference(artworkItem, newclaim, metadata[u'refurl'])

                # Try to add the acquisitiondate to the existing collection claim
                if u'P195' in claims:
                    if len(claims.get(u'P195'))==1 and metadata.get(u'acquisitiondate'):
                        collectionclaim = claims.get(u'P195')[0]
                        # Would like to use collectionclaim.has_qualifier(u'P580')
                        if collectionclaim.getTarget()==self.collectionitem and not collectionclaim.qualifiers.get(u'P580'):
                            dateregex = u'^(\d\d\d\d)-(\d\d)-(\d\d)'
                            datematch = re.match(dateregex, str(metadata[u'acquisitiondate']))
                            acdate = None
                            if type(metadata[u'acquisitiondate']) is int or (len(metadata[u'acquisitiondate'])==4 and \
                                    metadata[u'acquisitiondate'].isnumeric()): # It's a year
                                acdate = pywikibot.WbTime(year=metadata[u'acquisitiondate'])
                            elif datematch:
                                #print metadata[u'acquisitiondate']
                                acdate = pywikibot.WbTime(year=int(datematch.group(1)),
                                                          month=int(datematch.group(2)),
                                                          day=int(datematch.group(3)))
                            else:
                                try:
                                    acdate = pywikibot.WbTime.fromTimestr(metadata[u'acquisitiondate'])
                                    # Pff, precision is t0o high. Hack to fix this
                                    if acdate.precision > 11:
                                        acdate.precision=11
                                except ValueError:
                                    pywikibot.output(u'Can not parse %s' % metadata[u'acquisitiondate'])
                            if acdate:
                                colqualifier = pywikibot.Claim(self.repo, u'P580')
                                colqualifier.setTarget(acdate)
                                pywikibot.output('Update collection claim with start time on %s' % artworkItem)
                                collectionclaim.addQualifier(colqualifier)
                                # This might give multiple similar references
                                #self.addReference(artworkItem, collectionclaim, metadata[u'refurl'])

                    # Try to add the extra collection
                    if metadata.get(u'extracollectionqid'):
                        foundExtraCollection = False
                        extracollectionitem = pywikibot.ItemPage(self.repo, metadata.get(u'extracollectionqid'))
                        for collectionclaim in claims.get(u'P195'):
                            if collectionclaim.getTarget()==extracollectionitem:
                                foundExtraCollection = True
                        if not foundExtraCollection:
                            newclaim = pywikibot.Claim(self.repo, u'P195')
                            newclaim.setTarget(extracollectionitem)
                            pywikibot.output('Adding extra collection claim to %s' % artworkItem)
                            artworkItem.addClaim(newclaim)
                            self.addReference(artworkItem, newclaim, metadata[u'refurl'])

                # material used
                # FIXME: This does not scale at all.
                if u'P186' not in claims and metadata.get(u'medium'):
                    if metadata.get(u'medium') == u'oil on canvas':
                        oil_paint = pywikibot.ItemPage(self.repo, u'Q296955')
                        canvas = pywikibot.ItemPage(self.repo, u'Q4259259')
                        painting_surface = pywikibot.ItemPage(self.repo, u'Q861259')
                        
                        newclaim = pywikibot.Claim(self.repo, u'P186')
                        newclaim.setTarget(oil_paint)
                        pywikibot.output('Adding new oil paint claim to %s' % artworkItem)
                        artworkItem.addClaim(newclaim)

                        self.addReference(artworkItem, newclaim, metadata[u'refurl'])

                        newclaim = pywikibot.Claim(self.repo, u'P186')
                        newclaim.setTarget(canvas)
                        pywikibot.output('Adding new canvas claim to %s' % artworkItem)
                        artworkItem.addClaim(newclaim)

                        newqualifier = pywikibot.Claim(self.repo, u'P518') #Applies to part
                        newqualifier.setTarget(painting_surface)
                        pywikibot.output('Adding new qualifier claim to %s' % artworkItem)
                        newclaim.addQualifier(newqualifier)

                        self.addReference(artworkItem, newclaim, metadata[u'refurl'])

                # Height in centimetres. Expect something that can be converted to a Decimal with . and not ,
                if u'P2048' not in claims and metadata.get(u'heightcm'):
                    newheight = pywikibot.WbQuantity(amount=metadata.get(u'heightcm'),
                                                     unit=u'http://www.wikidata.org/entity/Q174728',
                                                     site=self.repo)
                    newclaim = pywikibot.Claim(self.repo, u'P2048')
                    newclaim.setTarget(newheight)
                    pywikibot.output('Adding height in cm claim to %s' % artworkItem)
                    artworkItem.addClaim(newclaim)

                    self.addReference(artworkItem, newclaim, metadata[u'refurl'])

                # Width in centimetres. Expect something that can be converted to a Decimal with . and not ,
                if u'P2049' not in claims and metadata.get(u'widthcm'):
                    newwidth = pywikibot.WbQuantity(amount=metadata.get(u'widthcm'),
                                                    unit=u'http://www.wikidata.org/entity/Q174728',
                                                    site=self.repo)
                    newclaim = pywikibot.Claim(self.repo, u'P2049')
                    newclaim.setTarget(newwidth)
                    pywikibot.output('Adding width in cm claim to %s' % artworkItem)
                    artworkItem.addClaim(newclaim)

                    self.addReference(artworkItem, newclaim, metadata[u'refurl'])

                # Depth (or thickness) in centimetres.
                # Expect something that can be converted to a Decimal with . and not ,
                # Some museums provide this, but not a lot
                if u'P2610' not in claims and metadata.get(u'depthcm'):
                    newdepth = pywikibot.WbQuantity(amount=metadata.get(u'depthcm'),
                                                    unit=u'http://www.wikidata.org/entity/Q174728',
                                                    site=self.repo)
                    newclaim = pywikibot.Claim(self.repo, u'P2610')
                    newclaim.setTarget(newdepth)
                    pywikibot.output('Adding depth in cm claim to %s' % artworkItem)
                    artworkItem.addClaim(newclaim)

                    self.addReference(artworkItem, newclaim, metadata[u'refurl'])

                # Quite a few collections have custom id's these days.
                if metadata.get(u'artworkidpid'):
                    if metadata.get(u'artworkidpid') not in claims:
                        newclaim = pywikibot.Claim(self.repo, metadata.get(u'artworkidpid') )
                        newclaim.setTarget(metadata[u'artworkid'])
                        pywikibot.output('Adding artwork id claim to %s' % artworkItem)
                        artworkItem.addClaim(newclaim)
                # Described at url
                else:
                    if u'P973' not in claims:
                        newclaim = pywikibot.Claim(self.repo, u'P973')
                        newclaim.setTarget(metadata[u'describedbyurl'])
                        pywikibot.output('Adding described at claim to %s' % artworkItem)
                        artworkItem.addClaim(newclaim)
                    else:
                        foundurl = False
                        for claim in claims.get(u'P973'):
                            if claim.getTarget()==metadata[u'describedbyurl']:
                                foundurl=True
                        if not foundurl:
                            newclaim = pywikibot.Claim(self.repo, u'P973')
                            newclaim.setTarget(metadata[u'describedbyurl'])
                            pywikibot.output('Adding additional described at claim to %s' % artworkItem)
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
    print ( u'Dude, write your own bot')
    

if __name__ == "__main__":
    main()
