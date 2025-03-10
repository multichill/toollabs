#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import art data to Wikidata.

"""
import pywikibot
import re
import pywikibot.data.sparql
import datetime
import time
import itertools
import copy
import requests
from collections import defaultdict

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
        self.wayback_session = requests.Session()
        self.create = create
        
        self.idProperty = firstrecord.get(u'idpid')
        self.collectionqid = firstrecord.get(u'collectionqid')
        self.collectionitem = pywikibot.ItemPage(self.repo, self.collectionqid)
        self.artworkIds = self.fillCache(self.collectionqid,self.idProperty)

    def fillCache(self, collectionqid, idProperty):
        """
        Build an ID cache so we can quickly look up the id's for property
        """
        result = {}
        sq = pywikibot.data.sparql.SparqlQuery()

        # FIXME: Do something with the collection qualifier
        #query = u'SELECT ?item ?id WHERE { ?item wdt:P195 wd:%s . ?item wdt:%s ?id }' % (collectionqid, idProperty)
        query = u"""SELECT ?item ?id WHERE {
        ?item p:P195/ps:P195 wd:%s .
        ?item p:%s ?idstatement .
        ?idstatement pq:P195 wd:%s .
        ?idstatement ps:%s ?id
        MINUS { ?idstatement wikibase:rank wikibase:DeprecatedRank }
        }""" % (collectionqid, idProperty, collectionqid, idProperty)
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
                if artworkItem.isRedirectPage():
                    artworkItem = artworkItem.getRedirectTarget()
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
                'claims': [],
                }

        # loop over stuff
        if metadata.get('labels'):
            for lang, label in metadata.get('labels').items():
                data['labels'][lang] = {'language': lang, 'value': label}

        if metadata.get('description'):
            for lang, description in metadata['description'].items():
                data['descriptions'][lang] = {'language': lang, 'value': description}

        # Add the id to the item so we can get back to it later
        newclaim = pywikibot.Claim(self.repo, self.idProperty)
        newclaim.setTarget(metadata['id'])

        newqualifier = pywikibot.Claim(self.repo, 'P195')
        newqualifier.setTarget(self.collectionitem)
        self.queue_qualifier(newclaim, newqualifier)
        self.addReference(None, newclaim, metadata['refurl'], queue=True)
        data['claims'].append(newclaim.toJSON())

        collectionclaim = pywikibot.Claim(self.repo, u'P195')
        collectionclaim.setTarget(self.collectionitem)

        # Add the date they got it as a qualifier to the collection
        if metadata.get(u'acquisitiondate'):
            if type(metadata[u'acquisitiondate']) is int or (len(metadata[u'acquisitiondate']) == 4 and \
                                                             metadata[u'acquisitiondate'].isnumeric()):  # It's a year
                acdate = pywikibot.WbTime(year=int(metadata[u'acquisitiondate']))
                colqualifier = pywikibot.Claim(self.repo, u'P580')
                colqualifier.setTarget(acdate)
                self.queue_qualifier(collectionclaim, colqualifier)

        self.addReference(None, collectionclaim, metadata[u'refurl'], queue=True)
        data['claims'].append(collectionclaim.toJSON())

        identification = {}
        summary = 'Creating new item with data from %s ' % (metadata['url'],)
        pywikibot.output(summary)
        try:
            result = self.repo.editEntity(identification, data, summary=summary)
        except pywikibot.exceptions.APIError:
            # TODO: Check if this is pywikibot.exceptions.OtherPageSaveError too
            # We got ourselves a duplicate label and description, let's correct that by adding collection and the id
            if metadata.get('collectionshort'):
                pywikibot.output('Oops, already had that one. Trying again with the collection added')
                for lang, description in metadata['description'].items():
                    data['descriptions'][lang] = {'language': lang, 'value': u'%s (%s %s)' % (description, metadata['collectionshort'], metadata['id'],) }
                try:
                    result = self.repo.editEntity(identification, data, summary=summary)
                except pywikibot.exceptions.APIError:
                    pywikibot.output(u'Oops, retry also failed. Skipping this one.')
                    # Just skip this one
                    return

        artworkItemTitle = result.get(u'entity').get('id')

        # Make a backup to the Wayback Machine when we have to wait anyway
        self.doWaybackup(metadata)

        # Wikidata is sometimes lagging. Wait for additional 5 seconds before trying to actually use the item
        time.sleep(5)

        artworkItem = pywikibot.ItemPage(self.repo, title=artworkItemTitle)

        # Add to self.artworkIds so that we don't create dupes
        self.artworkIds[metadata[u'id']] = artworkItemTitle

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
                pywikibot.output ('Backing up this url to the Wayback Machine: %s' % (url,))
                waybackUrl = 'https://web.archive.org/save/%s' % (url,)
                try:
                    waybackPage = self.wayback_session.post(waybackUrl)
                except requests.exceptions.RequestException as err:
                    pywikibot.output('Requests threw an exception. The wayback backup failed')
                    print(err)
                    pass
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

        self.statements_queue = []

        # Add instance of (P31) to the item.
        self.addItemStatement(artworkItem, u'P31', metadata.get(u'instanceofqid'), metadata.get(u'refurl'), queue=True)

        # Add collection (P195) to the item (if it doesn't already have that statement).
        self.addItemStatement(artworkItem, 'P195', metadata.get(u'collectionqid'), metadata.get(u'refurl'), queue=True)

        # Add inventory number (P217) to the item (if it doesn't already have that statement).
        self.add_inventory_number(artworkItem, metadata, queue=True)

        # Add location (P276) to the item.
        self.addItemStatement(artworkItem, u'P276', metadata.get(u'locationqid'), metadata.get(u'refurl'), queue=True)

        # Add owned by (P127) to the item.
        self.addItemStatement(artworkItem, u'P127', metadata.get(u'ownedbyqid'), metadata.get(u'refurl'), queue=True)

        # Add creator (P170) to the item.
        self.add_creator(artworkItem, metadata, queue=True)

        # Add inception (P571) to the item.
        self.add_inception(artworkItem, metadata, queue=True)

        # Add location of creation (P1071) to the item.
        self.addItemStatement(artworkItem, u'P1071', metadata.get(u'madeinqid'), metadata.get(u'refurl'), queue=True)

        # Add title (P1476) to the item.
        self.addTitle(artworkItem, metadata, queue=True)

        # Add movement (P135) to the item
        self.addItemStatement(artworkItem, 'P135', metadata.get('movementqid'), metadata.get('refurl'), queue=True)

        # Add genre (P136) to the item
        self.addItemStatement(artworkItem, 'P136', metadata.get('genreqid'), metadata.get('refurl'), queue=True)

        # Add religion or worldview (P140)
        self.addItemStatement(artworkItem, 'P140', metadata.get('religionqid'), metadata.get('refurl'), queue=True)

        # Add pendant of (P1639)
        self.addItemStatement(artworkItem, 'P1639', metadata.get('pendantqid'), metadata.get('refurl'), queue=True)

        # Add part of (P361)
        self.addItemStatement(artworkItem, 'P361', metadata.get('partofqid'), metadata.get('refurl'), queue=True)

        # Add part of the series (P179)
        self.addItemStatement(artworkItem, 'P179', metadata.get('partofseriesqid'), metadata.get('refurl'), queue=True)

        # Add owned by (P127)
        self.addItemStatement(artworkItem, 'P127', metadata.get('ownerqid'), metadata.get('refurl'), queue=True)

        # TODO: Add has part (P527) which is a list

        # Add the material used (P186) based on the medium to the item.
        self.addMaterialUsed(artworkItem, metadata, queue=True)

        # Add the dimensions height (P2048), width (P2049) and thickness (P2610) to the item.
        self.addDimensions(artworkItem, metadata, queue=True)

        # Add Commons compatible image available at URL (P4765) to an image that can be uploaded to Commons.
        self.addImageSuggestion(artworkItem, metadata, queue=True)

        # Add the IIIF manifest (P6108) to the item.
        self.addIiifManifestUrl(artworkItem, metadata, queue=True)

        # Add a link to the item in a collection. Either described at URL (P973) or custom.
        self.addCollectionLink(artworkItem, metadata, queue=True)

        # Update the collection with a start and end date
        self.updateCollection(artworkItem, metadata)

        # Add extra collections
        self.add_extra_collections(artworkItem, metadata)

        # Add catalog code
        self.addCatalogCode(artworkItem, metadata, queue=True)

        # Add Iconclass
        self.add_iconclass(artworkItem, metadata, queue=True)

        # Save all the queued statements
        self.save_statements(artworkItem)

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
                except pywikibot.exceptions.OtherPageSaveError:
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

        replace_descriptions = {'de': 'gemälde',
                                'en': 'painting',
                                'fr': 'peinture',
                                'nl': 'schilderij',
                                }

        if metadata.get('description'):
            descriptionschanged = False
            for lang, description in metadata['description'].items():
                if lang not in descriptions:
                    descriptions[lang] = description
                    descriptionschanged = True
                elif lang in replace_descriptions:
                    if descriptions.get(lang).lower() == replace_descriptions.get(lang).lower():
                        descriptions[lang] = description
                        descriptionschanged = True
            if descriptionschanged:
                summary = u'Adding missing description(s) from %s' % (metadata.get(u'refurl'),)
                try:
                    item.editDescriptions(descriptions, summary=summary)
                except pywikibot.exceptions.OtherPageSaveError: # pywikibot.exceptions.APIError:
                    # We got ourselves a duplicate label and description, let's correct that by adding collection and the id
                    descriptions = copy.deepcopy(item.get().get('descriptions'))
                    disambiguation_text = None
                    if metadata.get('collectionshort') and metadata.get('id'):
                        disambiguation_text = '%s %s' % (metadata['collectionshort'], metadata['id'],)
                    elif metadata.get('artworkid'):
                        disambiguation_text = metadata['artworkid']
                    if disambiguation_text:
                        pywikibot.output(u'Oops, already had that label/description combination. Trying again')
                        for lang, description in metadata['description'].items():
                            if lang not in descriptions:
                                descriptions[lang] = '%s (%s)' % (description, disambiguation_text,)
                        try:
                            item.editDescriptions(descriptions, summary=summary)
                        except pywikibot.exceptions.OtherPageSaveError:
                            pywikibot.output('Disambiguation (%s) did not work, skipping' % (disambiguation_text,))


    def add_creator(self, item, metadata, queue=False):
        """
        Add the creator statement

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork
        :return:
        """
        claims = item.get().get('claims')
        if metadata.get('creatorqid'):
            if metadata.get('creatorqid') == 'Q4233718':
                self.add_anonymous_creator(item, metadata, queue=queue)
            else:
                # Normal non anoymous creator to add
                self.addItemStatement(item, 'P170', metadata.get('creatorqid'), metadata.get('refurl'), queue=queue)
        elif 'P170' not in claims and metadata.get('uncertaincreatorqid') and metadata.get('creatorqualifierpid'):
            if metadata.get('creatorqualifiernames') and metadata.get('creatorqualifiernames').get('en') and \
                    metadata.get('creatorqualifiernames').get('en') == 'attributed to':
                newclaim = pywikibot.Claim(self.repo, 'P170')
                destitem = pywikibot.ItemPage(self.repo, metadata.get('uncertaincreatorqid'))
                if destitem.isRedirectPage():
                    destitem = destitem.getRedirectTarget()
                newclaim.setTarget(destitem)

                # nature of statement (P5102) -> attribution (Q230768)
                newqualifier = pywikibot.Claim(self.repo, 'P5102')
                attribution_item = pywikibot.ItemPage(self.repo, 'Q230768')
                if attribution_item.isRedirectPage():
                    attribution_item = attribution_item.getRedirectTarget()
                newqualifier.setTarget(attribution_item)

                if queue:
                    self.addReference(item, newclaim, metadata['refurl'], queue=True)
                    self.statements_queue.append(newclaim.toJSON())
                else:
                    item.addClaim(newclaim)
                    newclaim.addQualifier(newqualifier)
                    self.addReference(item, newclaim, metadata.get('refurl'))
            else:
                self.add_anonymous_creator(item, metadata, queue=queue)

    def add_anonymous_creator(self, item, metadata, queue=False):
        """
        Add the creator statement for an anonymous creator.

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork
        :return:
        """
        claims = item.get().get('claims')

        if 'P170' in claims:
            # Already has creator. Could implement adding a missing reference
            return

        newclaim = pywikibot.Claim(self.repo, 'P170')
        newclaim.setSnakType('somevalue')

        newqualifier = pywikibot.Claim(self.repo, 'P3831')
        anonymous = pywikibot.ItemPage(self.repo, 'Q4233718')
        newqualifier.setTarget(anonymous)
        if queue:
            self.queue_qualifier(newclaim, newqualifier)
        else:
            item.addClaim(newclaim)
            newclaim.addQualifier(newqualifier)

        if metadata.get('creatorqualifierpid') and metadata.get('uncertaincreatorqid'):
            newqualifier = pywikibot.Claim(self.repo, metadata.get('creatorqualifierpid'))
            destitem = pywikibot.ItemPage(self.repo, metadata.get('uncertaincreatorqid'))
            if destitem.isRedirectPage():
                destitem = destitem.getRedirectTarget()
            newqualifier.setTarget(destitem)

            if queue:
                self.queue_qualifier(newclaim, newqualifier)
            else:
                newclaim.addQualifier(newqualifier)

        if queue:
            self.addReference(item, newclaim, metadata['refurl'], queue=True)
            self.statements_queue.append(newclaim.toJSON())
        else:
            self.addReference(item, newclaim, metadata.get('refurl'))

    def add_inventory_number(self, item, metadata, queue=False):
        """
        Add the inventory number (P217) if item doesn't have one yet
        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork, should contain the title field as a dict
        :param queue:
        :return:
        """
        claims = item.get().get('claims')

        if 'P217' in claims:
            # Already has an inventory number. Just skip.
            return
        if metadata.get('idpid') == 'P217' and metadata.get('id') and metadata.get('collectionqid'):
            newclaim = pywikibot.Claim(self.repo, 'P217')
            newclaim.setTarget(metadata.get('id'))

            if not queue:
                pywikibot.output('Adding inventory number claim to %s' % item)
                item.addClaim(newclaim)

            newqualifier = pywikibot.Claim(self.repo, 'P195')
            newqualifier.setTarget(pywikibot.ItemPage(self.repo, metadata.get('collectionqid')))
            if queue:
                self.queue_qualifier(newclaim, newqualifier)
            else:
                pywikibot.output('Adding new collection qualifier claim to %s' % item)
                newclaim.addQualifier(newqualifier)

            if queue:
                self.addReference(item, newclaim, metadata['refurl'], queue=True)
                self.statements_queue.append(newclaim.toJSON())
            else:
                self.addReference(item, newclaim, metadata[u'refurl'])


            return
    def addTitle(self, item, metadata, queue=False):
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
                    newtitle = pywikibot.WbMonolingualText(text=metadata.get(u'title').get(lang).strip(),
                                                           language=lang,
                                                           )
                    newclaim = pywikibot.Claim(self.repo, u'P1476')
                    newclaim.setTarget(newtitle)
                    if queue:
                        self.addReference(item, newclaim, metadata['refurl'], queue=True)
                        self.statements_queue.append(newclaim.toJSON())
                    else:
                        try:
                            pywikibot.output('Adding title to %s' % item)
                            item.addClaim(newclaim)
                            self.addReference(item, newclaim, metadata[u'refurl'])
                        except pywikibot.exceptions.OtherPageSaveError:
                            pywikibot.output(u'The title was malformed, skipping it')
                            pass

    def add_inception(self, item, metadata, queue=False):
        """
        Add the inception to the item.

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork, should contain the inception field
        :return:
        """
        claims = item.get().get('claims')

        if 'P571' in claims:
            # Already has inception. Could add logic for sourcing
            return

        if metadata.get('inception'):
            if type(metadata['inception']) is int or (len(metadata['inception'])==4 and \
                                                               metadata['inception'].isnumeric()):  # It's a year
                if metadata.get('inceptionprecision'):
                    if metadata.get('inceptionprecision') == 'decade':
                        precision = 8  # decade
                    elif metadata.get('inceptionprecision') == 'century':
                        precision = 7  # century
                    else:
                        pywikibot.output('Invalid precision "%s", skipping' % (metadata.get('inceptionprecision'),))
                        return
                    newdate = pywikibot.WbTime(year=int(metadata['inception']), precision=precision)
                else:
                    newdate = pywikibot.WbTime(year=int(metadata['inception']))
                newclaim = pywikibot.Claim(self.repo, 'P571')
                newclaim.setTarget(newdate)
                if not queue:
                    pywikibot.output('Adding date of creation claim to %s' % item)
                    item.addClaim(newclaim)

                # Handle circa dates
                if metadata.get('inceptioncirca'):
                    newqualifier = pywikibot.Claim(self.repo, 'P1480')
                    newqualifier.setTarget(pywikibot.ItemPage(self.repo, 'Q5727902'))
                    if queue:
                        self.queue_qualifier(newclaim, newqualifier)
                    else:
                        pywikibot.output('Adding new circa qualifier claim to %s' % item)
                        newclaim.addQualifier(newqualifier)

                # Handle refine dates
                if metadata.get('inceptionrefine'):
                    refine_dates = {'beginning of': 'Q40719727',
                                    'middle of': 'Q40719748',
                                    'end of': 'Q40719766',
                                    }
                    if metadata.get('inceptionrefine') not in refine_dates:
                        pywikibot.output('Invalid refine date "%s", skipping' % (metadata.get('inceptionrefine'),))
                        return
                    refine_date = refine_dates.get(metadata.get('inceptionrefine'))
                    newqualifier = pywikibot.Claim(self.repo, 'P4241')
                    newqualifier.setTarget(pywikibot.ItemPage(self.repo, refine_date))
                    if queue:
                        self.queue_qualifier(newclaim, newqualifier)
                    else:
                        pywikibot.output('Adding new refine date qualifier claim to %s' % item)
                        newclaim.addQualifier(newqualifier)

                if queue:
                    self.addReference(item, newclaim, metadata['refurl'], queue=True)
                    self.statements_queue.append(newclaim.toJSON())
                else:
                    self.addReference(item, newclaim, metadata[u'refurl'])

        elif metadata.get(u'inceptionstart') and metadata.get(u'inceptionend'):
            if metadata.get(u'inceptionstart')==metadata.get(u'inceptionend'):
                #FIXME: Xqt broke this. Need to make sure it's an int
                newdate = pywikibot.WbTime(year=metadata[u'inceptionstart'])
                newclaim = pywikibot.Claim(self.repo, u'P571')
                newclaim.setTarget(newdate)
                if not queue:
                    pywikibot.output('Adding date of creation claim to %s' % item)
                    item.addClaim(newclaim)

                # Handle circa dates
                if metadata.get(u'inceptioncirca'):
                    newqualifier = pywikibot.Claim(self.repo, u'P1480')
                    newqualifier.setTarget(pywikibot.ItemPage(self.repo, u'Q5727902'))
                    if queue:
                        self.queue_qualifier(newclaim, newqualifier)
                    else:
                        pywikibot.output('Adding new circa qualifier claim to %s' % item)
                        newclaim.addQualifier(newqualifier)

                if queue:
                    self.addReference(item, newclaim, metadata['refurl'], queue=True)
                    self.statements_queue.append(newclaim.toJSON())
                else:
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
                if not queue:
                    pywikibot.output('Adding date of creation claim to %s' % item)
                    item.addClaim(newclaim)

                earliestqualifier = pywikibot.Claim(self.repo, u'P1319')
                earliestqualifier.setTarget(earliestdate)
                if queue:
                    self.queue_qualifier(newclaim, earliestqualifier)
                else:
                    newclaim.addQualifier(earliestqualifier)

                latestqualifier = pywikibot.Claim(self.repo, u'P1326')
                latestqualifier.setTarget(latestdate)
                if queue:
                    self.queue_qualifier(newclaim, latestqualifier)
                else:
                    newclaim.addQualifier(latestqualifier)

                # Handle circa dates
                if metadata.get(u'inceptioncirca'):
                    newqualifier = pywikibot.Claim(self.repo, u'P1480')
                    newqualifier.setTarget(pywikibot.ItemPage(self.repo, u'Q5727902'))
                    if queue:
                        self.queue_qualifier(newclaim, newqualifier)
                    else:
                        pywikibot.output('Adding new circa qualifier claim to %s' % item)
                        newclaim.addQualifier(newqualifier)

                if queue:
                    self.addReference(item, newclaim, metadata['refurl'], queue=True)
                    self.statements_queue.append(newclaim.toJSON())
                else:
                    self.addReference(item, newclaim, metadata[u'refurl'])

    def updateCollection(self, item, metadata):
        """
        Update the collection with a start/end date and add extra collections.

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork, should contain the acquisitiondate/deaccessiondate field
        :return: Nothing, updates item in place
        """
        acquisitiondate = None
        deaccessiondate = None
        if metadata.get('acquisitiondate'):
            acquisitiondate = self.parse_date(metadata.get('acquisitiondate'))
        if metadata.get('deaccessiondate'):
            deaccessiondate = self.parse_date(metadata.get('deaccessiondate'))

        if not acquisitiondate and not deaccessiondate:
            # Nothing to update
            return

        if not metadata.get('collectionqid'):
            # Don't know what collection to work on
            return

        claims = item.get().get('claims')

        if 'P195' in claims:
            for collectionclaim in claims.get('P195'):
                # Would like to use collectionclaim.has_qualifier(u'P580')
                if collectionclaim.getTarget() and collectionclaim.getTarget().title() == metadata.get('collectionqid'):
                    if acquisitiondate and not collectionclaim.qualifiers.get('P580'):
                        colqualifier = pywikibot.Claim(self.repo, 'P580')
                        colqualifier.setTarget(acquisitiondate)
                        pywikibot.output('Update collection claim with start time on %s' % item)
                        collectionclaim.addQualifier(colqualifier)
                    if deaccessiondate and not collectionclaim.qualifiers.get('P582'):
                        colqualifier = pywikibot.Claim(self.repo, 'P582')
                        colqualifier.setTarget(deaccessiondate)
                        pywikibot.output('Update collection claim with end time on %s' % item)
                        collectionclaim.addQualifier(colqualifier)

    def parse_date(self, date_string):
        """
        Try to parse a data
        :param date_string: The date string to pars
        :return: pywikibot.WbTime
        """
        date_regex = '^(\d\d\d\d)-(\d\d)-(\d\d)'
        date_match = re.match(date_regex, str(date_string))
        parsed_date = None
        if type(date_string) is int or (len(date_string)==4 and date_string.isnumeric()): # It's a year
            return pywikibot.WbTime(year=int(date_string))
        elif date_match:
            return pywikibot.WbTime(year=int(date_match.group(1)),
                                    month=int(date_match.group(2)),
                                    day=int(date_match.group(3)))
        else:
            try:
                parsed_date = pywikibot.WbTime.fromTimestr(date_string)
                # Pff, precision is t0o high. Hack to fix this
                if parsed_date.precision > 11:
                    parsed_date.precision=11

            except ValueError:
                pywikibot.output(u'Can not parse %s' % (date_string,))
                try:
                    parsed_date = pywikibot.WbTime.fromTimestr('%sZ' % (date_string,) )
                    if parsed_date.precision > 11:
                        parsed_date.precision=11
                except ValueError:
                    pywikibot.output(u'Also can not parse %sZ' % (date_string,))
            return parsed_date

    def add_extra_collections(self, item, metadata):
        """
        Add extra collections and identifiers

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork
        :return: Nothing, updates item in place
        """
        if metadata.get('extracollectionqids'):
            for extracollectionqid in metadata.get('extracollectionqids'):
                self.addCollection(item, extracollectionqid, metadata)
                # TODO: Figure out how to handle the inventory numbers
                #if metadata.get('extraid'):
                #    self.addExtraId(item, metadata.get('extraid'), metadata.get('extracollectionqid'), metadata)

        #if metadata.get('collectionqid'):
        #    self.addCollection(item, metadata.get('collectionqid'), metadata)
        #    if metadata.get('id'):
        #        self.addExtraId(item, metadata.get('id'), metadata.get('collectionqid'), metadata)

        if metadata.get('extracollectionqid'):
            self.addCollection(item, metadata.get('extracollectionqid'), metadata)
            if metadata.get('extraid'):
                self.addExtraId(item, metadata.get('extraid'), metadata.get('extracollectionqid'), metadata)
        if metadata.get('extracollectionqid2'):
            self.addCollection(item, metadata.get('extracollectionqid2'), metadata)
            if metadata.get('extraid2'):
                self.addExtraId(item, metadata.get('extraid2'), metadata.get('extracollectionqid2'), metadata)
        if metadata.get('extracollectionqid3'):
            self.addCollection(item, metadata.get('extracollectionqid3'), metadata)
            if metadata.get('extraid3'):
                self.addExtraId(item, metadata.get('extraid3'), metadata.get('extracollectionqid3'), metadata)

    def addCollection(self, item, collectionqid, metadata, queue=False):
        """
        Add an extra collection if it's not already in the item

        :param item: The artwork item to work on
        :param collectionqid: The id of the Wikidata collection item to add
        :param metadata: All the metadata about this artwork (for the reference)
        :return: Nothing, updates item in place
        """
        if collectionqid == 'Q768717':
            # TODO: Add private collection handling. This makes sure I don't produce junk
            return
        claims = item.get().get('claims')

        foundCollection = False
        collectionitem = pywikibot.ItemPage(self.repo, collectionqid)
        if 'P195' in claims:
            for collectionclaim in claims.get('P195'):
                if collectionclaim.getTarget() == collectionitem:
                    foundCollection = True
                    if not collectionclaim.getSources():
                        try:
                            self.addReference(item, collectionclaim, metadata['refurl'])
                        except pywikibot.exceptions.APIError:
                            pywikibot.output('Unable to add reference to collection on %s, probably double' % item)

        if not foundCollection:
            newclaim = pywikibot.Claim(self.repo, u'P195')
            newclaim.setTarget(collectionitem)
            pywikibot.output('Adding (extra) collection claim to %s' % item)
            item.addClaim(newclaim)
            self.addReference(item, newclaim, metadata['refurl'])

    def addExtraId(self, item, extraid, collectionqid, metadata):
        """
        Add an extra identifier (usually inventory number) if it's not already in the item

        :param item: The artwork item to work on
        :param extraid: The extra to add
        :param collectionqid: The id of the Wikidata collection item the identifier is valid in
        :param metadata: All the metadata about this artwork (for the reference)
        :return: Nothing, updates item in place
        """
        claims = item.get().get('claims')

        foundIdentifier = False
        collectionitem = pywikibot.ItemPage(self.repo, collectionqid)

        if self.idProperty in claims:
            for idclaim in claims.get(self.idProperty):
                # Only check if we already got an id in the collection (to prevent adding the wrong id over and over)
                if idclaim.qualifiers and idclaim.qualifiers.get('P195'):
                    qualifier = idclaim.qualifiers.get('P195')[0]
                    if qualifier.getTarget() == collectionitem:
                        foundIdentifier = True

        if not foundIdentifier:
            newclaim = pywikibot.Claim(self.repo, self.idProperty)
            newclaim.setTarget(extraid)
            pywikibot.output('Adding extra new id claim to %s' % item)
            item.addClaim(newclaim)

            self.addReference(item, newclaim, metadata['refurl'])

            newqualifier = pywikibot.Claim(self.repo, 'P195')
            newqualifier.setTarget(collectionitem)
            pywikibot.output('Adding new qualifier claim to %s' % item)
            newclaim.addQualifier(newqualifier)

    def addCatalogCode(self, item, metadata, queue=False):
        """
        Add the catalog code in a catalog if the catalog is not already in the item

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork (for the reference)
        :return: Nothing, updates item in place
        """
        if not metadata.get('catalog_code') or not metadata.get('catalog'):
            return

        claims = item.get().get('claims')
        found_catalog = False
        catalog_item = pywikibot.ItemPage(self.repo, metadata.get('catalog'))

        if 'P528' in claims:
            for catalog_code_claim in claims.get('P528'):
                # Only check if we have some catalog code in the catalog to prevent adding wrong id over and over
                if catalog_code_claim.qualifiers and catalog_code_claim.qualifiers.get('P972'):
                    qualifier = catalog_code_claim.qualifiers.get('P972')[0]
                    if qualifier.getTarget() == catalog_item:
                        found_catalog = True

        if found_catalog:
            return

        newclaim = pywikibot.Claim(self.repo, 'P528')
        newclaim.setTarget(metadata.get('catalog_code'))
        newqualifier = pywikibot.Claim(self.repo, 'P972')
        newqualifier.setTarget(catalog_item)

        if queue:
            self.queue_qualifier(newclaim, newqualifier)
            self.addReference(item, newclaim, metadata['refurl'], queue=True)
            self.statements_queue.append(newclaim.toJSON())
        else:
            pywikibot.output('Adding catalog code claim to %s' % item)
            item.addClaim(newclaim)
            pywikibot.output('Adding new qualifier claim to %s' % item)
            newclaim.addQualifier(newqualifier)
            self.addReference(item, newclaim, metadata['refurl'])

    def addMaterialUsed(self, item, metadata, queue=False):
        """
        Add the material used (P186) based on the medium to the item.

        Strings like "oil on canvas" are mapped to statements. Missing statements and missing sources will be added.

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork, should contain the medium field
        :return: Nothing, updates item in place
        """
        claims = item.get().get('claims')
        mediums = { 'oil on canvas' : {'paint' : 'Q296955', 'surface' : 'Q12321255'},
                    'oil on panel' : {'paint' : 'Q296955', 'surface' : 'Q106857709'},
                    'oil on wood panel' : {'paint' : 'Q296955', 'surface' : 'Q106857709'},
                    'oil on fir panel' : {'paint' : 'Q296955', 'surface' : 'Q107103505'},
                    'oil on lime panel' : {'paint' : 'Q296955', 'surface' : 'Q107296639'},
                    'oil on oak panel' : {'paint' : 'Q296955', 'surface' : 'Q106857823'},
                    'oil on pine panel' : {'paint' : 'Q296955', 'surface' : 'Q106940268'},
                    'oil on poplar panel' : {'paint' : 'Q296955', 'surface' : 'Q106857865'},
                    'oil on walnut panel' : {'paint' : 'Q296955', 'surface' : 'Q107103575'},
                    'oil on paper' : {'paint' : 'Q296955', 'surface' : 'Q11472'},
                    'oil on copper' : {'paint' : 'Q296955', 'surface' : 'Q753'},
                    'oil on cardboard' : {'paint' : 'Q296955', 'surface' : 'Q18668582'},
                    'tempera on canvas' : {'paint' : 'Q175166', 'surface' : 'Q12321255'},
                    'tempera on panel' : {'paint' : 'Q175166', 'surface' : 'Q106857709'},
                    'tempera on wood panel' : {'paint' : 'Q175166', 'surface' : 'Q106857709'},
                    'tempera on fir panel' : {'paint' : 'Q175166', 'surface' : 'Q107103505'},
                    'tempera on lime panel' : {'paint' : 'Q175166', 'surface' : 'Q107296639'},
                    'tempera on oak panel' : {'paint' : 'Q175166', 'surface' : 'Q106857823'},
                    'tempera on pine panel' : {'paint' : 'Q175166', 'surface' : 'Q106940268'},
                    'tempera on poplar panel' : {'paint' : 'Q175166', 'surface' : 'Q106857865'},
                    'tempera on walnut panel' : {'paint' : 'Q175166', 'surface' : 'Q107103575'},
                    'tempera on paper' : {'paint' : 'Q175166', 'surface' : 'Q11472'},
                    'acrylic paint on canvas' : {'paint' : 'Q207849', 'surface' : 'Q12321255'},
                    'acrylic on canvas' : {'paint' : 'Q207849', 'surface' : 'Q12321255'},
                    'acrylic paint on panel' : {'paint' : 'Q207849', 'surface' : 'Q106857709'},
                    'acrylic on panel' : {'paint' : 'Q207849', 'surface' : 'Q106857709'},
                    'acrylic on wood panel' : {'paint' : 'Q207849', 'surface' : 'Q106857709'},
                    'acrylic paint on paper' : {'paint' : 'Q207849', 'surface' : 'Q11472'},
                    'acrylic on paper' : {'paint' : 'Q207849', 'surface' : 'Q11472'},
                    'watercolor on paper' : {'paint' : 'Q22915256', 'surface' : 'Q11472'},
                    # In Germany often the type of paint is not mentioned.
                    'paint on canvas' : {'paint' : 'Q174219', 'surface' : 'Q12321255'},
                    'paint on panel' : {'paint' : 'Q174219', 'surface' : 'Q106857709'},
                    'paint on wood panel' : {'paint' : 'Q174219', 'surface' : 'Q106857709'},
                    'paint on fir panel' : {'paint' : 'Q174219', 'surface' : 'Q107103505'},
                    'paint on lime panel' : {'paint' : 'Q174219', 'surface' : 'Q107296639'},
                    'paint on oak panel' : {'paint' : 'Q174219', 'surface' : 'Q106857823'},
                    'paint on pine panel' : {'paint' : 'Q174219', 'surface' : 'Q106940268'},
                    'paint on poplar panel' : {'paint' : 'Q174219', 'surface' : 'Q106857865'},
                    'paint on walnut panel' : {'paint' : 'Q174219', 'surface' : 'Q107103575'},
                    'paint on paper': {'paint': 'Q174219', 'surface': 'Q11472'},
                    'paint on copper': {'paint': 'Q174219', 'surface': 'Q753'},
                    'black chalk on paper': {'paint': 'Q3387833', 'surface': 'Q11472'},
                    'black chalk on cardboard': {'paint': 'Q3387833', 'surface': 'Q18668582'},
                    'chalk on paper': {'paint': 'Q183670', 'surface': 'Q11472'},
                    'chalk on cardboard': {'paint': 'Q183670', 'surface': 'Q18668582'},
                    'charcoal on paper': {'paint': 'Q1424515', 'surface': 'Q11472'},
                    'charcoal on cardboard': {'paint': 'Q1424515', 'surface': 'Q18668582'},
                    'pencil on paper': {'paint': 'Q14674', 'surface': 'Q11472'},
                    'pencil on cardboard': {'paint': 'Q14674', 'surface': 'Q18668582'},
                    'oil on canvas on panel': {'paint': 'Q296955', 'surface': 'Q12321255', 'mount': 'Q106857709'},
                    'oil on paper on panel': {'paint': 'Q296955', 'surface': 'Q11472', 'mount': 'Q106857709'},
                    'oil on cardboard on panel': {'paint': 'Q296955', 'surface': 'Q18668582', 'mount': 'Q106857709'},
                    'oil on copper on panel': {'paint': 'Q296955', 'surface': 'Q753', 'mount': 'Q106857709'},
                    'oil on canvas on cardboard': {'paint': 'Q296955', 'surface': 'Q12321255', 'mount': 'Q18668582'},
                    'oil on paper on cardboard': {'paint': 'Q296955', 'surface': 'Q11472', 'mount': 'Q18668582'},
                    'tempera on canvas on panel': {'paint': 'Q175166', 'surface': 'Q12321255', 'mount': 'Q106857709'},
                    }
        if not metadata.get('medium'):
            return
        medium = metadata.get('medium').lower().strip()
        if medium not in mediums:
            pywikibot.output('Unable to match medium "%s" to materials' % (metadata.get('medium'),))
            return
        paint = pywikibot.ItemPage(self.repo, mediums.get(medium).get('paint'))
        surface = pywikibot.ItemPage(self.repo, mediums.get(medium).get('surface'))
        mount = None
        if mediums.get(medium).get('mount'):
            mount = pywikibot.ItemPage(self.repo, mediums.get(medium).get('mount'))

        painting_surface = pywikibot.ItemPage(self.repo, 'Q861259')
        painting_mount = pywikibot.ItemPage(self.repo, 'Q107105674')

        if 'P186' not in claims:
            # Paint
            newclaim = pywikibot.Claim(self.repo, 'P186')
            newclaim.setTarget(paint)
            if queue:
                self.addReference(item, newclaim, metadata['refurl'], queue=True)
                self.statements_queue.append(newclaim.toJSON())
            else:
                pywikibot.output('Adding new paint claim to %s' % item)
                item.addClaim(newclaim)
                self.addReference(item, newclaim, metadata['refurl'])

            # Surface
            newclaim = pywikibot.Claim(self.repo, 'P186')
            newclaim.setTarget(surface)
            # Surface qualifier
            newqualifier = pywikibot.Claim(self.repo, 'P518') #Applies to part
            newqualifier.setTarget(painting_surface)

            if queue:
                self.queue_qualifier(newclaim, newqualifier)
                self.addReference(item, newclaim, metadata['refurl'], queue=True)
                self.statements_queue.append(newclaim.toJSON())
            else:
                pywikibot.output('Adding new painting surface claim to %s' % item)
                item.addClaim(newclaim)
                pywikibot.output('Adding new painting surface qualifier claim to %s' % item)
                newclaim.addQualifier(newqualifier)
                self.addReference(item, newclaim, metadata['refurl'])

            # Mount if we have it
            if mount:
                newclaim = pywikibot.Claim(self.repo, 'P186')
                newclaim.setTarget(mount)

                newqualifier = pywikibot.Claim(self.repo, 'P518')
                newqualifier.setTarget(painting_mount)

                if queue:
                    self.queue_qualifier(newclaim, newqualifier)
                    self.addReference(item, newclaim, metadata['refurl'], queue=True)
                    self.statements_queue.append(newclaim.toJSON())
                else:
                    pywikibot.output('Adding new painting mount claim to %s' % item)
                    item.addClaim(newclaim)
                    pywikibot.output('Adding new painting mount qualifier claim to %s' % item)
                    newclaim.addQualifier(newqualifier)
                    self.addReference(item, newclaim, metadata['refurl'])

        elif 'P186' in claims and len(claims.get('P186')) == 1 and not mount:
            madeclaim = claims.get('P186')[0]
            if madeclaim.getTarget() == surface:
                if not madeclaim.getSources():
                    self.addReference(item, madeclaim, metadata['refurl'])
                newclaim = pywikibot.Claim(self.repo, 'P186')
                newclaim.setTarget(paint)
                pywikibot.output('Adding missing paint claim to %s' % item)
                item.addClaim(newclaim, summary='Adding missing paint statement')
                self.addReference(item, newclaim, metadata['refurl'])
            elif madeclaim.getTarget() == paint:
                if not madeclaim.getSources():
                    self.addReference(item, madeclaim, metadata['refurl'])
                newclaim = pywikibot.Claim(self.repo, 'P186')
                newclaim.setTarget(surface)
                pywikibot.output('Adding missing painting surface claim to %s' % item)
                item.addClaim(newclaim, summary='Adding missing painting surface statement')

                newqualifier = pywikibot.Claim(self.repo, 'P518') #Applies to part
                newqualifier.setTarget(painting_surface)
                pywikibot.output('Adding new painting surface qualifier claim to %s' % item)
                newclaim.addQualifier(newqualifier)
                self.addReference(item, newclaim, metadata['refurl'])
        elif 'P186' in claims and len(claims.get('P186')) == 2 and not mount:
            for madeclaim in claims.get('P186'):
                if madeclaim.getTarget()==surface or madeclaim.getTarget()==paint:
                    if not madeclaim.getSources():
                        self.addReference(item, madeclaim, metadata['refurl'])

    def addDimensions(self, item, metadata, queue=False):
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
            if queue:
                self.addReference(item, newclaim, metadata['refurl'], queue=True)
                self.statements_queue.append(newclaim.toJSON())
            else:
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
            if queue:
                self.addReference(item, newclaim, metadata['refurl'], queue=True)
                self.statements_queue.append(newclaim.toJSON())
            else:
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
            if queue:
                self.addReference(item, newclaim, metadata['refurl'], queue=True)
                self.statements_queue.append(newclaim.toJSON())
            else:
                pywikibot.output('Adding depth in cm claim to %s' % item)
                item.addClaim(newclaim)
                self.addReference(item, newclaim, metadata[u'refurl'])

    def addImageSuggestion(self, item, metadata, queue=False):
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

        # Simple url clean up
        imageurl = metadata.get(u'imageurl')
        for a, b in [(' ', '%20'), ('[', '%5B'), (']', '%5B')]:
            imageurl = imageurl.replace(a, b)

        if u'P18' in claims and not metadata.get(u'imageurlforce'):
            if not metadata.get(u'imageupgrade'):
                return
            newimage = requests.get(imageurl, stream=True)
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

        newclaim = pywikibot.Claim(self.repo, 'P4765')
        newclaim.setTarget(imageurl)
        if not queue:
            pywikibot.output('Adding commons compatible image available at URL claim to %s' % item)
            item.addClaim(newclaim)

        if metadata.get('imageurlformat'):
            newqualifier = pywikibot.Claim(self.repo, u'P2701')
            newqualifier.setTarget(pywikibot.ItemPage(self.repo, metadata.get(u'imageurlformat')))
            if queue:
                self.queue_qualifier(newclaim, newqualifier)
            else:
                pywikibot.output('Adding new qualifier claim to %s' % item)
                newclaim.addQualifier(newqualifier)

        newqualifier = pywikibot.Claim(self.repo, u'P2699')
        newqualifier.setTarget(metadata[u'imagesourceurl'])
        if queue:
            self.queue_qualifier(newclaim, newqualifier)
        else:
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
            if queue:
                self.queue_qualifier(newclaim, newqualifier)
            else:
                pywikibot.output('Adding new qualifier claim to %s' % item)
                newclaim.addQualifier(newqualifier)

        if metadata.get('creatorname'):
            newqualifier = pywikibot.Claim(self.repo, u'P2093')
            newqualifier.setTarget(metadata.get('creatorname'))
            if queue:
                self.queue_qualifier(newclaim, newqualifier)
            else:
                pywikibot.output('Adding new qualifier claim to %s' % item)
                newclaim.addQualifier(newqualifier)

        if metadata.get(u'imageurllicense'):
            newqualifier = pywikibot.Claim(self.repo, u'P275')
            newqualifier.setTarget(pywikibot.ItemPage(self.repo, metadata.get(u'imageurllicense')))
            if queue:
                self.queue_qualifier(newclaim, newqualifier)
            else:
                pywikibot.output('Adding new qualifier claim to %s' % item)
                newclaim.addQualifier(newqualifier)

        if metadata.get(u'imageoperatedby'):
            newqualifier = pywikibot.Claim(self.repo, u'P137')
            newqualifier.setTarget(pywikibot.ItemPage(self.repo, metadata.get(u'imageoperatedby')))
            if queue:
                self.queue_qualifier(newclaim, newqualifier)
            else:
                pywikibot.output('Adding new qualifier claim to %s' % item)
                newclaim.addQualifier(newqualifier)

        if queue:
            self.statements_queue.append(newclaim.toJSON())

    def addIiifManifestUrl(self, item, metadata, queue=False):
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
            if queue:
                self.addReference(item, newclaim, metadata['refurl'], queue=True)
                self.statements_queue.append(newclaim.toJSON())
            else:
                pywikibot.output('Adding IIIF manifest url claim to %s' % item)
                item.addClaim(newclaim)
                self.addReference(item, newclaim, metadata[u'refurl'])

    def addCollectionLink(self, item, metadata, queue=False):
        """
        Add a link to the item in a collection.
        This is either described at URL (P973) or a customer per collection id

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork, should contain the describedbyurl or the artworkidpid and artworkid fields.
        :return: Nothing, updates item in place
        """
        claims = item.get().get('claims')

        if metadata.get('artworkidpid'):
            if metadata.get('artworkidpid') == metadata.get('idpid'):
                # It's the lookup key so should always be set already. Prevents duplicates at creation
                return
            if metadata.get('artworkidpid') not in claims:
                newclaim = pywikibot.Claim(self.repo, metadata.get('artworkidpid') )
                newclaim.setTarget(metadata['artworkid'])
                if queue:
                    self.statements_queue.append(newclaim.toJSON())
                else:
                    pywikibot.output('Adding artwork id claim to %s' % item)
                    item.addClaim(newclaim)

            # Add an additional artwork ID 2
            if metadata.get('artworkidpid2') and metadata.get('artworkidpid2') not in claims:
                newclaim = pywikibot.Claim(self.repo, metadata.get('artworkidpid2') )
                newclaim.setTarget(metadata['artworkid2'])
                if queue:
                    self.statements_queue.append(newclaim.toJSON())
                else:
                    pywikibot.output('Adding artwork id2 claim to %s' % item)
                    item.addClaim(newclaim)

            # Add an additional artwork ID 3
            if metadata.get('artworkidpid3') and metadata.get('artworkidpid3') not in claims:
                newclaim = pywikibot.Claim(self.repo, metadata.get('artworkidpid3') )
                newclaim.setTarget(metadata['artworkid3'])
                if queue:
                    self.statements_queue.append(newclaim.toJSON())
                else:
                    pywikibot.output('Adding artwork id2 claim to %s' % item)
                    item.addClaim(newclaim)

        # Described at url
        elif metadata.get(u'describedbyurl'):
            if u'P973' not in claims:
                newclaim = pywikibot.Claim(self.repo, u'P973')
                newclaim.setTarget(metadata[u'describedbyurl'])
                if queue:
                    self.statements_queue.append(newclaim.toJSON())
                else:
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
                    if queue:
                        self.statements_queue.append(newclaim.toJSON())
                    else:
                        pywikibot.output('Adding additional described at claim to %s' % item)
                        item.addClaim(newclaim)

    def add_iconclass(self, item, metadata, queue=False):
        """
        Add depicts iconclass to item
        :param item:
        :param metadata:
        :return:
        """
        claims = item.get().get('claims')

        if metadata.get('depictsiconclass'):
            current_iconclass = []
            if claims.get('P1257'):
                for claim in claims.get('P1257'):
                    current_iconclass.append(claim.getTarget())

            for depictsiconclass in set(metadata.get('depictsiconclass')):
                if depictsiconclass not in current_iconclass:
                    newclaim = pywikibot.Claim(self.repo, 'P1257')
                    newclaim.setTarget(depictsiconclass)
                    if queue:
                        self.addReference(item, newclaim, metadata['refurl'], queue=True)
                        self.statements_queue.append(newclaim.toJSON())
                    else:
                        pywikibot.output('Adding depicts Iconclass notation claim to %s' % item)
                        item.addClaim(newclaim)
                        self.addReference(item, newclaim, metadata.get('refurl'))
                        # TO DO: Add sourcing of existing statements

    def save_statements(self, item):
        """
        Save the queued statements
        """
        if not self.statements_queue:
            return
        properties = set()
        for statement in self.statements_queue:
            properties.add(statement.get('mainsnak').get('property'))

        summary = 'Added'
        for prop in properties:
            summary += ' [[Property:%s]]' % (prop,)

        pywikibot.output(summary)
        item.editEntity(data={'claims': self.statements_queue}, summary=summary)

    def addItemStatement(self, item, pid, qid, url, queue=False):
        """
        Helper function to add a statement, or add missing reference, or update reference to existing statement
        """
        if not qid:
            return False

        claims = item.get().get('claims')
        if pid in claims:
            if len(claims.get(pid)) == 1:
                claim = claims.get(pid)[0]
                if claim and claim.getTarget() and claim.getTarget().title() and claim.getTarget().title() == qid:
                    if not claim.getSources():
                        self.addReference(item, claim, url)
                    else:
                        removable_source = self.is_removable_sources(claim.getSources())
                        if removable_source:
                            claim.removeSource(removable_source, summary='Removing to add better source')
                            self.addReference(item, claim, url)
            return

        newclaim = pywikibot.Claim(self.repo, pid)
        destitem = pywikibot.ItemPage(self.repo, qid)
        if destitem.isRedirectPage():
            destitem = destitem.getRedirectTarget()

        newclaim.setTarget(destitem)
        if queue:
            self.addReference(item, newclaim, url, queue=True)
            self.statements_queue.append(newclaim.toJSON())
        else:
            pywikibot.output(u'Adding %s->%s to %s' % (pid, qid, item))
            item.addClaim(newclaim)
            self.addReference(item, newclaim, url)

    def queue_qualifier(self, newclaim, qualifier):
        """
        Helper function to queue a qualifier
        :param newclaim: The claim to add the qualifier to
        :param qualifier: The qualifier to add
        :return:
        """
        qualifier.isQualifier = True
        if qualifier.getID() in newclaim.qualifiers:
            newclaim.qualifiers[qualifier.getID()].append(qualifier)
        else:
            newclaim.qualifiers[qualifier.getID()] = [qualifier]

    def addReference(self, item, newclaim, url, queue=False):
        """
        Add a reference with a retrieval url and todays date
        """
        refurl = pywikibot.Claim(self.repo, u'P854')
        refurl.setTarget(url)
        refdate = pywikibot.Claim(self.repo, u'P813')
        today = datetime.datetime.today()
        date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
        refdate.setTarget(date)
        if queue:
            source = defaultdict(list)
            for refclaim in [refurl, refdate]:
                refclaim.isReference = True
                source[refclaim.getID()].append(refclaim)
            newclaim.sources.append(source)
        else:
            pywikibot.output('Adding new reference claim to %s' % item)
            newclaim.addSources([refurl, refdate])

    def is_removable_sources(self, sources):
        """
        Will return the source claim if the list of sources is one entry and only is imported from and nothing else
        :param sources: The list of sources
        :return: Source claim
        """
        if not len(sources) == 1:
            return False
        source = sources[0]
        if not len(source) == 1:
            return False
        # FIXME: Handle Commons import cases like https://www.wikidata.org/wiki/Q112876539
        if 'P143' not in source:
            return False
        return source.get('P143')[0]


class ArtDataIdentifierBot(ArtDataBot):
    """
    Art data bot version that uses identifier properties instead of combination of inventory number and collection
    """
    def __init__(self, generator, id_property, create=False):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.
            * id_property  - The identifier property on Wikidata to work on
            * create       - Boolean to say if you want to create new items or just update existing

        """
        self.generator = generator
        self.idProperty = 'P217'  # The inventory number property probably needs some refactoring
        self.id_property = id_property
        self.create = create
        self.repo = pywikibot.Site().data_repository()
        self.wayback_session = requests.Session()
        self.artwork_ids = self.fillCache()

    def fillCache(self):
        """
        Build an ID cache so we can quickly look up the id's for property
        """
        result = {}

        query = u"""SELECT ?item ?id WHERE {        
        ?item p:%s ?idstatement .        
        ?idstatement ps:%s ?id
        MINUS { ?idstatement wikibase:rank wikibase:DeprecatedRank }
        }""" % (self.id_property, self.id_property, )
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace('http://www.wikidata.org/entity/', '')
            result[resultitem.get('id')] = qid
        pywikibot.output('The query "%s" returned %s items' % (query, len(result)))
        return result

    def run(self):
        """
        Starts the robot.
        """

        # FIXME: Add inventory / collection somewhere if it's available 

        for metadata in self.generator:
            metadata = super().enrichMetadata(metadata)

            if 'artworkidpid' not in metadata:
                pywikibot.output('artworkidpid not found in metadata')
                continue
            if metadata.get('artworkidpid') != self.id_property:
                pywikibot.output('id_property mismatch: "%s" & "%s"' % (metadata.get('artworkidpid'),
                                                                        self.id_property))
                continue

            artwork_item = None
            if metadata['artworkid'] in self.artwork_ids:
                artwork_item_title = self.artwork_ids.get(metadata['artworkid'])
                print(artwork_item_title)
                artwork_item = pywikibot.ItemPage(self.repo, title=artwork_item_title)

            elif self.create:
                artwork_item = self.create_artwork_item(metadata)

            if artwork_item and artwork_item.exists():
                if artwork_item.isRedirectPage():
                    artwork_item = artwork_item.getRedirectTarget()
                metadata['wikidata'] = artwork_item.title()
                super().updateArtworkItem(artwork_item, metadata)

    def create_artwork_item(self, metadata):
        """
        Create a new artwork item based on the metadata

        :param metadata: All the metadata for this new artwork.
        :return: The newly created artworkItem
        """
        data = {'labels': {},
                'descriptions': {},
                'claims': [],
                }

        # loop over stuff
        if metadata.get('labels'):
            for lang, label in metadata.get('labels').items():
                data['labels'][lang] = {'language': lang, 'value': label}

        if metadata.get('description'):
            for lang, description in metadata['description'].items():
                data['descriptions'][lang] = {'language': lang, 'value': description}

        # Add the id to the item so we can get back to it later
        newclaim = pywikibot.Claim(self.repo, self.id_property)
        newclaim.setTarget(metadata['artworkid'])
        data['claims'].append(newclaim.toJSON())

        identification = {}
        summary = 'Creating new item with data from %s ' % (metadata['url'],)
        pywikibot.output(summary)
        try:
            result = self.repo.editEntity(identification, data, summary=summary)
        except pywikibot.exceptions.APIError:
            # TODO: Check if this is pywikibot.exceptions.OtherPageSaveError too
            # We got ourselves a duplicate label and description, just add the identifier to the description
            pywikibot.output('Oops, already had that one. Trying again with the identifier added')
            for lang, description in metadata['description'].items():
                data['descriptions'][lang] = {'language': lang, 'value': u'%s (%s)' % (description, metadata['artworkid'], )}
            try:
                result = self.repo.editEntity(identification, data, summary=summary)
            except pywikibot.exceptions.APIError:
                pywikibot.output(u'Oops, retry also failed. Skipping this one.')
                # Just skip this one
                return

        artwork_item_title = result.get(u'entity').get('id')

        # Make a backup to the Wayback Machine when we have to wait anyway
        self.doWaybackup(metadata)

        # Wikidata is sometimes lagging. Wait for additional 5 seconds before trying to actually use the item
        time.sleep(5)

        artwork_item = pywikibot.ItemPage(self.repo, title=artwork_item_title)

        # Add to self.artworkIds so that we don't create dupes
        self.artwork_ids[metadata['artworkid']] = artwork_item_title

        # Moved to the generic bot
        ## Only add the collection and inventory number at creation to prevent messy data
        #if metadata.get('collectionqid'):
        #    self.addCollection(artwork_item, metadata.get('collectionqid'), metadata)
        #    if metadata.get('id'):
        #        self.addExtraId(artwork_item, metadata.get('id'), metadata.get('collectionqid'), metadata)

        return artwork_item


