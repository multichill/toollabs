#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to get all the paintings in the Dali catalog matched with Wikidata.

See https://www.salvador-dali.org/en/artwork/catalogue-raisonne-paintings/obres/ for the paintings.

Should generate mix'n'match output and maybe more.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import csv
import string
from html.parser import HTMLParser

class DaliPaintingDataBot(artdatabot.ArtDataBot):
    """
    Subclass of ArtDataBot because that one has logic completely based on collections
    """
    def __init__(self, dictGenerator, create=False):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.
            * create       - Boolean to say if you want to create new items or just update existing

        """
        self.generator = dictGenerator
        self.repo = pywikibot.Site().data_repository()
        self.create = create

        self.idProperty = 'P6595'
        self.artworkIds = self.fillCache()

    def fillCache(self):
        """
        Build an ID cache so we can quickly look up the id's for property
        """
        result = {}
        query = """SELECT ?item ?id WHERE { ?item wdt:P6595 ?id }"""
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

        for metadata in self.generator:
            metadata = self.enrichMetadata(metadata)

            artworkItem = None
            if metadata['id'] in self.artworkIds:
                artworkItemTitle = self.artworkIds.get(metadata['id'])
                print (artworkItemTitle)
                artworkItem = pywikibot.ItemPage(self.repo, title=artworkItemTitle)

            elif self.create:
                artworkItem = self.createArtworkItem(metadata)

            if artworkItem and artworkItem.exists():
                metadata['wikidata'] = artworkItem.title()
                self.updateArtworkItem(artworkItem, metadata)

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
            # We got ourselves a duplicate label and description, let's correct that by adding the catalogcode
            pywikibot.output(u'Oops, already had that one. Trying again')
            for lang, description in metadata['description'].items():
                data['descriptions'][lang] = {'language': lang, 'value': u'%s (%s)' % (description, metadata['catalogcode'],) }
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
        self.artworkIds[metadata['id']]=artworkItemTitle

        # Add the id to the item so we can get back to it later
        newclaim = pywikibot.Claim(self.repo, self.idProperty)
        newclaim.setTarget(metadata[u'id'])
        pywikibot.output('Adding new id claim to %s' % artworkItem)
        artworkItem.addClaim(newclaim)

        self.addReference(artworkItem, newclaim, metadata['idrefurl'])

        return artworkItem

    def updateArtworkItem(self, artworkItem, metadata):
        """
        Override this one for now

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

        ## Add title (P1476) to the item.
        #self.addTitle(artworkItem, metadata)

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

        # Add collection
        self.addItemStatement(artworkItem, 'P195', metadata.get('collectionqid'), metadata.get('refurl'))

        # Add the catalog code
        self.addCatalogCode(artworkItem, metadata)

    def addCatalogCode(self, item, metadata):
        """
        Add the catalog code (P528)

        :param item: The artwork item to work on
        :param metadata: All the metadata about this artwork, should contain the catalogcode and catalogqid field
        :return: Nothing, updates item in place
        """
        claims = item.get().get('claims')

        if 'P528' not in claims and metadata.get('catalogcode') and metadata.get('catalogqid'):
            catalog = pywikibot.ItemPage(self.repo, metadata.get('catalogqid'))

            newclaim = pywikibot.Claim(self.repo, 'P528')
            newclaim.setTarget(metadata.get('catalogcode'))
            pywikibot.output('Adding new catalog code to %s' % item)
            item.addClaim(newclaim)

            newqualifier = pywikibot.Claim(self.repo, 'P972') # Catalog
            newqualifier.setTarget(catalog)
            pywikibot.output('Adding new qualifier claim to %s' % item)
            newclaim.addQualifier(newqualifier)
            self.addReference(item, newclaim, metadata['refurl'])

