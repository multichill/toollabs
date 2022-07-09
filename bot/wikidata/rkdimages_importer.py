#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import missing data from RKDimages ( https://rkd.nl/en/explore/images/ )

This is a fork of the RKDartists importer.

First it does a (SPARQL) query to find wikidata items that miss something relevant.
Bot will try to find the missing info

This should make https://www.wikidata.org/wiki/Wikidata:Database_reports/Constraint_violations/P350 shorter

"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import requests
import re
import datetime
import time
import artdatabot


class RKDImagesImporterBot(artdatabot.ArtDataBot):
    """
    A bot to enrich humans on Wikidata
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields ItemPage objects.

        """
        self.generator = generator
        self.rkd_artists = self.get_rkd_artists()
        self.artwork_metadata_generator = self.get_artwork_metadata_generator(generator)
        self.repo = pywikibot.Site().data_repository()

    def get_rkd_artists(self):
        """
        Make a lookup table for RKDartists
        :return:
        """
        result = {}
        query = """SELECT ?item ?id WHERE { ?item wdt:P650 ?id }"""
        sq = pywikibot.data.sparql.SparqlQuery()
        query_result = sq.select(query)

        for result_item in query_result:
            qid = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
            result[result_item.get('id')] = qid
        return result

    def get_artwork_metadata_generator(self, generator):
        """
        Loop over the items in the generator, get more metadata and return the result
        :param generator: itempages with and RKDimages link
        :yield: Tuple to be processed
        """
        for itempage in generator:
            pywikibot.output('Working on %s' % (itempage.title(),))

            if not itempage.exists():
                pywikibot.output(u'Item does not exist, skipping')
                continue

            data = itempage.get()
            claims = data.get('claims')

            # Do some checks so we are sure we found exactly one inventory number and one collection
            if 'P350' not in claims:
                pywikibot.output(u'No RKDimages found, skipping')
                continue

            rkdimagesid = claims.get(u'P350')[0].getTarget()
            metadata = self.get_rkdimage_metadata(rkdimagesid)
            if metadata:
                yield itempage, metadata

    def get_rkdimage_metadata(self, rkdimagesid):
        """
        :param rkdimagesid:
        :return:
        """
        rkdimages_url = 'https://api.rkd.nl/api/record/images/%s?format=json' % (rkdimagesid,)
        refurl = 'https://rkd.nl/explore/images/%s' % (rkdimagesid,)

        # Do some checking if it actually exists?
        rkdimages_page = requests.get(rkdimages_url)
        rkdimages_json = rkdimages_page.json()

        if rkdimages_json.get('content') and rkdimages_json.get('content').get('message'):
            pywikibot.output(u'Something went wrong, got "%s" for %s, skipping' % (rkdimages_json.get('content').get('message'),
                                                                                   rkdimagesid))
            return None

        rkdimages_docs = rkdimages_json.get(u'response').get(u'docs')[0]

        metadata = {}
        metadata['refurl'] = refurl
        metadata['title'] = {}

        if rkdimages_docs.get('benaming_kunstwerk') and rkdimages_docs.get('benaming_kunstwerk')[0]:
            metadata['title']['nl'] = rkdimages_docs.get('benaming_kunstwerk')[0]
        if rkdimages_docs.get('titel_engels'):
            metadata['title']['en'] = rkdimages_docs.get('titel_engels')

        if rkdimages_docs.get('toeschrijving') and len(rkdimages_docs.get('toeschrijving')) == 1 and rkdimages_docs.get('toeschrijving')[0]:
            toeschrijving = rkdimages_docs.get('toeschrijving')[0]
            print (toeschrijving)
            toeschrijving.pop('opmerking_toeschrijving', None)
            if toeschrijving.get('status') and toeschrijving.get('status')=='huidig':
                if toeschrijving.get('naam') and toeschrijving.get('naam')=='Anoniem':
                    metadata['creatorqid'] = 'Q4233718'
                elif len(toeschrijving.keys())==4 and toeschrijving.get('naam') and \
                        toeschrijving.get('naam_linkref') and toeschrijving.get('naam_inverted'):
                    if toeschrijving.get('naam_linkref') in self.rkd_artists:
                        metadata['creatorqid'] = self.rkd_artists.get(toeschrijving.get('naam_linkref'))
                    metadata['creatorname'] = toeschrijving.get('naam_inverted')
                    metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                                'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                                'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'),),
                                                'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'),),
                                                }
                elif len(toeschrijving.keys())==7 and toeschrijving.get('naam') and toeschrijving.get('naam_linkref') \
                        and toeschrijving.get('naam_inverted') and toeschrijving.get('kwalificatie_en') and \
                        toeschrijving.get('kwalificatie') and toeschrijving.get('kwalificatie_linkref'):
                        metadata['creatorname'] = toeschrijving.get('naam_inverted')
                        if toeschrijving.get('naam_linkref') in self.rkd_artists:
                            metadata['uncertaincreatorqid'] = self.rkd_artists.get(toeschrijving.get('naam_linkref'))
                        if toeschrijving.get('kwalificatie_en') == 'after' and toeschrijving.get('kwalificatie') == 'naar':
                            metadata['description'] = { 'nl' : 'schilderij naar %s' % (metadata.get('creatorname'),),
                                                        'en' : 'painting after %s' % (metadata.get('creatorname'),),
                                                    }





        print (metadata)

        return metadata

    def run(self):
        """
        Starts the robot.
        """
        for itempage, metadata in self.artwork_metadata_generator:
            metadata = super().enrichMetadata(metadata)
            super().updateArtworkItem(itempage, metadata)


    def isRemovableSource(self, source):
        """
        Will return the source claim if the source is imported from and nothing else
        :param source: The source
        :return:
        """
        if not len(source)==1:
            return False
        if not u'P143' in source:
            return False
        return source.get('P143')[0]


