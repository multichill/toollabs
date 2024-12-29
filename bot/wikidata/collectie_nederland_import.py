#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from multiple collections in Collectie Nederland to Wikidata.

https://www.collectienederland.nl/search/?qf%5B%5D=dc_type%3Aschilderij currently returns 32.571 paintings
Overlaps a lot with what we already have, but also adds new collections

This bot uses artdatabot to upload it to Wikidata
"""
import artdatabot
import pywikibot
import requests
import re
#import html

def get_collectie_nederland_generator(edm_dataProvider, collection_qid, collection_short, location_qid):
    """
    Generator to return Collectie Nederland paintings
    """
    rkd_artists = {} # Do lazy loading for this one
    #apikey = '4c536e8a-6cdd-11e9-ab74-37871f3093e6'
    rows = 10
    base_search_url = 'https://data.collectienederland.nl/api/search/v2/?format=json&page=%s&rows=%s&q=&qf[]=dc_type%%3Aschilderij&qf[]=edm_dataProvider%%3A%s'

    #genres = {'portretten': 'Q134307',  # portrait (Q134307)
    #          'landschappen (voorstellingen)': 'Q191163',  # landscape art (Q191163)
    #          'stadsgezichten (beeldmateriaal)': 'Q1935974',  # cityscape (Q1935974)
    #}

    search_url = base_search_url % ('1', rows, edm_dataProvider)
    print(search_url)
    session = requests.Session()
    search_page = session.get(search_url)
    pages = search_page.json().get('result').get('pagination').get('lastPage')

    for current_page in range(1, pages+1):
        search_url = base_search_url % (current_page, rows, edm_dataProvider)
        print(search_url)
        search_page = session.get(search_url)

        for item_info in search_page.json().get('result').get('items'):
            item_fields = item_info.get('item').get('fields')
            #print(item_fields)
            metadata = {}
            url = item_fields.get('entryURI').replace('http://', 'https://')

            pywikibot.output(url)
            metadata['url'] = url

            # Extract the identifier from the URL
            metadata['artworkidpid'] = 'P13172'  # Collectie Nederland ID
            metadata['artworkid'] = url.replace('https://data.collectienederland.nl/resource/aggregation/', '')

            metadata['collectionqid'] = collection_qid
            metadata['collectionshort'] = collection_short
            if location_qid:
                metadata['locationqid'] = location_qid

            # Searching for paintings
            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = 'P217'

            if not item_fields.get('dc_identifier'):
                continue
            elif len(item_fields.get('dc_identifier')) == 1 and item_fields.get('dc_identifier')[0].get('raw'):
                metadata['id'] = item_fields.get('dc_identifier')[0].get('raw').strip()
            elif len(item_fields.get('dc_identifier')) == 2:
                if not item_fields.get('dc_identifier')[0].get('raw').startswith('http'):
                    metadata['id'] = item_fields.get('dc_identifier')[0].get('raw').strip()
                elif not item_fields.get('dc_identifier')[1].get('raw').startswith('http'):
                    metadata['id'] = item_fields.get('dc_identifier')[1].get('raw').strip()
                else:
                    pywikibot.output('Unable to get identifier without http')
                    continue
            else:
                pywikibot.output('Unable to get identifier')
                continue

            if item_fields.get('dc_title') and item_fields.get('dc_title')[0].get('raw'):
                title = item_fields.get('dc_title')[0].get('raw')
                if len(title) > 220:
                    title = title[0:200]
                title = title.replace('\r', '').replace('\t', '').replace('\n', '').replace('  ', ' ').strip()
                metadata['title'] = {'nl': title, }

            if item_fields.get('dc_creator') and len(item_fields.get('dc_creator')) == 1 and \
                    item_fields.get('dc_creator')[0].get('raw'):
                name = item_fields.get('dc_creator')[0].get('raw')
                if name.startswith('schilder '):
                    name = name.replace('schilder ', '')
                if ',' in name:
                    (surname, sep, firstname) = name.partition(',')
                    name = '%s %s' % (firstname.strip(), surname.strip(),)
                metadata['creatorname'] = name.strip()

                if item_fields.get('dc_creator')[0].get('id'):
                    identifier_url = item_fields.get('dc_creator')[0].get('id')
                    print(identifier_url)
                    if identifier_url.startswith('https://rkd.nl/explore/artists/'):
                        rkd_artists_id = int(identifier_url.replace('https://rkd.nl/explore/artists/', ''))
                        print(rkd_artists_id)
                        if not rkd_artists:
                            # We got one, let's load the lookup table now
                            rkd_artists = get_rkd_artists_wikidata()
                        if rkd_artists_id in rkd_artists:
                            metadata['creatorqid'] = rkd_artists.get(rkd_artists_id)
                            pywikibot.output('Found http://www.wikidata.org/entity/%s for %s' % (metadata['creatorqid'],
                                                                                                 identifier_url))
                        else:
                            pywikibot.output('No item for %s' % (identifier_url,))

            if metadata.get('creatorname'):
                if metadata.get('creatorname') in ['onbekend', 'anoniem', 'Anoniem']:
                    # Doesn't seem to work for some collections
                    #metadata['description'] = {'nl': 'schilderij van anonieme schilder',
                    #                           'en': 'painting by anonymous painter',
                    #                           }
                    #metadata['creatorqid'] = 'Q4233718'
                    pass
                else:
                    metadata['description'] = { 'nl': '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                                'en': '%s by %s' % ('painting', metadata.get('creatorname'),),
                                                'de': '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                                'fr': '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                                }
            if item_fields.get('dcterms_created') and len(item_fields.get('dcterms_created')) == 1 and \
                    item_fields.get('dcterms_created')[0].get('raw'):
                date_value = item_fields.get('dcterms_created')[0].get('raw')
                date_regex = u'^(\d\d\d\d)$'
                period_regex = u'^(\d\d\d\d)\s*[–-]\s*(\d\d\d\d)$'
                date_match = re.match(date_regex, date_value)
                period_match = re.match(period_regex, date_value)

                if date_match:
                    metadata['inception'] = int(date_match.group(1))
                elif period_match:
                    metadata['inceptionstart'] = int(period_match.group(1))
                    metadata['inceptionend'] = int(period_match.group(2))
                else:
                    print (u'Could not parse date: "%s"' % (date_value,))
            if item_fields.get('dcterms_medium') and len(item_fields.get('dcterms_medium')) == 1 and \
                    item_fields.get('dcterms_medium')[0].get('raw'):
                medium_value = item_fields.get('dcterms_medium')[0].get('raw')
                if medium_value == 'olieverf op doek':
                    metadata['medium'] = 'oil on canvas'
                elif medium_value == 'olieverf op paneel':
                    metadata['medium'] = 'oil on panel'
                else:
                    print('Unable to match medium for %s' % (medium_value,))
            yield metadata

        if False:
            for fields in item_info.get('metadata'):
                field = fields.get('field')
                label = fields.get('label')
                value = fields.get('value')
                if field == 'spectrum_objectnummer' and label == 'Objectnummer':
                    metadata['id'] = value.strip()

                elif field == 'object_title' and label == 'Titel':
                    title = value
                    if len(title) > 220:
                        title = title[0:200]
                    title = title.replace('\r', '').replace('\t', '').replace('\n', '').replace('  ', ' ').strip()
                    metadata['title'] = {'nl': title, }

                elif field == 'dcterms_subject' and label == 'Onderwerp':
                    if bool(set(value) & {'Vrouwenportretten', 'Familieportretten', 'mansportret'}):
                        metadata['genreqid'] = 'Q134307'  # portrait

                elif field == 'controlled_subjects' and label == 'Gecontroleerde onderwerpen':
                    if value[0] in genres:
                        metadata['genreqid'] = genres.get(value[0])

                elif field == 'creators' and label == 'Vervaardiger':
                    if len(value) == 1 and len(value[0]) == 1 and value[0][0].get('field') == 'creators.surname':
                        name = value[0][0].get('value')
                        if ',' in name:
                            (surname, sep, firstname) = name.partition(',')
                            name = '%s %s' % (firstname.strip(), surname.strip(),)
                        metadata['creatorname'] = name.strip()


                    elif len(value) == 1 and len(value[0]) == 2 and value[0][1].get('field') == 'creators.surname':
                        name = value[0][1].get('value')
                        name_parts = name.split(',')
                        if len(name_parts) == 2:
                            surname = name_parts[0].strip()
                            firstname = name_parts[1].strip()
                            name = '%s %s' % (firstname, surname)
                            metadata['creatorname'] = name.strip()
                        elif len(name_parts) == 3:
                            surname = name_parts[0].strip()
                            firstname = name_parts[2].strip()
                            (initials, sep, name_prefix) = name_parts[1].strip().partition(' ')
                            if name_prefix:
                                surname = '%s %s' % (name_prefix, surname)
                            if len(initials) > 2 or initials[0] != firstname[0]:
                                firstname = '%s (%s)' % (initials, firstname)
                            name = '%s %s' % (firstname, surname)
                            metadata['creatorname'] = name.strip()
                    # Let's see if we got something
                    if metadata.get('creatorname'):
                        if metadata.get('creatorname') in ['onbekend', 'anoniem', 'Anoniem']:
                            metadata['description'] = {'nl': 'schilderij van anonieme schilder',
                                                       'en': 'painting by anonymous painter',
                                                       }
                            metadata['creatorqid'] = 'Q4233718'
                        else:
                            metadata['description'] = { 'nl': '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                                        'en': '%s by %s' % ('painting', metadata.get('creatorname'),),
                                                        'de': '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                                        'fr': '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                                        }





                elif field == 'dcterms_temporal_start' and label == 'Datering van' and value.isdigit():
                    metadata['inceptionstart'] = int(value)

                elif field == 'dcterms_temporal_end' and label == 'Datering tot' and value.isdigit():
                    metadata['inceptionend'] = int(value)

                elif field == 'spectrum_materiaal' and label == 'Materiaal':
                    materials = set(value)

                    if materials == {'olieverf', 'doek'} or materials == {'olieverf op doek'} \
                            or materials == {'Olieverf op doek'} \
                            or materials == {'verf', 'doek', 'olieverf'} or materials == {'linnen', 'olieverf'}:
                        metadata['medium'] = 'oil on canvas'
                    elif materials == {'olieverf', 'paneel'} or materials == {'olieverf op paneel'} \
                            or materials == {'Olieverf op paneel'} or materials == {'olieverf', 'paneel (hout)'} \
                            or materials == {'verf', 'paneel', 'olieverf'} or materials == {'olieverf', 'paneel', 'hout'}:
                        metadata['medium'] = 'oil on panel'
                    elif materials == {'paneel', 'olieverf', 'eikenhout'} or materials == {'eikenhout', 'olieverf'}:
                        metadata['medium'] = 'oil on oak panel'
                    elif materials == {'olieverf', 'koper'}:
                        metadata['medium'] = 'oil on copper'
                    elif materials == {'olieverf', 'papier'}:
                        metadata['medium'] = 'oil on paper'
                    elif materials == {'olieverf', 'karton'}:
                        metadata['medium'] = 'oil on cardboard'
                    elif materials == {'acryl', 'doek'} or materials == {'acrylverf', 'doek'}:
                        metadata['medium'] = 'acrylic paint on canvas'
                    elif materials == {'olieverf', 'doek', 'paneel'} or materials == {'hout [plantaardig materiaal]', 'stof [textiel]', 'olieverf'}:
                        metadata['medium'] = 'oil on canvas on panel'
                    elif materials == {'olieverf', 'papier', 'paneel'}:
                        metadata['medium'] = 'oil on paper on panel'
                    elif materials == {'olieverf', 'karton', 'paneel'}:
                        metadata['medium'] = 'oil on cardboard on panel'
                    elif materials == {'olieverf', 'koper', 'paneel'}:
                        metadata['medium'] = 'oil on copper on panel'
                    elif materials == {'olieverf', 'doek', 'karton'}:
                        metadata['medium'] = 'oil on canvas on cardboard'
                    elif materials == {'olieverf', 'papier', 'karton'}:
                        metadata['medium'] = 'oil on paper on cardboard'
                    else:
                        print('Unable to match materials for %s' % (materials,))

                elif field == 'sizes' and label == 'Afmetingen':
                    if len(value) >= 2 and len(value[0]) == 3 and len(value[1]) == 3:
                        hoogte = value[0]
                        if hoogte[0].get('field') == 'sizes.size_type' and hoogte[0].get('label') == 'Afmeting type' \
                            and hoogte[0].get('value') == 'hoogte' and hoogte[1].get('field') == 'sizes.value' \
                            and hoogte[1].get('label') == 'Waarde' and hoogte[2].get('field') == 'sizes.unit' \
                            and hoogte[2].get('label') == 'Eenheid' and hoogte[2].get('value') == 'cm':
                            metadata['heightcm'] = hoogte[1].get('value')
                        breedte = value[1]
                        if breedte[0].get('field') == 'sizes.size_type' and breedte[0].get('label') == 'Afmeting type' \
                                and breedte[0].get('value') == 'breedte' and breedte[1].get('field') == 'sizes.value' \
                                and breedte[1].get('label') == 'Waarde' and breedte[2].get('field') == 'sizes.unit' \
                                and breedte[2].get('label') == 'Eenheid' and breedte[2].get('value') == 'cm':
                            metadata['widthcm'] = breedte[1].get('value')

                elif field == 'reference_source' and label == 'Bronvermelding':
                    if value == 'Geldersch Landschap & Kasteelen, bruikleen Brantsen van de Zyp Stichting':
                        metadata['extracollectionqid'] = 'Q116311926'
                        if metadata.get('id'):
                            metadata['extraid'] = metadata.get('id')

                elif field == 'dcterms_rights_url' and label == 'Auteursrechten url':
                    if value == 'https://creativecommons.org/publicdomain/mark/1.0/' and item_info.get('asset'):
                        asset = item_info.get('asset')[0]
                        if asset.get('mimetype') == 'image/jpeg' and asset.get('download'):
                            metadata['imageurl'] = asset.get('download')
                            metadata['imageurlformat'] = 'Q2195'  # JPEG
                            #    metadata['imageurllicense'] = 'Q18199165' # cc-by-sa.40
                            metadata['imageoperatedby'] = metadata.get('collectionqid')
                            metadata['imageurlforce'] = False  # Used this to add suggestions everywhere

            yield metadata

def get_rkd_artists_wikidata():
    """
    Some collection have the RKDartists ID so we need a lookup table for that
    """
    pywikibot.output('Loading RKDartists ID lookup table')
    result = {}
    query = 'SELECT ?item ?id WHERE { ?item wdt:P650 ?id  }'
    sq = pywikibot.data.sparql.SparqlQuery()
    query_result = sq.select(query)

    for result_item in query_result:
        qid = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
        result[int(result_item.get('id'))] = qid
    pywikibot.output('Loaded %s Wikidata items for RKD artist' % (len(result,)))
    return result


def process_collection(collection_info, dry_run=False, create=False):

    # collection_info = collections.get(collectionqid)
    generator = get_collectie_nederland_generator(collection_info.get('edm_dataProvider').replace(' ', '%20'),
                                                  collection_info.get('collectionqid'),
                                                  collection_info.get('collectionshort'),
                                                  collection_info.get('locationqid'),
                                                  )

    if dry_run:
        for painting in generator:
            print(painting)
    else:
        art_data_bot = artdatabot.ArtDataBot(generator, create=create)
        art_data_bot.run()


def main(*args):
    """
