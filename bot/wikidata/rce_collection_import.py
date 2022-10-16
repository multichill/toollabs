#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the RCE to Wikidata. This is going to be a fun one because this one is a meta collection.
This collection came from different sources, most notably the Stichting Nederlands Kunstbezit

Overview of those at http://herkomstgezocht.nl/nl/search/collection?f[0]=type%3Ank_record&f[1]=field_objectaanduiding%3A11621

The collection is on loan to a lot of different museums so we probably already had quite a few of them.

Using the v2 dimcon api, see
http://data.collectienederland.nl/api/search/v2/?q=&qf=edm_dataProvider%3ARijksdienst+voor+het+Cultureel+Erfgoed&qf=dc_type%3Aschilderij&format=json&start=1

This bot uses artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re

def getRCEGenerator():
    """
    Generator to return RCE paintings

    """
    # Over 10.000 breaks so had to mess with facets
    # "&qf[]=europeana_dataProvider%3ARijksdienst+voor+het+Cultureel+Erfgoed&qf[]=dc_type%3Aschilderij&qf[]=icn_material_facet%3Aolieverf"
    basesearchurl = 'http://data.collectienederland.nl/api/search/v1/?q=&qf=edm_dataProvider%%3ARijksdienst+voor+het+Cultureel+Erfgoed&qf=dc_type%%3Aschilderij&format=json&start=%s&rows=%s'
    #basesearchurl = 'http://data.collectienederland.nl/api/search/v1/?q=&qf=edm_dataProvider%%3ARijksdienst+voor+het+Cultureel+Erfgoed&qf=dc_type%%3Aschilderij&qf[]=icn_material_facet%%3Aolieverf&format=json&start=%s&rows=%s'
    #basesearchurl = 'http://data.collectienederland.nl/api/search/v1/?q=&qf=edm_dataProvider%%3ARijksdienst+voor+het+Cultureel+Erfgoed&qf=dc_type%%3Aschilderij&qf[]=icn_material_facet%%3Aacrylverf&format=json&start=%s&rows=%s'
    #basesearchurl = 'http://data.collectienederland.nl/api/search/v1/?q=&qf=edm_dataProvider%%3ARijksdienst+voor+het+Cultureel+Erfgoed&qf=dc_type%%3Aschilderij&qf[]=icn_material_facet%%3Adoek&format=json&start=%s&rows=%s'
    #basesearchurl = 'http://data.collectienederland.nl/api/search/v1/?q=&qf=edm_dataProvider%%3ARijksdienst+voor+het+Cultureel+Erfgoed&qf=dc_type%%3Aschilderij&qf[]=icn_material_facet%%3Apaneel&format=json&start=%s&rows=%s'
    #basesearchurl = 'http://data.collectienederland.nl/api/search/v1/?q=&qf=edm_dataProvider%%3ARijksdienst+voor+het+Cultureel+Erfgoed&qf=dc_type%%3Aschilderij&qf[]=icn_material_facet%%3Akoper&format=json&start=%s&rows=%s'
    #basesearchurl = 'http://data.collectienederland.nl/api/search/v1/?q=&qf=edm_dataProvider%%3ARijksdienst+voor+het+Cultureel+Erfgoed&qf=dc_type%%3Aolieverfschildering&format=json&start=%s&rows=%s'
    #basesearchurl = 'http://data.collectienederland.nl/api/search/v1/?q=&qf=edm_dataProvider%%3ARijksdienst+voor+het+Cultureel+Erfgoed&qf=dc_type%%3Apastel&format=json&start=%s&rows=%s'

    #basesearchurl = u'http://data.collectienederland.nl/api/search/v2/?q=&qf=edm_dataProvider%%3ARijksdienst+voor+het+Cultureel+Erfgoed&qf=dc_type%%3Aminiatuur&format=json&start=%s&rows=%s'
    start = 1
    rows = 50
    hasNext = True

    provenancecounts = {}
    locationcounts = {}

    provcollections = { u'Stichting Nederlands Kunstbezit' : u'Q28045665',
                        u'Rijksmuseum Amsterdam' : u'Q190804',
                        u'Mauritshuis' : u'Q221092',
                        u'Kröller-Müller Museum' : u'Q1051928',
                        }

    locations = { u'Depot ICN' : u'Q28058409', # 6636
                  u'niet-museale instelling' : u'', # 2826
                  u'Bonnefantenmuseum, MAASTRICHT' : u'Q892727', # 128
                  u'Dordrechts Museum, DORDRECHT' : u'Q2874177', # 126
                  u'Gemeente Musea Delft, DELFT' : u'Q18668555', # 76
                  u'Museum voor Moderne Kunst Arnhem, ARNHEM' : u'Q2114028', # 71
                  u'Centraal Museum, UTRECHT' : u'Q260913', # 68
                  u'Museum Boijmans Van Beuningen, ROTTERDAM' : u'Q679527', # 66
                  u'Rijksmuseum Twenthe, ENSCHEDE' : u'Q1505892', # 64
                  u'Noordbrabants Museum, DEN BOSCH' : u'Q12013217', # 58
                  u'Stedelijk Museum Amsterdam, AMSTERDAM' : u'Q924335', # 54
                  u'Stedelijk Museum Roermond, ROERMOND' : u'Q2598787', # 50
                  u'Frans Halsmuseum, HAARLEM' : u'Q574961', # 50
                  u'Paleis Het Loo Nationaal Museum, APELDOORN' : u'Q692381', # 34
                  u'Stedelijk Museum De Lakenhal, LEIDEN' : u'Q2098586', # 34
                  u'Westfries Museum, HOORN' : u'Q2382575', # 33
                  u'Limburgs Museum, VENLO' : u'Q2798268', # 32
                  u'Stedelijk Museum Schiedam, SCHIEDAM' : u'Q2779535', # 26
                  u'Museum Catharijneconvent, UTRECHT' : u'Q1954426', # 25
                  u'Museum De Wieger, DEURNE' : u'Q3483633', # 25
                  u'MuseumgoudA, GOUDA' : u'Q4360916', # 24
                  u'Gemeentemuseum Den Haag, DEN HAAG' : u'Q1499958', # 23
                  u'Groninger Museum, GRONINGEN' : u'Q1542668', # 21
                  u'Rijksmuseum Amsterdam, AMSTERDAM' : u'Q190804', # 19
                  u'Drents Museum, ASSEN' : u'Q1258370', # 16
                  u'Museum Het Rembrandthuis, AMSTERDAM' : u'Q277316', # 16
                  u'Gemeentemuseum Helmond, HELMOND' : u'Q22015126', # 15
                  u'Afrika Museum, BERG EN DAL' : u'Q2470853', # 15
                  u'Van Gogh Museum, AMSTERDAM' : u'Q224124', # 15
                  u'Cobra Museum voor Moderne Kunst, AMSTELVEEN' : u'Q2161858', # 14
                  u'Museum Bronbeek, ARNHEM' : u'Q1948006', # 12
                  u'Historisch Museum Rotterdam, ROTTERDAM' : u'Q2130225', # 11
                  u'Fries Museum, LEEUWARDEN' : u'Q848313', # 11
                  u'Museum voor Religieuze Kunst, UDEN' : u'Q2112422', # 10
                  u'Amsterdams Historisch Museum, AMSTERDAM' : u'Q1820897', # 9
                  u'Letterkundig Museum, DEN HAAG' : u'Q1821169', # 9
                  u'Stadsmuseum IJsselstein, IJSSELSTEIN' : u'Q28058453', # 9
                  u'Museum De Schotse Huizen, VEERE' : u'Q4288330', # 8
                  u'Legermuseum, DELFT' : u'Q1781661', # 8
                  u'Nederlands Scheepvaartmuseum, AMSTERDAM' : u'Q1616123', # 8
                  u'Historisch Museum Den Briel, BRIELLE' : u'Q15224245', # 7
                  u'Museum Ons’ Lieve Heer Op Solder, AMSTERDAM' : u'Q493160', # 7
                  u'Van Abbemuseum, EINDHOVEN' : u'Q1782422', # 7
                  u'Museum Kranenburgh, BERGEN' : u'Q4350196', # 7
                  u'Stedelijk Museum voor Actuele Kunst, GENT' : u'Q1540707', # 5
                  u'Zeeuws Museum, MIDDELBURG' : u'Q2153365', # 5
                  u'Museum Het Valkhof, NIJMEGEN' : u'Q1127079', # 5
                  u'Haags Historisch Museum, DEN HAAG' : u'Q11722011', # 5
                  u'Museum Tongerlohuys, ROOSENDAAL' : u'Q2640806', # 4
                  # u'Museum mr. Simon van Gijn' : u'', # museum aan huis, DORDRECHT' : u'', # 4 niet te vinden
                  u'Bijbels Museum, AMSTERDAM' : u'Q2919762', # 4
                  u'Stedelijk Museum Zwolle, ZWOLLE' : u'Q14388973', # 4
                  u'Museum aan het Vrijthof, MAASTRICHT' : u'Q1634251', # 3
                  u'Voerman Museum, HATTEM' : u'Q1967125', # 3
                  u'Stedelijk Museum Zutphen, ZUTPHEN' : u'', # 3
                  # u'Museum Theo Swagemakers, HAARLEM' : u'', # 3 Niet gevonden
                  u'Katwijks Museum, KATWIJK' : u'Q5462003', # 3
                  # u'Academisch Historisch Museum, LEIDEN' : u'', # 3 niet gevonden
                  u'Museum Bommel van Dam, VENLO' : u'Q1994770', # 3
                  u'Museum Van Loon, AMSTERDAM' : u'Q2191110', # 3
                  u'Allard Pierson Museum, AMSTERDAM' : u'Q1244372', # 2
                  # u'Huygensmuseum Hofwijck, VOORBURG' : u'', # 2 niet gevonden
                  # u'Nationaal Veeteelt Museum, BEERS' : u'', # 2 niet gevonden
                  # u'Landelijk Gevangenismuseum, VEENHUIZEN' : u'', # 2
                  # u'Museum Rijswijk Het Tollenshuis, RIJSWIJK' : u'', # 2
                  u'Marinemuseum, DEN HELDER' : u'Q17402020', # 2
                  u'Nederlands Openluchtmuseum, ARNHEM' : u'Q674449', # 2
                  u'Stedelijk Museum \'s-Hertogenbosch, DEN BOSCH' : u'Q7605588', # 2
                  u'Gorcums Museum, GORINCHEM' : u'Q2530116', # 2
                  u'Fries Scheepvaart Museum, SNEEK' : u'Q893334', # 2
                  # u'Streekmuseum De Groote Sociëteit, TIEL' : u'', # 2
                  u'Het Hollands Kaasmuseum, ALKMAAR' : u'Q2725746', # 1
                  u'Gemeentemuseum Weert, locatie Jacob van Horne, WEERT' : u'Q2538283', # 1
                  u'Koninklijk Museum voor Schone Kunsten, ANTWERPEN' : u'Q1471477', # 1
                  u'Chabot Museum, ROTTERDAM' : u'Q2676195', # 1
                  u'Museum voor Schone Kunsten, GENT' : u'Q2365880', # 1
                  u'Belasting- en Douane Museum, ROTTERDAM' : u'Q13437069', # 1
                  u'Visserijmuseum Vlaardingen, VLAARDINGEN' : u'Q3192854', # 1
                  u'Museum voor Communicatie, DEN HAAG' : u'Q1954787', # 1
                  u'Mariniersmuseum, ROTTERDAM' : u'Q2530385', # 1
                  # u'Maritiem- en Juttersmuseum, DEN BURG (TEXEL)' : u'', # 1
                  u'Tropenmuseum, AMSTERDAM' : u'Q1131589', # 1
                  u'Museum Jan Cunen, OSS' : u'Q2342262', # 1
                  # u'Maarten van Rossum Museum, ZALTBOMMEL' : u'', # 1
                  # u'Streekmuseum Land Van Valkenburg, VALKENBURG' : u'', # 1
                  u'Rijksmuseum van Oudheden, LEIDEN' : u'Q1860378', # 1
                  u'Stichting Rijksmuseum Muiderslot, MUIDEN' : u'Q2426916', # 1
                  u'Joods Historisch Museum, AMSTERDAM' : u'Q702726', # 1
                  u'Singer Museum, LAREN' : u'Q431431', # 1
                  u'Museum Mesdag, DEN HAAG' : u'Q255409', # 1
                  u'Museum Swaensteyn, VOORBURG' : u'Q2761825', # 1
                  u'Apeldoorns Museum Cultureel Onder Dak (CODA), APELDOORN' : u'Q13447121', # 1
                  # u'Museum De Gevangenpoort, DEN HAAG' : u'', # 1
                 }

    while hasNext:
        searchUrl = basesearchurl % (start, rows)
        print (searchUrl)
        searchPage = requests.get(searchUrl)
        searchJson = searchPage.json()

        start = searchJson.get(u'result').get(u'pagination').get(u'nextPage')
        hasNext = searchJson.get(u'result').get(u'pagination').get(u'hasNext')

        for item in searchJson.get(u'result').get(u'items'):
            itemfields = item.get('item').get(u'fields')
            #print (itemfields)
            metadata = {}

            collectionid = itemfields.get('delving_spec')[0]
            if collectionid in ['rijkscollectie-rce', 'rce-kunstcollectie', 'rce-bkr-collectie']:
                metadata['collectionqid'] = u'Q18600731'
                metadata['collectionshort'] = u'RCE'
                # It's a meta collection, leaving out the location
                #metadata['locationqid'] = u'Q18600731'
            else:
                #Another collection, skip
                print (u'Found other collection %s' % (collectionid,))
                continue

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = itemfields.get('dc_identifier')[0]
            if u'?' in metadata['id']:
                # Some messed up records in there!
                print (u'mess')
                #time.sleep(5)
                continue
            metadata['idpid'] = u'P217'

            if itemfields.get('dc_title'):
                title = itemfields.get('dc_title')[0]
                if len(title) > 220:
                    title = title[0:200]
                metadata['title'] = { u'nl' : title,
                                    }

            metadata['url'] = itemfields.get('europeana_aggregatedCHO')[0].replace('http://data.collectienederland.nl/resource/document', 'https://data.collectienederland.nl/resource/aggregation')

            ## Is this enough or do we need to use requests to see if all urls point somewhere?
            #metadata['url'] = metadata['refurl'].replace(u'http://data.collectienederland.nl/resource/aggregation/dordrechts-museum/', u'https://www.dordrechtsmuseum.nl/objecten/id/')

            name = u''
            if itemfields.get('dc_creator'):
                for possiblename in itemfields.get('dc_creator'):
                    if possiblename !=  'onbekend':
                        name = possiblename

            if not name:
                name = u'onbekend'

            if u',' in name:
                (surname, sep, firstname) = name.partition(u',')
                name = u'%s %s' % (firstname.strip(), surname.strip(),)

            creatordob = u''
            creatordod = u''
            if itemfields.get('icn_creatorYearOfBirth'):
                creatordob = itemfields.get('icn_creatorYearOfBirth')[0]
            if itemfields.get('icn_creatorYearOfDeath'):
                creatordod = itemfields.get('icn_creatorYearOfDeath')[0]

            # Expand the crap names with livespan information
            if creatordob and creatordod:
                metadata['creatorname'] = u'%s (%s - %s)' % (name, creatordob, creatordod)
            elif creatordob:
                metadata['creatorname'] = u'%s (%s)' % (name, creatordob)
            else:
                metadata['creatorname'] = name

            # FIXME: Everything is stuff into one field with ; in between. Take different field or split it
            # Don't think we'll find onbekend, but doesn't hurt
            if metadata['creatorname'] == u'onbekend;':
                metadata['creatorname'] = u'anonymous'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
                metadata['creatorqid'] = u'Q4233718'
            else:
                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            u'de' : u'%s von %s' % (u'Gemälde', metadata.get('creatorname'), ),
                                            u'fr' : u'%s de %s' % (u'peinture', metadata.get('creatorname'), ),
                                            }

            if itemfields.get('dcterms_medium'):
                if len(itemfields.get('dcterms_medium')) == 1:
                    if itemfields.get('dcterms_medium')[0] == u'doek, olieverf':
                        metadata['medium'] = u'oil on canvas'
                    else:
                        print('Unable to match %s ' % (itemfields.get('dcterms_medium')[0],))
                elif len(itemfields.get('dcterms_medium')) == 2:
                    material1 = itemfields.get('dcterms_medium')[0]
                    material2 = itemfields.get('dcterms_medium')[1]
                    if (material1 == 'doek' and material2 == 'olieverf') or (material1 == 'olieverf' and material2 == 'doek'):
                        metadata['medium'] = 'oil on canvas'
                    elif (material1 == 'linnen' and material2 == 'olieverf') or (material1 == 'olieverf' and material2 == 'linnen'):
                        metadata['medium'] = 'oil on canvas'
                    elif (material1 == 'paneel' and material2 == 'olieverf') or (material1 == 'olieverf' and material2 == 'paneel'):
                        metadata['medium'] = 'oil on panel'
                    elif (material1 == 'hout' and material2 == 'olieverf') or (material1 == 'olieverf' and material2 == 'hout'):
                        metadata['medium'] = 'oil on panel'
                    elif (material1 == 'paneel(board)' and material2 == 'olieverf') or (material1 == 'olieverf' and material2 == 'paneel(board)'):
                        metadata['medium'] = 'oil on panel'
                    elif (material1 == 'paneel(eikenhout)' and material2 == 'olieverf') or (material1 == 'olieverf' and material2 == 'paneel(eikenhout)'):
                        metadata['medium'] = 'oil on oak panel'
                    elif (material1 == 'papier' and material2 == 'olieverf') or (material1 == 'olieverf' and material2 == 'papier'):
                        metadata['medium'] = 'oil on paper'
                    elif (material1 == 'doek' and material2 == 'tempera') or (material1 == 'tempera' and material2 == 'doek'):
                        metadata['medium'] = 'tempera on canvas'
                    elif (material1 == 'paneel' and material2 == 'tempera') or (material1 == 'tempera' and material2 == 'paneel'):
                        metadata['medium'] = 'tempera on panel'
                    elif (material1 == 'doek' and material2 == 'acrylverf') or (material1 == 'acrylverf' and material2 == 'doek'):
                        metadata['medium'] = 'acrylic paint on canvas'
                    elif (material1 == 'doek' and material2 == 'acryl') or (material1 == 'acryl' and material2 == 'doek'):
                        metadata['medium'] = 'acrylic paint on canvas'
                    elif (material1 == 'paneel' and material2 == 'acrylverf') or (material1 == 'acrylverf' and material2 == 'paneel'):
                        metadata['medium'] = 'acrylic paint on panel'
                    elif (material1 == 'papier' and material2 == 'aquarel') or (material1 == 'aquarel' and material2 == 'papier'):
                        metadata['medium'] = 'watercolor on paper'
                    else:
                        print('Unable to match %s & %s' % (material1, material2,))
                elif len(itemfields.get('dcterms_medium')) == 3:
                    rce_materials = set(itemfields.get('dcterms_medium'))
                    if rce_materials == {'olieverf', 'doek', 'paneel'}:
                        metadata['medium'] = 'oil on canvas on panel'
                    elif rce_materials == {'olieverf', 'papier', 'paneel'}:
                        metadata['medium'] = 'oil on paper on panel'
                    elif rce_materials == {'olieverf', 'karton', 'paneel'}:
                        metadata['medium'] = 'oil on cardboard on panel'
                    elif rce_materials == {'olieverf', 'koper', 'paneel'}:
                        metadata['medium'] = 'oil on copper on panel'
                    elif rce_materials == {'olieverf', 'doek', 'karton'}:
                        metadata['medium'] = 'oil on canvas on cardboard'
                    elif rce_materials == {'olieverf', 'papier', 'karton'}:
                        metadata['medium'] = 'oil on paper on cardboard'
                    else:
                        print('Unable to match %s' % (rce_materials,))
                elif len(itemfields.get('dcterms_medium')) > 2:
                    print ('That is a lof of medium fields %s' % (itemfields.get('dcterms_medium'),))

            if itemfields.get('dcterms_created'):
                dcvalue = itemfields.get('dcterms_created')[0]
                dateregex = u'^(\d\d\d\d)$'
                periodregex = u'^(\d\d\d\d)\s*[–-]\s*(\d\d\d\d)$'
                datematch = re.match(dateregex, dcvalue)
                periodmatch = re.match(periodregex, dcvalue)

                if datematch:
                    metadata['inception'] = int(datematch.group(1))
                elif periodmatch:
                    metadata['inceptionstart'] = int(periodmatch.group(1))
                    metadata['inceptionend'] = int(periodmatch.group(2))
                else:
                    print (u'Could not parse date: "%s"' % (dcvalue,))

            # TODO: Check if this still works
            # Where did it come from????
            if itemfields.get('dcterms_provenance'):
                provenance = itemfields.get('dcterms_provenance')[0]
                if provenance not in provenancecounts:
                    provenancecounts[provenance] = 0
                provenancecounts[provenance] = provenancecounts[provenance] + 1

                if provenance in provcollections:
                    metadata['extracollectionqid'] = provcollections[provenance]
                    if provenance == u'Stichting Nederlands Kunstbezit':
                        metadata['extraid'] = metadata['id']

            # TODO: Check if this still works
            # And where is it hiding now?
            if itemfields.get('nave_location'):
                location = itemfields.get('nave_location')[0]
                if location not in locationcounts:
                    locationcounts[location] = 0
                locationcounts[location] = locationcounts[location] + 1

                if location in locations:
                    locationtarget = locations[location]
                    if locationtarget:
                        metadata['locationqid'] = locationtarget
                        if location!=u'Depot ICN':
                            metadata['extracollectionqid2'] = locations[location]

            genres = { u'genre' : u'Q1047337',
                       u'historie' : u'Q742333',
                       u'landschap' : u'Q191163',
                       u'portret' : u'Q134307',
                       u'religie' : u'Q2864737',
                       u'stadsgezicht' : u'Q1935974',
                       u'stilleven' : u'Q170571',
                       u'zelfportret' : u'Q192110',
                       }

            if itemfields.get('dc_subject'):
                for dcsubject in itemfields.get('dc_subject'):
                    dcvalue = dcsubject
                    if dcvalue=='schilderkunst':
                        continue
                    if dcvalue in genres:
                        metadata[u'genreqid'] = genres.get(dcvalue)
                        break
                    else:
                        print (u'Found unkown genre type: %s' % (dcvalue,))
                        print (u'Found unkown genre type: %s' % (dcvalue,))
                        print (u'Found unkown genre type: %s' % (dcvalue,))
                        print (u'Found unkown genre type: %s' % (dcvalue,))
                        print (u'Found unkown genre type: %s' % (dcvalue,))

                # Add a genre
            if not metadata.get(u'genreqid') and itemfields.get('dc_description'):
                dcdesc = itemfields.get('dc_description')[0]
                if dcdesc.startswith(u'Portret van'):
                    metadata[u'genreqid'] = u'Q134307'
                elif dcdesc.startswith(u'Stilleven '):
                    metadata[u'genreqid'] = u'Q170571'
                elif u'Christus' in dcdesc:
                    metadata[u'genreqid'] = u'Q2864737'

            dcformatregex = u'^(breedte|diepte \/ diameter|hoogte)\:\s*([\d\.]+)\s*cm$'
            if itemfields.get('dc_format'):
                for dcformat in itemfields.get('dc_format'):
                    dcvalue = dcformat
                    dcformatmatch = re.match(dcformatregex, dcvalue)
                    if dcformatmatch:
                        if dcformatmatch.group(1)==u'breedte':
                            metadata['widthcm'] = dcformatmatch.group(2)
                        elif dcformatmatch.group(1)==u'diepte / diameter':
                            metadata['depthcm'] = dcformatmatch.group(2)
                        elif dcformatmatch.group(1)==u'hoogte':
                            metadata['heightcm'] = dcformatmatch.group(2)
                        else:
                            print (u'Found weird type: %s' % (dcvalue,))

            # High resolution tiff images for some, jpgeg for all images!!!!!
            if itemfields.get('nave_allowSourceDownload') and itemfields.get('nave_allowSourceDownload')[0] == 'true':
                if itemfields.get('nave_thumbLarge'):
                    imageurl = itemfields.get('nave_thumbLarge')[0].replace(u'https://images.memorix.nl/rce/thumb/fullsize/', u'https://images.memorix.nl/rce/download/fullsize/')
                    metadata[u'imageurl'] = imageurl
                    metadata[u'imagesourceurl'] = itemfields.get('edm_isShownAt')[0]
                    metadata[u'imageurlformat'] = u'Q2195' # JPEG
                    metadata[u'imageurlforce'] = False # Already did a full forced run

            # For now only the SNK collection
            # if metadata.get('extracollectionqid') and metadata.get('extracollectionqid')==u'Q28045665':
            yield metadata

    pywikibot.output(u'Provenance top 100:')
    for provenance in sorted(provenancecounts, key=provenancecounts.get, reverse=True)[:100]:
        pywikibot.output(u'* %s - %s' % (provenance, provenancecounts[provenance]))

    pywikibot.output(u'Locations top 100:')
    for location in sorted(locationcounts, key=locationcounts.get, reverse=True)[:100]:
        pywikibot.output(u'* %s - %s' % (location, locationcounts[location]))

    return

def main(*args):
    dictGen = getRCEGenerator()
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True

    if dryrun:
        for painting in dictGen:
            print (painting)
    else:
        artDataBot = artdatabot.ArtDataBot(dictGen, create=create)
        artDataBot.run()

if __name__ == "__main__":
 main()
