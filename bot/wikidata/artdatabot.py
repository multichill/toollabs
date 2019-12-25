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
import requests

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
        #query = u'SELECT ?item ?id WHERE { ?item wdt:P195 wd:%s . ?item wdt:%s ?id }' % (collectionqid, idProperty)
        query = u"""SELECT ?item ?id WHERE {
        ?item p:P195/ps:P195 wd:%s .
        ?item p:%s ?idstatement .
        ?idstatement pq:P195 wd:%s .
        ?idstatement ps:%s ?id }""" % (collectionqid, idProperty, collectionqid, idProperty)
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
            metadata = self.enrichMetadata(metadata)

            artworkItem = None
            if metadata[u'id'] in self.artworkIds:
                artworkItemTitle = self.artworkIds.get(metadata[u'id'])
                print (artworkItemTitle)
                artworkItem = pywikibot.ItemPage(self.repo, title=artworkItemTitle)

            elif self.create:
                artworkItem = self.createArtworkItem(metadata)

            if artworkItem and artworkItem.exists():
                metadata['wikidata'] = artworkItem.title()
                self.updateArtworkItem(artworkItem, metadata)

    def enrichMetadata(self, metadata):
        """
        Take the metadata and enrich it with some missing fields
        :param metadata: The current metadata dict
        :return: The enriched metadata dict
        """

        # Do some url magic so that all url fields are always filled
        if not metadata.get('refurl'):
            metadata['refurl']=metadata['url']
        if not metadata.get('idrefurl'):
            metadata['idrefurl']=metadata['refurl']
        if not metadata.get('describedbyurl') and metadata.get(u'url'):
            metadata['describedbyurl']=metadata['url']
        if not metadata.get('imagesourceurl') and metadata.get(u'url'):
            metadata['imagesourceurl']=metadata['url']

        # Use title to fill labels. If just labels is passed, no title property will be set.
        if not metadata.get('labels') and metadata.get('title'):
            metadata[u'labels'] = {}
            for lang, label in metadata.get('title').items():
                metadata[u'labels'][lang] = label

        return metadata

    def createArtworkItem(self, metadata):
        """
        Create a new artwork item based on the metadata

        :param metadata: All the metadata for this new artwork.
        :return: The newly created artworkItem
        """
        data = {'labels': {},
                'descriptions': {},
                }

        # loop over stuff
        if metadata.get('labels'):
            for lang, label in metadata.get('labels').items():
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
            try:
                result = self.repo.editEntity(identification, data, summary=summary)
            except pywikibot.data.api.APIError:
                pywikibot.output(u'Oops, retry also failed. Skipping this one.')
                # Just skip this one
                return
            pass

        artworkItemTitle = result.get(u'entity').get('id')

        # Make a backup to the Wayback Machine when we have to wait anyway
        self.doWaybackup(metadata)

        # Wikidata is sometimes lagging. Wait for additional 5 seconds before trying to actually use the item
        time.sleep(5)

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
                #FIXME: Xqt broke this. Need to make sure it's an int
                acdate = pywikibot.WbTime(year=int(metadata[u'acquisitiondate']))
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

        return artworkItem

    def doWaybackup(self, metadata):
        """
        Links to paintings are subject to link rot. When creating a new item, have the Wayback Machine make a snapshot.
        That way always have a copy of the page we used to source a bunch of statements.

        See also https://www.wikidata.org/wiki/Wikidata:WikiProject_sum_of_all_paintings/Link_rot

        :param metadata: Metadata containing url fields
        :return: Nothing
        """
        urfields = [u'url', u'idrefurl', u'refurl', u'describedbyurl', u'imagesourceurl']
        doneurls = []
        for urlfield in urfields:
            url = metadata.get(urlfield)
            if url and url not in doneurls:
                print (u'Backing up this url to the Wayback Machine: %s' % (url,))
                waybackUrl = u'https://web.archive.org/save/%s' % (url,)
                waybackPage = requests.get(waybackUrl)
                doneurls.append(url)

    def updateArtworkItem(self, artworkItem, metadata):
        """
        Add statements and other data to the artworkItem
        :param artworkItem: The artwork item to work on
        :param metadata: All the metadata about this artwork.
        :return: Nothing, updates item in place
        """

        # Add the (missing) labels to the item based on the title.
        self.addLabels(artworkItem, metadata)

        # Add the (missing) descriptions to the item.
        self.addDescriptions(artworkItem, metadata)

        # Add instance of (P31) to the item.
        self.addItemStatement(artworkItem, u'P31', metadata.get(u'instanceofqid'), metadata.get(u'refurl'))

        # Add location (P276) to the item.
        self.addItemStatement(artworkItem, u'P276', metadata.get(u'locationqid'), metadata.get(u'refurl'))

        # Add creator (P170) to the item.
        self.addItemStatement(artworkItem, u'P170', metadata.get(u'creatorqid'), metadata.get(u'refurl'))

        # Add inception (P571) to the item.
        self.addInception(artworkItem, metadata)

        # Add location of final assembly (P1071) to the item.
        self.addItemStatement(artworkItem, u'P1071', metadata.get(u'madeinqid'), metadata.get(u'refurl'))

        # Add title (P1476) to the item.
        self.addTitle(artworkItem, metadata)

        # Add genre (P136) to the item
        self.addItemStatement(artworkItem, u'P136', metadata.get(u'genreqid'), metadata.get(u'refurl'))

        # Add the material used (P186) based on the medium to the item.
        self.addMaterialUsed(artworkItem, metadata)

        # Add the dimensions height (P2048), width (P2049) and thickness (P2610) to the item.
        self.addDimensions(artworkItem, metadata)

        # Add Commons compatible image available at URL (P4765) to an image that can be uploaded to Commons.
        self.addImageSuggestion(artworkItem, metadata)

        # Add the IIIF manifest (P6108) to the item.
        self.addIiifManifestUrl(artworkItem, metadata)

        # Add a link to the item in a collection. Either described at URL (P973) or custom.
        self.addCollectionLink(artworkItem, metadata)

        # Update the collection with a start date and add extra collections.
        self.updateCollection(artworkItem, metadata)

    def addLabels(self, item, metadata):
        """
        Add the (missing) labels to the item based.

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork, should contain the labels field
        :return: Nothing, updates item in place
        """
        labels = item.get().get('labels')
        if metadata.get('labels'):
            labelschanged = False
            for lang, label in metadata['labels'].items():
                if lang not in labels:
                    labels[lang] = label
                    labelschanged = True
            if labelschanged:
                summary = u'Adding missing label(s) from %s' % (metadata.get(u'refurl'),)
                try:
                    item.editLabels(labels, summary=summary)
                except pywikibot.OtherPageSaveError:
                    # Just skip it for no
                    pywikibot.output(u'Oops, already had that label/description combination. Skipping')
                    pass

    def addDescriptions(self, item, metadata):
        """
        Add the (missing) descriptions to the item

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork, should contain the description field
        :return: Nothing, updates item in place
        """
        descriptions = copy.deepcopy(item.get().get('descriptions'))

        if metadata.get('description'):
            descriptionschanged = False
            for lang, description in metadata['description'].items():
                if lang not in descriptions:
                    descriptions[lang] = description
                    descriptionschanged = True
            if descriptionschanged:
                summary = u'Adding missing description(s) from %s' % (metadata.get(u'refurl'),)
                try:
                    item.editDescriptions(descriptions, summary=summary)
                except pywikibot.exceptions.OtherPageSaveError: # pywikibot.data.api.APIError:
                    # We got ourselves a duplicate label and description, let's correct that by adding collection and the id
                    descriptions = copy.deepcopy(item.get().get('descriptions'))
                    pywikibot.output(u'Oops, already had that label/description combination. Trying again')
                    for lang, description in metadata['description'].items():
                        if lang not in descriptions:
                            descriptions[lang] = u'%s (%s %s)' % (description,
                                                                  metadata['collectionshort'],
                                                                  metadata['id'],)
                    item.editDescriptions(descriptions, summary=summary)
                    pass

    def addTitle(self, item, metadata):
        """
        Add the title (P1476) to the item. For now just skip items that already have a title
        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork, should contain the title field as a dict
        :return:
        """
        claims = item.get().get('claims')

        if u'P1476' in claims:
            # Already has a title. Don't care if it's the same contents and or language for now
            return

        if metadata.get(u'title'):
            for lang in metadata.get(u'title'):
                # To prevent any empty titles
                if metadata.get(u'title').get(lang):
                    try:
                        newtitle = pywikibot.WbMonolingualText(text=metadata.get(u'title').get(lang).strip(),
                                                               language=lang,
                                                               )
                        newclaim = pywikibot.Claim(self.repo, u'P1476')
                        newclaim.setTarget(newtitle)
                        pywikibot.output('Adding title to %s' % item)
                        item.addClaim(newclaim)
                        self.addReference(item, newclaim, metadata[u'refurl'])
                    except pywikibot.exceptions.OtherPageSaveError:
                        pywikibot.output(u'The title was malformed, skipping it')
                        pass

    def addInception(self, item, metadata):
        """
        Add the inception to the item.

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork, should contain the imageurl field
        :return:
        """
        claims = item.get().get('claims')

        if u'P571' in claims:
            # Already has inception
            return

        if metadata.get(u'inception'):
            if type(metadata[u'inception']) is int or (len(metadata[u'inception'])==4 and \
                                                               metadata[u'inception'].isnumeric()): # It's a year
                #FIXME: Xqt broke this. Need to make sure it's an int
                newdate = pywikibot.WbTime(year=metadata[u'inception'])
                newclaim = pywikibot.Claim(self.repo, u'P571')
                newclaim.setTarget(newdate)
                pywikibot.output('Adding date of creation claim to %s' % item)
                item.addClaim(newclaim)

                # Handle circa dates
                if metadata.get(u'inceptioncirca'):
                    newqualifier = pywikibot.Claim(self.repo, u'P1480')
                    newqualifier.setTarget(pywikibot.ItemPage(self.repo, u'Q5727902'))
                    pywikibot.output('Adding new circa qualifier claim to %s' % item)
                    newclaim.addQualifier(newqualifier)
                self.addReference(item, newclaim, metadata[u'refurl'])

        elif metadata.get(u'inceptionstart') and metadata.get(u'inceptionend'):
            if metadata.get(u'inceptionstart')==metadata.get(u'inceptionend'):
                #FIXME: Xqt broke this. Need to make sure it's an int
                newdate = pywikibot.WbTime(year=metadata[u'inceptionstart'])
                newclaim = pywikibot.Claim(self.repo, u'P571')
                newclaim.setTarget(newdate)
                pywikibot.output('Adding date of creation claim to %s' % item)
                item.addClaim(newclaim)

                # Handle circa dates
                if metadata.get(u'inceptioncirca'):
                    newqualifier = pywikibot.Claim(self.repo, u'P1480')
                    newqualifier.setTarget(pywikibot.ItemPage(self.repo, u'Q5727902'))
                    pywikibot.output('Adding new circa qualifier claim to %s' % item)
                    newclaim.addQualifier(newqualifier)
                self.addReference(item, newclaim, metadata[u'refurl'])
            else:
                if len(str(metadata.get(u'inceptionstart')))!=4 or len(str(metadata.get(u'inceptionend')))!=4:
                    return
                precision = 5 # 10 millenia

                # For things like 1901-2000 I want to end with century
                incstart = str(metadata.get(u'inceptionstart'))
                normalend = str(metadata.get(u'inceptionend'))
                lowerend = str(int(metadata.get(u'inceptionend'))-1)

                # The normal loop
                if incstart[0]==normalend[0]:
                    precision = 6 # millenium
                    if incstart[1]==normalend[1]:
                        precision = 7 # century
                        if incstart[2]==normalend[2]:
                            precision = 8 # decade
                # The one lower loop. Can't mix them, will give funky results with things like 1701 and 1800
                if incstart[0]==lowerend[0]:
                    if precision < 6:
                        precision = 6 # millenium
                    if incstart[1]==lowerend[1]:
                        if precision < 7:
                            precision = 7 # century
                        # Don't do it for decade

                averageYear = int(abs((metadata.get(u'inceptionstart') + metadata.get(u'inceptionend'))/2))
                newdate = pywikibot.WbTime(year=averageYear, precision=precision)
                earliestdate = pywikibot.WbTime(year=metadata.get(u'inceptionstart'))
                latestdate = pywikibot.WbTime(year=metadata.get(u'inceptionend'))

                newclaim = pywikibot.Claim(self.repo, u'P571')
                newclaim.setTarget(newdate)
                pywikibot.output('Adding date of creation claim to %s' % item)
                item.addClaim(newclaim)

                earliestqualifier = pywikibot.Claim(self.repo, u'P1319')
                earliestqualifier.setTarget(earliestdate)
                newclaim.addQualifier(earliestqualifier)

                latestqualifier = pywikibot.Claim(self.repo, u'P1326')
                latestqualifier.setTarget(latestdate)
                newclaim.addQualifier(latestqualifier)

                # Handle circa dates
                if metadata.get(u'inceptioncirca'):
                    newqualifier = pywikibot.Claim(self.repo, u'P1480')
                    newqualifier.setTarget(pywikibot.ItemPage(self.repo, u'Q5727902'))
                    pywikibot.output('Adding new circa qualifier claim to %s' % item)
                    newclaim.addQualifier(newqualifier)
                self.addReference(item, newclaim, metadata[u'refurl'])

    def updateCollection(self, item, metadata):
        """
        Update the collection with a start date and add extra collections.

        This is a bit of a weird function and needs to be improved.

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork, should contain the acquisitiondate field
        :return: Nothing, updates item in place
        """
        claims = item.get().get('claims')

        # Try to add the acquisitiondate to the existing collection claim
        # TODO: Move to function and also work with multiple collection claims
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
                        #FIXME: Xqt broke this. Need to make sure it's an int
                        acdate = pywikibot.WbTime(year=int(metadata[u'acquisitiondate']))
                    elif datematch:
                        #print metadata[u'acquisitiondate']
                        acdate = pywikibot.WbTime(year=int(datematch.group(1)),
                                                  month=int(datematch.group(2)),
                                                  day=int(datematch.group(3)))
                    else:
                        try:
                            #FIXME: Xqt broke this. Need to make sure it's an int
                            acdate = pywikibot.WbTime.fromTimestr(metadata[u'acquisitiondate'])
                            # Pff, precision is t0o high. Hack to fix this
                            if acdate.precision > 11:
                                acdate.precision=11
                        except ValueError:
                            pywikibot.output(u'Can not parse %s' % metadata[u'acquisitiondate'])
                    if acdate:
                        colqualifier = pywikibot.Claim(self.repo, u'P580')
                        colqualifier.setTarget(acdate)
                        pywikibot.output('Update collection claim with start time on %s' % item)
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
                    pywikibot.output('Adding extra collection claim to %s' % item)
                    item.addClaim(newclaim)
                    self.addReference(item, newclaim, metadata[u'refurl'])

    def addMaterialUsed(self, item, metadata):
        """
        Add the material used (P186) based on the medium to the item.

        This currently only supports oil on canvas so doesn't scale at all.

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork, should contain the medium field
        :return: Nothing, updates item in place
        """
        claims = item.get().get('claims')

        if u'P186' not in claims and metadata.get(u'medium'):
            if metadata.get(u'medium') == u'oil on canvas':
                oil_paint = pywikibot.ItemPage(self.repo, u'Q296955')
                canvas = pywikibot.ItemPage(self.repo, u'Q4259259')
                painting_surface = pywikibot.ItemPage(self.repo, u'Q861259')

                newclaim = pywikibot.Claim(self.repo, u'P186')
                newclaim.setTarget(oil_paint)
                pywikibot.output('Adding new oil paint claim to %s' % item)
                item.addClaim(newclaim)
                self.addReference(item, newclaim, metadata[u'refurl'])

                newclaim = pywikibot.Claim(self.repo, u'P186')
                newclaim.setTarget(canvas)
                pywikibot.output('Adding new canvas claim to %s' % item)
                item.addClaim(newclaim)

                newqualifier = pywikibot.Claim(self.repo, u'P518') #Applies to part
                newqualifier.setTarget(painting_surface)
                pywikibot.output('Adding new qualifier claim to %s' % item)
                newclaim.addQualifier(newqualifier)
                self.addReference(item, newclaim, metadata[u'refurl'])

    def addDimensions(self, item, metadata):
        """
        Add the dimensions height (P2048), width (P2049) and thickness (P2610) to the item.

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork, should contain the heightcm, widthcm and depthcm fields.
        :return: Nothing, updates item in place
        """
        claims = item.get().get('claims')

        # Height in centimetres.
        if u'P2048' not in claims and metadata.get(u'heightcm'):
            newheight = pywikibot.WbQuantity(amount=metadata.get(u'heightcm').replace(u',', u'.'),
                                             unit=u'http://www.wikidata.org/entity/Q174728',
                                             site=self.repo)
            newclaim = pywikibot.Claim(self.repo, u'P2048')
            newclaim.setTarget(newheight)
            pywikibot.output('Adding height in cm claim to %s' % item)
            item.addClaim(newclaim)
            self.addReference(item, newclaim, metadata[u'refurl'])

        # Width in centimetres.
        if u'P2049' not in claims and metadata.get(u'widthcm'):
            newwidth = pywikibot.WbQuantity(amount=metadata.get(u'widthcm').replace(u',', u'.'),
                                            unit=u'http://www.wikidata.org/entity/Q174728',
                                            site=self.repo)
            newclaim = pywikibot.Claim(self.repo, u'P2049')
            newclaim.setTarget(newwidth)
            pywikibot.output('Adding width in cm claim to %s' % item)
            item.addClaim(newclaim)
            self.addReference(item, newclaim, metadata[u'refurl'])

        # Depth (or thickness) in centimetres. Some museums provide this, but not a lot
        if u'P2610' not in claims and metadata.get(u'depthcm'):
            newdepth = pywikibot.WbQuantity(amount=metadata.get(u'depthcm').replace(u',', u'.'),
                                            unit=u'http://www.wikidata.org/entity/Q174728',
                                            site=self.repo)
            newclaim = pywikibot.Claim(self.repo, u'P2610')
            newclaim.setTarget(newdepth)
            pywikibot.output('Adding depth in cm claim to %s' % item)
            item.addClaim(newclaim)
            self.addReference(item, newclaim, metadata[u'refurl'])

    def addImageSuggestion(self, item, metadata):
        """
        Add  Commons compatible image available at URL (P4765) to an image that can be uploaded to Commons

        It will also add the suggestion if the item already has an image, but new one is of much better quality

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork, should contain the imageurl field
        :return: Nothing, updates item in place
        """
        claims = item.get().get('claims')

        if not metadata.get(u'imageurl'):
            # Nothing to add
            return
        if u'P4765' in claims:
            # Already has a suggestion
            return
        if u'P6500' in claims:
            # Already has a non-free artwork image URL
            return

        if u'P18' in claims and not metadata.get(u'imageurlforce'):
            if not metadata.get(u'imageupgrade'):
                return
            newimage = requests.get(metadata.get(u'imageurl'), stream=True)
            if not newimage.headers.get('Content-length'):
                return
            if not newimage.headers.get('Content-length').isnumeric():
                return
            newimagesize = int(newimage.headers['Content-length'])
            #print (u'Size of the new image is %s according to the headers' % (newimagesize,))
            if newimagesize < 500000:
                # Smaller than 500KB is just too small to bother check to replace
                return

            for imageclaim in claims.get(u'P18'):
                currentsize = imageclaim.getTarget().latest_file_info.size
                #print (u'Size of the current image is %s' % (currentsize,))
                # New image should at least be 4 times larger
                if currentsize * 4 > newimagesize:
                    return

        newclaim = pywikibot.Claim(self.repo, u'P4765')
        newclaim.setTarget(metadata[u'imageurl'])
        pywikibot.output('Adding commons compatible image available at URL claim to %s' % item)
        item.addClaim(newclaim)

        if metadata.get(u'imageurlformat'):
            newqualifier = pywikibot.Claim(self.repo, u'P2701')
            newqualifier.setTarget(pywikibot.ItemPage(self.repo, metadata.get(u'imageurlformat')))
            pywikibot.output('Adding new qualifier claim to %s' % item)
            newclaim.addQualifier(newqualifier)

        newqualifier = pywikibot.Claim(self.repo, u'P2699')
        newqualifier.setTarget(metadata[u'imagesourceurl'])
        pywikibot.output('Adding new qualifier claim to %s' % item)
        newclaim.addQualifier(newqualifier)

        if metadata.get('title'):
            if metadata.get('title').get(u'en'):
                title = pywikibot.WbMonolingualText(metadata.get('title').get(u'en'), u'en')
            else:
                lang = list(metadata.get('title').keys())[0]
                title = pywikibot.WbMonolingualText(metadata.get('title').get(lang), lang)
            newqualifier = pywikibot.Claim(self.repo, u'P1476')
            newqualifier.setTarget(title)
            pywikibot.output('Adding new qualifier claim to %s' % item)
            newclaim.addQualifier(newqualifier)

        if metadata.get('creatorname'):
            newqualifier = pywikibot.Claim(self.repo, u'P2093')
            newqualifier.setTarget(metadata.get('creatorname'))
            pywikibot.output('Adding new qualifier claim to %s' % item)
            newclaim.addQualifier(newqualifier)

        if metadata.get(u'imageurllicense'):
            newqualifier = pywikibot.Claim(self.repo, u'P275')
            newqualifier.setTarget(pywikibot.ItemPage(self.repo, metadata.get(u'imageurllicense')))
            pywikibot.output('Adding new qualifier claim to %s' % item)
            newclaim.addQualifier(newqualifier)

        if metadata.get(u'imageoperatedby'):
            newqualifier = pywikibot.Claim(self.repo, u'P137')
            newqualifier.setTarget(pywikibot.ItemPage(self.repo, metadata.get(u'imageoperatedby')))
            pywikibot.output('Adding new qualifier claim to %s' % item)
            newclaim.addQualifier(newqualifier)

    def addIiifManifestUrl(self, item, metadata):
        """
        Add the  IIIF manifest (P6108) to the item.

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork, should contain the iiifmanifesturl field
        :return: Nothing, updates item in place
        """
        claims = item.get().get('claims')

        if u'P6108' not in claims and metadata.get(u'iiifmanifesturl'):
            newclaim = pywikibot.Claim(self.repo, u'P6108')
            newclaim.setTarget(metadata[u'iiifmanifesturl'])
            pywikibot.output('Adding IIIF manifest url claim to %s' % item)
            item.addClaim(newclaim)
            self.addReference(item, newclaim, metadata[u'refurl'])

    def addCollectionLink(self, item, metadata):
        """
        Add a link to the item in a collection.
        This is either described at URL (P973) or a customer per collection id

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork, should contain the describedbyurl or the artworkidpid and artworkid fields.
        :return: Nothing, updates item in place
        """
        claims = item.get().get('claims')

        if metadata.get(u'artworkidpid'):
            if metadata.get(u'artworkidpid') not in claims:
                newclaim = pywikibot.Claim(self.repo, metadata.get(u'artworkidpid') )
                newclaim.setTarget(metadata[u'artworkid'])
                pywikibot.output('Adding artwork id claim to %s' % item)
                item.addClaim(newclaim)
        # Described at url
        elif metadata.get(u'describedbyurl'):
            if u'P973' not in claims:
                newclaim = pywikibot.Claim(self.repo, u'P973')
                newclaim.setTarget(metadata[u'describedbyurl'])
                pywikibot.output('Adding described at claim to %s' % item)
                item.addClaim(newclaim)
            else:
                foundurl = False
                for claim in claims.get(u'P973'):
                    if claim.getTarget()==metadata[u'describedbyurl']:
                        foundurl=True
                if not foundurl:
                    newclaim = pywikibot.Claim(self.repo, u'P973')
                    newclaim.setTarget(metadata[u'describedbyurl'])
                    pywikibot.output('Adding additional described at claim to %s' % item)
                    item.addClaim(newclaim)

    def addItemStatement(self, item, pid, qid, url):
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
        self.addReference(item, newclaim, url)
        
    def addReference(self, item, newclaim, url):
        """
        Add a reference with a retrieval url and todays date
        """
        pywikibot.output('Adding new reference claim to %s' % item)
        refurl = pywikibot.Claim(self.repo, u'P854')
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