* "Eindhoven Museum" data-count="236">
* "Drents Museum" data-count="231">
* "Museum Martena" data-count="191">
* "Stadskasteel Zaltbommel" data-count="191">
* "Valkhof Museum" data-count="190">
* "Museum Henriette Polak" data-count="183">
* "Huismuseum Huys Auerhaen" data-count="180">
* "Nederlands Openluchtmuseum" data-count="170">
* "Historisch Museum den Briel" data-count="153">
* "Flipje en Streekmuseum Tiel" data-count="149">
* "Collectie van der Kop" data-count="137">
* "Museum Dr8888" data-count="131">
* "Museum Bronbeek" data-count="127">
* "CODA" data-count="126">
* "Stedelijk Museum Schiedam" data-count="107">
* "Historisch Museum Ede" data-count="84">
* "Frans Halsmuseum" data-count="82">
* "Voerman Stadsmuseum Hattem" data-count="75">
* "Belasting en Douane Museum" data-count="70">
* "Verzamelingen van de gemeente Veere" data-count="68">
* "Rijksmuseum Muiderslot" data-count="63">
* "Van &#39;t Lindenhoutmuseum" data-count="62">
* "Vrijheidsmuseum" data-count="62">
* "Museon-Omniversum" data-count="56">
* "Elisabeth Weeshuis Museum" data-count="55">
* "Streekmuseum de Roode Tooren" data-count="52">
* "Museum Flehite" data-count="44">
* "Museum Nijkerk" data-count="36">
* "Rijksakademie van beeldende kunsten" data-count="36">
* "Inspectie Overheidsinformatie en Erfgoed" data-count="34">
* "Museum Oud Amelisweerd" data-count="33">
* "Stadsmuseum Harderwijk" data-count="33">
* "Fries Landbouwmuseum" data-count="31">
* "Museum Meermanno" data-count="30">
* "Paleis Het Loo" data-count="24">
* "Collectie Hilversum" data-count="22">
* "Geldmuseum" data-count="22">
* "Kasteel Museum Sypesteyn" data-count="22">
* "Museum Stad Appingedam" data-count="21">
* "TextielMuseum" data-count="21">
* "Rijksmuseum van Oudheden" data-count="17">
* "Museum Elburg" data-count="15">
* "Streekmuseum Krimpenerwaard" data-count="15">
* "Nationaal Museum van Wereldculturen" data-count="14">
* "Museum Veere" data-count="13">
* "Gysbert Japicx (Holckema) Stichting" data-count="12">
* "Het Scheepvaartmuseum" data-count="12">
* "Slot Loevestein" data-count="11">
* "Universiteitsmuseum Utrecht" data-count="11">
* "Museum Oud Westdorpe" data-count="7">
* "Nationaal Orgelmuseum" data-count="7">
* "OosterscheldeMuseum" data-count="7">
* "Museum Het Pakhuis" data-count="6">
* "Rijksmuseum de Gevangenpoort" data-count="6">
* "Stadsmuseum Doetinchem" data-count="6">
* "Stadsmuseum Veenendaal" data-count="6">
* "Hoogheemraadschap Hollands Noorderkwartier" data-count="5">
* "Museum Joure" data-count="5">
* "Nationaal Onderduikmuseum" data-count="5">
* "Historisch Museum De Scheper" data-count="3">
* "Nederlands Vestingmuseum" data-count="3">
* "NOC*NSF" data-count="2">
* "Nederlands Tegelmuseum" data-count="2">
* "Stichting Folkingestraat Synagoge" data-count="2">
* "Bevrijdingsmuseum Zeeland" data-count="1">
* "Comenius Museum" data-count="1">
* "Het Nieuwe Instituut" data-count="1">
* "Keramiekcentrum Tiendschuur Tegelen" data-count="1">
* "Museum Villa Mondriaan" data-count="1">
* "Museumpark Orientalis" data-count="1">
* "Muzeeaquarium Delfzijl" data-count="1">

    :param args:
    :return:
    """
    collections = {'Q18600731': {'edm_dataProvider': 'Rijksdienst voor het Cultureel Erfgoed', # 12162
                                'collectionqid': 'Q18600731',
                                'collectionshort': 'RCE',
                                'locationqid': None,
                                },
                   'Q190804': {'edm_dataProvider': 'Rijksmuseum Amsterdam', # 4702
                                'collectionqid': 'Q190804',
                                'collectionshort': 'Rijksmuseum Amsterdam',
                                'locationqid': 'Q190804',
                                },
                   'Q1820897': {'edm_dataProvider': 'Amsterdam Museum', # 2544
                                'collectionqid': 'Q1820897',
                                'collectionshort': 'AM',
                                'locationqid': 'Q1820897',
                                },
                   'Q40304752': {'edm_dataProvider': 'Deventer Musea', # 1975
                                'collectionqid': 'Q40304752',  #  Museum De Waag (Q40304752) /  Deventer Museums (Q75616506)
                                'collectionshort': 'Deventer',
                                #'locationqid': 'Q40304752',
                                },
                   'Q2874177': {'edm_dataProvider': 'Dordrechts Museum', # 1302
                                'collectionqid': 'Q2874177',
                                'collectionshort': 'Dordrechts',
                                'locationqid': 'Q2874177',
                                },
                   'Q12013196': {'edm_dataProvider': 'Museum Belvédère', # 920
                                 'collectionqid': 'Q12013196',
                                 'collectionshort': 'Belvédère',
                                 'locationqid': 'Q12013196',
                                 },
                   'Q702726': {'edm_dataProvider': 'Joods Historisch Museum', # 763
                                'collectionqid': 'Q702726',
                                'collectionshort': 'JHM',
                                'locationqid': 'Q702726',
                                },
                   'Q221092': {'edm_dataProvider': 'Mauritshuis', # 752
                               'collectionqid': 'Q221092',
                               'collectionshort': 'Mauritshuis',
                               'locationqid': 'Q221092',
                               },
                   'Q2114028': {'edm_dataProvider': 'Museum Arnhem', # 712
                               'collectionqid': 'Q2114028',
                               'collectionshort': 'Arnhem',
                               'locationqid': 'Q2114028',
                               },
                   'Q2436387': {'edm_dataProvider': 'Museum de Fundatie', # 582
                                'collectionqid': 'Q2436387',
                                'collectionshort': 'Fundatie',
                                'locationqid': 'Q2436387',
                                },
                   'Q4350196': {'edm_dataProvider': 'Museum Kranenburgh', # 566
                                  'collectionqid': 'Q4350196',
                                  'collectionshort': 'Kranenburgh',
                                  'locationqid': 'Q4350196',
                                  },
                   'Q11722011': {'edm_dataProvider': 'Haags Historisch Museum', # 512
                                'collectionqid': 'Q11722011',
                                'collectionshort': 'HHM',
                                'locationqid': 'Q11722011',
                                },
                   'Q18089004': {'edm_dataProvider': 'Noord-Veluws Museum', # 357
                                 'collectionqid': 'Q18089004',
                                 'collectionshort': 'Noord-Veluws Museum',
                                 'locationqid': 'Q18089004',
                                 },
                   'Q2382575': {'edm_dataProvider': 'Westfries Museum', # 312
                                'collectionqid': 'Q2382575',
                                'collectionshort': 'Westfries',
                                'locationqid': 'Q2382575',
                                },
                   'Q2736515': {'edm_dataProvider': 'Stedelijk Museum Zutphen', # 300
                                'collectionqid': 'Q2736515',
                                'collectionshort': 'Zutphen',
                                'locationqid': 'Q2736515',
                                },
                   'Q431431': {'edm_dataProvider': 'Singer Laren', # 271
                                'collectionqid': 'Q431431',
                                'collectionshort': 'Singer',
                                'locationqid': 'Q431431',
                                },
                   'Q1258370': {'edm_dataProvider': 'Drents Museum', # 231
                                 'collectionqid': 'Q1258370',
                                 'collectionshort': 'Drents Museum',
                                 'locationqid': 'Q1258370',
                                 },
                   'Q11715588': {'edm_dataProvider': 'Museum Martena', # 191
                                  'collectionqid': 'Q11715588',
                                  'collectionshort': 'Martena',
                                  'locationqid': 'Q11715588',
                                  },
                   'Q674449': {'edm_dataProvider': 'Nederlands Openluchtmuseum', # 170
                                 'collectionqid': 'Q674449',
                                 'collectionshort': 'Openluchtmuseum',
                                 'locationqid': 'Q674449',
                                 },
                   'Q131407014': {'edm_dataProvider': 'Huismuseum Huys Auerhaen', # 180
                                 'collectionqid': 'Q131407014',
                                 'collectionshort': 'Auerhaen',
                                 'locationqid': 'Q131407014',
                                 },
                   'Q110282065': {'edm_dataProvider': 'Collectie van der Kop', # 137
                                'collectionqid': 'Q110282065',  # No inventory number in this collection
                                'collectionshort': 'van der Kop',
                                'locationqid': 'Q110282065',
                                },
                   'Q3457274': {'edm_dataProvider': 'Museum Dr8888', # 131
                                  'collectionqid': 'Q3457274',
                                  'collectionshort': 'Dr8888',
                                  'locationqid': 'Q3457274',
                                  },
                   'Q98962037': {'edm_dataProvider': 'Elisabeth Weeshuis Museum', # 55
                                'collectionqid': 'Q98962037',
                                'collectionshort': 'Elisabeth Weeshuis',
                                'locationqid': 'Q98962037',
                                },
                   'Q1127079': {'filter': 'search_s_object_name:%22schilderij%22',
                                'participant': 'Valkhof Museum',
                                'prefix': 'museumhetvalkhof',
                                'collectionqid': 'Q1127079',
                                'collectionshort': 'Valkhof',
                                'locationqid': 'Q1127079',
                                },
                   'Q1886369': {'filter': 'search_s_object_name:%22schilderij%22',
                                'participant': 'Museum Henriette Polak',
                                'prefix': 'museumhenriettepolak',
                                'collectionqid': 'Q1886369',
                                'collectionshort': 'Polak',
                                'locationqid': 'Q1886369',
                                },
                   'Q13636575': {'filter': 'search_s_object_name:%22schilderij%22',
                                'participant': 'Flipje en Streekmuseum Tiel',
                                'prefix': 'streekmuseumtiel',
                                'collectionqid': 'Q13636575',
                                'collectionshort': 'Flipje',
                                'locationqid': 'Q13636575',
                                },
                   'Q99346823': {'filter': 'search_s_object_name:%22schilderij%22',
                                 'participant': 'CODA',
                                 'prefix': 'codamuseum',
                                 'collectionqid': 'Q99346823',
                                 'collectionshort': 'CODA',
                                 'locationqid': 'Q99346823',
                                 },
                   'Q2539475': {'filter': 'search_s_object_name:%22schilderij%22',
                                 'participant': 'Stadskasteel Zaltbommel',
                                 'prefix': 'stadskasteelzaltbommel',
                                 'collectionqid': 'Q2539475',
                                 'collectionshort': 'Stadskasteel',
                                 'locationqid': 'Q2539475',
                                },
                   'Q7476442': {'filter': 'search_s_object_name:%22schilderij%22',
                                'participant': 'Historisch Museum Ede',
                                'prefix': 'historischmuseumede',
                                'collectionqid': 'Q7476442',
                                'collectionshort': 'Ede',
                                'locationqid': 'Q7476442',
                                },
                   'Q1967125': {'filter': 'search_s_object_name:%22schilderij%22',
                               'participant': 'Voerman Museum Hattem',
                               'prefix': 'voermanmuseumhattem',
                               'collectionqid': 'Q1967125',
                               'collectionshort': 'Voerman',
                               'locationqid': 'Q1967125',
                               },
                   'Q17605261': {'filter': 'search_s_spectrum_collection_name:schilderijen',
                                'participant': 'Kasteel Huis Bergh',
                                'prefix': 'huisbergh',
                                'collectionqid': 'Q17605261',
                                'collectionshort': 'Huis Bergh',
                                'locationqid': 'Q17605261',
                                },
                   }

    collection_id = None
    dry_run = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-collectionid:'):
            if len(arg) == 14:
                collection_id = pywikibot.input(
                    u'Please enter the collectionid you want to work on:')
            else:
                collection_id = arg[14:]
        elif arg.startswith('-dry'):
            dry_run = True
        elif arg.startswith('-create'):
            create = True

    if collection_id:
        if collection_id not in collections.keys():
            pywikibot.output(u'%s is not a valid collectionid!' % (collection_id,))
            return
        process_collection(collections[collection_id], dry_run=dry_run, create=create)
    else:
        collection_list = list(collections.keys())
        collection_list.reverse()
        # random.shuffle(collectionlist) # Different order every time we run
        for collection_id in collection_list:
            process_collection(collections[collection_id], dryrun=dry_run, create=create)

if __name__ == "__main__":
    main()
