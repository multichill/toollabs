#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to get all the paintings in the Piet Mondri(a)an catalog matched with Wikidata.

See http://pietmondrian.rkdmonographs.nl/sitemap for the paintings.

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

class MondrianArtDataBot(artdatabot.ArtDataBot):
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

        self.idProperty = 'P350'
        self.artworkIds = self.fillCache()

    def fillCache(self):
        """
        Build an ID cache so we can quickly look up the id's for property
        """
        result = {}
        query = """SELECT ?item ?id WHERE {
  ?item p:P170/ps:P170 wd:Q151803;
    wdt:P350 ?id.
}"""
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

        ## Make a backup to the Wayback Machine when we have to wait anyway
        #self.doWaybackup(metadata)

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

def getMondrianCatalogArtworkGenerator():
    """
    Generator to get the paintings from http://pietmondrian.rkdmonographs.nl/sitemap

    :return:
    """
    htmlparser = HTMLParser()
    session = requests.Session()

    sitemapurl = 'http://pietmondrian.rkdmonographs.nl/sitemap'
    pageurlregex = '\<a href\=\"(http\:\/\/pietmondrian\.rkdmonographs\.nl\/[^\"]+\da?)\"[\r\n\s\t]*class\=\"state-published\"'

    sitemap = session.get(sitemapurl)

    pageurlmatches = re.finditer(pageurlregex, sitemap.text)

    allurls = []

    for pageurlmatch in pageurlmatches:
        allurls.append(pageurlmatch.group(1))
    allurls.append('http://pietmondrian.rkdmonographs.nl/additions')

    seenurl = []

    for pageurl in allurls:
        if pageurl in seenurl:
            continue
        seenurl.append(pageurl)
        print(pageurl)

        searchpage = session.get(pageurl)

        simpleitemregex = 'addthis\:url\=\"%s\/#(?P<id>\d+)\"\>' % (pageurl,)
        longitemregex = simpleitemregex + '\<div class\=\"visualClear\"\>\<\/div\>\<a class\=\"addthis_button_facebook\"\>\<\/a\>\<a class\=\"addthis_button_twitter\"\>\<\/a\>\<a class\=\"addthis_button_linkedin\"\>\<\/a\>\<\/div\>\<\/div\>\<\/td\>\<td\/\>\<td valign\=\"top\" align\=\"left\"\>\<br\/\>\s*(?P<artist>[^\<]+)\<br\/\>\<b\>(?P<title>[^\<]+)\<\/b\>\s*(?P<date>[^\<]+)\<br\/\>(?P<medium>[^\<]+)\<br\/\>(?P<signed>[^\<]+\<i\>[^\<]+\<\/i\>\<br\/\>)?((?P<provenance>[^\<]+)\<br\/\>)?\<br\/\>(?P<catalogcode>[^\<]+)\<\/td\>\<\/tr\>'

        simpleitemurlmatches = re.finditer(simpleitemregex, searchpage.text)
        longitemurlmatches = re.finditer(longitemregex, searchpage.text, re.DOTALL)

        simplerkdid = []
        longrkdid = []

        for itemurlmatch in simpleitemurlmatches:
            simplerkdid.append(itemurlmatch.group('id'))


        for itemurlmatch in longitemurlmatches:
            rkdid = itemurlmatch.group('id')
            longrkdid.append(rkdid)
            metadata = {}
            metadata['instanceofqid'] = 'Q838948' # Artwork, will overwrite
            metadata['creatorname'] = 'Piet Mondrian'
            metadata['creatorqid'] = 'Q151803'
            metadata['artworkidpid'] = metadata['idpid'] = 'P350'
            metadata['artworkid'] = metadata['id'] = '%s' % (rkdid,)
            metadata['url'] = 'https://rkd.nl/explore/images/%s' % (rkdid,)
            metadata['refurl'] = '%s/#%s' % (pageurl, rkdid)

            artist = htmlparser.unescape(itemurlmatch.group('artist')).strip().replace('\xa0', ' ').replace('\n', '').replace('\t', '').replace('   ', ' ')
            title = htmlparser.unescape(itemurlmatch.group('title')).strip().replace('\n', '').replace('\t', '').replace('   ', ' ')
            metadata['mmtitle'] = title
            metadata['title'] = { 'en' : title, }
            date = htmlparser.unescape(itemurlmatch.group('date')).strip().replace('\n', '').replace('\t', '').replace('   ', ' ')
            metadata['date'] = date

            # TODO: Add date logic here
            # Try to extract the date
            dateregex = '^(dated\s*)?(?P<date>\d\d\d\d)$'
            datecircaregex = '^c\.\s*(\d\d\d\d)$'
            periodregex = '^(\d\d\d\d)-(\d\d\d\d)$'
            circaperiodregex = '^c\.\s*(\d\d\d\d)-(\d\d\d\d)$'

            datematch = re.match(dateregex, metadata.get('date'))
            datecircamatch = re.match(datecircaregex, metadata.get('date'))
            periodmatch = re.match(periodregex, metadata.get('date'))
            circaperiodmatch = re.match(circaperiodregex, metadata.get('date'))

            if datematch:
                metadata['inception'] = int(datematch.group('date'))
            elif datecircamatch:
                metadata['inception'] = int(datecircamatch.group(1))
                metadata['inceptioncirca'] = True
            elif periodmatch:
                metadata['inceptionstart'] = int(periodmatch.group(1),)
                metadata['inceptionend'] = int(periodmatch.group(2),)
            elif circaperiodmatch:
                metadata['inceptionstart'] = int(circaperiodmatch.group(1),)
                metadata['inceptionend'] = int(circaperiodmatch.group(2),)
                metadata['inceptioncirca'] = True
            else:
                print (u'Could not parse date: "%s"' % (metadata.get('date'),))

            medium = htmlparser.unescape(itemurlmatch.group('medium')).strip().replace('\xa0', ' ').replace('\n', '').replace('\t', '').replace('   ', ' ')

            if 'oil' in medium and 'canvas' in medium:
                metadata['instanceofqid'] = 'Q3305213'
                metadata['medium'] = 'oil on canvas'

            rkdapipage = session.get('https://api.rkd.nl/api/record/images/%s?format=json' % (rkdid,))
            rkddata = rkdapipage.json()

            objectcategorie = rkddata.get('response').get('docs')[0].get('objectcategorie')[0]
            #import json
            #print (json.dumps(rkddata.get('response').get('docs')[0], indent = 2, separators=(',', ': '), sort_keys=True))

            print (objectcategorie)

            cats = { 'schilderij' : 'Q3305213',
                     'tekening' : 'Q93184',
                     'prent' : 'Q11060274',
                     'aquarel (schildering)' : 'Q18761202',
                     'olieverfschets' : 'Q3305213',
                     }
            if objectcategorie in cats:
                metadata['instanceofqid'] = cats.get(objectcategorie)

            if metadata.get('instanceofqid') == 'Q3305213':
                metadata['description'] = { 'ca' : 'pintura de Piet Mondrian',
                                            'en' : 'painting by Piet Mondrian',
                                            'es' : 'pintura de Piet Mondrian',
                                            'de' : 'Gemälde von Piet Mondrian',
                                            'fr' : 'peinture de Piet Mondrian',
                                            'nl' : 'schilderij van Piet Mondriaan',
                                            }
            elif metadata.get('instanceofqid') == 'Q93184':
                metadata['description'] = { 'en' : 'drawing by Piet Mondrian',
                                            'nl' : 'tekening van Piet Mondriaan',
                                            }
            elif metadata.get('instanceofqid') == 'Q11060274':
                metadata['description'] = { 'en' : 'print by Piet Mondrian',
                                            'nl' : 'prent van Piet Mondriaan',
                                            }
            elif metadata.get('instanceofqid') == 'Q18761202':
                metadata['description'] = { 'en' : 'watercolor painting by Piet Mondrian',
                                            'nl' : 'aquarel van Piet Mondriaan',
                                            }

            mmdescription = '%s / %s' % (artist, date)

            if itemurlmatch.group('provenance'):
                provenance = htmlparser.unescape(itemurlmatch.group('provenance')).strip().replace('\xa0', ' ').replace('\n', '').replace('\t', '').replace('   ', ' ')
                mmdescription += ' / %s' % (provenance,)

                if provenance.lower().startswith('private collection'):
                    metadata['collectionqid'] = 'Q768717'
                elif provenance.startswith('Kunstmuseum Den Haag'):
                    metadata['collectionqid'] = metadata['locationqid'] ='Q1499958'
                elif provenance.startswith('Stedelijk Museum Amsterdam'):
                    metadata['collectionqid'] = metadata['locationqid'] = 'Q924335'
                elif provenance.startswith('Solomon R. Guggenheim Museum'):
                    metadata['collectionqid'] = metadata['locationqid'] = 'Q201469'

            catalogcode = htmlparser.unescape(itemurlmatch.group('catalogcode')).strip()

            metadata['catalogcode'] = catalogcode
            metadata['catalogqid'] = 'Q50383647'

            mmdescription += ' / %s/ %s' % (medium,catalogcode,)
            metadata['mmdescription'] = mmdescription

            #mmdescription = '%s : %s / %s / %s / %s' % (artist, title, date, medium, catalogcode)

            itemurl = itemurlmatch.group('id')
            #print(mmdescription)
            yield metadata

        missedrkdid = set(simplerkdid) - set(longrkdid)
        if missedrkdid:
            print ('Missed some items on this page %s' % (pageurl,))
            print (missedrkdid)


    return


