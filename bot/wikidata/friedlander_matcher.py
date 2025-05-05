#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Tool to match Friedlander with Wikidata
"""
import pywikibot
import requests
import pywikibot.data.sparql
import time
import re
import json
#import urllib.parse
import os.path


class FriedlanderMatcher:
    """
    Program to do the matching of Friedlander with Wikidata
    """
    def __init__(self, friedlander_json):
        """
        Setup the bot
        """
        self.friedlander_ids = {}
        self.friedlander_artists = {}
        self.friedlander_locations = {}
        self.friedlander_volumes = {}
        for artwork in friedlander_json:
            friedlander_id = artwork.get('friedlanderId')
            self.friedlander_ids[friedlander_id] = artwork

            friedlander_artist = artwork.get('artist')  # .encode('cp1252').decode('utf8') solved?
            if friedlander_artist not in self.friedlander_artists:
                self.friedlander_artists[friedlander_artist] = []
            self.friedlander_artists[friedlander_artist].append(artwork)

            if artwork.get('location').strip():
                friedlander_location = artwork.get('location').strip()
                if friedlander_location not in self.friedlander_locations:
                    self.friedlander_locations[friedlander_location] = []
                self.friedlander_locations[friedlander_location].append(artwork)
            #if artwork.get('reference details') and artwork.get('reference details').get('volume'):
            if artwork.get('reference'):
                friedlander_volume = artwork.get('reference')[0:2].lstrip('0')
                if friedlander_volume not in self.friedlander_volumes:
                    self.friedlander_volumes[friedlander_volume] = []
                self.friedlander_volumes[friedlander_volume].append(artwork)

        self.repo = pywikibot.Site().data_repository()
        self.friedlander_on_wikidata = self.get_usage_on_wikidata('P11918')  # self.get_friedlander_on_wikidata()
        self.balat_on_wikidata = self.get_usage_on_wikidata('P3293')
        self.rkd_on_wikidata = self.get_usage_on_wikidata('P350')
        self.data_session = requests.Session()

        self.artists = {'Albrecht Bouts': 'Q380743',
                        'Colijn de Coter': 'Q1108307',
                        'Dirk Bouts': 'Q313561',
                        'Geertgen tot Sint Jans': 'Q360888',
                        'Gerard David': 'Q333380',
                        'Goossen van der Weyden': 'Q1537756',
                        'Hans Memling': 'Q106851',
                        'Hieronymus Bosch': 'Q130531',
                        'Hugo van der Goes': 'Q215251',
                        'Jacques Daret': 'Q728249',
                        'Jan van Eyck': 'Q102272',
                        'Joos van Gent': 'Q515796',
                        'Master of 1499': 'Q996886',
                        'Master of Flémalle': 'Q653719',
                        'Master of Frankfurt': 'Q204874',
                        'Master of Hoogstraten': 'Q16748690',
                        'Master of the Baroncelli Portraits': 'Q15105353',
                        'Master of the Embroidered Foliage': 'Q1918642',
                        'Master of the Joseph Sequence': 'Q576860',
                        'Master of the Khanenko Adoration': 'Q1738339',
                        'Master of the Legend of Saint Augustine': 'Q18516733',
                        'Master of the Legend of Saint Barbara': 'Q1233615',
                        'Master of the Legend of Saint Catherine': 'Q17006553',
                        'Master of the Legend of Saint Lucy': 'Q963476',
                        'Master of the Legend of Saint Ursula': 'Q617611',
                        'Master of the Legend of the Magdalen': 'Q2364288',
                        'Master of the Morrison Triptych': 'Q1918577',
                        'Master of the Portraits of Princes': 'Q1701814',
                        'Master of the Prado Redemption, Vranke van der Stockt': 'Q7942584',
                        'Master of the View of Saint Gudula': 'Q1918711',
                        'Master of the Virgo inter Virgines': 'Q945799',
                        'Melchior Broederlam': 'Q469613',
                        'Michel Sittow': 'Q372203',
                        'Petrus Christus': 'Q312616',
                        'Rogier van der Weyden': 'Q68631',
                        }
        self.bad_artists = ['Albrecht Bouts, Dirk Bouts',
                            'Anonymous',
                            'Horenbout',
                            'Master of the Gold Brocade, Rogier van der Weyden',
                            ]
        self.locations = {'Aartsbisschoppelijk Museum': 'Q43655709',
                          'Accademia Carrara': 'Q338367',
                          'Alte Pinakothek': 'Q154568',
                          'Anhaltische Gemäldegalerie': 'Q76638284',
                          'Bob Jones University Museum and gallery': 'Q5481539',
                          'Bowes Museum': 'Q895434',
                          'Buckingham Palace': 'Q42182',
                          'Clark Art Institute': 'Q1465805',
                          'Courtauld Institute of Art': 'Q734266',
                          'Fitzwilliam Museum': 'Q1421440',
                          'Galleria Sabauda': 'Q2245152',
                          'Galleria degli Uffizi': 'Q51252',
                          'Germanisches Nationalmuseum': 'Q478695',
                          'Groeninge Museum': 'Q1948674',
                          'Gruuthusemuseum': 'Q1108949',
                          'Hamburger Kunsthalle': 'Q169542',
                          'Harvard Art Museums': 'Q3783572',
                          'Indianapolis Museum of Art': 'Q1117704',
                          'J. Paul Getty Museum': 'Q731126',
                          'Kelvingrove Art Gallery and Museum': 'Q1061094',
                          'Kunsthistorisches Museum': 'Q95569',
                          'Los Angeles County Museum of Art (LACMA)': 'Q1641836',
                          'M Museum': 'Q2362660',
                          'Mauritshuis': 'Q221092',
                          'Metropolitan Museum of Art': 'Q160236',
                          'Morgan Library and Museum': 'Q1478423',
                          'Museo Correr': 'Q1470912',
                          'Museo Lázaro Galdiano': 'Q386570',
                          'Museo Nacional Thyssen-Bornemisza': 'Q176251',
                          'Museo Nacional del Prado': 'Q160112',
                          'Museo Nazionale del Bargello': 'Q388448',
                          'Museo de Bellas Artes de Bilbao': 'Q127064',
                          'Museu Nacional d\'Art de Catalunya': 'Q861252',
                          'Museum Boijmans Van Beuningen': 'Q679527',
                          'Museum Catharijneconvent': 'Q1954426',
                          'Museum Mayer van den Bergh': 'Q1699233',
                          'Musée Condé': 'Q1236032',
                          'Musée Jacquemart-André': 'Q1165526',
                          'Musée de Picardie': 'Q3107709',
                          'Musée de la Chartreuse': 'Q30524595',
                          'Musée du Louvre': 'Q3044768',  # Department of Paintings of the Louvre (Q3044768)/Q19675
                          'Musée du Louvre, Département des Arts graphiques': 'Q3044753',
                          'National Gallery': 'Q180788',
                          'National Gallery of Art': 'Q214867',  # ???
                          'National Gallery of Denmark': 'Q671384',
                          'National Gallery of Ireland': 'Q2018379',
                          'National Gallery of Scotland': 'Q2051997',
                          'National Gallery of Victoria': 'Q1464509',
                          'National Museum of Ancient Art': 'Q212459',
                          'National Museum of Western Art': 'Q1362629',
                          'Nelson-Atkins Museum of Art': 'Q1976985',
                          'Philadelphia Museum of Art': 'Q510324',
                          'Princeton University Art Museum': 'Q2603905',
                          'Rijksmuseum': 'Q190804',
                          'Rijksmuseum Twenthe': 'Q1505892',
                          'Royal Monastery of San Lorenzo': 'Q28471',
                          'Royal Museums of Fine Arts of Belgium': 'Q377500',
                          'Saint John\'s Hospital': 'Q2432540',
                          'San Diego Museum of Art': 'Q1368166',
                          'Staatliche Kunstsammlungen, Gemäldegalerie Alte Meister': 'Q653002',
                          'Staatliche Museen zu Berlin, Gemäldegalerie': 'Q165631',
                          'Staatliche Museen zu Berlin, Kupferstichkabinett': 'Q555946',
                          'State Hermitage Museum': 'Q132783',
                          'Städel Museum': 'Q163804',
                          'Suermondt Ludwig Museum': 'Q468169',
                          'The Pushkin State Museum of Fine Arts': 'Q4872',
                          'Upton House': 'Q2188329',
                          'Virginia Museum of Fine Arts': 'Q4013975',
                          'Wallraf-Richartz-Museum': 'Q700959',
                          'Walters Art Gallery': 'Q210081',
                          'Wildenstein gallery': 'Q10288082',
                          'Worcester Art Museum': 'Q847508',
                          }
        self.bad_locations = ['Art Institute',
                              'Capilla Real',
                              'Cathedral',
                              'Christie\'s auction',
                              'Drouot auction',
                              'Fischer gallery',  # https://www.wikidata.org/wiki/Q107622082 ?
                              'Fiévez auction',
                              'Giroux gallery',
                              'Institute of Arts',
                              'Lempertz auction',
                              'Lepke auction',
                              'Museum of Art',
                              'Museum of Fine Arts',
                              'Musée des Beaux-Arts',
                              'National Museum',
                              'Palais des Beaux-Arts',
                              'Private collection',
                              'Robert Finck gallery',
                              'Royal Museum of Fine Arts',
                              'Sotheby\'s auction',
                              'Staatsgalerie',
                              'Whereabouts unknown',
                              ]
        self.volumes = {'1': 'Q113667108',
                        '2': 'Q116872369',
                        '3': 'Q121298068',
                        '4': 'Q121298096',
                        '5': 'Q117360131',
                        '6': 'Q67277194',
                        '7': 'Q121298122',
                        '8': 'Q121298137',
                        '9': 'Q121298155',
                        '10': 'Q121298167',
                        '11': 'Q121298188',
                        '12': 'Q67275272',
                        '13': 'Q121298233',
                        '14': 'Q118868327',
                        '99': 'Q121501917',  # The online additions in the extended data
                        'VX': 'Q121501917',  # The online additions in the basic data
                        }

    def artist_unmatched_on_wikidata(self, artist_qid):
        """

        """
        result = []

        query = """SELECT DISTINCT ?item ?itemLabel ?itemDescription ?relation ?collection WHERE {
  ?item p:P170 [ ?relation wd:%s ] .
  MINUS { ?item wdt:P11918 [] } .
  OPTIONAL { ?item wdt:P195 ?collection . ?collection wdt:P31 [] } . 
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,nl,fr". }
  } LIMIT 1000""" % (artist_qid, )

        sq = pywikibot.data.sparql.SparqlQuery()
        query_result = sq.select(query)

        for result_item in query_result:
            result_item['qid'] = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
            #if result_item.get('itemLabel'):
            #    result_item['title'] = result_item.get('itemLabel')
            if result_item.get('collection'):
                result_item['collection'] = result_item.get('collection').replace('http://www.wikidata.org/entity/', '')
            result.append(result_item)
        return result

    def collection_unmatched_on_wikidata(self, collection_qid):
        """

        """
        result = []

        query = """SELECT DISTINCT ?item ?itemLabel ?itemDescription ?relation ?artist WHERE {
  ?item p:P195/ps:P195 wd:%s.
  MINUS { ?item wdt:P11918 [] } .
  { ?item wdt:P135 wd:Q443153 } UNION
  { ?item p:P170 [ ?relation ?artist] . 
  ?artist wdt:P135 wd:Q443153 }.  
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,nl,fr". }
  } LIMIT 1000""" % (collection_qid, )

        sq = pywikibot.data.sparql.SparqlQuery()
        query_result = sq.select(query)

        for result_item in query_result:
            result_item['qid'] = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
            #if result_item.get('itemLabel'):
            #    result_item['title'] = result_item.get('itemLabel')
            if result_item.get('artist'):
                result_item['artist'] = result_item.get('artist').replace('http://www.wikidata.org/entity/', '')
            result.append(result_item)
        return result

    def get_friedlander_on_wikidata(self):
        """
        Get all Friedlander links on Wikidata
        :return:
        """
        result = {}
        query = """SELECT ?item ?id WHERE {
        ?item wdt:P11918 ?id .
        }"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace('http://www.wikidata.org/entity/', '')
            identifier = resultitem.get('id')
            result[identifier] = qid
        return result

    def get_usage_on_wikidata(self, pid):
        """
        Get all links on Wikidata for a property
        :return:
        """
        result = {}
        query = """SELECT ?item ?id WHERE {
        ?item wdt:%s ?id .
        }""" % (pid,)
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace('http://www.wikidata.org/entity/', '')
            identifier = resultitem.get('id')
            result[identifier] = qid
        return result

    def run(self):
        """
        Do the actual run
        :return:
        """
        report_page = 'Wikidata:WikiProject sum of all paintings/Friedlander to match'

        text = 'This page gives an overview of Friedlander images to match with {{P|P11918}}. '
        text += 'You can help by connecting these.\n'

        locations_text = ''
        volumes_text = ''
        works_other_locations = 0

        for location in sorted(self.friedlander_locations.keys()):
            works = len(self.friedlander_locations.get(location))
            if location not in self.bad_locations and works > 9:
                locations_text += '* [[/%s|%s]] - %s\n' % (location, location, len(self.friedlander_locations.get(location)))
                if location in self.locations:
                    self.process_location(location)
            else:
                works_other_locations += works
        locations_text += '%s works in other locations' % (works_other_locations,)

        for volume in sorted(self.friedlander_volumes.keys()):
            works = len(self.friedlander_volumes.get(volume))
            if volume in self.volumes and volume != 'XV':
                volumes_text += '* [[/ENP vol. %s|%s]] - %s\n' % (volume, volume, len(self.friedlander_volumes.get(volume)))
                if volume in self.volumes:
                    self.process_volume(volume)
            else:
                works_other_locations += works

        artists_text = ''
        local_text = self.get_table_header()

        total_works = 0

        for artist in sorted(self.friedlander_artists.keys()):
            works = len(self.friedlander_artists.get(artist))
            total_works += works
            if artist not in self.bad_artists and works > 7:
                artists_text += '* [[/%s|%s]] - %s\n' % (artist, artist, len(self.friedlander_artists.get(artist)))
                if artist in self.artists:
                    self.process_artist(artist)
            else:
                for artwork in self.friedlander_artists.get(artist):
                    local_text += self.get_table_row(artwork)
        local_text += '|}\n'

        matched_works = len(self.friedlander_on_wikidata)
        matched_percentage = round(matched_works / total_works * 100, 1)

        text += 'Found %s artworks of which %s (%s%%) have been matched.\n' % (total_works,
                                                                               matched_works,
                                                                               matched_percentage)

        text += '__TOC__\n'
        text += '== Popular artists ==\n'
        text += artists_text
        text += '\n== Locations ==\n'
        text += locations_text
        text += '\n== Volumes ==\n'
        text += volumes_text
        text += '\n== Other artists ==\n'
        text += local_text
        text += '\n[[Category:WikiProject sum of all paintings Friedlander to match| ]]'
        page = pywikibot.Page(self.repo, title=report_page)
        summary = 'Updating Friedlander overview page: %s out of %s (%s%%) matched' % (matched_works,
                                                                                       total_works,
                                                                                       matched_percentage)
        page.put(text, summary)

    def process_artist(self, artist):
        report_page = 'Wikidata:WikiProject sum of all paintings/Friedlander to match/%s' % (artist, )
        artist_qid = self.artists.get(artist)

        text = 'This page gives an overview of Friedlander images to match with {{P|P11918}} '
        text += 'for the {{Q|%s}} (%s) group. \n' % (artist_qid, artist)

        header = self.get_table_header()
        rows = ''
        for artwork in self.friedlander_artists.get(artist):
            rows += self.get_table_row(artwork)

        if rows:
            text += 'You can help by connecting these.\n'
            text += '== To match ==\n'
            text += header
            text += rows
            text += '|}\n'
            text += '\n== On Wikidata ==\n'
            text += '{| class=\'wikitable sortable\' style=\'width:100%\'\n'
            text += '! Item\n'
            text += '! Title\n'
            text += '! Description\n'
            text += '! Collection\n'

            for artwork in self.artist_unmatched_on_wikidata(artist_qid):
                text += '|-\n'
                text += '| {{Q|%s}} \n' % (artwork.get('qid'), )
                text += '| %s \n' % (artwork.get('itemLabel'), )
                text += '| %s \n' % (artwork.get('itemDescription'), )
                if artwork.get('collection'):
                    text += '| {{Q|%s}} \n' % (artwork.get('collection'), )
                else:
                    text += '| \n'
            text += '|}\n'
            text += '\n[[Category:WikiProject sum of all paintings Friedlander to match|%s]]' % (artist, )
        else:
            text += 'All done matching, see [[Wikidata:WikiProject sum of all paintings/Friedlander to match]].\n'
            text += '\n[[Category:WikiProject sum of all paintings Friedlander completely matched|%s]]' % (artist, )
        page = pywikibot.Page(self.repo, title=report_page)
        summary = 'Updating Friedlander overview page'
        page.put(text, summary)

    def process_location(self, location):
        report_page = 'Wikidata:WikiProject sum of all paintings/Friedlander to match/%s' % (location, )
        location_qid = self.locations.get(location)

        text = 'This page gives an overview of Friedlander images to match with {{P|P11918}} '
        text += 'for {{Q|%s}} (%s) location or collection. \n' % (location_qid, location)

        header = self.get_table_header()
        rows = ''
        for artwork in self.friedlander_locations.get(location):
            rows += self.get_table_row(artwork)
        if rows:
            text += 'You can help by connecting these.\n'
            text += '== To match ==\n'
            text += header
            text += rows
            text += '|}\n'
            text += '\n== On Wikidata ==\n'
            text += '{| class=\'wikitable sortable\' style=\'width:100%\'\n'
            text += '! Item\n'
            text += '! Title\n'
            text += '! Description\n'
            text += '! Artist\n'

            for artwork in self.collection_unmatched_on_wikidata(location_qid):
                text += '|-\n'
                text += '| {{Q|%s}} \n' % (artwork.get('qid'), )
                text += '| %s \n' % (artwork.get('itemLabel'), )
                text += '| %s \n' % (artwork.get('itemDescription'), )
                if artwork.get('artist'):
                    text += '| {{Q|%s}} \n' % (artwork.get('artist'), )
                else:
                    text += '| \n'
            text += '|}\n'
            text += '\n[[Category:WikiProject sum of all paintings Friedlander to match|%s]]' % (location, )
        else:
            text += 'All done matching, see [[Wikidata:WikiProject sum of all paintings/Friedlander to match]].\n'
            text += '\n[[Category:WikiProject sum of all paintings Friedlander completely matched|%s]]' % (location, )
        page = pywikibot.Page(self.repo, title=report_page)
        summary = 'Updating Friedlander overview page'
        page.put(text, summary)

    def process_volume(self, volume):
        report_page = 'Wikidata:WikiProject sum of all paintings/Friedlander to match/ENP vol. %s' % (volume, )
        volume_qid = self.volumes.get(volume)

        text = 'This page gives an overview of Friedlander images to match with {{P|P11918}} '
        text += 'for {{Q|%s}} (ENP vol. %s) location or collection. \n' % (volume_qid, volume)

        header = self.get_table_header()
        rows = ''
        for artwork in self.friedlander_volumes.get(volume):
            rows += self.get_table_row(artwork)
        if rows:
            text += 'You can help by connecting these.\n'
            text += '== To match ==\n'
            text += header
            text += rows
            text += '|}\n'

            text += '\n[[Category:WikiProject sum of all paintings Friedlander to match|ENP vol. %s]]' % (volume, )
        else:
            text += 'All done matching, see [[Wikidata:WikiProject sum of all paintings/Friedlander to match]].\n'
            text += '\n[[Category:WikiProject sum of all paintings Friedlander completely matched|{{SUBPAGENAME}}]]'
        page = pywikibot.Page(self.repo, title=report_page)
        summary = 'Updating Friedlander overview page'
        page.put(text, summary)
    def get_table_header(self):
        text = '{| class=\'wikitable sortable\' style=\'width:100%\'\n'
        text += '! ID\n'
        text += '! Title\n'
        text += '! Painter\n'
        text += '! Collection\n'
        text += '! Reference\n'
        text += '! Balat\n'
        text += '! RKD\n'
        text += '! Suggestion\n'
        return text

    def get_table_row(self, artwork):
        """
        Construct a table row based on the information in artwork
        :param artwork:
        :return:
        """
        friedlander_id = str(artwork.get('friedlanderId'))
        if friedlander_id in self.friedlander_on_wikidata:
            return ''
        friedlander_data = self.get_friedlander_by_id(friedlander_id).get('data')
        balat_regex = '^https?://balat\.kikirpa\.be/(object/|photo\.php\?path=[^&]+&objnr=)(?P<id>\d+)\s*$'
        rkd_regex = '^https?://(explore\.)?rkd\.nl/(en/|nl/)?explore/images/(?P<id>\d+)\s*$'
        balat_link = ''
        rkd_link = ''
        suggestion_link = ''
        for link_info in friedlander_data.get('relatedlinks'):
            if link_info.get('description') == 'KIK-IRPA, Brussels':
                match = re.match(balat_regex, link_info.get('link'))
                if match:
                    balat_id = str(match.group('id'))
                    balat_link += '[%s %s] ' % (link_info.get('link'), balat_id, )

                    if balat_id in self.balat_on_wikidata:
                        qid = self.balat_on_wikidata.get(balat_id)
                        suggestion_link += '{{Q|%s}} ' % (qid, )

            elif link_info.get('description') == 'RKD, The Hague':
                match = re.match(rkd_regex, link_info.get('link'))
                if match:
                    rkd_id = match.group('id')
                    rkd_link += '[%s %s] ' % (link_info.get('link'), rkd_id, )
                    if rkd_id in self.rkd_on_wikidata:
                        qid = self.rkd_on_wikidata.get(rkd_id)
                        suggestion_link += '{{Q|%s}} ' % (qid, )

        #data_url = 'https://www.kikirpa.be/actions/statik/friedlander/get-project-by-id?id=%s' % (friedlander_id,)
        #print(data_url)
        #time.sleep(1)
        #artwork_data = self.data_session.get(data_url).json()
        text = '|-\n'
        text += '| [https://www.kikirpa.be/friedlaender/%s %s] \n' % (artwork.get('friedlanderId'),
                                                                      artwork.get('friedlanderId'))
        text += '| %s \n' % (artwork.get('title'), )
        artist = artwork.get('artist')  # .encode('cp1252').decode('utf8') solved?
        if artist in self.artists:
            text += '| {{Q|%s}} \n' % (self.artists.get(artist), )
        else:
            text += '| %s \n' % (artwork.get('artist'), )  # .encode('cp1252').decode('utf8'), ) solved?
        if artwork.get('location') in self.locations:
            text += '| {{Q|%s}} (%s) \n' % (self.locations.get(artwork.get('location')), artwork.get('location'), )
        else:
            text += '| %s / %s / %s \n' % (artwork.get('location'), artwork.get('city'), artwork.get('country'),)
        if friedlander_data.get('reference details') and friedlander_data.get('reference details').get('explicit'):
            text += '| %s \n' % (friedlander_data.get('reference details').get('explicit'), )
        else:
            text += '| \n'
        text += '| %s\n' % (balat_link,)
        text += '| %s \n' % (rkd_link,)
        text += '| %s \n' % (suggestion_link,)
        return text

    def get_friedlander_by_id(self, friedlander_id):
        """
        Get json like https://www.kikirpa.be/actions/statik/friedlander/get-project-by-id?id=7122
        Uses local caching
        :param friedlander_id: The Friedlander id
        :return: dict
        """
        url = 'https://www.kikirpa.be/actions/statik/friedlander/get-project-by-id?id=%s' % (friedlander_id)
        filename = '../friedlander_cache/%s.json' % (friedlander_id)
        if os.path.isfile(filename):
            with open(filename, 'r') as jsonfile:
                return json.load(jsonfile)
        else:
            page = requests.get(url)
            try:
                jsondata = page.json()
            except ValueError:
                print('Invalid json for %s. Sleeping' % (url,))
                time.sleep(120)
                page = requests.get(url)
                jsondata = page.json()
            with open(filename, 'w') as jsonfile:
                jsonfile.write(json.dumps(jsondata, indent=4))
                return jsondata




def main(*args):
    """
    :param args:
    :return:
    """
    friedlander_data_url = 'https://www.kikirpa.be/actions/statik/friedlander/get-projects'
    friedlander_page = requests.get(friedlander_data_url)  #, stream=True)
    #text = friedlander_page.content
    #text = text.decode('utf8').encode('cp1252').decode('utf8')
    #friedlander_page.encoding = 'cp1252'  # friedlander_page.apparent_encoding
    #friedlander_json = json.loads(text)
    friedlander_json = requests.get(friedlander_data_url).json()



    for arg in pywikibot.handle_args(args):
        if arg.startswith('-collectionid:'):
            if len(arg) == 14:
                collection = pywikibot.input(
                        u'Please enter the collectionid you want to work on:')
            else:
                collection = arg[14:]


    friedlander_matcher = FriedlanderMatcher(friedlander_json)
    friedlander_matcher.run()


if __name__ == "__main__":
    main()
