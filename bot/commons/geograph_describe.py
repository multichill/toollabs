#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to describe Geograph images using SDoC (structured data on Commons).

Bot will use geograph.org.uk image ID (P7384) and retrieve the original metadata from geograph. It will try to add:
* location of creation (P1071) based on reverse geocoding at http://edwardbetts.com/geocode/
* depicts (P180) based on the mappings at https://commons.wikimedia.org/wiki/User:GeographBot/Tags
* depicts (P180) based on the object location and reverse geocoding

Should be switched to a more general Pywikibot implementation.
"""

import pywikibot
import re
import pywikibot.data.sparql
import time
from pywikibot.comms import http
import requests
import json
import math
from pywikibot import pagegenerators

class GeographDescribeBot:
    """
    Bot to add structured data to Geograph uploads
    """
    def __init__(self, gen):
        """
        Grab generator based on search to work on.

        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()
        self.tags = self.getGeographTags()
        self.generator = gen

    def getGeographTags(self):
        """
        Get the Geograph tags and subjects. Just merge them into one.
        :return: Dict
        """
        page = pywikibot.Page(self.site , title='User:GeographBot/Tags')
        text = page.get()
        regex = u'^\*\s*https\:\/\/www\.geograph\.org\.uk\/tagged\/(?P<tag>[^\s]+)\s*-\s*\{\{Q\|(?P<qid>Q\d+)\}\}.*$'
        result = {}

        for match in re.finditer(regex, text, flags=re.M):
            tag = match.group('tag').replace('+', ' ').lower()
            if match.group('tag').startswith('subject:'):
                tag = tag.replace('subject:', u'')
            result[tag] = match.group('qid')
        return result

    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            pywikibot.output('Working on %s' % (filepage.title(),))
            self.describe_file(filepage)

        for filepage in self.generator:
            if not filepage.exists():
                continue
            # Probably want to get this all in a preloading generator to make it faster
            mediaid = u'M%s' % (filepage.pageid,)
            currentdata = self.getCurrentMediaInfo(mediaid)
            self.describeGeographFile(filepage, mediaid, currentdata)

    def describe_file(self, filepage):
        """
        Describe a single file
        :param filepage: File to work on
        :return:
        """
        mediainfo = filepage.data_item()
        if not mediainfo:
            return

        try:
            statements = mediainfo.statements
            labels = mediainfo.labels
        except Exception:
            # Bug in Pywikibot, no statements
            return

        # Check if we geograph.org.uk image ID (P7384), otherwise we have nothing to work on
        if 'P7384' not in statements:
            return
        geograph_id = statements.get('P7384')[0].getTarget()

        #if currentdata.get('statements'):
        #    if currentdata.get('statements').get('P180') and currentdata.get('statements').get('P1071'):
        #        # Already done
        #        return

        try:
            metadata = self.get_geograph_metadata(geograph_id)
        except json.decoder.JSONDecodeError:
            pywikibot.output('Got invalid JSON. Skipping this one')
            time.sleep(60)
            return

        if not metadata:
            return
        #print(json.dumps(metadata))

        data = {'claims': []}

        # TODO: Add label
        if 'en' not in labels:
            data['labels'] = {'en' : { 'language' : 'en',
                                       'value' : metadata.get('title').strip(),
                                       }
                              }

        new_claims = {}

        # Instance of -> photograph
        if 'P31' not in statements:
            new_claim = pywikibot.Claim(self.repo, 'P31')
            new_item = pywikibot.ItemPage(self.repo, 'Q125191')
            new_claim.setTarget(new_item)
            new_claims['instance'] = [new_claim.toJSON(), ]

        # Copyright status -> copyrighted
        if 'P6216' not in statements:
            new_claim = pywikibot.Claim(self.repo, 'P6216')
            new_item = pywikibot.ItemPage(self.repo, 'Q50423863')
            new_claim.setTarget(new_item)
            new_claims['copyright'] = [new_claim.toJSON(), ]

        # License -> cc-by-2.0
        if 'P275' not in statements:
            new_claim = pywikibot.Claim(self.repo, 'P275')
            new_item = pywikibot.ItemPage(self.repo, 'Q19068220')
            new_claim.setTarget(new_item)

            title_qualifier = pywikibot.Claim(self.repo, 'P1476')
            title_text = pywikibot.WbMonolingualText(text=metadata.get('title').strip(), language='en')
            title_qualifier.setTarget(title_text)
            title_qualifier.isQualifier = True

            author_qualifier = pywikibot.Claim(self.repo, 'P2093')
            author_qualifier.setTarget(metadata.get('realname').strip())
            author_qualifier.isQualifier = True

            new_claim.qualifiers['P1476'] = [title_qualifier]
            new_claim.qualifiers['P2093'] = [author_qualifier]
            new_claims['license'] = [new_claim.toJSON(), ]
        else:
            # It already has a license
            license_claim = statements.get('P275')[0]
            if license_claim.getTarget().title() == 'Q19068220':
                # It's the right license (cc-by-2.0)
                if 'P1476' not in license_claim.qualifiers or 'P2093' not in license_claim.qualifiers:
                    # One or both of the qualifiers are missing
                    if 'P1476' not in license_claim.qualifiers:
                        title_qualifier = pywikibot.Claim(self.repo, 'P1476')
                        title_text = pywikibot.WbMonolingualText(text=metadata.get('title').strip(), language='en')
                        title_qualifier.setTarget(title_text)
                        title_qualifier.isQualifier = True
                        license_claim.qualifiers['P1476'] = [title_qualifier]
                    if 'P2093' not in license_claim.qualifiers:
                        author_qualifier = pywikibot.Claim(self.repo, 'P2093')
                        author_qualifier.setTarget(metadata.get('realname').strip())
                        author_qualifier.isQualifier = True
                        license_claim.qualifiers['P2093'] = [author_qualifier]
                    new_claims['license'] = [license_claim.toJSON(), ]

        # Source
        if 'P7482' not in statements:
            new_claim = pywikibot.Claim(self.repo, 'P7482')
            new_item = pywikibot.ItemPage(self.repo, 'Q74228490')
            new_claim.setTarget(new_item)

            operator_qualifier = pywikibot.Claim(self.repo, 'P137')
            operator_item = pywikibot.ItemPage(self.repo, 'Q1503119')
            operator_qualifier.setTarget(operator_item)
            operator_qualifier.isQualifier = True

            geograph_id_qualifier = pywikibot.Claim(self.repo, 'P7384')
            geograph_id_qualifier.setTarget(metadata.get('id'))
            geograph_id_qualifier.isQualifier = True

            url_qualifier = pywikibot.Claim(self.repo, 'P973')
            url_qualifier.setTarget(metadata.get('sourceurl'))
            url_qualifier.isQualifier = True

            new_claim.qualifiers['P137'] = [operator_qualifier]
            new_claim.qualifiers['P7384'] = [geograph_id_qualifier]
            new_claim.qualifiers['P973'] = [url_qualifier]
            new_claims['source'] = [new_claim.toJSON(), ]
        else:
            # It already has a source
            source_claim = statements.get('P7482')[0]
            if source_claim.getTarget().title() == 'Q74228490':
                # It's file available on the internet (Q74228490)
                if 'P137' not in source_claim.qualifiers or 'P7384' not in source_claim.qualifiers \
                        or 'P973' not in source_claim.qualifiers:
                    # One or more of the qualifiers are missing
                    if 'P137' not in source_claim.qualifiers:
                        operator_qualifier = pywikibot.Claim(self.repo, 'P137')
                        operator_item = pywikibot.ItemPage(self.repo, 'Q1503119')
                        operator_qualifier.setTarget(operator_item)
                        operator_qualifier.isQualifier = True
                        source_claim.qualifiers['P137'] = [operator_qualifier]
                    if 'P7384' not in source_claim.qualifiers.qualifiers:
                        geograph_id_qualifier = pywikibot.Claim(self.repo, 'P7384')
                        geograph_id_qualifier.setTarget(metadata.get('id'))
                        geograph_id_qualifier.isQualifier = True
                        source_claim.qualifiers['P7384'] = [geograph_id_qualifier]
                    if 'P973' not in source_claim.qualifiers.qualifiers:
                        url_qualifier = pywikibot.Claim(self.repo, 'P973')
                        url_qualifier.setTarget(metadata.get('sourceurl'))
                        url_qualifier.isQualifier = True
                        source_claim.qualifiers['P973'] = [url_qualifier]
                    new_claims['source'] = [license_claim.toJSON(), ]

        # creator
        if 'P170' not in statements:
            new_claim = pywikibot.Claim(self.repo, 'P170')
            new_claim.setSnakType('somevalue')

            #  object of statement has role (P3831) -> photographer (Q33231)
            photographer_qualifier = pywikibot.Claim(self.repo, 'P3831')
            photographer_item = pywikibot.ItemPage(self.repo, 'Q33231')
            photographer_qualifier.setTarget(photographer_item)
            photographer_qualifier.isQualifier = True

            author_qualifier = pywikibot.Claim(self.repo, 'P2093')
            author_qualifier.setTarget(metadata.get('realname').strip())
            author_qualifier.isQualifier = True

            author_url = 'https://www.geograph.org.uk/profile/%s' % (metadata.get('user_id'))
            url_qualifier = pywikibot.Claim(self.repo, 'P2699')
            url_qualifier.setTarget(author_url)
            url_qualifier.isQualifier = True

            new_claim.qualifiers['P3831'] = [photographer_qualifier]
            new_claim.qualifiers['P2093'] = [author_qualifier]
            new_claim.qualifiers['P2699'] = [url_qualifier]
            new_claims['creator'] = [new_claim.toJSON(), ]

        if 'P571' not in statements:
            date = self.getDate(metadata)
            if date:
                new_claims['date'] = [date, ]

        if 'P1259' not in statements:
            coordinates = self.getPhotographerCoordinates(metadata)
            if coordinates:
                new_claims['coordinates'] = [coordinates, ]

        if 'P9149' not in statements:
            object_coordinates = self.getObjectCoordinates(metadata)
            if object_coordinates:
                new_claims['object coordinates'] = [object_coordinates, ]

        # MIME type
        if 'P1163' not in statements:
            new_claim = pywikibot.Claim(self.repo, 'P1163')
            new_claim.setTarget('image/jpeg')
            new_claims['MIME'] = [new_claim.toJSON(), ]

        # Do the reverse lookup
        if 'P180' not in statements or 'P1071' not in statements:
            if metadata.get('photographer_lat') and metadata.get('photographer_lon'):
                location_qid = self.reverse_geocode(metadata.get('photographer_lat'), metadata.get('photographer_lon'))
                if location_qid:
                    metadata['locationqid'] = location_qid

            if metadata.get('object_lat') and metadata.get('object_lon'):
                object_qid = self.reverse_geocode(metadata.get('object_lat'), metadata.get('object_lon'), )
                if object_qid:
                    if not metadata.get('locationqid'):
                        metadata['locationqid'] = object_qid
                    metadata['depictsqids'].append(object_qid)

            if 'P180' not in statements:
                new_claims['depicts'] = self.get_depicts(metadata)

            if 'P1071' not in statements and metadata.get('locationqid'):
                new_claim = pywikibot.Claim(self.repo, 'P1071')
                new_item = pywikibot.ItemPage(self.repo, metadata.get('locationqid'))
                new_claim.setTarget(new_item)
                new_claims['location'] = [new_claim.toJSON(), ]



        added_claims = []

        for new_claim in new_claims:
            if new_claims.get(new_claim):
                data['claims'].extend(new_claims.get(new_claim))
                added_claims.append(new_claim)

        if data.get('labels') or len(added_claims) > 0:
            if data.get('labels') and len(added_claims) == 0:
                summary = 'Adding structured data from Geograph %s: label' % (geograph_id, )
            else:
                if data.get('labels'):
                    summary = 'Adding structured data from Geograph %s: label, %s' % (geograph_id, added_claims[0], )
                else:
                    summary = 'Adding structured data from Geograph %s: %s' % (geograph_id, added_claims[0], )
                if len(added_claims) > 2:
                    for i in range(1, len(added_claims)-1):
                        summary = summary + ', %s' % (added_claims[i],)
                if len(added_claims) > 1:
                    summary = summary + ' & %s' % (added_claims[-1],)

            # Flush it
            pywikibot.output(summary)

            try:
                # FIXME: Switch to mediainfo.editEntity() https://phabricator.wikimedia.org/T376955
                print(data)
                response = self.site.editEntity(mediainfo, data, summary=summary, tags='BotSDC')
                filepage.touch()
            except pywikibot.exceptions.APIError as e:
                print(e)

    def get_geograph_metadata(self, geograph_id):
        """
        Get the metadata for a single geograph file from the source
        :param geograph_id: The id of the file
        :return: Dict with the metadata
        """
        searchurl = 'http://api.geograph.org.uk/api-facetql.php?select=*&limit=1&where=id=%s' % (geograph_id)
        try:
            searchpage = requests.get(searchurl)
        except requests.exceptions.ConnectionError:
            pywikibot.output(u'Got a connection error on %s. Sleeping 5 minutes' % (searchurl,))
            time.sleep(300)
            searchpage = requests.get(searchurl)
        if searchpage.json().get('rows'):
            row = searchpage.json().get('rows')[0]
        else:
            return False
        metadata = row

        metadata['imageurl'] = 'https://www.geograph.org.uk/reuse.php?id=%s&download=%s&size=largest' % (row.get('id'), row.get('hash'))
        metadata['sourceurl'] = 'https://www.geograph.org.uk/photo/%s' % (row.get('id'), )

        if row.get('takenday'):
            dateregex = '^(\d\d\d\d)(\d\d)(\d\d)$'
            datematch = re.match(dateregex, row.get('takenday'))
            if datematch:
                row['date'] = '%s-%s-%s' % (datematch.group(1), datematch.group(2), datematch.group(3), )

        if row.get('vlat'):
            metadata['photographer_lat'] = math.degrees(float(row.get('vlat')))
        if row.get('vlong'):
            metadata['photographer_lon'] = math.degrees(float(row.get('vlong')))
        if row.get('vgrlen'):
            if int(row.get('vgrlen')) == 0:
                metadata['photographer_precision'] = None
            elif int(row.get('vgrlen')) <= 4:
                metadata['photographer_precision'] = 0.01
            elif int(row.get('vgrlen')) <= 6:
                metadata['photographer_precision'] = 0.001
            elif int(row.get('vgrlen')) <= 8:
                metadata['photographer_precision'] = 0.0001
            elif int(row.get('vgrlen')) > 8:
                metadata['photographer_precision'] = 0.00001
        if row.get('wgs84_lat'):
            metadata['object_lat'] = math.degrees(float(row.get('wgs84_lat')))
        if row.get('wgs84_long'):
            metadata['object_lon'] = math.degrees(float(row.get('wgs84_long')))
        if row.get('natgrlen'):
            if int(row.get('natgrlen')) == 0:
                metadata['object_precision'] = None
            elif int(row.get('natgrlen')) <= 4:
                metadata['object_precision'] = 0.01
            elif int(row.get('natgrlen')) <= 6:
                metadata['object_precision'] = 0.001
            elif int(row.get('natgrlen')) <= 8:
                metadata['object_precision'] = 0.0001
            elif int(row.get('natgrlen')) > 8:
                metadata['object_precision'] = 0.00001
        metadata['depictsqids'] = []
        if row.get('contexts'):
            for tag in row.get('contexts').replace('_SEP_', '|').split('|'):
                tag = tag.strip().lower()
                if tag:
                    tag = 'top:%s' % (tag,)
                    pywikibot.debug('Tag found:"%s"' % (tag,), 'bot')
                    if tag in self.tags:
                        depictsqid = self.tags.get(tag)
                        if depictsqid not in metadata.get('depictsqids'):
                            metadata['depictsqids'].append(depictsqid)
        if row.get('subjects'):
            for tag in row.get('subjects').replace('_SEP_', '|').split('|'):
                tag = tag.strip().lower()
                if tag:
                    pywikibot.debug('Tag found:"%s"' % (tag,), 'bot')
                    if tag in self.tags:
                        depictsqid = self.tags.get(tag)
                        if depictsqid not in metadata.get('depictsqids'):
                            metadata['depictsqids'].append(depictsqid)
        if row.get('tags'):
            for tag in row.get('tags').replace('_SEP_', '|').split('|'):
                tag = tag.strip().lower()
                if tag:
                    pywikibot.debug('Tag found:"%s"' % (tag,), 'bot')
                    if tag in self.tags:
                        depictsqid = self.tags.get(tag)
                        if depictsqid not in metadata.get('depictsqids'):
                            metadata['depictsqids'].append(depictsqid)

        return metadata

    def getDate(self, metadata):
        """

        :param metadata:
        :return:
        """
        if not metadata.get('date'):
            return False

        dateregex = '(\d\d\d\d-\d\d-\d\d)'
        datematch = re.search(dateregex, metadata.get('date'))
        if datematch:
            date = datematch.group(1)
        else:
            date = metadata.get('date')

        request = self.site.simple_request(action='wbparsevalue', datatype='time', values=date)
        data = request.submit()
        # Not sure if this works or that I get an exception.
        if data.get('error'):
            return False
        postvalue = data.get(u'results')[0].get('value')

        toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': 'P571',
                                 'datavalue': { 'value': postvalue,
                                                'type' : 'time',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        return toclaim

    def getPhotographerCoordinates(self, metadata):
        """

        :param metadata:
        :return:
        """
        if not metadata.get('photographer_lat') or not metadata.get('photographer_lon') or not metadata.get('photographer_precision'):
            return False

        toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': 'P1259',
                                 'datavalue': { 'value': { 'latitude': metadata.get('photographer_lat'),
                                                           'longitude':metadata.get('photographer_lon'),
                                                           'altitude': None,
                                                           'precision': metadata.get('photographer_precision'),
                                                           'globe':'http://www.wikidata.org/entity/Q2'},
                                                'type' : 'globecoordinate',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        if metadata.get('direction') and not metadata.get('direction')=='Unknown' and not metadata.get('direction')=='0':
            toclaim['qualifiers'] = {'P7787' : [ {'snaktype': 'value',
                                                  'property': 'P7787',
                                                  'datavalue': { 'value': { 'amount': '+%s' % (metadata.get('direction'),),
                                                                            'unit' : 'http://www.wikidata.org/entity/Q28390',
                                                                            },
                                                                 'type' : 'quantity',
                                                                 },
                                                  },
                                                 ],
                                     }
        return toclaim

    def getObjectCoordinates(self, metadata):
        """

        :param metadata:
        :return:
        """
        if not metadata.get('object_lat') or not metadata.get('object_lon') or not metadata.get('object_precision'):
            return False

        toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': 'P9149',
                                 'datavalue': { 'value': { 'latitude': metadata.get('object_lat'),
                                                           'longitude':metadata.get('object_lon'),
                                                           'altitude': None,
                                                           'precision': metadata.get('object_precision'),
                                                           'globe':'http://www.wikidata.org/entity/Q2'},
                                                'type' : 'globecoordinate',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        return toclaim

    def reverse_geocode(self, lat, lon, tries=3):
        """
        Do reverse geocoding based on latitude & longitude and return Wikidata item and Commons category
        :param lat: The latitude
        :parim lon: The longitude
        :return: Tuple of Wikidata item and Commons category
        """
        qid = None
        commonscat = None

        url = 'http://edwardbetts.com/geocode/?lat=%s&lon=%s' % (lat, lon)
        try:
            page = requests.get(url)
            jsondata = page.json()
        except ValueError:
            # Either json.decoder.JSONDecodeError or simplejson.scanner.JSONDecodeError, both subclass of ValueError
            pywikibot.output('Got invalid json at %s' % (url,))
            time.sleep(60)
            if tries > 0:
                return self.reverse_geocode(lat, lon, tries=tries-1)
            return qid
        except IOError:
            # RequestExceptions was thrown
            pywikibot.output('Got an IOError at %s' % (url,))
            time.sleep(60)
            if tries > 0:
                return self.reverse_geocode(lat, lon, tries=tries-1)
            return qid

        if not jsondata.get('missing'):
            if jsondata.get('wikidata'):
                qid = jsondata.get('wikidata')
            if jsondata.get('commons_cat') and jsondata.get('commons_cat').get('title'):
                commonscat = jsondata.get('commons_cat').get('title')
        return qid

    def get_depicts(self, metadata):
        """

        :param metadata:
        :return:
        """
        depicts_to_add = []
        if metadata.get('depictsqids'):
            depicts_to_add.extend(metadata.get('depictsqids'))
        if metadata.get('depictslocationqid'):
            depicts_to_add.append(metadata.get('depictslocationqid'))
        if not depicts_to_add:
            return False

        result = []
        for depicts_qid in depicts_to_add:
            new_claim = pywikibot.Claim(self.repo, 'P180')
            new_item = pywikibot.ItemPage(self.repo, depicts_qid)
            new_claim.setTarget(new_item)
            result.append(new_claim.toJSON())
        return result


def main(*args):
    """

    :param args:
    :return:
    """
    gen = None

    gen_factory = pagegenerators.GeneratorFactory()

    for arg in pywikibot.handle_args(args):
        if arg == '-loose':
            pass
        elif gen_factory.handle_arg(arg):
            continue

    gen = pagegenerators.PageClassGenerator(gen_factory.getCombinedGenerator(gen, preload=True))

    geographDescribeBot = GeographDescribeBot(gen)
    geographDescribeBot.run()


if __name__ == "__main__":
    main()
