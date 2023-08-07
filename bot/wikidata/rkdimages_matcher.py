#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Tool to match RKDimages on Wikidata with RKDimages and make some sort of easy result

"""
import pywikibot
import requests
import pywikibot.data.sparql
import re
import json
import urllib.parse


class RKDimagesMatcher:
    """
    Program to do the matching of RKDimages with Wikidata
    """
    def __init__(self, run_mode='full', work_qid=None, autoadd=0):
        """
        Setup the bot
        :param run_mode:
        :param work_qid:
        """
        self.repo = pywikibot.Site().data_repository()
        self.max_length = 2000
        self.run_mode = run_mode
        self.work_qid = work_qid
        self.autoadd = autoadd

        self.all_rkdimages_wikidata = None
        self.all_rkdartists_wikidata = None

        self.manual_collections = {}
        self.automatic_collections = {}
        self.collections = {}

        self.manual_artists = {}
        self.automatic_artists = {}
        self.artists = {}

        self.collection_stats = []
        self.artist_stats = []

        self.manual_collections = self.get_manual_collections()
        self.collections.update(self.manual_collections)
        self.manual_artists = self.get_manual_artists()
        self.artists.update(self.manual_artists)

        if run_mode == 'check_collections':
            self.automatic_collections = self.get_automatic_collections()
        elif run_mode == 'single_collection':
            self.all_rkdimages_wikidata = self.rkdimages_on_wikidata()
            if work_qid not in self.collections:
                self.automatic_collections = self.get_automatic_collections()
        elif run_mode == 'single_artist':
            self.all_rkdimages_wikidata = self.rkdimages_on_wikidata()
            if work_qid not in self.artists:
                self.automatic_artists = self.get_automatic_artists()
        elif run_mode == 'oldest' or run_mode == 'newest':
            self.all_rkdimages_wikidata = self.rkdimages_on_wikidata()
            self.all_rkdartists_wikidata = self.rkdartists_on_wikidata()
        elif run_mode == 'full':
            self.all_rkdimages_wikidata = self.rkdimages_on_wikidata()
            self.all_rkdartists_wikidata = self.rkdartists_on_wikidata()
            self.automatic_collections = self.get_automatic_collections()
            self.automatic_artists = self.get_automatic_artists()
        self.collections.update(self.automatic_collections)
        self.artists.update(self.automatic_artists)
        self.rkd_collectienaam = self.get_rkd_collectienaam(self.collections)

    def rkdimages_on_wikidata(self, collection_qid=None):
        """
        To do: Merge with artists
        Return a dict with the RKDimages on Wikidata.
        :param collection_qid: If set, only from this collection
        :return: Dict
        """
        result = {}
        if collection_qid:
            # Need to use the long version here to get all ranks
            query = """SELECT DISTINCT ?item ?id WHERE {
            ?item p:P350 ?idstatement .
            ?idstatement ps:P350 ?id .
            MINUS { ?idstatement wikibase:rank wikibase:DeprecatedRank }
            { ?item p:P195 ?colstatement .
            ?colstatement ps:P195 wd:%s . } UNION
            { ?item p:P276 ?locationstatement .
            ?locationstatement ps:P276 wd:%s . }
            }""" % (collection_qid, collection_qid)
        else:
            query = """SELECT ?item ?id WHERE {
            ?item p:P350 ?idstatement.
            ?idstatement ps:P350 ?id.
            MINUS { ?idstatement wikibase:rank wikibase:DeprecatedRank. }
            }"""
        sq = pywikibot.data.sparql.SparqlQuery()
        query_result = sq.select(query)

        for result_item in query_result:
            qid = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
            try:
                result[int(result_item.get('id'))] = qid
            except ValueError:
                # Unknown value will trigger this
                pass
        return result

    def rkdartists_on_wikidata(self):
        """
        Get all rkdartists on Wikidata
        :return: Lookup table
        """
        result = {}
        query = 'SELECT ?item ?id WHERE { ?item wdt:P650 ?id }'
        sq = pywikibot.data.sparql.SparqlQuery()
        query_result = sq.select(query)

        for result_item in query_result:
            qid = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
            result[result_item.get('id')] = qid
        return result

    def get_manual_collections(self):
        """
        Use config at https://www.wikidata.org/wiki/User:BotMultichillT/rkdimages_collections.js for lookup table
        :return: The lookup table as a dict
        """
        #FIXME: Migrate this all to the wiki config
        result = {             # Next on the TODO is Museum Het Valkhof
                               #u'Q768717' : { u'collectienaam' : u'Private collection', # Probably still too big
                               #                u'replacements' : [],
                               #                u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Private collection',
                               #                },

                               }
        configpage = pywikibot.Page(self.repo, title='User:BotMultichillT/rkdimages collections.js')
        (comments, sep, jsondata) = configpage.get().partition('[')
        jsondata = '[' + jsondata
        configjson = json.loads(jsondata)
        for collection_info in configjson:
            result[collection_info.get('qid')] = collection_info
        # Can do override here
        #result['Q2066737'] = {"qid": "Q2066737",
        #                      "collectienaam": "Instituut Collectie Nederland",
        #                      "reportpage": "Wikidata:WikiProject sum of all paintings/RKD to match/Instituut Collectie Nederland",
        #                      "use_collection" : "Q18600731",
        #                      "replacements": [("^(.+)\s(.+)$", "\\1\\2"),],
        #                      }

        return result

    def get_automatic_collections(self):
        """
        Do a query for the relevant collections to work on. Try to guess the collection name.
        Filter based on the manual collections. When in check mode, this list is empty
        :return:
        """
        result = {}

        collection_names = ['Private collection']  # Keep a list of names already found so we can ignore these
        use_collections = []
        for manual_collection in self.manual_collections:
            collection_names.append(self.manual_collections.get(manual_collection).get('collectienaam'))
            if self.manual_collections.get(manual_collection).get('use_collection'):
                use_collections.append(self.manual_collections.get(manual_collection).get('use_collection'))

        query = """SELECT ?item ?label (COUNT(*) AS ?count) WHERE {
      ?painting wdt:P350 [] ;
                wdt:P31 wd:Q3305213 ;
                p:P195/ps:P195 ?item .
      ?item rdfs:label ?label .
      FILTER(LANG(?label)="en")
      } GROUP BY ?item ?label
    ORDER BY DESC(?count)
    LIMIT 250"""
        sq = pywikibot.data.sparql.SparqlQuery()
        query_result = sq.select(query)

        for result_item in query_result:
            qid = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
            report_page = 'Wikidata:WikiProject sum of all paintings/RKD to match/%s' % (result_item.get('label'),)

            if qid not in self.manual_collections and qid not in use_collections:
                pywikibot.output('Working on %s (%s)' % (result_item.get('label'), qid))
                collection_name = self.guess_collection_name(qid, collection_names)
                collection_names.append(collection_name)
                if collection_name:
                    pywikibot.output('Collection name %s was returned for %s (%s)' % (collection_name, result_item.get('label'), qid))
                    collection_data = {'qid': qid,
                                       'collectienaam': collection_name,
                                       'reportpage': report_page,
                                       'replacements': [],
                                       }
                    result[qid] = collection_data
                else:
                    result[qid] = None
        return result
    def get_manual_artists(self):
        """

        :return:
        """
        # FIXME: Probably trash this part
        manual_artists = { u'Q711737' : { u'artistname' : u'Berchem, Nicolaes',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Nicolaes Pieterszoon Berchem',
                                          },
                           u'Q374039' : { u'artistname' : u'Bol, Ferdinand',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Ferdinand Bol',
                                          },
                           u'Q346808' : { u'artistname' : u'Borch, Gerard ter (II)',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Gerard ter Borch',
                                          },
                           u'Q130531' : { u'artistname' : u'Bosch, Jheronimus',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Hieronymus Bosch',
                                          },
                           u'Q289441' : { u'artistname' : u'Breitner, George Hendrik',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/George Hendrik Breitner',
                                          },
                           u'Q153472' : { u'artistname' : u'Cleve, Joos van',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Joos van Cleve',
                                          },
                           u'Q367798' : { u'artistname' : u'Coorte, Adriaen',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Adriaen Coorte',
                                          },
                           u'Q313194' : { u'artistname' : u'Cuyp, Aelbert',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Aelbert Cuyp',
                                          },
                           u'Q160422' : { u'artistname' : u'Doesburg, Theo van',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Theo van Doesburg',
                                          },
                           u'Q335927' : { u'artistname' : u'Dou, Gerard',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Gerrit Dou',
                                          },
                           u'Q150679' : { u'artistname' : u'Dyck, Anthony van',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Anthony van Dyck',
                                          },
                           u'Q624802' : { u'artistname' : u'Fijt, Joannes',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jan Fyt',
                                          },
                           u'Q1442507' : { u'artistname' : u'Francken, Frans (II)',
                                           u'replacements' : [],
                                           u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Frans Francken the Younger',
                                           },
                           u'Q5582' : { u'artistname' : u'Gogh, Vincent van',
                                        u'replacements' : [],
                                        u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Vincent van Gogh',
                                        },
                           u'Q315996' : { u'artistname' : u'Goyen, Jan van',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jan van Goyen',
                                          },
                           u'Q167654' : { u'artistname' : u'Hals, Frans (I)',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Frans Hals',
                                          },
                           u'Q538350' : { u'artistname' : u'Heemskerck, Maarten van',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Maarten van Heemskerck',
                                          },
                           u'Q380704' : { u'artistname' : u'Helst, Bartholomeus van der',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Bartholomeus van der Helst',
                                          },
                           u'Q370567' : { u'artistname' : u'Heyden, Jan van der',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jan van der Heyden',
                                          },
                           u'Q314548' : { u'artistname' : u'Honthorst, Gerard van',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Gerard van Honthorst',
                                          },
                           u'Q314889' : { u'artistname' : u'Hooch, Pieter de',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Pieter de Hooch',
                                          },
                           u'Q979534' : { u'artistname' : u'Israels, Isaac',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Isaac Israëls',
                                          },
                           u'Q528460' : { u'artistname' : u'Israëls, Jozef',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jozef Israëls',
                                          },
                           u'Q270658' : { u'artistname' : u'Jordaens, Jacob (I)',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jacob Jordaens',
                                          },
                           u'Q2500930' : { u'artistname' : u'Kat, Otto B. de',
                                           u'replacements' : [],
                                           u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Otto B. de Kat',
                                           },
                           u'Q505150' : { u'artistname' : u'Maes, Nicolaes',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Nicolaes Maes',
                                          },
                           u'Q978158' : { u'artistname' : u'Maris, Jacob',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jacob Maris',
                                          },
                           u'Q1375830' : { u'artistname' : u'Maris, Matthijs',
                                           u'replacements' : [],
                                           u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Matthijs Maris',
                                           },
                           u'Q591907' : { u'artistname' : u'Mauve, Anton',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Anton Mauve',
                                          },
                           u'Q355213' : { u'artistname' : u'Metsu, Gabriel',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Gabriël Metsu',
                                          },
                           u'Q864092' : { u'artistname' : u'Mierevelt, Michiel van',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Michiel van Mierevelt',
                                          },
                           u'Q959236' : { u'artistname' : u'Mieris, Frans van (I)',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Frans van Mieris the Elder',
                                          },
                           u'Q151803' : { u'artistname' : u'Mondriaan, Piet',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Piet Mondrian',
                                          },
                           u'Q352438' : { u'artistname' : u'Ostade, Adriaen van',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Adriaen van Ostade',
                                          },
                           u'Q5598' : { u'artistname' : u'Rembrandt',
                                        u'replacements' : [],
                                        u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Rembrandt',
                                        },
                           u'Q5599' : { u'artistname' : u'Rubens, Peter Paul',
                                        u'replacements' : [],
                                        u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Peter Paul Rubens',
                                        },
                           u'Q213612' : { u'artistname' : u'Ruisdael, Jacob van',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jacob van Ruisdael',
                                          },
                           u'Q1682227' : { u'artistname' : u'Sluijters, Jan',
                                           u'replacements' : [],
                                           u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jan Sluyters',
                                           },
                           u'Q205863' : { u'artistname' : u'Steen, Jan',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jan Steen',
                                          },
                           u'Q335022' : { u'artistname' : u'Teniers, David (II)',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/David Teniers the Younger',
                                          },
                           u'Q41264' : { u'artistname' : u'Vermeer, Johannes',
                                         u'replacements' : [],
                                         u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Johannes Vermeer',
                                         },
                           u'Q1691988' : { u'artistname' : u'Weissenbruch, Jan Hendrik',
                                           u'replacements' : [],
                                           u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Johan Hendrik Weissenbruch',
                                           },
                           u'Q2614892' : { u'artistname' : u'Witsen, Willem',
                                           u'replacements' : [],
                                           u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Willem Witsen',
                                           },
                           u'Q454671' : { u'artistname' : u'Wouwerman, Philips',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Philips Wouwerman',
                                          },
                           u'Q170339' : { u'artistname' : u'Cranach, Lucas (II)',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Lucas Cranach the Younger',
                                          },
                           u'Q191748' : { u'artistname' : u'Cranach, Lucas (I)',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Lucas Cranach the Elder',
                                          },
                           u'Q380743' : { u'artistname' : u'Bouts, Albrecht',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Albrecht Bouts',
                                          },
                           u'Q360888' : { u'artistname' : u'Geertgen tot Sint Jans',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Geertgen tot Sint Jans',
                                          },
                           u'Q102272' : { u'artistname' : u'Eyck, Jan van',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jan van Eyck',
                                          },
                           u'Q312616' : { u'artistname' : u'Christus, Petrus (I)',
                                          u'replacements' : [],
                                          u'reportpage' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Petrus Christus',
                                          },
                           }
        return manual_artists

    def get_automatic_artists(self):
        """
        Do a query for the relevant artists to work on
        :return:
        """
        result = {}

        query = """SELECT ?item ?label ?id (COUNT(*) AS ?count) WHERE {
      ?painting wdt:P350 [] ;
                wdt:P31 wd:Q3305213 ;
                wdt:P170 ?item .
      ?item wdt:P650 ?id ;
            rdfs:label ?label .
      FILTER(LANG(?label)="en")
      } GROUP BY ?item ?label ?id 
    ORDER BY DESC(?count)
    LIMIT 250"""
        sq = pywikibot.data.sparql.SparqlQuery()
        query_result = sq.select(query)

        for result_item in query_result:
            qid = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
            report_page = 'Wikidata:WikiProject sum of all paintings/RKD to match/%s' % (result_item.get('label'),)
            rkdartists_id = result_item.get('id')

            rkdartists_url = 'https://api.rkd.nl/api/record/artists/%s?format=json&language=en' % (rkdartists_id,)

            # Do some checking if it actually exists?
            rkdartists_page = requests.get(rkdartists_url)
            try:
                rkdartists_json = rkdartists_page.json()
                artistname = rkdartists_json.get('response').get('docs')[0].get('kunstenaarsnaam')
            except ValueError:  # Throws simplejson.errors.JSONDecodeError
                pywikibot.output('Got invalid json for%s, skipping' % (rkdartists_id,))
                continue
            artist_data = {'qid': qid,
                           'artistname': artistname,
                           'rkdartistsid': rkdartists_id,
                           'reportpage': report_page,
                           'replacements': [],
                           }
            result[qid] = artist_data
        return result

    def get_rkd_collectienaam(self, collections):
        """
        Make a collectienaam lookup table
        :param collections: The collections we found
        :return: Lookup table
        """
        result = {}
        for collection in collections:
            if collections.get(collection) and collections.get(collection).get('collectienaam'):
                result[collections.get(collection).get('collectienaam')] = collection
        return result

    def run(self):
        """
        Do the actual run
        :return:
        """
        if self.run_mode == 'check_collections':
            self.check_collections()
        elif self.run_mode == 'find_collections':
            self.find_collections()
        elif self.run_mode == 'single_collection':
            if self.work_qid not in self.collections:
                pywikibot.output('%s is not a valid collection qid!' % (self.work_qid,))
                return
            self.process_collection(self.work_qid)
        elif self.run_mode == 'single_artist':
            if self.work_qid not in self.artists:
                pywikibot.output('%s is not a valid artist qid!' % (self.work_qid,))
                return
            self.process_artist(self.work_qid)
        elif self.run_mode == 'oldest':
            self.process_period('oldest')
        elif self.run_mode == 'newest':
            self.process_period('newest')
        elif self.run_mode == 'full':
            self.process_period('oldest')
            self.process_period('newest')
            for collection_qid in self.collections:
                self.process_collection(collection_qid)
            for artist_qid in self.artists:
                self.process_artist(artist_qid)
            self.publish_statistics()

    def wikidata_paintings_in_collection(self, collection_qid):
        """
        Was paintingsInvOnWikidata
        Get the paintings on Wikidata in the collection
        :param collection_qid: The collection to work on
        :return: Dict with the paintings
        """
        result = {}
        # Need to use the long version here to get all ranks
        query = u"""SELECT DISTINCT ?item ?id ?url ?rkdimageid ?rkdartistid WHERE {
        ?item wdt:P31 wd:Q3305213 .
        { ?item p:P195/ps:P195 wd:%s .
        ?item p:P217 [ps:P217 ?id ; pq:P195 wd:%s ] } UNION
        { wd:%s wdt:P361 ?collection .
        ?item p:P276/ps:P276 wd:%s  ;
              p:P217 [ps:P217 ?id ; pq:P195 ?collection ] }
        OPTIONAL { ?item wdt:P973 ?url } .
        OPTIONAL { ?item wdt:P350 ?rkdimageid } .
        OPTIONAL { ?item wdt:P170 ?creator .
        ?creator wdt:P650 ?rkdartistid }
        } LIMIT 30000""" % (collection_qid, collection_qid, collection_qid, collection_qid)
        sq = pywikibot.data.sparql.SparqlQuery()
        query_result = sq.select(query)

        for result_item in query_result:
            qid = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
            result[result_item.get('id')] = {'qid': qid}
            if result_item.get('url'):
                result[result_item.get('id')]['url'] = result_item.get('url')
            if result_item.get('rkdimageid'):
                result[result_item.get('id')]['rkdimageid'] = result_item.get('rkdimageid')
            if result_item.get('rkdartistid'):
                result[result_item.get('id')]['rkdartistid'] = result_item.get('rkdartistid')

        return result

    def wikidata_paintings_for_artist(self, artist_qid):
        """
        Was paintingsArtistOnWikidata
        Get the paintings on Wikidata for the artist
        :param artist_qid: The artist to work on
        :return: Dict with the paintings

        FIXME: Just return a dict instead of a generator
        """
        result = {}
        query = u"""SELECT DISTINCT ?item ?year ?collection ?inv WHERE {
        ?item wdt:P31 wd:Q3305213 .
        ?item wdt:P170 wd:%s .
        MINUS { ?item wdt:P350 [] } .
        OPTIONAL { ?item wdt:P571 ?inception . BIND(year(?inception) as ?year) } .
        OPTIONAL { ?item wdt:P195 ?collection } .
        } ORDER BY ?item LIMIT 1000000""" % (artist_qid, )
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        previousqid = None

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')

            paintingitem = { u'qid' : qid,
                             u'inception' : u'',
                             u'collection' : u'',
                             }
            if resultitem.get('year'):
                paintingitem['inception'] = resultitem.get('year')
            if resultitem.get('collection'):
                paintingitem['collection'] = resultitem.get('collection').replace(u'http://www.wikidata.org/entity/', u'')

            #result[qid] = { u'qid' : qid }
            #if resultitem.get('url'):
            #    result[resultitem.get('id')]['url'] = resultitem.get('url')
            #if resultitem.get('rkdimageid'):
            #    result[resultitem.get('id')]['rkdimageid'] = resultitem.get('rkdimageid')
            #if resultitem.get('rkdartistid'):
            #    result[resultitem.get('id')]['rkdartistid'] = resultitem.get('rkdartistid')
            yield paintingitem

        #return result

    def rkdimages_collection_generator(self, invnumbers, collectienaam, replacements):
        """
        Get all the RKDimages for one collection
        :param invnumbers: The inventory numbers we found on Wikidata
        :param collectienaam: The name of the collection in RKDimages ("collectienaam")
        :param replacements: The replacements to do on the inventory numbers
        :return: Generator yield dicts
        """
        start = 0
        rows = 50
        basesearchurl = u'https://api.rkd.nl/api/search/images?filters[collectienaam]=%s&filters[objectcategorie][]=schilderij&format=json&start=%s&rows=%s'
        while True:
            searchUrl = basesearchurl % (urllib.parse.quote_plus(collectienaam), start, rows)
            searchPage = requests.get(searchUrl)  #, verify=False)
            searchJson = searchPage.json()
            if not searchJson.get('response') or not searchJson.get('response').get('numFound'):
                # If we don't get a valid response, just return
                return
            numfound = searchJson.get('response').get('numFound')
            if not start < numfound:
                return
            start = start + rows
            for rkdimage in  searchJson.get('response').get('docs'):
                imageinfo = {}
                imageinfo[u'id'] = rkdimage.get(u'priref')
                if rkdimage.get(u'benaming_kunstwerk') and rkdimage.get(u'benaming_kunstwerk')[0]:
                    imageinfo[u'title_nl'] = rkdimage.get(u'benaming_kunstwerk')[0]
                else:
                    imageinfo[u'title_nl'] = u'(geen titel)'
                imageinfo[u'title_en'] = rkdimage.get(u'titel_engels')
                imageinfo[u'creator'] = rkdimage.get(u'kunstenaar')
                if rkdimage.get(u'toeschrijving'):
                    imageinfo[u'rkdartistid'] = rkdimage.get(u'toeschrijving')[0].get(u'naam_linkref')
                    # Overwrite creator with something more readable
                    imageinfo[u'creator'] = rkdimage.get(u'toeschrijving')[0].get(u'naam_inverted')
                imageinfo[u'invnum'] = None
                imageinfo[u'qid'] = None
                imageinfo[u'url'] = None
                for collectie in rkdimage.get(u'collectie'):
                    #First we have to extract the collection name. This can be a string or a dict
                    collectienaam_found = None
                    if collectie.get('collectienaam'):
                        if collectie.get('collectienaam')[0]:
                            if collectie.get('collectienaam')[0].get('collectienaam'):
                                collectienaam_found = collectie.get('collectienaam')[0].get('collectienaam')
                        else:
                            collectienaam_found = collectie.get('collectienaam')
                    # And is it the one we're looking for?
                    if collectienaam == collectienaam_found:
                        invnum = collectie.get('inventarisnummer')
                        if invnum:
                            for (regex, replace) in replacements:
                                invnum = re.sub(regex, replace, invnum)
                        imageinfo[u'invnum'] = invnum
                        imageinfo[u'startime'] = collectie.get('begindatum_in_collectie')
                        if invnum in invnumbers:
                            #pywikibot.output(u'Found a Wikidata id!')
                            imageinfo[u'qid'] = invnumbers.get(invnum).get('qid')
                            if invnumbers.get(invnum).get('url'):
                                imageinfo[u'url'] = invnumbers.get(invnum).get('url')
                            # Break out of the loop, otherwise the inventory might get overwritten
                            break

                yield imageinfo

    def rkdImagesArtistGenerator(self, artistname):
        """

        :param artistname:
        :return:
        """
        # https://api.rkd.nl/api/search/images?filters[collectienaam]=Rijksmuseum&format=json&start=100&rows=50
        start = 0
        rows = 50
        basesearchurl = u'https://api.rkd.nl/api/search/images?filters[naam]=%s&filters[objectcategorie][]=schilderij&format=json&start=%s&rows=%s'
        while True:
            searchUrl = basesearchurl % (urllib.parse.quote_plus(artistname), start, rows)
            searchPage = requests.get(searchUrl)
            searchJson = searchPage.json()
            if not searchJson.get('response') or not searchJson.get('response').get('numFound'):
                # If we don't get a valid response, just return
                return
            numfound = searchJson.get('response').get('numFound')
            if not start < numfound:
                return
            start = start + rows
            for rkdimage in  searchJson.get('response').get('docs'):
                imageinfo = {}
                imageinfo[u'id'] = rkdimage.get(u'priref')
                imageinfo[u'id'] = rkdimage.get(u'priref')
                if rkdimage.get(u'benaming_kunstwerk') and rkdimage.get(u'benaming_kunstwerk')[0]:
                    imageinfo[u'title_nl'] = rkdimage.get(u'benaming_kunstwerk')[0]
                else:
                    imageinfo[u'title_nl'] = u'(geen titel)'
                imageinfo[u'title_en'] = rkdimage.get(u'titel_engels')
                if imageinfo.get(u'title_nl')==imageinfo.get(u'title_en'):
                    imageinfo[u'title'] = imageinfo.get(u'title_nl')
                else:
                    imageinfo[u'title'] = u'%s / %s' % (imageinfo.get(u'title_nl'), imageinfo.get(u'title_en'))
                if rkdimage.get(u'datering'):
                    datering = rkdimage.get(u'datering')[0]
                    if datering.startswith(u'ca.'):
                        imageinfo[u'inception'] = datering[3:] + u' ' + datering[:3]
                    else:
                        imageinfo[u'inception'] = datering
                else:
                    imageinfo[u'inception'] = u''

                # Inception and collection
                imageinfo[u'creator'] = rkdimage.get(u'kunstenaar')
                #if rkdimage.get(u'toeschrijving'):
                #        imageinfo[u'rkdartistid'] = rkdimage.get(u'toeschrijving')[0].get(u'naam_linkref')
                #        # Overwrite creator with something more readable
                #        imageinfo[u'creator'] = rkdimage.get(u'toeschrijving')[0].get(u'naam_inverted')
                collection = u''
                if len(rkdimage.get(u'collectie')) > 0 :
                    for collectie in rkdimage.get(u'collectie'):
                        if collectie.get('collectienaam'):
                            collectienaam = None
                            if isinstance(collectie.get('collectienaam'), str):
                                # For some reason I sometimes get a list.
                                collectienaam = collectie.get('collectienaam')
                            elif collectie.get('collectienaam')[0].get('collectienaam'):
                                collectienaam = collectie.get('collectienaam')[0].get('collectienaam')
                            if collectienaam:
                                if collectienaam in self.rkd_collectienaam:
                                    collection += '{{Q|%s}}' % (self.rkd_collectienaam.get(collectienaam), )
                                else:
                                    collection += collectienaam
                            if collectie.get('inventarisnummer') or collectie.get('begindatum_in_collectie'):
                                collection = collection + u' (%s, %s)' % (collectie.get('inventarisnummer'),
                                                                          collectie.get('begindatum_in_collectie'),)
                            collection = collection + u'<BR/>\n'
                imageinfo[u'collection'] = collection
                yield imageinfo

    def process_collection(self, collection_qid):
        """

        :param collection_qid:
        :return:
        """
        if not self.collections.get(collection_qid):
            return
        collection_info = self.collections.get(collection_qid)
        if not collection_info:
            return
        collectienaam = collection_info.get('collectienaam')
        if not collectienaam:
            return
        replacements = collection_info.get('replacements')
        reportpage = collection_info.get('reportpage')

        if collection_info.get('use_collection'):
            collection_qid = collection_info.get('use_collection')

        currentimages = self.rkdimages_on_wikidata(collection_qid)
        invnumbers = self.wikidata_paintings_in_collection(collection_qid)

        gen = self.rkdimages_collection_generator(invnumbers, collectienaam, replacements)

        # Page consists of several sections
        autoaddedtext = u''  # List of auto added links in this run so user can review
        nextaddedtext = u''  # List of links that will be auto added on the next run\
        suggestionstext = u''  # List of suggestions that not completely add up
        failedtext = u''  # List of links that failed, but might have some suggestions
        text = u''  # Everything combined in the end

        text = text + u'This page gives an overview of [https://rkd.nl/en/explore/images#filters%%5Bcollectienaam%%5D=%s&filters%%5Bobjectcategorie%%5D%%5B%%5D=painting %s paintings in RKDimages] ' % (urllib.parse.quote_plus(collectienaam), collectienaam, )
        if collection_info.get('qid') == collection_qid:
            text = text + u'that are not in use on a painting item here on Wikidata in the {{Q|%s}} collection.\n' % (collection_qid, )
        else:
            text = text + u'that are not in use on a painting item here on Wikidata in the {{Q|%s}}/{{Q|%s}} collection.\n' % (collection_qid, collection_info.get('qid'))
        text = text + u'This pages is split up in several sections.\n__TOC__'

        autoaddedtext = autoaddedtext + u'\n== Auto added links ==\n'
        autoaddedtext = autoaddedtext + u'A maxiumum of %s links have been added in the previous bot run. Please review.\n' % (self.autoadd,)
        autoaddedtext = autoaddedtext + u'If you find an incorrect link, you have two options:\n'
        autoaddedtext = autoaddedtext + u'# Move it to the right painting in the same collection.\n'
        autoaddedtext = autoaddedtext + u'# Set the rank to deprecated so the bot won\'t add it again.\n'
        autoaddedtext = autoaddedtext + u'-----\n\n'

        nextaddedtext = nextaddedtext + u'\n== Links to add on next run ==\n'
        nextaddedtext = nextaddedtext + u'On this run the bot added a maximum of %s links. Next up are these links. \n' % (self.autoadd,)
        nextaddedtext = nextaddedtext + u'-----\n\n'

        suggestionstext = suggestionstext + u'== Suggestions to add ==\n'
        suggestionstext = suggestionstext + u'These suggestions are based on same collection and inventory number, but not a link to the same RKDartist.\n'
        suggestionstext = suggestionstext + u'This can have several reasons: \n'
        suggestionstext = suggestionstext + u'# It\'s a (completely) different painting. Just skip it.\n'
        suggestionstext = suggestionstext + u'# Same painting, but Wikidata and RKD don\'t agree on the creator. Just add the link. You could check and maybe correct the creator.\n'
        suggestionstext = suggestionstext + u'# Same painting, Wikidata and RKD agree on the creator, but the creator doesn\'t have the {{P|P650}} link. Just add the link. You can also add the missing RKDartists link to the creator.\n'
        suggestionstext = suggestionstext + u'-----\n\n'

        failedtext = failedtext + u'\n== No matches found ==\n'
        failedtext = failedtext + u'For the following links, no direct matches were found. This is the puzzle part.\n'
        failedtext = failedtext + u'# If the id is used on an item not in {{Q|%s}}, it will be mentioned here.\n' % (collection_qid, )
        failedtext = failedtext + u'# If painter has other works in {{Q|%s}}, these will be suggested.\n' % (collection_qid, )
        failedtext = failedtext + u'-----\n\n'

        #text = u'<big><big><big>This list contains quite a few mistakes. These will probably fill up at the top. Please check every suggestion before approving</big></big></big>\n\n'
        #text = text + u'This list was generated with a bot. If I was confident enough about the suggestions I would have just have the bot add them. '
        #text = text + u'Feel free to do any modifications in this page, but a bot will come along and overwrite this page every once in a while.\n\n'
        addtext = u''

        totalimages = 0
        totaltolink = 0
        totalautoadded = 0
        totalnextadd = 0
        totalsuggestions = 0
        totalfailedinuse = 0
        totailfailedoptions= 0
        totalfailedelse = 0
        bestsuggestions = ''
        othersuggestions = ''
        failedsuggestions = ''

        i = 0
        addcluster = 10

        addlink = u'** [https://tools.wmflabs.org/wikidata-todo/quick_statements.php?list={{subst:urlencode:%s}} Add the previous %s]\n'

        imagedict = {}
        for rkdimageid in gen:
            totalimages += 1
            if rkdimageid.get('id') not in currentimages:
                invnum = rkdimageid.get('invnum')
                if not invnum:
                    invnum = ''
                if invnum not in imagedict:
                    imagedict[invnum] = []
                imagedict[invnum].append(rkdimageid)

        for invnum in sorted(list(imagedict.keys())):
            for rkdimageid in imagedict.get(invnum):
                totaltolink = totaltolink + 1
                # We found a match, just not sure how solid it is
                if rkdimageid.get(u'qid'):
                    # We found the same inventory number. If the creator matches too than I'm confident enough to add it by bot
                    if invnumbers[invnum].get(u'rkdartistid') and \
                                    invnumbers[invnum].get(u'rkdartistid') == rkdimageid.get(u'rkdartistid') and \
                            rkdimageid.get(u'qid') not in self.all_rkdimages_wikidata.values():
                        if self.autoadd > 0:
                            summary = u'Based on [[%s]]' % (collection_qid,)
                            summary = summary + u' / %(invnum)s / https://rkd.nl/explore/artists/%(rkdartistid)s (name: %(creator)s)' % rkdimageid
                            #summary = u'Based on [[%s]] / %s / [https://rkd.nl/explore/artists/%s %s]' % (collection_qid,
                            #                                                                            rkdimageid.get(u'invnum'),
                            #                                                                            rkdimageid.get(u'rkdartistid'),
                            #                                                                            rkdimageid.get(u'creator'))
                            addsuccess = self.addRkdimagesLink(rkdimageid.get('qid'), rkdimageid.get('id'), summary)
                            if addsuccess:
                                autoaddedtext = autoaddedtext + u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid
                                self.autoadd = self.autoadd - 1
                                totalautoadded = totalautoadded + 1
                            else:
                                suggestionstext = suggestionstext + u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid
                                othersuggestions += u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid

                                #addtext = addtext + u'%(qid)s\tP350\t"%(id)s"\n' % rkdimageid
                                i = i + 1
                                totalsuggestions = totalsuggestions + 1
                                #if not i % addcluster:
                                #    suggestionstext = suggestionstext + addlink % (addtext, addcluster)
                                #    addtext = u''

                        else:
                            nextaddedtext = nextaddedtext + u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid
                            bestsuggestions += u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid
                            totalnextadd = totalnextadd + 1
                    # Something is not adding up, add it to the suggestions list
                    else:
                        suggestionstext = suggestionstext + u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid
                        othersuggestions += u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid

                        #addtext = addtext + u'%(qid)s\tP350\t"%(id)s"\n' % rkdimageid
                        i = i + 1
                        totalsuggestions = totalsuggestions + 1
                        #if not i % addcluster:
                        #    suggestionstext = suggestionstext + addlink % (addtext, addcluster)
                        #    addtext = u''

                    #if i > 5000:
                    #    break
                # Failed to find a Qid to suggest
                else:
                    failedtext = failedtext + u'* [https://rkd.nl/explore/images/%(id)s %(id)s] -  %(invnum)s - %(title_nl)s - %(title_en)s' % rkdimageid
                    failedsuggestions += u'* [https://rkd.nl/explore/images/%(id)s %(id)s] -  %(invnum)s - %(title_nl)s - %(title_en)s' % rkdimageid
                    failedsuggestions += u' {{Q|%s}}' % (collection_info.get('qid'),)
                    # The id is used on some other Wikidata item.
                    if rkdimageid['id'] in self.all_rkdimages_wikidata.keys():
                        failedtext = failedtext + u' -> Id already in use on {{Q|%s}}\n' % self.all_rkdimages_wikidata.get(rkdimageid['id'])
                        failedsuggestions += u' -> Id already in use on {{Q|%s}}\n' % self.all_rkdimages_wikidata.get(rkdimageid['id'])
                        totalfailedinuse = totalfailedinuse + 1

                    # Anonymous (rkd id 1984) will make the list explode
                    elif not rkdimageid.get(u'rkdartistid')==u'1984':
                        firstsuggestion = True
                        for inv, invitem in invnumbers.items():
                            if invitem.get(u'rkdartistid') and not invitem.get(u'rkdimageid') \
                                    and invitem.get(u'rkdartistid')==rkdimageid.get(u'rkdartistid'):
                                if firstsuggestion:
                                    failedtext = failedtext + u' -> Paintings by \'\'%s\'\' that still need a link: ' % (rkdimageid.get(u'creator'),)
                                    failedsuggestions += u' -> Paintings by \'\'%s\'\' that still need a link: ' % (rkdimageid.get(u'creator'),)
                                    firstsuggestion = False
                                    totailfailedoptions = totailfailedoptions + 1
                                else:
                                    failedtext = failedtext + u', '
                                    failedsuggestions += u', '
                                failedtext = failedtext + u'{{Q|%s}}' % (invitem.get(u'qid'),)
                                failedsuggestions += u'{{Q|%s}}' % (invitem.get(u'qid'),)
                        failedtext = failedtext + u'\n'
                        failedsuggestions += u'\n'
                        if firstsuggestion:
                            totalfailedelse = totalfailedelse + 1
                    else:
                        failedtext = failedtext + u'\n'
                        failedsuggestions += u'\n'
                        totalfailedelse = totalfailedelse + 1

        # Add the last link if needed
        if addtext:
            suggestionstext = suggestionstext + addlink % (addtext, i % addcluster)

        text = text + autoaddedtext
        text = text + nextaddedtext
        text = text + suggestionstext
        text = text + failedtext
        text = text + u'\n== Statistics ==\n'
        text = text + u'* RKDimages in this collection: %s\n' % (totalimages,)
        text = text + u'* Needing a link: %s\n' % (totaltolink,)
        text = text + u'* Auto added links this run: %s\n' % (totalautoadded,)
        text = text + u'* To auto add nex run: %s\n' % (totalnextadd,)
        text = text + u'* Number of suggestions: %s\n' % (totalsuggestions,)
        text = text + u'* No suggestion, but in use on another item: %s\n' % (totalfailedinuse,)
        text = text + u'* No suggestion, but paintings available by the same painter: %s\n' % (totailfailedoptions,)
        text = text + u'* No suggestion and nothing found: %s\n' % (totalfailedelse,)

        text = text + u'\n[[Category:WikiProject sum of all paintings RKD to match|%s]]' % (collectienaam, )

        page = pywikibot.Page(self.repo, title=reportpage)

        if collection_info.get('completely_matched') and totaltolink == 0:
            text = 'The collection [https://rkd.nl/en/explore/images#filters%%5Bcollectienaam%%5D=%s&filters%%5Bobjectcategorie%%5D%%5B%%5D=painting %s paintings in RKDimages] ' % (urllib.parse.quote_plus(collectienaam), collectienaam, )
            if collection_info.get('qid') == collection_qid:
                text = text + 'has been completely matched to the {{Q|%s}} collection.\n' % (collection_qid, )
            else:
                text = text + 'has been completely matched to the {{Q|%s}}/{{Q|%s}} collection.\n' % (collection_qid, collection_info.get('qid'))
            text = text + 'Have a look at [[Wikidata:WikiProject sum of all paintings/RKD to match#Collections]] for other collections to match.\n'
            text = text + u'\n[[Category:WikiProject sum of all paintings RKD completely matched|%s]]' % (collectienaam, )
            summary = 'All %s RKDimages in this collection have been matched' % (totalimages,)
        else:
            summary = u'%s RKDimages, %s to link, autoadd now %s, autoadd next %s , suggestions %s, failed in use %s, failed with options %s, left fails %s' % (totalimages,
                                                                                                                                                                totaltolink,
                                                                                                                                                                totalautoadded,
                                                                                                                                                                totalnextadd,
                                                                                                                                                                totalsuggestions,
                                                                                                                                                                totalfailedinuse,
                                                                                                                                                                totailfailedoptions,
                                                                                                                                                                totalfailedelse,
                                                                                                                                                            )
        page.put(text[0:2000000], summary)

        collectionstats = {u'collectionid': collection_qid,
                           u'collectienaam': collectienaam,
                           u'reportpage': reportpage,
                           u'totalimages': totalimages,
                           u'totaltolink': totaltolink,
                           u'totalautoadded': totalautoadded,
                           u'totalnextadd': totalnextadd,
                           u'totalsuggestions': totalsuggestions,
                           u'totalfailedinuse': totalfailedinuse,
                           u'totailfailedoptions' : totailfailedoptions,
                           u'totalfailedelse': totalfailedelse,
                           u'bestsuggestions': bestsuggestions,
                           u'othersuggestions': othersuggestions,
                           u'failedsuggestions': failedsuggestions,
                           u'completely_matched': collection_info.get('completely_matched')
                           }
        self.collection_stats.append(collectionstats)

    def process_artist(self, artist_qid):

        if not self.artists.get(artist_qid):
            return
        artistname = self.artists.get(artist_qid).get('artistname')
        #replacements = self.artists.get(artist_qid).get('artistname')
        reportpage = self.artists.get(artist_qid).get('reportpage')

        text = u''  # Everything combined in the end

        text = text + u'This page gives an overview of [https://rkd.nl/en/explore/images#filters%%5Bnaam%%5D=%s&filters%%5Bobjectcategorie%%5D%%5B%%5D=painting %s paintings in RKDimages] ' % (artistname.replace(u' ', u'%20'), artistname, )
        text = text + u'that are not in use on a painting item (left table) and the painting items by {{Q|%s}} that do not have a link to RKDimages (right table).\n' % (artist_qid, )
        text = text + u'You can help by connecting these two lists.\n'
        text = text + u'{| style=\'width:100%\'\n| style=\'width:50%;vertical-align: top;\' |\n'
        text = text + u'== RKD with no link to Wikidata ==\n'

        text = text + u'{| class=\'wikitable sortable\' style=\'width:100%\'\n'
        text = text + u'! RKDimage id\n'
        text = text + u'! Title\n'
        text = text + u'! Inception\n'
        text = text + u'! Collection(s)\n'

        genrkd = self.rkdImagesArtistGenerator(artistname)
        rkdcount = 0
        rkdsuggestioncount = 0
        for imageinfo in genrkd:
            rkdcount = rkdcount + 1
            if imageinfo.get('id') not in self.all_rkdimages_wikidata:
                rkdsuggestioncount = rkdsuggestioncount + 1
                text = text + u'|-\n'
                text = text + u'| [https://rkd.nl/explore/images/%(id)s %(id)s]\n| %(title)s \n| %(inception)s \n| %(collection)s\n' % imageinfo

        text = text + u'|}\n| style=\'width:50%;vertical-align: top;\' |\n'
        text = text + u'== Wikidata with no link to RKD ==\n'
        text = text + u'{| class=\'wikitable sortable\' style=\'width:100%\'\n'
        text = text + u'! Painting\n'
        text = text + u'! Inception\n'
        text = text + u'! Collection\n'
        #text = text + u'! Title (nl)\n'
        #text = text + u'! Title (en)\n'
        #text = text + u'! Collection(s)\n'

        genwd = self.wikidata_paintings_for_artist(artist_qid)

        wdsuggestioncount = 0
        for painting in genwd:
            wdsuggestioncount = wdsuggestioncount + 1
            text = text + u'|-\n'
            text = text + u'| {{Q|%(qid)s}} || %(inception)s ||' % painting
            if painting.get(u'collection'):
                text = text + u' {{Q|%(collection)s}} \n' % painting
            else:
                text = text + u'\n'

        text = text + u'|}\n\n'

        text = text + u'\n[[Category:WikiProject sum of all paintings RKD to match|%s]]' % (artistname, )

        page = pywikibot.Page(self.repo, title=reportpage)
        summary = u'Updating RKD artist page'
        page.put(text, summary)

        artiststats = {u'artistid' : artist_qid,
                       u'artistname' : artistname,
                       u'reportpage' : reportpage,
                       u'rkdcount' : rkdcount,
                       u'rkdsuggestioncount' : rkdsuggestioncount,
                       u'wdsuggestioncount' : wdsuggestioncount,
                       }
        self.artist_stats.append(artiststats)

    def addRkdimagesLink(self, itemTitle, rkdid, summary):
        item = pywikibot.ItemPage(self.repo, title=itemTitle)
        if not item.exists():
            return False
        if item.isRedirectPage():
            return False
        data = item.get()
        claims = data.get('claims')
        if u'P350' in claims:
            claim = claims.get('P350')[0]
            if claim.getTarget()==u'%s' % (rkdid,):
                pywikibot.output(u'Already got the right link on %s to rkdid %s!' % (itemTitle, rkdid))
                return True
            pywikibot.output(u'Already got a link to %s on %s, I\'m trying to add %s' % (claim.getTarget(),
                                                                                         itemTitle,
                                                                                         rkdid))
            return False

        newclaim = pywikibot.Claim(self.repo, u'P350')
        newclaim.setTarget(u'%s' % (rkdid,))
        pywikibot.output(summary)
        item.addClaim(newclaim, summary=summary)

        return True

    def process_period(self, period):
        """

        :param period:
        :return:
        """
        if period == 'oldest':
            generator = self.get_period_generator('asc')
            page_title = 'Wikidata:WikiProject sum of all paintings/RKD to match/Oldest additions'
            see_also = 'See also the [[Wikidata:WikiProject sum of all paintings/RKD to match/Recent additions|Recent additions]].\n\n'
            sort_key = 'Oldest additions'
        elif period == 'newest':
            generator = self.get_period_generator('desc')
            page_title = 'Wikidata:WikiProject sum of all paintings/RKD to match/Recent additions'
            see_also = 'See also the [[Wikidata:WikiProject sum of all paintings/RKD to match/Oldest additions|Oldest additions]].\n\n'
            sort_key = 'Recent additions'
        else:
            return

        text = u'This is an overview of additions to [https://rkd.nl/en/explore/images#filters%5Bobjectcategorie%5D%5B%5D=painting&start=0 paintings in RKDimages] to [[Wikidata:WikiProject sum of all paintings/RKD to match|match]].\n'
        #text += u'This page lists %s suggestions from %s to %s.\n' % (self.maxlength,
        #                                                              self.highestrkdimage,
        #                                                              self.lowestrkdimage)
        text += see_also
        text += u'{| class="wikitable sortable"\n'
        text += u'|-\n! RKDimage !! Title !! Creator !! Collection !! Query !! Create\n'
        lowest_rkdimage = None
        highest_rkdimage = None
        for foundimage in generator:
            if not lowest_rkdimage:
                lowest_rkdimage = foundimage.get('id')
            elif foundimage.get('id') < lowest_rkdimage:
                lowest_rkdimage = foundimage.get('id')
            if not highest_rkdimage:
                highest_rkdimage = foundimage.get('id')
            elif foundimage.get('id') > highest_rkdimage:
                highest_rkdimage = foundimage.get('id')

            text += u'|-\n'
            text += u'| [%(url)s %(id)s]\n' % foundimage
            text += u'| %(title_nl)s / %(title_en)s\n' % foundimage
            if foundimage.get(u'artistqid'):
                text += '| {{Q|%(artistqid)s}} <small>([https://rkd.nl/explore/artists/%(rkdartistid)s %(creator)s])</small>\n' % foundimage
            else:
                text += '| [https://rkd.nl/explore/artists/%(rkdartistid)s %(creator)s]\n' % foundimage


            text += u'| %(collection)s\n' % foundimage
            text += u'| \n'
            text += u'| \n'
        text += u'|}\n'
        text += u'\n[[Category:WikiProject sum of all paintings RKD to match| %s]]' % (sort_key, )

        page = pywikibot.Page(self.repo, title=page_title)
        summary = u'Updating %s RKDimages suggestions with %s suggestions from %s to %s' % (period,
                                                                                            self.max_length,
                                                                                            lowest_rkdimage,
                                                                                            highest_rkdimage)
        page.put(text, summary)

    def get_period_generator(self, sort_priref):
        """
        Get a generator that returns metadata from RKDimages
        :param sort_priref: asc or desc
        :return: A generator yielding metdata
        """
        start = 0
        rows = 50
        base_search_url = 'https://api.rkd.nl/api/search/images?filters[objectcategorie][]=schilderij&sort[priref]=%s&format=json&start=%s&rows=%s'
        count = 0
        while count < self.max_length:
            search_url = base_search_url % (sort_priref, start, rows)
            search_page = requests.get(search_url)
            search_json = search_page.json()
            if not search_json.get('response') or not search_json.get('response').get('numFound'):
                # If we don't get a valid response, just return
                return
            numfound = search_json.get('response').get('numFound')

            if not start < numfound:
                return
            start = start + rows
            for rkdimage in search_json.get('response').get('docs'):
                rkdimage_id = rkdimage.get('priref')

                if rkdimage_id not in self.all_rkdimages_wikidata:
                    imageinfo = {}
                    imageinfo['id'] = rkdimage_id
                    imageinfo[u'url'] = 'https://rkd.nl/explore/images/%s'  % (rkdimage_id,)
                    if rkdimage.get('benaming_kunstwerk') and rkdimage.get('benaming_kunstwerk')[0]:
                        imageinfo['title_nl'] = rkdimage.get('benaming_kunstwerk')[0]
                    else:
                        imageinfo[u'title_nl'] = '(geen titel)'
                    imageinfo['title_en'] = rkdimage.get('titel_engels')
                    imageinfo['creator'] = rkdimage.get('kunstenaar')
                    if rkdimage.get('toeschrijving'):
                        imageinfo[u'rkdartistid'] = rkdimage.get(u'toeschrijving')[0].get(u'naam_linkref')
                        # Overwrite creator with something more readable
                        imageinfo[u'creator'] = rkdimage.get(u'toeschrijving')[0].get(u'naam_inverted')
                    imageinfo['artistqid'] = None
                    if imageinfo.get('rkdartistid') in self.all_rkdartists_wikidata:
                        imageinfo[u'artistqid'] = self.all_rkdartists_wikidata.get(imageinfo.get('rkdartistid'))

                    collection = ''
                    if len(rkdimage.get(u'collectie')) > 0 :
                        for collectie in rkdimage.get('collectie'):
                            if collectie.get('collectienaam'):
                                collectienaam = None
                                if isinstance(collectie.get('collectienaam'), str):
                                    # For some reason I sometimes get a list.
                                    collectienaam = collectie.get('collectienaam')
                                elif collectie.get('collectienaam')[0].get('collectienaam'):
                                    collectienaam = collectie.get('collectienaam')[0].get('collectienaam')
                                if collectienaam:
                                    if collectienaam in self.rkd_collectienaam:
                                        collection_qid = self.rkd_collectienaam.get(collectienaam)
                                        if collection_qid in self.collections:
                                            collection += '[[%s|%s]]' % (self.collections.get(collection_qid).get('reportpage'), collectienaam)
                                        else:
                                            collection += '{{Q|%s}}' % (self.rkd_collectienaam.get(collectienaam), )
                                    else:
                                        collection += collectienaam
                                if collectie.get('inventarisnummer') or collectie.get('begindatum_in_collectie'):
                                    collection = collection + u' (%s, %s)' % (collectie.get('inventarisnummer'),
                                                                              collectie.get('begindatum_in_collectie'),)
                                collection = collection + u'<BR/>\n'
                    imageinfo['collection'] = collection
                    count += 1
                    yield imageinfo

    def publish_statistics(self):
        page = pywikibot.Page(self.repo, title=u'Wikidata:WikiProject sum of all paintings/RKD to match')
        text = u'This pages gives an overview of [https://rkd.nl/en/explore/images#filters%5Bobjectcategorie%5D%5B%5D=painting paintings in RKDimages] to match with paintings in [[Wikidata:WikiProject sum of all paintings/Collection|collections]] and [[Wikidata:WikiProject sum of all paintings/Creator|creators]] on Wikidata.\n'
        text = text + u'\nSee also the [[Wikidata:WikiProject sum of all paintings/RKD to match/Oldest additions|oldest]] and [[Wikidata:WikiProject sum of all paintings/RKD to match/Recent additions|recent additions]] to RKDimages.\n'
        text = text + u'== Collections ==\n'
        text = text + u'{| class="wikitable sortable"\n'
        text = text + u'! Collection !! RKDimages !! Page !! Total RKDimages || Left to match !! Auto added !! Auto next !! Suggestions !! Failed in use !! Failed options !! Failed else\n'

        totalimages = 0
        totaltolink = 0
        totalautoadded = 0
        totalnextadd = 0
        totalsuggestions = 0
        totalfailedinuse = 0
        totailfailedoptions= 0
        totalfailedelse = 0
        bestsuggestions = ''
        othersuggestions = ''
        failedsuggestions = ''
        completed_collections = ''

        for collectionstats in self.collection_stats:
            rkdimageslink = '[https://rkd.nl/en/explore/images#filters%%5Bcollectienaam%%5D=%s&filters%%5Bobjectcategorie%%5D%%5B%%5D=painting %s in RKDimages] ' % (collectionstats.get('collectienaam').replace(u' ', u'%20'),
                                                                                                                                                                     collectionstats.get('collectienaam'), )
            pagelink = u'[[%s|%s]]' % (collectionstats.get(u'reportpage'),
                                       collectionstats.get(u'reportpage').replace(u'Wikidata:WikiProject sum of all paintings/RKD to match/', u''),
                                       )
            text = text + u'|-\n'
            text = text + u'|| {{Q|%s}} ' % (collectionstats.get(u'collectionid'),)
            text = text + u'|| %s ' % (rkdimageslink,)
            text = text + u'|| %s ' % (pagelink,)
            text = text + u'|| %s ' % (collectionstats.get(u'totalimages'),)
            text = text + u'|| %s ' % (collectionstats.get(u'totaltolink'),)
            text = text + u'|| %s ' % (collectionstats.get(u'totalautoadded'),)
            text = text + u'|| %s ' % (collectionstats.get(u'totalnextadd'),)
            text = text + u'|| %s ' % (collectionstats.get(u'totalsuggestions'),)
            text = text + u'|| %s ' % (collectionstats.get(u'totalfailedinuse'),)
            text = text + u'|| %s ' % (collectionstats.get(u'totailfailedoptions'),)
            text = text + u'|| %s \n' % (collectionstats.get(u'totalfailedelse'),)

            totalimages = totalimages + collectionstats.get(u'totalimages')
            totaltolink = totaltolink + collectionstats.get(u'totaltolink')
            totalautoadded = totalautoadded + collectionstats.get(u'totalautoadded')
            totalnextadd = totalnextadd + collectionstats.get(u'totalnextadd')
            totalsuggestions = totalsuggestions + collectionstats.get(u'totalsuggestions')
            totalfailedinuse = totalfailedinuse + collectionstats.get(u'totalfailedinuse')
            totailfailedoptions = totailfailedoptions + collectionstats.get(u'totailfailedoptions')
            totalfailedelse = totalfailedelse + collectionstats.get(u'totalfailedelse')
            bestsuggestions += collectionstats.get(u'bestsuggestions')  # FIXME: Move to different list
            othersuggestions += collectionstats.get('othersuggestions')  # FIXME: Move to different list too
            if collectionstats.get('completely_matched'):
                failedsuggestions += collectionstats.get('failedsuggestions')  # FIXME: Move to different list too
            elif collectionstats.get(u'totalimages') > 0 and collectionstats.get(u'totaltolink') == 0:
                completed_collections += '* %s\n' % (pagelink,)

        text = text + u'|- class="sortbottom"\n'
        text = text + u'| || || || %s || %s || %s || %s || %s || %s || %s || %s\n' % (totalimages,
                                                                                      totaltolink,
                                                                                      totalautoadded,
                                                                                      totalnextadd,
                                                                                      totalsuggestions,
                                                                                      totalfailedinuse,
                                                                                      totailfailedoptions,
                                                                                      totalfailedelse,
                                                                                )
        text = text + u'|}\n\n'
        text = text + u'<small>Collections configuration is at [[User:BotMultichillT/rkdimages collections.js]]</small>\n'
        text = text + u'=== Best suggestions ===\n'
        text = text + bestsuggestions + '\n\n'
        text = text + u'=== Other suggestions ===\n'
        text = text + othersuggestions + '\n\n'
        text = text + u'=== Suggestions from previously completely matched collections ===\n'
        text = text + failedsuggestions + '\n\n'
        if completed_collections:
            text = text + u'=== Completed collections ===\n'
            text = text + u'These collections appear to have been completed. Configuration at [[User:BotMultichillT/rkdimages collections.js]] should be updated.\n'
            text = text + completed_collections + '\n\n'

        totalrkd = 0
        totalrkdsuggestions = 0
        totalwikidata = 0

        text = text + u'== Artists ==\n'
        text = text + u'{| class="wikitable sortable"\n'
        text = text + u'! Artist !! RKDimages !! Page !! Total RKDimages !! RKDimages left to match !! Wikidata possibilities\n'

        for artiststats in self.artist_stats:
            rkdimageslink = '[https://rkd.nl/en/explore/images#filters%%5Bnaam%%5D=%s&filters%%5Bobjectcategorie%%5D%%5B%%5D=painting %s in RKDimages] ' % (artiststats.get('artistname').replace(u' ', u'%20'),
                                                                                                                                                            artiststats.get('artistname'), )
            pagelink = u'[[%s|%s]]' % (artiststats.get(u'reportpage'),
                                       artiststats.get(u'reportpage').replace(u'Wikidata:WikiProject sum of all paintings/RKD to match/', u''),
                                       )
            text = text + u'|-\n'
            text = text + u'|| {{Q|%s}} ' % (artiststats.get(u'artistid'),)
            text = text + u'|| %s ' % (rkdimageslink,)
            text = text + u'|| %s ' % (pagelink,)
            text = text + u'|| %s ' % (artiststats.get(u'rkdcount'),)
            text = text + u'|| %s ' % (artiststats.get(u'rkdsuggestioncount'),)
            text = text + u'|| %s \n' % (artiststats.get(u'wdsuggestioncount'),)

            totalrkd = totalrkd + artiststats.get(u'rkdcount')
            totalrkdsuggestions = totalrkdsuggestions + artiststats.get(u'rkdsuggestioncount')
            totalwikidata = totalwikidata + artiststats.get(u'wdsuggestioncount')

        text = text + u'|- class="sortbottom"\n'
        text = text + u'| || || || %s || %s || %s\n' % (totalrkd,
                                                        totalrkdsuggestions,
                                                        totalwikidata,
                                                        )
        text = text + u'|}\n\n[[Category:WikiProject sum of all paintings RKD to match| ]]'

        summary = u'%s RKDimages, %s to link, autoadd now %s, autoadd next %s , suggestions %s, failed in use %s, failed with options %s, left fails %s' % (totalimages,
                                                                                                                                                            totaltolink,
                                                                                                                                                            totalautoadded,
                                                                                                                                                            totalnextadd,
                                                                                                                                                            totalsuggestions,
                                                                                                                                                            totalfailedinuse,
                                                                                                                                                            totailfailedoptions,
                                                                                                                                                            totalfailedelse,
                                                                                                                                                        )
        page.put(text, summary)

    def guess_collection_name(self, qid, collection_names, sample_size=15, verbose=False):
        """
        Try to guess the name of the collection for qid
        :param qid: The id of the Wikidata item
        :param collection_names: List of collection names we already found and should be ignored
        :param sample_size: How many sample items should be retrieved
        :return: The name of the collection in RKDimages
        """
        collections = {}
        result_count = 0
        query = """SELECT ?item ?id (SHA1(CONCAT(str(?item),str(NOW()), str(RAND()))) as ?random) WHERE {
      ?item wdt:P350 ?id;
                wdt:P31 wd:Q3305213 ;
                p:P195/ps:P195 wd:%s .  
      } ORDER BY (?random)
    LIMIT %s""" % (qid, sample_size)
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            result_count += 1
            qid = resultitem.get('item').replace('http://www.wikidata.org/entity/', '')
            rkdimages_id = resultitem.get('id')
            rkdimages_url = 'https://api.rkd.nl/api/record/images/%s?format=json&language=en' % (rkdimages_id,)

            # Do some checking if it actually exists?
            rkdimages_page = requests.get(rkdimages_url)
            try:
                rkdimages_json = rkdimages_page.json()
                for rkdimage in rkdimages_json.get('response').get('docs'):
                    if len(rkdimage.get('collectie')) > 0 :
                        for collectie in rkdimage.get('collectie'):
                            collectienaam = collectie.get('collectienaam')
                            if not collectienaam in collection_names:
                                if collectienaam not in collections:
                                    collections[collectienaam] = 0
                                collections[collectienaam] += 1
            except ValueError:  # Throws simplejson.errors.JSONDecodeError
                pywikibot.output('Got invalid json for%s, skipping' % (rkdimages_id,))
                return None
        if verbose:
            pywikibot.output(json.dumps(collections, indent=4, sort_keys=True))

        # Adjust the sample size for collections which are still smaller than the sample size
        if result_count < sample_size:
            sample_size = result_count

        top_collections = sorted(collections, key=collections.get, reverse=True)

        if not collections:
            return None
        if collections.get(top_collections[0]) * 2 > sample_size:
            if len(top_collections) == 1:
                return top_collections[0]
            elif len(top_collections) > 1 and collections.get(top_collections[0]) > collections.get(top_collections[1]):
                return top_collections[0]
        return None

    def check_collections(self):
        """
        :return: Nothing, print the results
        """
        base_search_url = 'https://api.rkd.nl/api/search/images?filters[collectienaam]=%s&filters[objectcategorie][]=schilderij&format=json&start=0&rows=10'
        use_collections = []
        for collection in self.manual_collections:
            collectienaam = self.manual_collections.get(collection).get('collectienaam')
            if self.manual_collections.get(collection).get('use_collection'):
                use_collections.append(self.manual_collections.get(collection).get('use_collection'))
            if collectienaam:
                search_url = base_search_url % (urllib.parse.quote_plus(collectienaam),)
                search_page = requests.get(search_url)
                number_found = search_page.json().get('response').get('numFound')
                if number_found == 0:
                    pywikibot.output('On %s the collectienaam %s did not return anything at all' % (collection, collectienaam))
                    collectienaam = self.guess_collection_name(collection, [], sample_size=15)
                    if collectienaam:
                        pywikibot.output('On %s the collectienaam should be set to "%s"' % (collection, collectienaam))

        for collection in self.automatic_collections:
            if not self.automatic_collections.get(collection) and collection not in use_collections:
                pywikibot.output('Trying to guess a collection of %s' % (collection,))
                collectienaam = self.guess_collection_name(collection, [], sample_size=25, verbose=True)
                pywikibot.output('The trying for collection %s returned "%s"' % (collection, collectienaam))

    def find_collections(self):
        """
        Find possible collections
        :return:
        """
        collection_names = {}
        start = 0
        rows = 50
        base_search_url = 'https://api.rkd.nl/api/search/images?filters[objectcategorie][]=schilderij&sort[priref]=desc&format=json&start=%s&rows=%s'

        while True:
            search_url = base_search_url % (start, rows)
            search_page = requests.get(search_url)
            search_json = search_page.json()
            if not search_json.get('response') or not search_json.get('response').get('numFound'):
                # If we don't get a valid response, just go to the next page
                continue
            numfound = search_json.get('response').get('numFound')

            if not start < numfound:
                break
            start = start + rows
            for rkdimage in search_json.get('response').get('docs'):
                if len(rkdimage.get('collectie')) > 0 :
                    for collectie in rkdimage.get('collectie'):
                        if collectie.get('collectienaam'):
                            collectienaam = None
                            if isinstance(collectie.get('collectienaam'), str):
                                # For some reason I sometimes get a list.
                                collectienaam = collectie.get('collectienaam')
                            elif collectie.get('collectienaam')[0].get('collectienaam'):
                                collectienaam = collectie.get('collectienaam')[0].get('collectienaam')
                            if collectienaam:
                                if collectienaam not in self.rkd_collectienaam:
                                    if collectienaam not in collection_names:
                                        collection_names[collectienaam] = 0
                                    collection_names[collectienaam] +=1
        pywikibot.output('Overview of collections not used yet on Wikidata:')
        for collectienaam in sorted(collection_names, key=collection_names.get, reverse=True)[:100]:
            pywikibot.output('* "%s" - %s' % (collectienaam, collection_names.get(collectienaam)))


def main(*args):
    """
    :param args:
    :return:
    """
    run_mode = 'full'
    work_qid = None
    autoadd = 0

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-collectionid:'):
            run_mode = 'single_collection'
            if len(arg) == 14:
                work_qid = pywikibot.input(
                        u'Please enter the collectionid you want to work on:')
            else:
                work_qid = arg[14:]
        elif arg.startswith('-artistid:'):
            run_mode = 'single_artist'
            if len(arg) == 10:
                work_qid = pywikibot.input(
                        u'Please enter the aristid you want to work on:')
            else:
                work_qid = arg[10:]
        elif arg.startswith('-autoadd:'):
            if len(arg) == 9:
                autoadd = int(pywikibot.input(
                        u'Please enter the number of items you want to update automatically:'))
            else:
                autoadd = int(arg[9:])
        elif arg == '-checkcollections':
            run_mode = 'check_collections'
        elif arg == '-findcollections':
            run_mode = 'find_collections'
        elif arg == '-oldest':
            run_mode = 'oldest'
        elif arg == '-newest':
            run_mode = 'newest'

    rkimages_matcher = RKDimagesMatcher(run_mode=run_mode, work_qid=work_qid, autoadd=autoadd)
    rkimages_matcher.run()


if __name__ == "__main__":
    main()
