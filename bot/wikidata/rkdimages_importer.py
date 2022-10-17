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
import json
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
        self.rkd_artists = self.get_id_lookup_table('P650')
        self.rkd_images = self.get_id_lookup_table('P350')
        self.repo = pywikibot.Site().data_repository()
        self.rkd_collections = self.get_collection_lookup_table()
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
        # TODO: Move to the function
        self.connector_word = {'nl': 'van', 'en': 'by', 'de': 'von', 'fr': 'de'}
        self.creator_qualifiers = {'attributed to': {'pid': 'P5102',  # nature of statement (P5102)
                                                     'labels': {'en': 'attributed to',
                                                                'nl': 'toegeschreven aan'}
                                                     },
                                   'studio of': {'pid': 'P1774',  # workshop of (P1774)
                                                 'labels': {'en': 'studio of',
                                                            'nl': 'atelier van'}
                                                 },
                                   'circle of': {'pid': 'P1776',  # circle of (P1776)
                                                 'labels': {'en': 'circle of',
                                                            'nl': 'omgeving van'}
                                                 },
                                   'follower of': {'pid': 'P1775',  # follower of (P1775)
                                                   'labels': {'en': 'follower of',
                                                              'nl': 'navolger van'}
                                                   },
                                   'school of': {'pid': 'P1780',  # school of (P1780)
                                                        'labels': {'en': 'school of',
                                                                   'nl': 'school van'}
                                                       },
                                   'possibly': {'pid': 'P1779',  # possible creator (P1779)
                                                'labels': {'en': 'possibly',
                                                           'nl': 'mogelijk'}
                                                },
                                   'manner of': {'pid': 'P1777',  # manner of (P1777)
                                                 'labels': {'en': 'manner of',
                                                            'nl': 'trant van'}
                                                 },
                                   'manner of/after': {'pid': 'P1777',  # manner of (P1777)
                                                       'labels': {'en': 'manner of/after',
                                                                  'nl': 'trant/naar'}
                                                       },
                                   'after': {'pid': 'P1877',  # after a work by (P1877)
                                             'labels': {'en': 'after',
                                                        'nl': 'naar'}
                                             },
                                   'free after': {'pid': 'P1877',  # after a work by (P1877)
                                                  'labels': {'en': 'free after',
                                                             'nl': 'vrij naar'}
                                                  },
                                   'P1778 forgery': {'pid' : 'P1778',  # forgery after (P1778)
                                                     'labels': {'en': '',
                                                                'nl': ''}
                                                     },
                                   }

    def get_id_lookup_table(self, id_property):
        """
        Make a lookup table for provided id property
        :param id_property: String like P350
        :return: The lookup table as a dict
        """
        result = {}
        query = """SELECT ?item ?id WHERE { ?item wdt:%s ?id }""" % (id_property,)
        sq = pywikibot.data.sparql.SparqlQuery()
        query_result = sq.select(query)

        for result_item in query_result:
            qid = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
            result[result_item.get('id')] = qid
        return result

    def get_collection_lookup_table(self):
        """
        Use config at https://www.wikidata.org/wiki/User:BotMultichillT/rkdimages_collections.js for lookup table
        :return: The lookup table as a dict
        """
        result = {}
        configpage = pywikibot.Page(self.repo, title='User:BotMultichillT/rkdimages collections.js')
        (comments, sep, jsondata) = configpage.get().partition('[')
        jsondata = '[' + jsondata
        configjson = json.loads(jsondata)
        for collection_info in configjson:
            if collection_info.get('collectienaam') and not collection_info.get('skip_collection'):
                if collection_info.get('use_collection'):
                    result[collection_info.get('collectienaam')] = collection_info.get('use_collection')
                else:
                    result[collection_info.get('collectienaam')] = collection_info.get('qid')
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

            rkdimagesid = None
            for claim in claims.get('P350'):
                if claim.getRank() == 'preferred':
                    rkdimagesid = claim.getTarget()
                    break  # It's preferred, so we'll take it
                elif claim.getRank() == 'normal':
                    rkdimagesid = claim.getTarget()

            if rkdimagesid:
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

        metadata = {'refurl': refurl}

        metadata.update(self.get_instance_of(rkdimages_docs))
        metadata.update(self.get_title(rkdimages_docs))
        metadata.update(self.get_creator(rkdimages_docs))
        metadata.update(self.get_description(metadata))
        metadata.update(self.get_medium(rkdimages_docs))
        metadata.update(self.get_inception(rkdimages_docs))
        metadata.update(self.get_genre(rkdimages_docs))
        metadata.update(self.get_part_of_related(rkdimages_docs))
        metadata.update(self.get_dimensions(rkdimages_docs))
        metadata.update(self.get_collections(rkdimages_docs))

        # Format?
        # Depicts?
        # Main subject?
        # Could add the shape rectangle (portrait format)

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
        one_attribution = False
        if rkdimages_docs.get('toeschrijving') and len(rkdimages_docs.get('toeschrijving')) == 1:
            toeschrijving = rkdimages_docs.get('toeschrijving')[0]
            if toeschrijving.get('status') and toeschrijving.get('status') == 'huidig':
                one_attribution = True
        elif rkdimages_docs.get('toeschrijving') and len(rkdimages_docs.get('toeschrijving')) == 2:
            toeschrijving = rkdimages_docs.get('toeschrijving')[0]
            toeschrijving2 = rkdimages_docs.get('toeschrijving')[1]
            toeschrijving.pop('opmerking_toeschrijving', None)
            if toeschrijving.get('status') and toeschrijving.get('status') == 'huidig':
                if toeschrijving2.get('status') and toeschrijving2.get('status') == 'huidig':
                    return metadata
                elif toeschrijving2.get('status') and toeschrijving2.get('status') == 'verworpen':
                    one_attribution = True

        if one_attribution:
            toeschrijving.pop('opmerking_toeschrijving', None)
            toeschrijving.pop('datum_toeschrijving', None)
            toeschrijving.pop('bron', None)
            toeschrijving.pop('bron_linkref', None)
            toeschrijving.pop('naam_engels', None) # Not using this one anyway
            if toeschrijving.get('naam') and toeschrijving.get('naam') == 'Anoniem':
                metadata['creatorqid'] = 'Q4233718'
            elif len(toeschrijving.keys()) == 4 and toeschrijving.get('naam') and \
                    toeschrijving.get('naam_linkref') and toeschrijving.get('naam_inverted'):
                if toeschrijving.get('naam_linkref') in self.rkd_artists:
                    metadata['creatorqid'] = self.rkd_artists.get(toeschrijving.get('naam_linkref'))
                metadata['creatorname'] = toeschrijving.get('naam_inverted')

            elif len(toeschrijving.keys()) == 7 and toeschrijving.get('naam') and toeschrijving.get('naam_linkref') \
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
        # TODO: Implement logic for more than 1 line
        return metadata

    def get_description(self, input_metadata):
        """
        Make descriptions based on the type of work and creator
        :param input_metadata: Metadata to base the descriptions on
        :return: Dict with the descriptions
        """
        metadata = {}
        if not input_metadata.get('instanceofnames'):
            return {}
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
        Get the medium
        :param rkdimages_docs:
        :return:
        """
        metadata = {}
        mediums = {'canvas, oil paint': 'oil on canvas',
                   'panel, oil paint': 'oil on panel',
                   'panel (lime), oil paint': 'oil on lime panel',
                   'panel (oak), oil paint': 'oil on oak panel',
                   'panel (pine), oil paint' : 'oil on pine panel',
                   'panel (poplar), oil paint': 'oil on poplar panel',
                   'copper, oil paint': 'oil on copper',
                   'paper, oil paint' : 'oil on paper',
                   'paper, aquarel paint (watercolor)': 'watercolor on paper',
                   'paper, watercolor': 'watercolor on paper',
                   'cardboard, oil paint': 'oil on cardboard',
                   'panel (mahogany), oil paint': 'oil on mahogany panel',
                   'panel, tempera': 'tempera on panel',
                   'paper, black chalk': 'black chalk on paper',
                   'canvas on panel, oil paint': 'oil on canvas on panel',
                   'paper on panel, oil paint': 'oil on paper on panel',
                   'cardboard on panel, oil paint': 'oil on cardboard on panel',
                   'copper on panel, oil paint': 'oil paint on copper on panel',
                   'canvas on cardboard, oil paint': 'oil on canvas on cardboard',
                   'paper on cardboard, oil paint': 'oil on paper on cardboard',
                   'canvas on panel, tempera': 'tempera on canvas on panel',
                   }

        paint_surfaces = {'canvas': 'paint on canvas',
                          'panel': 'paint on panel',
                          'panel (lime)': 'paint on lime panel',
                          'panel (oak)': 'paint on oak panel',
                          'panel (poplar)': 'paint on poplar panel',
                          }

        if rkdimages_docs.get('virtualFields') and rkdimages_docs.get('virtualFields').get('drager_techniek'):
            medium = rkdimages_docs.get('virtualFields').get('drager_techniek').get('contents')
            if medium:  # Sometimes it's just empty
                if medium in mediums:
                    medium = mediums.get(medium)
                elif medium in paint_surfaces:
                    if rkdimages_docs.get('objectcategorie') and len(rkdimages_docs.get('objectcategorie')) == 1:
                        object_type = rkdimages_docs.get('objectcategorie')[0]
                        if object_type == 'painting':
                            medium = paint_surfaces.get(medium)
                elif ',' in medium:
                    (surface, sep, paint) = medium.partition(',')
                    medium = '%s on %s' % (paint.strip(), surface.strip())
                metadata['medium'] = medium
        return metadata

    def get_inception(self, rkdimages_docs):
        """
        Get the inception. Try to parse the text if it's available
        :param rkdimages_docs: The metadata from RKDimages
        :return:
        """
        metadata = {}
        earliest_date = rkdimages_docs.get('zoekmarge_begindatum')
        latest_date = rkdimages_docs.get('zoekmarge_einddatum')
        if not earliest_date or not latest_date:
            return {}
        if rkdimages_docs.get('datering'):
            date = rkdimages_docs.get('datering')[0]

            year_regex = '^(\d\d\d\d)(\s*gedateerd)?$'
            date_circa_regex = '^ca?\.\s*(\d\d\d\d)$'
            period_regex = '^(\d\d\d\d)[-–\/](\d\d\d\d)$'
            circa_period_regex = '^ca?\.\s*(\d\d\d\d)[-–\/](\d\d\d\d)$'
            short_period_regex = '^(\d\d)(\d\d)[-–\/](\d\d)$'
            circa_short_period_regex = '^ca?\.\s*(\d\d)(\d\d)[-–\/](\d\d)$'

            year_match = re.match(year_regex, date)
            date_circa_match = re.match(date_circa_regex, date)
            period_match = re.match(period_regex, date)
            circa_period_match = re.match(circa_period_regex, date)
            short_period_match = re.match(short_period_regex, date)
            circa_short_period_match = re.match(circa_short_period_regex, date)

            if year_match:
                # Don't worry about cleaning up here.
                metadata['inception'] = int(year_match.group(1))
            elif date_circa_match:
                metadata['inception'] = int(date_circa_match.group(1))
                metadata['inceptioncirca'] = True
            elif period_match:
                metadata['inceptionstart'] = int(period_match.group(1),)
                metadata['inceptionend'] = int(period_match.group(2),)
            elif circa_period_match:
                metadata['inceptionstart'] = int(circa_period_match.group(1),)
                metadata['inceptionend'] = int(circa_period_match.group(2),)
                metadata['inceptioncirca'] = True
            elif short_period_match:
                metadata['inceptionstart'] = int('%s%s' % (short_period_match.group(1), short_period_match.group(2), ))
                metadata['inceptionend'] = int('%s%s' % (short_period_match.group(1), short_period_match.group(3), ))
            elif circa_short_period_match:
                metadata['inceptionstart'] = int('%s%s' % (circa_short_period_match.group(1), circa_short_period_match.group(2), ))
                metadata['inceptionend'] = int('%s%s' % (circa_short_period_match.group(1), circa_short_period_match.group(3), ))
                metadata['inceptioncirca'] = True
            else:
                print('Could not parse date: "%s". Using %s to %s' % (date, earliest_date, latest_date))
                if earliest_date.isdecimal() and latest_date.isdecimal():
                    metadata['inceptionstart'] = int(earliest_date)
                    metadata['inceptionend'] = int(latest_date)
        else:
            if earliest_date.isdecimal() and earliest_date == latest_date:
                metadata['inception'] = int(earliest_date)
            elif earliest_date.isdecimal() and latest_date.isdecimal():
                metadata['inceptionstart'] = int(earliest_date)
                metadata['inceptionend'] = int(latest_date)
        return metadata

    def get_genre(self, rkdimages_docs):
        """

        :param rkdimages_docs:
        :return:
        """
        metadata = {}
        genres = {'allegory': 'Q2839016',  # allegory (Q2839016)
                  'animal painting (genre)': 'Q16875712',  # animal art (Q16875712)
                  'architecture (genre)': 'Q18353841',  # architectural painting (Q18353841)
                  'cityscape': 'Q1935974',  # cityscape (Q1935974)
                  'genre': 'Q1047337',  # genre art (Q1047337)
                  'landscape (as genre)': 'Q191163',  # landscape art (Q191163)
                  'marine (as genre)': 'Q158607',  # marine art (Q158607)
                  'portrait': 'Q134307',  # portrait (Q134307)
                  'still life': 'Q170571',  # still life (Q170571)
                  'abstraction': 'Q128115'  # abstract art (Q128115)
                  }
        if rkdimages_docs.get('genre') and len(rkdimages_docs.get('genre')) == 1:
            genre = rkdimages_docs.get('genre')[0]
            first_keyword = None
            if rkdimages_docs.get('RKD_algemene_trefwoorden'):
                first_keyword = rkdimages_docs.get('RKD_algemene_trefwoorden')[0]
            if genre:
                if genre in ['history (as a genre)', 'history (genre)'] and first_keyword:
                    if first_keyword in ['Old Testament and Apocrypha', 'New Testament and Apocrypha']:
                        metadata['genreqid'] = 'Q2864737'  # religious art (Q2864737)
                        metadata['religionqid'] = 'Q5043'  # Christianity (Q5043)
                    elif first_keyword in ['mythology', 'Greek mythology', 'Roman mythology']:
                        metadata['genreqid'] = 'Q3374376'  # mythological painting (Q3374376)
                elif genre == 'undetermined' and first_keyword:
                    if first_keyword in genres:
                        metadata['genreqid'] = genres.get(first_keyword)
                elif genre in genres:
                    metadata['genreqid'] = genres.get(genre)
        return metadata

    def get_part_of_related(self, rkdimages_docs):
        """
        Get related entries. Currently supported:
        * pendant of (P1639)
        * part of the series (P179)
        Could later be changed to also get more kind of relations
        :param rkdimages_docs:
        :return:
        """
        metadata = {}
        if rkdimages_docs.get('onderdeel_van') and len(rkdimages_docs.get('onderdeel_van')) == 1:
            onderdeel_van = rkdimages_docs.get('onderdeel_van')[0]
            if onderdeel_van.get('onderdeel_van_verband') == 'pendant':
                if onderdeel_van.get('object_onderdeel_van') and len(onderdeel_van.get('object_onderdeel_van')) == 1:
                    onderdeel_van_rkdimages_id = onderdeel_van.get('object_onderdeel_van')[0].get('priref')
                    if onderdeel_van_rkdimages_id in self.rkd_images:
                        metadata['pendantqid'] = self.rkd_images.get(onderdeel_van_rkdimages_id)
            elif rkdimages_docs.get('fysiek_verband') and len(rkdimages_docs.get('fysiek_verband')) == 1 \
                    and rkdimages_docs.get('fysiek_verband')[0] == 'part of a series':
                onderdeel_van_rkdimages_id = onderdeel_van.get('object_onderdeel_van')[0].get('priref')
                if onderdeel_van_rkdimages_id in self.rkd_images:
                    metadata['partofseriesqid'] = self.rkd_images.get(onderdeel_van_rkdimages_id)

        return metadata

    def get_dimensions(self, rkdimages_docs):
        """
        Get the width and height. The virtualFields also contains vorm-maten, but that appears to be just these two
        :param rkdimages_docs:
        :return:
        """
        metadata = {}
        if rkdimages_docs.get('hoogte') and rkdimages_docs.get('breedte') and rkdimages_docs.get('eenheid'):
            height = rkdimages_docs.get('hoogte')
            width = rkdimages_docs.get('breedte')
            if height == '?' or width == '?':
                return metadata
            # Should I test here if it's a integer or a float?
            if rkdimages_docs.get('eenheid') == 'cm':
                metadata['heightcm'] = height.replace(',', '.')
                metadata['widthcm'] = width.replace(',', '.')
            elif rkdimages_docs.get('eenheid') == 'mm':
                metadata['heightcm'] = '%s' % (float(height.replace(',', '.'))/10, )
                metadata['widthcm'] = '%s' % (float(width.replace(',', '.'))/10, )
        return metadata

    def get_collections(self, rkdimages_docs):
        """
        Get the collections.

        TODO: Implement private collection handling
        :param rkdimages_docs:
        :return:
        """
        collections = []
        if rkdimages_docs.get('collectie'):
            for collection_info in rkdimages_docs.get('collectie'):
                if collection_info.get('collectienaam'):
                    collectienaam = None
                    if isinstance(collection_info.get('collectienaam'), str):
                        # For some reason I sometimes get a list.
                        collectienaam = collection_info.get('collectienaam')
                    elif collection_info.get('collectienaam')[0].get('collectienaam'):
                        collectienaam = collection_info.get('collectienaam')[0].get('collectienaam')
                    if collectienaam and collectienaam in self.rkd_collections:
                        collections.append(self.rkd_collections.get(collectienaam))
        return {'extracollectionqids': collections}

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
    query = ''
    for arg in pywikibot.handle_args(args):
        if arg == '-dry':
            dryrun = True
        elif arg == '-create':
            create = True
        elif arg == '-source':
            source = True
        elif arg == '-recentedited':
            query = """SELECT ?item WHERE {
  ?item wdt:P350 ?id ; schema:version ?revision
} ORDER BY DESC(?revision) LIMIT 2000"""
        elif arg == '-recentcreated':
            query = """SELECT ?item WHERE {
  ?item wdt:P350 ?id .
  BIND (xsd:integer(STRAFTER(str(?item), "Q")) AS ?qid)
} ORDER BY DESC(?qid) LIMIT 1000"""
        elif arg == '-allrkdimages':
            query = """SELECT ?item WHERE {
  ?item wdt:P350 ?id .
} ORDER BY ASC(xsd:integer(?id))"""

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

        if not query:

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
            query3 = """SELECT ?item WHERE {
      ?item wdt:P350 ?id ;
        FILTER NOT EXISTS { ?item wdt:P136 [] }
    } LIMIT 100"""
            query = """SELECT ?item WHERE {
      ?item wdt:P350 ?id ;
        FILTER NOT EXISTS { ?item wdt:P186 [] }
    } LIMIT 10000"""
            query = """SELECT ?item WHERE {
      ?item wdt:P350 ?id ;
        FILTER NOT EXISTS { ?item wdt:P31 [] ;
                                  wdt:P170 [] ;
                                  wdt:P571 [] ;
                                  wdt:P2048 [] ;
                                  wdt:P2049 [] ;
                                  wdt:P186 [] ;
                                  wdt:P136 [] ;
                                  wdt:P1476 [] .
                          }
    } LIMIT 10000"""
            query2 = """SELECT ?item WHERE {
      ?item wdt:P350 ?id .
      MINUS { ?item rdfs:label ?enlabel;
                    rdfs:label ?nllabel;
                    FILTER(LANG(?enlabel)="en" && LANG(?nllabel)="nl") }				
    } LIMIT 10000"""
            query2 = """SELECT ?item WHERE {
      ?item wdt:P350 ?id .
      MINUS { ?item schema:description ?endescription;
                    schema:description ?nldescription.
                    FILTER(LANG(?endescription)="en" && LANG(?nldescription)="nl") }
    } LIMIT 1000"""
            query = """SELECT ?item WHERE {
      ?item wdt:P350 ?id ;
        FILTER NOT EXISTS { ?item wdt:P31 [] ;
                                  wdt:P170 [] .
                          }
    } LIMIT 10000"""
            query2 = """SELECT ?item WHERE {
      ?item p:P31 [ prov:wasDerivedFrom [ pr:P143 ?reference ] ; ps:P31 wd:Q3305213 ] ;
            wdt:P350 [] .
      } LIMIT 2000"""
            query = """SELECT ?item WHERE {
      ?item wdt:P350 ?id ;
            wdt:P170 wd:Q167654 .
    } LIMIT 10000"""
        generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    metadata_generator = RKDImagesExpanderGenerator(generator)

    if dryrun:
        for metadata in metadata_generator:
            print(metadata)
    else:
        art_data_expander_bot = ArtDataExpanderBot(metadata_generator)
        art_data_expander_bot.run()


if __name__ == "__main__":
    main()
