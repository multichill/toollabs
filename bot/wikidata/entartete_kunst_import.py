#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape "entartete" ("degenerate") paintings (the stuff I love)

Takes it from the http://emuseum.campus.fu-berlin.de/eMuseumPlus?service=ExternalInterface&moduleFunction=search
It's horrible old emuseum so I just loop over a bunch of integers in hope to find a painting
"""
import artdatabot
import pywikibot
import urllib3
import requests
import re
import html


def get_entarte_generator():
    """
    Search for paintings and loop over it. Did I mention that old emuseum sucks?
    """
    #urllib3.disable_warnings()
    #htmlparser = HTMLParser()

    # Inventory can be found at https://www.vam.ac.uk/articles/explore-entartete-kunst-the-nazis-inventory-of-degenerate-art
    # This also lists the number of works per collection
    # https://www.geschkult.fu-berlin.de/en/e/db_entart_kunst/datenbank/aktueller_stand/index.html


    """
    Berlin, National Galerie / Crown Prince’s Palace (October 2010)
    Dresden, City Museum (January 2011)
    Düsseldorf, Kunstsammlungen der Stadt (sculptures, June 2013)
    Erfurt, Angermuseum (November 2010) <--- also ge
    Essen, Museum Folkwang (excluding prints, July 2010)
    Frankfurt/Main, Städel Art Institute and Municipal Gallery (paintings and sculptures, December 2010)
    Freiburg im Breisgau, Municipial Art Collections (March 2016)
    Halle/Salle, Museum for Arts and Crafts (April 2010)
    Hamm, Gustav Lübcke Museum (January 2012)
    Jena, Kunstverein (January 2011)
    Munich, Bavarian State Painting Collections (November 2010)
    Oldenburg, Landesmuseum (November 2010)
    Rostock, Municipal Museum (April 2010)
    Schwerin, Staatliches Museum Schwerin (April 2010)
    Stuttgart, State Gallery (March 2016)
    Ulm, Municipial Museum (March 2016)
    """
    collections = { 'Berlin, Nationalgalerie (Kronprinzen-Palais)': 'Q162111',
                    'Dresden, Stadtmuseum': 'Q2327655',
                    'Düsseldorf, Kunstsammlungen der Stadt': 'Q131748853',
                    'Erfurt, Angermuseum': 'Q538183',
                    # Erfurt, Museen der Stadt (Museum für Kunst und Heimatgeschichte) ?????
                    'Essen, Museum Folkwang': 'Q125634',
                    'Frankfurt/M, Städelsches Kunstinstitut und Städtische Galerie': 'Q163804',
                    # Freiburg im Breisgau, Städtische Sammlungen
                    # Halle/Salle, Museum for Arts and Crafts (April 2010)
                    'Hamm, Städtisches Gustav-Lübke-Museum': 'Q59926017',
                    'Hamburg, Kunsthalle' : 'Q169542',
                    'Jena, Kunstverein' : 'Q1686807',
                    'Karlsruhe, Staatliche Kunsthalle' : 'Q658725',
                    'Köln, Wallraf-Richartz-Museum' : 'Q700959',
                    'München, Bayerische Staatsgemäldesammlungen' : 'Q812285',
                    'München, Bayerische Staatsgemäldesammlungen – Pinakothek der Moderne' : 'Q812285',
                    'München, Bayerische Staatsgemälde-Sammlung' : 'Q812285',
                    'Oldenburg, Landesmuseum': 'Q1988652',
                    'Schwerin, Staatliches Museum': 'Q2324618',
                    'Stuttgart, Württembergische Staatsgalerie': 'Q14917275',
                    'Ulm, Stadtmuseum': 'Q2475379',
                    # https://www.wikidata.org/w/index.php?title=User_talk:Achim_Raschka&oldid=2299813045#EK_found_collections
                    # done section
                    'Altenburg, Staatliches Lindenau-Museum': 'Q878678',
                    'Altona, Stadtmuseum': 'Q126971',
                    'Amsterdam, Stedelijk Museum': 'Q924335',
                    'Antwerpen, Koninklijk Museum voor Schone Kunsten': 'Q1471477',
                    'Basel, Kunstmuseum': 'Q194626',
                    'Basel, Fondation Beyeler': 'Q673833',
                    'Bautzen, Stadtmuseum': 'Q1471331',
                    'Berlin, Akademie der Künste': 'Q414110',
                    'Berlin, Alte Nationalgalerie': 'Q162111',
                    'Berlin, Bauhaus Archiv': 'Q811389',
                    'Berlin, Berlinische Galerie': 'Q700222',
                    'Berlin, Brücke-Museum': 'Q833759',
                    'Berlin, Neue Nationalgalerie': 'Q32659772',
                    'Bern, Kunstmuseum': 'Q194622',
                    'Bernried, Buchheim Museum': 'Q895596',
                    'Bielefeld, Kunsthalle': 'Q321716',
                    'Bloomington, Indiana University Art Museum': 'Q6023573',
                    'Bordeaux, Musée Des Beaux Arts': 'Q954222',
                    'Boston, Museum of Fine Arts': 'Q49133',
                    'Braunschweig, Herzog Anton Ulrich-Museum': 'Q678082',
                    'Bremen, Kunsthalle': 'Q693591',
                    'Breslau, Schlesisches Museum der Bildenden Künste': 'Q15127520',
                    'Brüssel, Musées royaux des Beaux-Arts': 'Q377500',
                    'Cambridge/MA, Busch-Reisinger Museum - Harvard University Art Museums': 'Q1017269',
                    'Cambridge/MA, Fogg Art Museum': 'Q809600',
                    'Cardiff, Amgueddfa Cymru – National Museum of Wales': 'Q2046319',
                    'Chemnitz, Kunsthütte': 'Q59926011',
                    'Chicago, The Art Institute': 'Q239303',
                    'Darmstadt, Hessisches Landesmuseum': 'Q452362',
                    'Davos, Kirchner Museum': 'Q1743358',
                    'Detroit, Institute of Arts': 'Q1201549',
                    'Dortmund, Museum am Ostwall': 'Q314441',
                    'Dresden, Galerie Neue Meister': 'Q472706',
                    'Dresden, Staatliche Gemäldegalerie': 'Q4890',
                    'Dresden, Städtische Galerie': 'Q830042',
                    'Duisburg, Stiftung Wilhelm Lehmbruck Museum': 'Q315753',
                    'Düsseldorf, Galerie Paffrath': 'Q23786742',
                    'Düsseldorf, Stiftung Museum Kunstpalast': 'Q461277',
                    'Eindhoven, Van Abbemuseum': 'Q1782422',
                    'Emden, Kunsthalle': 'Q896726',
                    'Frankfurt am Main, Städelsches Kunstinstitut und Städtische Galerie': 'Q163804',
                    'Freiburg im Breisgau, Augustinermuseum': 'Q542932',
                    'Galerie Karsten Greve AG, St. Moritz': 'Q23786747',
                    'Gelsenkirchen, Städtisches Museum': 'Q1792542',
                    'Güstrow, Stadtmuseum': 'Q56286157',
                    'Hagen, Karl Ernst Osthaus Museum': 'Q314559',
                    'Halle, Stiftung Moritzburg': 'Q879819',
                    'Hamburg, Ernst Barlach Haus, Stiftung Hermann F. Reemtsma': 'Q871581',
                    'Hamburg, Hamburger Kunsthalle': 'Q169542',
                    'Hamburg, Hansische Hochschule für Bildende Künste': 'Q1622237',
                    'Hamburg, Museum für Kunst und Gewerbe': 'Q896052',
                    'Hannover, Kestner-Museum': 'Q457671',
                    'Hannover, Niedersächsisches Landesmuseum': 'Q314082',
                    'Hannover, Sprengel Museum': 'Q510144',
                    'Hiroshima, Museum of Art': 'Q63828',
                    'Houston, The Menil Collection': 'Q1888308',
                    'Köln, Albertus Magnus Universität': 'Q54096',
                    'Köln, Museum Ludwig': 'Q703640',
                    'Kopenhagen, Statens Museum for Kunst': 'Q671384',
                    'Krefeld, Kaiser Wilhelm Museum': 'Q1721563',
                    'Krefeld, Kaiser Wilhelm-Museum': 'Q1721563',
                    'Künzelsau, Museum Würth': 'Q371836',
                    'Leipzig, Museum der bildenden Künste': 'Q566661',
                    'Liechtenstein, Hilti Foundation': 'Q27926230',
                    'Linz, Lentos Kunstmuseum': 'Q686531',
                    'Locarno, Museo Civico e Archeologico Castello Visconteo': 'Q27484731',
                    'London, Tate Modern': 'Q193375',
                    'Lübeck, Museum Behnhaus': 'Q814533',
                    'Lübeck, Museum Behnhaus/Drägerhaus': 'Q814533',
                    'Los Angeles, Robert Gore Rifkind Center for German Expressionist Studies': 'Q130403733',
                    'Ludwigshafen, Wilhelm-Hack-Museum': 'Q499901',
                    'Madrid, Museo Nacional Thyssen-Bornemisza': 'Q176251',
                    'Magdeburg, Kaiser-Friedrich-Museum': 'Q1673285',
                    'Mannheim, Kunsthalle': 'Q468458',
                    'Mannheim, Städtische Kunsthalle': 'Q468458',
                    'Luzern, Galerie Fischer': 'Q47001605',
                    'Minneapolis, Walker Art Center': 'Q1851516',
                    'Mönchengladbach, Städtisches Museum Abteiberg': 'Q206346',
                    'Neuss, Stiftung Insel Hombroich': 'Q2349026',
                    'New York, Metropolitan Museum of Art': 'Q160236',
                    'New York, Museum of Modern Art': 'Q188740',
                    'New York, Solomon R. Guggenheim Museum': 'Q201469',
                    'New York, Whitney Museum of American Art': 'Q639791',
                    'Nürnberg, Städtische Galerie': 'Q122900048',
                    'Oberlin, Allen Memorial Art Museum': 'Q3816734',
                    'Oldenburg, Landesmuseum für Kunst und Kulturgeschichte': 'Q1988652',
                    'Paris, Collection Niarchos': 'Q15697027',
                    'Philadelphia, Museum of Art': 'Q510324',
                    'Pasadena, Norton Simon Museum': 'Q1752085',
                    'Recklinghausen, Kunsthalle': 'Q1792419',
                    'Recklinghausen, Vestisches Museum': 'Q2521245',
                    'Regensburg, Kunstforum Ostdeutsche Galerie': 'Q1328893',
                    'Marburg, Museum der Universität': 'Q50978681',
                    'München, Ketterer Kunst': 'Q94694319',
                    'München, Städtische Galerie im Lenbachhaus': 'Q262234',
                    'München, Städtische Galerie und Lenbachgalerie': 'Q262234',
                    'Münster, Landesmuseum': 'Q1798475',
                    'Münster, Westfälisches Landesmuseum für Kunst und Kulturgeschichte': 'Q1798475',
                    'Saarbrücken, Saarlandmuseum': 'Q829296',
                    'Saarbrücken, Staatliches Museum': 'Q829296',
                    'Saint Louis, University of Missouri': 'Q625103',
                    'Salzburg, Museum der Moderne Salzburg Rupertinum': 'Q1571914',
                    'São Paulo, Museu Lasar Segall': 'Q1954360',
                    'Wien, Leopold Museum': 'Q59435',
                    'Witten an der Ruhr, Märkisches Museum': 'Q1957463',
                    'Wuppertal, Von der Heydt-Museum': 'Q819504',
                    'Zürich, Kunsthaus': 'Q685038',
                    'Wuppertal-Barmen, Ruhmeshalle': 'Q808369',
                    'Solothurn, Kunstmuseum': 'Q683163',
                    'St. Louis, Saint Louis Art Museum': 'Q1760539',
                    'Chemnitz, Kunstsammlungen': 'Q1792616',
                    'Chemnitz, Kunstsammlungen Chemnitz - Museum Gunzenhauser, Eigentum der Stiftung Gunzenhauser': 'Q832393',
                    'Chemnitz, Städtische Kunstsammlung': 'Q1792617',
                    'Chemnitz, Städtische Kunstsammlung (Leihgabe)': 'Q1792617',
                    'Bochum, Städtische Gemäldegalerie': 'Q529069',
                    'Frankfurt am Main, Slg. Deutsche Bank AG': 'Q2217335',
                    'Husum, Nissenhaus': 'Q1998605',
                    'Flensburg, Kunstgewerbe-Museum': 'Q1954806',
                    'Frankfurt/O, Oderland-Museum': 'Q76632791',
                    'Gera, Städtisches Museum': 'Q1280968',
                    'Braunschweig, Städtisches Museum': 'Q2360096',
                    'Seattle, Seattle Art Museum': 'Q1816301',
                    'Seebüll, Nolde Stiftung': 'Q14399994',
                    'Soest, Kunstsammlung der Stadt / Museum Wilhelm Morgner': 'Q1552421',
                    'Stettin, Museum für Kunst und Kunstgewerbe': 'Q2802195',
                    'Stuttgart, Staatsgalerie': 'Q14917275',
                    'Stuttgart, Kunstmuseum Stuttgart – Galerie der Stadt': 'Q317398',
                    'Vevey, Musée Jenisch': 'Q2400378',
                    'Washington, Smithsonian Institution': 'Q1192305',
                    'Weimar, Schloßmuseum': 'Q878253',
                    'Wichtrach, Galerie Henze & Ketterer AG': 'Q1491867',
                    'Winterthur, Kunstmuseum': 'Q14565992',
                    'Wiesbaden, Museum': 'Q316514',
                    'Neuss, Clemens-Sels-Museum': 'Q1099859',
                    'Rochester, Memorial Art Gallery of the University of Rochester': 'Q6815343',
                    'Rostock, Kulturhistorisches Museum': 'Q72102600',
                    'Kaiserslautern, Museum Pfalzgalerie': 'Q1386526',
                    'Kansas City, The Nelson-Atkins Museum of Art': 'Q1976985',
                    'Kassel, Staatliche Kunstsammlungen': 'Q1954840',
                    'Ulm, Ulmer Museum': 'Q2475379',
                    'Schweinfurt, Museum Georg Schäfer': 'Q880898',
                    'Wiesbaden, Nassauisches Landesmuseum': 'Q316514',
                    'Mönchengladbach, Städtische Bildergalerie': 'Q206346',
                    'Zürich, Stiftung Sammlung E. G. Bührle': 'Q666331',
                    'Dessau, Anhaltinische Gemäldegalerie': 'Q76638284',
                    'Dortmund, Städtisches Kunst- und Gewerbemuseum': 'Q164887',
                    'Wuppertal-Elberfeld, Städtische Bildergalerie': 'Q819504',
                    'Nagoya, Aichi Prefectural Museum of Art': 'Q4696562',
                    'Mülheim, Städtisches Museum': 'Q1792546',
                    'Mainz, Städtisches Museum': 'Q3329673',
                    'Kiel, Kunsthalle': 'Q327540',
                    'Konstanz, Wessenberg-Galerie': 'Q15849542',
                    'Görlitz, Städtische Kunstsammlungen': 'Q1791752',
                    'Hagen, Städtisches Museum': 'Q123296003',
                    'Zwickau, König Albert-Museum': 'Q15130656',
                    'Washington, National Gallery of Art': 'Q214867',
                    'Sydney, Art Gallery New South Wales': 'Q705551',
                    'Kaiserslautern, Pfälzisches Gewerbemuseum': 'Q1386526',
                    'Meersburg, Galerie Bodenseekreis': 'Q131787231',
                    'Oslo, Rathaus': 'Q373850',
                    'Halle (Saale), Kulturstiftung Sachsen-Anhalt - Kunstmuseum Moritzburg Halle (Saale)': 'Q80943953',
                    'Beuthen, Oberschlesisches Landesmuseum': 'Q11786987',
                    'Houston, The Museum of Fine Arts': 'Q1565911',
                    'Kunstmuseum, Krefeld': 'Q24264237',
                    'Minneapolis, Institute of Arts': 'Q1700481',
                    'Cincinnati, Art Museum': 'Q2970522',
                    'Arrode, Peter-August-Böckstiegel-Haus': 'Q131787286',
                    'Erfurt, Museen der Stadt (Museum für Kunst und Heimatgeschichte)': 'Q538183',
                    'Breslau, Kunstsammlungen der Stadt (Schloßmuseum)': 'Q444070',
                    'Liège, Le Musée d’Art moderne et d’Art contemporain': 'Q2526644',
                    'Jena, Städtische Museen - Kunstsammlung': 'Q994151',
                    'Freiburg im Breisgau, Städtische Sammlungen': 'Q55409491',
                    'Dublin, National Gallery': 'Q2018379',
                    'Gelsenkirchen, Städtische Kunstsammlung': 'Q1792542',
                    'Lübeck, Museum für Kunst und Kulturgeschichte': 'Q18674699',
                    'Bochum, Kunstsammlung': 'Q529069',
                    'Koblenz, Städtisches Schloßmuseum': 'Q1940336',
                    'Mülheim an der Ruhr, Städtisches Museum': 'Q1792546',
                    }

    unknown_collections = {}

    session = requests.Session()

    # 109589 is the first one giving content
    # 130586 and above nothing (might be lower)

    for i in range(109589, 130586):
        url = 'http://emuseum.campus.fu-berlin.de/eMuseumPlus?service=ExternalInterface&module=collection&objectId=%s&viewType=detailView' % (i,)

        print (url)

        item_page = session.get(url)

        metadata = {}
        metadata['url'] = url

        instance_regex = '\<span class\=\"tspPrefix\"\>Category\/Object Type\:\<\/span\>\<span class\=\"tspValue\"\>Gem&#228\;lde\<\/span\>'
        instance_match = re.search(instance_regex, item_page.text)

        if not instance_match:
            # Not for us
            continue

        # It's a painting
        metadata['instanceofqid'] = 'Q3305213'
        metadata['collectionqid'] = 'Q111796449'
        metadata['collectionshort'] = 'entartete'
        metadata['locationqid'] = 'Q111796449'

        inv_regex = '\<li class\=\"ekInventarNr\"\>\<span class\=\"tspPrefix\"\>NS Inventar EK-Nr\.\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        inv_match = re.search(inv_regex, item_page.text)
        if not inv_match:
            continue

        # FIXME: Still need to check if it's not "nicht im NS Inventar"
        # FIXME: Also add the extended EK numbers here

        metadata['id'] = inv_match.group(1)
        metadata['idpid'] = 'P217'

        # Disable to trigger the url addition
        metadata['artworkid'] = inv_match.group(1)
        metadata['artworkidpid'] = 'P4627'

        title_regex = '\<li class\=\"titel\"\>\<h3\>\<span class\=\"tspPrefix\"\>Title\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        title_match = re.search(title_regex, item_page.text)
        # Burn if no title found
        title = html.unescape(title_match.group(1)).strip()

        metadata['title'] = { 'de' : title,
                              }

        creator_regex = '\<li class\=\"kuenstler\"\>\<span class\=\"tspPrefix\"\>Artist\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        creator_match = re.search(creator_regex, item_page.text)

        name = html.unescape(creator_match.group(1)).strip()
        metadata['creatorname'] = name

        if metadata.get('instanceofqid') == 'Q3305213':
            metadata['description'] = { 'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'),),
                                        'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                        'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                        }

        # This is for the collection where it got stolen from
        origin_regex = '\<li class\=\"herkunftsort\"\>\<span class\=\"tspPrefix\"\>Museum of Origin\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        origin_inv_regex = '\<li class\=\"herkunftsinventar\"\><span class\=\"tspPrefix\"\>Inventory of Origin\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        origin_match = re.search(origin_regex, item_page.text)
        origin_inv_match = re.search(origin_inv_regex, item_page.text)
        if origin_match:
            origin = html.unescape(origin_match.group(1)).strip()

            if origin in collections:
                metadata['extracollectionqid'] = collections.get(origin)
                if origin_inv_match:
                    origin_inv = html.unescape(origin_inv_match.group(1)).strip()
                    if origin in collections:
                        metadata['extraid'] = origin_inv
            else:
                print ('Collection %s not found' % (origin,))
                if origin not in unknown_collections:
                    unknown_collections[origin] = 0
                unknown_collections[origin] += 1

        # This is for the collection where it currently is
        location_regex = '\<li class\=\"standort\"\>\<span class\=\"tspPrefix\"\>Location\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        location_match = re.search(location_regex, item_page.text)
        if location_match:
            location = html.unescape(location_match.group(1)).strip()

            if location in collections:
                metadata['extracollectionqid2'] = collections.get(location)
            else:
                print ('Collection %s not found' % (location,))
                if location not in unknown_collections:
                    unknown_collections[location] = 0
                unknown_collections[location] += 1

        date_field_regex = '\<li class\=\"datierung\"\>\<span class\=\"tspPrefix\"\>Date\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        date_field_match = re.search(date_field_regex, item_page.text)

        if date_field_match:
            date_field = date_field_match.group(1)
            # Quite incomplete, but covers a lot
            dateregex = '^(\d\d\d\d)$'
            datecircaregex = '^um\s*(\d\d\d\d)\s*$'
            periodregex = '^(\d\d\d\d)[-\/](\d\d\d\d)$'
            circaperiodregex = '(\d\d\d\d)[-\/](\d\d\d\d)\s*\(um\)\s*$' # No hits I think

            datematch = re.match(dateregex, date_field)
            datecircamatch = re.match(datecircaregex, date_field)
            periodmatch = re.match(periodregex, date_field)
            circaperiodmatch = re.match(circaperiodregex, date_field)

            if datematch:
                # Don't worry about cleaning up here.
                metadata['inception'] = int(datematch.group(1))
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
                print (u'Could not parse date: "%s"' % (date_field,))

        medium_regex = '\<li class\=\"material\"\>\<span class\=\"tspPrefix\"\>Material\/Technique\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        medium_match = re.search(medium_regex, item_page.text)

        if medium_match:
            medium = html.unescape(medium_match.group(1)).strip()
            mediums = { 'Öl auf Leinwand' : 'oil on canvas',
                        'Öl auf Holz' : 'oil on panel',
                        'Öl auf Papier' : 'oil on paper',
                        'Öl auf Kupfer' : 'oil on copper',
                        'Öl auf Pappe' : 'oil on cardboard',
                        'Tempera auf Leinwand' : 'tempera on canvas',
                        'Tempera auf Holz' : 'tempera on panel',
                        'Acryl auf Leinwand' : 'acrylic paint on canvas',
                        }
            if medium in mediums:
                metadata['medium'] = mediums.get(medium)
            else:
                print('Unable to match medium %s' % (medium,))

        dimensions_regex = '\<li class\=\"masse\"\><span class\=\"tspPrefix\"\>Measure\:\<\/span\>\<span class\=\"tspValue\"\>([^\<]+)\<'
        dimensions_match = re.search(dimensions_regex, item_page.text)

        if dimensions_match:
            dimensions = html.unescape(dimensions_match.group(1)).strip()
            regex_2d = '^Bildmaß\s*(?P<height>\d+(,\d+)?)\s*(x|×)\s*(?P<width>\d+(,\d+)?)\s*cm\s*$'
            match_2d = re.match(regex_2d, dimensions)
            if match_2d:
                metadata['heightcm'] = match_2d.group('height')
                metadata['widthcm'] = match_2d.group('width')

        yield metadata
        # TODO: Do some sort of pretty print
        print(unknown_collections)


def main(*args):
    dict_gen = get_entarte_generator()
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True

    if dryrun:
        for painting in dict_gen:
            print (painting)
    else:
        art_data_bot = artdatabot.ArtDataBot(dict_gen, create=create)
        art_data_bot.run()

if __name__ == "__main__":
    main()