def main(*args):
    """
    Main function. Grab a generator and pass it to the bot to work on
    """
    create = False
    source = False
    for arg in pywikibot.handle_args(args):
        if arg=='-create':
            create = True
        elif arg=='-source':
            source = True

    repo = pywikibot.Site().data_repository()
    if create:
        # Not implemented yet
        return
        pywikibot.output(u'Going to create new artworks!')
        rkdArtistsCreatorBot = RKDArtistsCreatorBot()
        generator = rkdArtistsCreatorBot.run()
    elif source:
        # Not implemented yet
        return
        pywikibot.output(u'Going to try to expand and source existing artworks')

        query = u"""SELECT DISTINCT ?item {
        {
            ?item wdt:P650 [].
            ?item wdt:P31 wd:Q5 . # Needs to be human
          MINUS {
            # Has sourced gender
            ?item p:P21 ?genderclaim .
            FILTER EXISTS {
              ?genderclaim prov:wasDerivedFrom ?provenance .
              MINUS { ?provenance pr:P143 [] }
              }
            # Has occupation
            ?item wdt:P106 [] .
            # Has sourced date of birth
            ?item p:P569 ?birthclaim .
            FILTER EXISTS {
              ?birthclaim prov:wasDerivedFrom ?provenance .
              MINUS { ?provenance pr:P143 [] }
              }
          }
        } UNION {
          ?item wdt:P650 [] .
          ?item p:P569 ?birthclaim .
          MINUS { ?item p:P27 [] } # No country of citizenship
          ?birthclaim ps:P569 ?birth .
          FILTER(?birth > "+1900-00-00T00:00:00Z"^^xsd:dateTime) .
        } UNION {
          ?item wdt:P650 [] .
          ?item p:P569 ?birthclaim .
          # Has sourced date of death
          MINUS {
            ?item p:P570 ?deathclaim .
            FILTER EXISTS {
              ?deathclaim prov:wasDerivedFrom ?provenance .
              MINUS { ?provenance pr:P143 [] }
              }
          }
          ?birthclaim ps:P569 ?birth .
          FILTER(?birth < "+1900-00-15T00:00:00Z"^^xsd:dateTime)
        }
        }"""
        generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))
    else:
        pywikibot.output(u'Going to try to expand existing artworks')

        query = u"""SELECT DISTINCT ?item {
            ?item wdt:P350 [] .
            #?item wdt:P31 wd:Q5 . # Needs to be human
            MINUS { ?item wdt:P1257 [] . # No Iconclass
                    #?item wdt:P106 [] . # No occupation
                    #?item wdt:P569 [] . # No date of birth
                   } 
            }"""
        query = """SELECT DISTINCT ?item WHERE {
  ?item wdt:P350 ?value.
  MINUS {
    ?item rdfs:label ?enlabel.
    FILTER((LANG(?enlabel)) = "en")
    ?item rdfs:label ?nllabel.
    FILTER((LANG(?nllabel)) = "nl")    
  }
}
LIMIT 100000"""
        query2 = """SELECT DISTINCT ?item WHERE {
  ?item wdt:P350 ?value.
  MINUS {
    ?item wdt:P170 []
  }
}
LIMIT 10000"""
        generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    rkd_images_importer_bot = RKDImagesImporterBot(generator)
    rkd_images_importer_bot.run()

if __name__ == "__main__":
    main()
