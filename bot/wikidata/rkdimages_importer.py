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


class ArtDataExpanderBot(artdatabot.ArtDataBot):
    """
    Wrapper around ArtDataBot that only expands items. Will probably refactor at some point
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.
            The dict in this generator needs to contain 'itempage' with an ItemPage object
        """
        self.generator = generator
        self.repo = pywikibot.Site().data_repository()

    def run(self):
        """
        Starts the robot.
        """
        for metadata in self.generator:
            itempage = metadata.pop('itempage', None)
            if itempage:
                metadata = super().enrichMetadata(metadata)
                super().updateArtworkItem(itempage, metadata)


class RKDImagesExpanderGenerator():
    """
    A generator for data from RKDimages
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields ItemPage objects.
        """
        self.generator = generator
        self.rkd_artists = self.get_rkd_artists()
        self.repo = pywikibot.Site().data_repository()
        self.object_types = {'painting': {'qid': 'Q3305213',
                                          'labels': {'en': 'painting',
                                                     'nl': 'schilderij',
                                                     'de': 'Gemälde',
                                                     'fr': 'peinture',
                                                     }
                                          },
                             'drawing': {'qid': 'Q93184',
                                         'labels': {'en': 'drawing', 'nl': 'tekening'}
                                         },
                             }
        self.connector_word = {'nl': 'van', 'en': 'by', 'de': 'von', 'fr': 'de'}
        self.creator_qualifiers = {'test1234': {}, } # TODO: Implement
        self.mediums = {'canvas, oil paint': 'oil on canvas',
                        'panel, oil paint': 'oil on panel',
                        'panel (oak), oil paint': 'oil on oak panel',
                        'panel (lime), oil paint': 'oil on lime panel',
                        'copper, oil paint': 'oil on copper',
                        'panel (poplar), oil paint': 'oil on poplar panel',
                        'paper, aquarel paint (watercolor)': 'watercolor on paper',
                        'cardboard, oil paint': 'oil on cardboard',
                        }

    def get_rkd_artists(self):
        """
        Make a lookup table for RKDartists
        :return: The lookup table as a dict
        """
        result = {}
        query = """SELECT ?item ?id WHERE { ?item wdt:P650 ?id }"""
        sq = pywikibot.data.sparql.SparqlQuery()
        query_result = sq.select(query)

        for result_item in query_result:
            qid = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
            result[result_item.get('id')] = qid
        return result

    def __iter__(self):
        """
        Loop over the items in the generator, get more metadata and return the result
        :param generator: itempages with and RKDimages link
        :yield: Tuple to be processed
        """

        for itempage in self.generator:
            pywikibot.output('Working on %s' % (itempage.title(),))

            if not itempage.exists():
                pywikibot.output('Item does not exist, skipping')
                continue

            data = itempage.get()
            claims = data.get('claims')

            # Do some checks so we are sure we found exactly one inventory number and one collection
            if 'P350' not in claims:
                pywikibot.output('No RKDimages found, skipping')
                continue

            rkdimagesid = claims.get(u'P350')[0].getTarget()
            metadata = self.get_rkdimage_metadata(rkdimagesid)
            if metadata:
                metadata['itempage'] = itempage
                yield metadata

    def get_rkdimage_metadata(self, rkdimagesid):
        """
        :param rkdimagesid:
        :return:
        """
        # Force to English for consistent output
        rkdimages_url = 'https://api.rkd.nl/api/record/images/%s?format=json&language=en' % (rkdimagesid,)
        refurl = 'https://rkd.nl/explore/images/%s' % (rkdimagesid,)

        # Do some checking if it actually exists?
        rkdimages_page = requests.get(rkdimages_url)
        try:
            rkdimages_json = rkdimages_page.json()
        except ValueError: # Throws simplejson.errors.JSONDecodeError
            pywikibot.output('Got invalid json for%s, skipping' % (rkdimagesid,))
            return None

        if rkdimages_json.get('content') and rkdimages_json.get('content').get('message'):
            pywikibot.output(u'Something went wrong, got "%s" for %s, skipping' % (rkdimages_json.get('content').get('message'),
                                                                                   rkdimagesid))
            return None

        rkdimages_docs = rkdimages_json.get(u'response').get(u'docs')[0]

        metadata = {}
        metadata['refurl'] = refurl

        metadata.update(self.get_instance_of(rkdimages_docs))
        metadata.update(self.get_title(rkdimages_docs))
        metadata.update(self.get_creator(rkdimages_docs))
        metadata.update(self.get_description(metadata))
        metadata.update(self.get_medium(rkdimages_docs))
        metadata.update(self.get_genre(rkdimages_docs))

        return metadata

    def get_instance_of(self, rkdimages_docs):
        """
        :param rkdimages_docs:
        :return:
        """
        metadata = {}
        if rkdimages_docs.get('objectcategorie') and len(rkdimages_docs.get('objectcategorie'))==1:
            object_type = rkdimages_docs.get('objectcategorie')[0]
            if object_type in self.object_types:
                metadata['instanceofqid'] = self.object_types.get(object_type).get('qid')
                metadata['instanceofnames'] = self.object_types.get(object_type).get('labels')
        return metadata

    def get_title(self, rkdimages_docs):
        """
        Get the title in Dutch and English
        :param rkdimages_docs: The metadata from RKDimages
        :return: Dict
        """
        metadata = {}
        nl_title = None
        en_title = None

        if rkdimages_docs.get('benaming_kunstwerk') and rkdimages_docs.get('benaming_kunstwerk')[0]:
            nl_title = rkdimages_docs.get('benaming_kunstwerk')[0]
        if rkdimages_docs.get('titel_engels'):
            en_title = rkdimages_docs.get('titel_engels')

        if nl_title or en_title:
            metadata['title'] = {}
            if nl_title:
                metadata['title']['nl'] = nl_title
            if en_title:
                metadata['title']['en'] = en_title

        return metadata

    def get_creator(self, rkdimages_docs):
        """
        Get the (sometimes uncertain) creator of the work
        :param rkdimages_docs: The metadata from RKDimages
        :return: Dict
        """
        metadata = {}
        if rkdimages_docs.get('toeschrijving') and len(rkdimages_docs.get('toeschrijving')) == 1:
            toeschrijving = rkdimages_docs.get('toeschrijving')[0]
            print (toeschrijving)
            toeschrijving.pop('opmerking_toeschrijving', None)
            if toeschrijving.get('status') and toeschrijving.get('status') == 'huidig':
                if toeschrijving.get('naam') and toeschrijving.get('naam') == 'Anoniem':
                    metadata['creatorqid'] = 'Q4233718'
                elif len(toeschrijving.keys()) == 4 and toeschrijving.get('naam') and \
                        toeschrijving.get('naam_linkref') and toeschrijving.get('naam_inverted'):
                    if toeschrijving.get('naam_linkref') in self.rkd_artists:
                        metadata['creatorqid'] = self.rkd_artists.get(toeschrijving.get('naam_linkref'))
                    metadata['creatorname'] = toeschrijving.get('naam_inverted')

                elif len(toeschrijving.keys())==7 and toeschrijving.get('naam') and toeschrijving.get('naam_linkref') \
                        and toeschrijving.get('naam_inverted') and toeschrijving.get('kwalificatie_en') and \
                        toeschrijving.get('kwalificatie') and toeschrijving.get('kwalificatie_linkref'):
                        metadata['uncertaincreatorname'] = toeschrijving.get('naam_inverted')
                        creator_qualifier = toeschrijving.get('kwalificatie_en')
                        if creator_qualifier in self.creator_qualifiers:
                            metadata['creatorqualifierpid'] = self.creator_qualifiers.get(creator_qualifier).get('pid')
                            metadata['creatorqualifiernames'] = self.creator_qualifiers.get(creator_qualifier).get('labels')
                        else:
                            metadata['creatorqualifiernames'] = {'en': creator_qualifier, }
                        # Always set the Dutch description to how it set at the source
                        metadata['creatorqualifiernames']['nl'] = toeschrijving.get('kwalificatie')
                        if toeschrijving.get('naam_linkref') in self.rkd_artists:
                            metadata['uncertaincreatorqid'] = self.rkd_artists.get(toeschrijving.get('naam_linkref'))
                        #if toeschrijving.get('kwalificatie_en') == 'after' and toeschrijving.get('kwalificatie') == 'naar':
                        #    metadata['description'] = { 'nl' : 'schilderij naar %s' % (metadata.get('creatorname'),),
                        #                                'en' : 'painting after %s' % (metadata.get('creatorname'),),
                        #                            }


        return metadata

    def get_description(self, input_metadata):
        """

        :param rkdimages_docs:
        :return:
        """
        metadata = {}
        if not input_metadata.get('instanceofnames'):
            return metadata
        if input_metadata.get('creatorname'):
            metadata['description'] = {}
            creatorname = input_metadata.get('creatorname')
            for lang in input_metadata.get('instanceofnames'):
                if lang in self.connector_word:
                    object_type = input_metadata.get('instanceofnames').get(lang)
                    connector_word = self.connector_word.get(lang)
                    metadata['description'][lang] = '%s %s %s' % (object_type, connector_word, creatorname)
        elif input_metadata.get('uncertaincreatorname') and input_metadata.get('creatorqualifiernames'):
            metadata['description'] = {}
            creatorname = input_metadata.get('uncertaincreatorname')
            for lang in input_metadata.get('instanceofnames'):
                if lang in input_metadata.get('creatorqualifiernames'):
                    object_type = input_metadata.get('instanceofnames').get(lang)
                    connector_word = input_metadata.get('creatorqualifiernames').get(lang)
                    metadata['description'][lang] = '%s %s %s' % (object_type, connector_word, creatorname)
        return metadata

    def get_medium(self, rkdimages_docs):
        """

        :param rkdimages_docs:
        :return:
        """
        metadata = {}
        if rkdimages_docs.get('virtualFields') and rkdimages_docs.get('virtualFields').get('drager_techniek'):
            medium = rkdimages_docs.get('virtualFields').get('drager_techniek').get('contents')
            if medium:  # Sometimes it's just empty
                if medium in self.mediums:
                    medium = self.mediums.get(medium)
                metadata['medium'] = medium
        return metadata

    def get_genre(self, rkdimages_docs):
        """

        :param rkdimages_docs:
        :return:
        """
        metadata = {}
        return metadata



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

    dryrun = False
    create = False
    source = False
    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg=='-create':
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
        query = """SELECT DISTINCT ?item WHERE {
  ?item wdt:P350 ?value.
  MINUS {
    ?item wdt:P170 []
  }
}
LIMIT 10000"""
        query2 = """SELECT ?item WHERE {
  ?item wdt:P350 ?id ;
        p:P170 ?creatorstatement .
    FILTER NOT EXISTS { ?creatorstatement prov:wasDerivedFrom ?derivedFrom .}
} LIMIT 10"""
        query = """SELECT ?item WHERE {
  ?item wdt:P350 ?id ;
        p:P31 ?statement .
    FILTER NOT EXISTS { ?statement prov:wasDerivedFrom ?derivedFrom .}
} LIMIT 10000"""
        generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    metadata_generator = RKDImagesExpanderGenerator(generator)
    #metadata_generator.run()

    if dryrun:
        for metadata in metadata_generator:
            print(metadata)
    else:
        art_data_expander_bot = ArtDataExpanderBot(metadata_generator)
        art_data_expander_bot.run()

if __name__ == "__main__":
    main()