def main():
    #repo = pywikibot.Site().data_repository()
    artworkGenerator = getMondrianCatalogArtworkGenerator()

    #for artwork in artworkGenerator:
    #    print(artwork)

    artDataBot = MondrianArtDataBot(artworkGenerator, create=True)
    artDataBot.run()
    """
    with open('/tmp/mondriaan_cat_rkdimages.tsv', 'w') as tsvfile:
        fieldnames = [u'Entry ID', # (your alphanumeric identifier; must be unique within the catalog)
                      u'Entry name', # (will also be used for the search in mix'n'match later)
                      u'Entry description', #
                      u'Entry type', # (short string, e.g. "person" or "location"; recommended)
                      u'Entry URL', # if omitted, it will be constructed from the URL pattern and the entry ID. Either a URL pattern or a URL column are required!
                      ]

        writer = csv.DictWriter(tsvfile, fieldnames, dialect='excel-tab')

        #No header!
        #writer.writeheader()

        for painting in artworkGenerator:
            print (painting)
            paintingdict = {'Entry ID' : painting['id'],
                            'Entry name' : painting['mmtitle'],
                            'Entry description' : painting['mmdescription'],
                            'Entry type' : painting['instanceofqid'],
                            'Entry URL': painting['url'],
                            }
            writer.writerow(paintingdict)
    """

if __name__ == "__main__":
    main()