def getDaliCatalogPaintingsGenerator():
    """
    Generator to get the paintings from https://www.salvador-dali.org/en/artwork/catalogue-raisonne-paintings/obres/

    I'm just going to be lazy and loop from 1 to 1200 and work on it if I don't get a 404
    :return:
    """
    htmlparser = HTMLParser()
    urlpattern = 'https://www.salvador-dali.org/en/artwork/catalogue-raisonne-paintings/obra/%s/'
    caurlpattern = 'https://www.salvador-dali.org/en/artwork/catalogue-raisonne-paintings/obra/%s/'
    esurlpattern = 'https://www.salvador-dali.org/en/artwork/catalogue-raisonne-paintings/obra/%s/'
    frurlpattern = 'https://www.salvador-dali.org/en/artwork/catalogue-raisonne-paintings/obra/%s/'
    session = requests.Session()

    collections =  { 'Fundació Gala-Salvador Dalí, Figueres. Dalí bequest' : 'Q1143722',
                     'Fundació Gala-Salvador Dalí, Figueres' : 'Q1143722',
                     'Museo Nacional Centro de Arte Reina Sofía, Madrid. Dalí bequest' : 'Q460889',
                     'Museo Nacional Centro de Arte Reina Sofía, Madrid' : 'Q460889',
                     'The Dali Museum, St. Petersburg (Florida)' : 'Q674427',
                     }


    for i in range(760,1220):
        metadata = {}
        metadata['instanceofqid'] = 'Q3305213'
        metadata['creatorname'] = 'Salvador Dalí'
        metadata['creatorqid'] = 'Q5577'
        metadata['artworkidpid'] = metadata['idpid'] = 'P6595'
        metadata['artworkid'] = metadata['id'] = '%s' % (i,)

        metadata['catalogcode'] = 'P %s' % (i,)
        metadata['catalogqid'] = 'Q24009539'

        url = urlpattern % (i,)
        metadata['url'] = url
        page = session.get(url)
        if page.status_code == 404:
            # Ok, that one didn't exist
            print('No painting found for %s at %s' % (i, url))
            continue

        refurlregex = '\<link rel\=\"canonical\" href\="(%s[^\"]*)\" \/\>' % (url,)
        refurlmatch = re.search(refurlregex, page.text)
        metadata['refurl'] = refurlmatch.group(1)

        titleregex = '\<title\>([^\|]+)\s*\| Fundació Gala - Salvador Dalí\<\/title\>'
        titlematch = re.search(titleregex, page.text)
        metadata['title'] = { 'en' :htmlparser.unescape(titlematch.group(1)).strip(), }

        # TODO: Add title in the other languages too

        dateregex = '\<dt\>Date\:\<\/dt\>[\s\r\n\t]*\<dd\>\<a href\=\"[^\"]*\"\>([^\<]+)\<\/a\>\<\/dd\>'
        datematch = re.search(dateregex, page.text)
        metadata['date'] = htmlparser.unescape(datematch.group(1)).strip()

        # TODO: Add date logic here
        # Try to extract the date
        dateregex = '^(\d\d\d\d)$'
        datecircaregex = '^c\.\s*(\d\d\d\d)$'
        periodregex = '^(\d\d\d\d)-(\d\d\d\d)$'

        datematch = re.match(dateregex, metadata.get('date'))
        datecircamatch = re.match(datecircaregex, metadata.get('date'))
        periodmatch = re.match(periodregex, metadata.get('date'))

        if datematch:
            metadata['inception'] = int(datematch.group(1))
        elif datecircamatch:
            metadata['inception'] = int(datecircamatch.group(1))
            metadata['inceptioncirca'] = True
        elif periodmatch:
            metadata['inceptionstart'] = int(periodmatch.group(1),)
            metadata['inceptionend'] = int(periodmatch.group(2),)
        else:
            print (u'Could not parse date: "%s"' % (metadata.get('date'),))



        mediumregex = '\<dt\>Technique\:\<\/dt\>[\s\r\n\t]*\<dd\>([^\<]+)\<\/dd\>'
        mediummatch = re.search(mediumregex, page.text)
        metadata['medium'] = htmlparser.unescape(mediummatch.group(1)).strip().lower()

        dimensionregex = '\<dt\>Dimensions\:\<\/dt\>[\s\r\n\t]*\<dd\>([^\<]+)\<'
        dimensionmatch = re.search(dimensionregex, page.text)
        if dimensionmatch:
            metadata['dimension'] = htmlparser.unescape(dimensionmatch.group(1)).strip()

            regex_2d = '^(?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) cm$'
            match_2d = re.match(regex_2d, metadata.get('dimension'))
            if match_2d:
                metadata['heightcm'] = match_2d.group('height').replace(',', '.')
                metadata['widthcm'] = match_2d.group('width').replace(',', '.')

        locationregex = '\<dt\>Location\:\<\/dt\>[\s\r\n\t]*\<dd\>\<a href\=\"[^\"]*\"\>([^\<]+)\<\/a\>\<\/dd\>'
        locationmatch = re.search(locationregex, page.text)
        if locationmatch:
            metadata['location'] = htmlparser.unescape(locationmatch.group(1)).strip()
            metadata['collectionshort'] = metadata.get('location')

            if metadata.get('location').startswith('Private collection'):
                metadata['collectionqid'] = 'Q768717'
            elif metadata.get('location') in collections:
                metadata['collectionqid'] = collections.get(metadata.get('location'))
                metadata['locationqid'] = collections.get(metadata.get('location'))

        # Build the description
        if metadata.get('collectionqid'):
            metadata['description'] = { 'ca' : 'pintura de Salvador Dalí',
                                        'en' : 'painting by Salvador Dalí',
                                        'es' : 'pintura de Salvador Dalí',
                                        'de' : 'Gemälde von Salvador Dalí',
                                        'fr' : 'peinture de Salvador Dalí',
                                        'nl' : 'schilderij van Salvador Dalí',
                                        }
        else:
            metadata['description'] = { 'ca' : 'pintura de Salvador Dalí',
                                        'en' : 'painting by Salvador Dalí (%s)' % (metadata.get('location')),
                                        'es' : 'pintura de Salvador Dalí',
                                        'de' : 'Gemälde von Salvador Dalí',
                                        'fr' : 'peinture de Salvador Dalí',
                                        'nl' : 'schilderij van Salvador Dalí',
                                        }


        metadata['mmdescription'] = 'Date: %s Technique: %s Dimensions: %s Location: %s' % (metadata.get('date'),
                                                                                            metadata.get('medium'),
                                                                                            metadata.get('dimension'),
                                                                                            metadata.get('location'),)
        yield metadata