class ArtDataCatelogBot(ArtDataBot):
    """
    Art data bot version that uses catalog properties instead of combination of inventory number and collection
    """
    def __init__(self, generator, create=False):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.
            * create       - Boolean to say if you want to create new items or just update existing

        """
        firstrecord = next(generator)
        self.generator = itertools.chain([firstrecord], generator)
        self.repo = pywikibot.Site().data_repository()
        self.wayback_session = requests.Session()
        self.create = create

        self.idProperty = 'P528'
        self.catalogqid = firstrecord.get('catalog')
        self.catalogitem = pywikibot.ItemPage(self.repo, self.catalogqid)
        self.artwork_ids = self.fillCache(self.catalogqid, self.idProperty)

    def fillCache(self, catalogqid, idProperty):
        """
        Build an ID cache so we can quickly look up the id's for property
        """
        result = {}
        sq = pywikibot.data.sparql.SparqlQuery()

        # FIXME: Do something with the collection qualifier
        query = u"""SELECT ?item ?id WHERE {
        ?item p:P528 ?idstatement .
        ?idstatement pq:P972 wd:%s .
        ?idstatement ps:P528 ?id
        MINUS { ?idstatement wikibase:rank wikibase:DeprecatedRank }
        }""" % (catalogqid,)
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

        # FIXME: Add inventory / collection somewhere if it's available

        for metadata in self.generator:
            metadata = super().enrichMetadata(metadata)

            artwork_item = None
            if metadata['catalog_code'] in self.artwork_ids:
                artwork_item_title = self.artwork_ids.get(metadata['catalog_code'])
                print(artwork_item_title)
                artwork_item = pywikibot.ItemPage(self.repo, title=artwork_item_title)

            elif self.create:
                artwork_item = self.create_artwork_item(metadata)

            if artwork_item and artwork_item.exists():
                if artwork_item.isRedirectPage():
                    artwork_item = artwork_item.getRedirectTarget()
                metadata['wikidata'] = artwork_item.title()
                super().updateArtworkItem(artwork_item, metadata)

    def create_artwork_item(self, metadata):
        """
        Create a new artwork item based on the metadata

        :param metadata: All the metadata for this new artwork.
        :return: The newly created artworkItem
        """
        data = {'labels': {},
                'descriptions': {},
                'claims': [],
                }

        # loop over stuff
        if metadata.get('labels'):
            for lang, label in metadata.get('labels').items():
                data['labels'][lang] = {'language': lang, 'value': label}

        if metadata.get('description'):
            for lang, description in metadata['description'].items():
                data['descriptions'][lang] = {'language': lang, 'value': description}

        # Add the catalog code to the item so we can get back to it later
        newclaim = pywikibot.Claim(self.repo, 'P528')
        newclaim.setTarget(metadata['catalog_code'])

        newqualifier = pywikibot.Claim(self.repo, 'P972')
        newqualifier.setTarget(self.catalogitem)
        self.queue_qualifier(newclaim, newqualifier)
        self.addReference(None, newclaim, metadata['refurl'], queue=True)
        data['claims'].append(newclaim.toJSON())

        identification = {}
        summary = 'Creating new item with data from %s ' % (metadata['url'],)
        pywikibot.output(summary)
        try:
            result = self.repo.editEntity(identification, data, summary=summary)
        except pywikibot.exceptions.APIError:
            # TODO: Check if this is pywikibot.exceptions.OtherPageSaveError too
            # We got ourselves a duplicate label and description, just add the identifier to the description
            pywikibot.output('Oops, already had that one. Trying again with the catalog code added')
            for lang, description in metadata['description'].items():
                data['descriptions'][lang] = {'language': lang, 'value': u'%s (%s)' % (description, metadata['catalog_code'], )}
            try:
                result = self.repo.editEntity(identification, data, summary=summary)
            except pywikibot.exceptions.APIError:
                pywikibot.output(u'Oops, retry also failed. Skipping this one.')
                # Just skip this one
                return

        artwork_item_title = result.get(u'entity').get('id')

        # Make a backup to the Wayback Machine when we have to wait anyway
        self.doWaybackup(metadata)

        # Wikidata is sometimes lagging. Wait for additional 5 seconds before trying to actually use the item
        time.sleep(5)

        artwork_item = pywikibot.ItemPage(self.repo, title=artwork_item_title)

        # Add to self.artworkIds so that we don't create dupes
        self.artwork_ids[metadata['catalog_code']] = artwork_item_title

        # Moved to the generic bot
        ## Only add the collection and inventory number at creation to prevent messy data
        #if metadata.get('collectionqid'):
        #    self.addCollection(artwork_item, metadata.get('collectionqid'), metadata)
        #    if metadata.get('id'):
        #        self.addExtraId(artwork_item, metadata.get('id'), metadata.get('collectionqid'), metadata)

        return artwork_item

def main():
    print('Dude, write your own bot')


if __name__ == "__main__":
    main()