def main():
    #repo = pywikibot.Site().data_repository()
    paintingGenerator = getDaliCatalogPaintingsGenerator()

    #for painting in paintingGenerator:
    #    print(painting)

    artDataBot = DaliPaintingDataBot(paintingGenerator, create=True)
    artDataBot.run()

    """
    with open('/tmp/dali_cat_paintings.tsv', 'w') as tsvfile:
        fieldnames = [u'Entry ID', # (your alphanumeric identifier; must be unique within the catalog)
                      u'Entry name', # (will also be used for the search in mix'n'match later)
                      u'Entry description', #
                      u'Entry type', # (short string, e.g. "person" or "location"; recommended)
                      u'Entry URL', # if omitted, it will be constructed from the URL pattern and the entry ID. Either a URL pattern or a URL column are required!
                      ]

        writer = csv.DictWriter(tsvfile, fieldnames, dialect='excel-tab')

        #No header!
        #writer.writeheader()

        for painting in paintingGenerator:
            print (painting)
            paintingdict = {'Entry ID' : painting['id'],
                            'Entry name' : painting['title'],
                            'Entry description' : painting['mmdescription'],
                            'Entry type' : painting['instanceofqid'],
                            'Entry URL': painting['url'],
                            }
            writer.writerow(paintingdict)
            #if artist[u'id'] not in belvederewd:
            #    processArtist(artist, ulanwd, gndwd, repo)
    """

if __name__ == "__main__":
    main()
