#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape paintings (and other artworks) from the Hermann Göring database.

Works on https://www.dhm.de/datenbank/goering/dhm_goering.php?seite=6&fld_14=*&suchen=Suchen

No clear way to filter for paintings. Does have a lot of cross references so option to import those instead.
"""
import artdatabot
import pywikibot
import urllib3
import requests
import re
import html

def get_goering_generator(collectionid='Q2647884'):
    """
    Search for paintings and loop over it. Have to use a session to get this data
    :param collectionid: The Wikidata id of the collection to return from
    :return: Generator for artdatabot
    """
    urllib3.disable_warnings()

    session = requests.Session()
    session.get('https://www.dhm.de/datenbank/goering/dhm_goering.php?seite=6&fld_14=*&suchen=Suchen')
    base_search_url = 'https://www.dhm.de/datenbank/goering/dhm_goering.php?seite=8&current=%s'

    for i in range(0, 4300, 20):
        search_url = base_search_url % (i,)
        print (search_url)
        search_page = session.get(search_url) # , verify=False)
        search_page_data = search_page.text
        search_regex = '\<a href\=\"\?seite\=5&amp;fld_0\=(RMG\d+)\"\>Details\<\/a\>'

        for match in list(re.finditer(search_regex, search_page_data)):
            metadata = {}

            url = 'https://www.dhm.de/datenbank/goering/dhm_goering.php?seite=5&fld_0=%s' % (match.group(1),)
            print (url)
            metadata['url'] = url
            metadata['artworkidpid'] = 'P10779'
            metadata['artworkid'] = match.group(1)

            item_page = session.get(url) #, verify=False)
            item_page_data = item_page.text

            # Grab the different inventory numbers
            goering_regex = '\>RM-Nr\.\:\s*(\d+[^\<^\s]*)\s*\<'
            mccp_regex = '\>Mü-Nr\.\:\s*(\d+[^\<^\s]*)\s*\<'
            linz_regex = '\>Sonstige Signatur\:\s*Linz\s*(\d+[^\<^\s]*)\s*\<'
            mnr_regex = '\>Restitution Frankreich\:\s*MNR\s*(\d+[^\<^\s]*)\s*\<'
            nk_regex = '\>Restitution Niederlande\:\s*NK\s*(\d+)\<'

            goering_match = re.search(goering_regex, item_page_data)
            mccp_match = re.search(mccp_regex, item_page_data)
            linz_match = re.search(linz_regex, item_page_data)
            mnr_match = re.search(mnr_regex, item_page_data)
            nk_match = re.search(nk_regex, item_page_data)

            goering_inv = None
            mccp_inv = None
            linz_inv = None
            mnr_inv = None
            nk_inv = None

            if goering_match:
                goering_inv = goering_match.group(1)
            if mccp_match:
                mccp_inv = mccp_match.group(1)
            if linz_match:
                linz_inv = linz_match.group(1)
            if mnr_match:
                mnr_inv = 'MNR %s' % (mnr_match.group(1),)
            if nk_match:
                nk_inv = 'NK%s' % (nk_match.group(1),)

            inventory_collection_list = [(goering_inv, 'Q2647884'),
                                         (mccp_inv, 'Q1053735'),
                                         (linz_inv, 'Q475667'),
                                         (mnr_inv, 'Q19013512'),
                                         (nk_inv, 'Q28045665'),
                                         ]

            # I'm pretty sure everything was in the collection, but not sure
            if collectionid=='Q2647884':
                if not goering_inv:
                    continue
                metadata['collectionqid']= 'Q2647884'
                metadata['collectionshort'] = 'Göring'
                metadata['locationqid'] = 'Q2647884'
                metadata['id'] = goering_inv
                metadata['idpid'] = 'P217'
            elif collectionid=='Q1053735':
                if not mccp_inv:
                    continue
                metadata['collectionqid']= 'Q1053735'
                metadata['collectionshort'] = 'MCCP'
                metadata['locationqid'] = 'Q1053735'
                metadata['id'] = mccp_inv
                metadata['idpid'] = 'P217'
                ## Temp to quickly add the MCCP ID's
                #metadata['artworkidpid'] = 'P10760'
                #metadata['artworkid'] = mccp_inv
            elif collectionid=='Q475667':
                if not linz_inv:
                    continue
                metadata['collectionqid']= 'Q475667'
                metadata['collectionshort'] = 'Linz'
                metadata['locationqid'] = 'Q475667'
                metadata['id'] = linz_inv
                metadata['idpid'] = 'P217'
            elif collectionid=='Q19013512':
                if not mnr_inv:
                    continue
                metadata['collectionqid']= 'Q19013512'
                metadata['collectionshort'] = 'MNR'
                metadata['id'] = mnr_inv
                metadata['idpid'] = 'P217'
            elif collectionid=='Q28045665':
                if not nk_inv:
                    continue
                metadata['collectionqid']= 'Q28045665'
                metadata['collectionshort'] = 'NK'
                metadata['id'] = nk_inv
                metadata['idpid'] = 'P217'

            # Also add the other inventory numbers
            inventory_collection_new = []
            for (extra_inv, extra_collection) in inventory_collection_list:
                if extra_inv and extra_collection!=collectionid:
                    inventory_collection_new.append((extra_inv, extra_collection))

            if len(inventory_collection_new) > 0:
                metadata['extraid'] = inventory_collection_new[0][0]
                metadata['extracollectionqid'] = inventory_collection_new[0][1]

            if len(inventory_collection_new) > 1:
                metadata['extraid2'] = inventory_collection_new[1][0]
                metadata['extracollectionqid2'] = inventory_collection_new[1][1]

            if len(inventory_collection_new) > 2:
                metadata['extraid3'] = inventory_collection_new[2][0]
                metadata['extracollectionqid3'] = inventory_collection_new[2][1]

            if len(inventory_collection_new) > 3:
                # I don't think I'm actually hitting this
                print ('PANIC, TOO MANY INVENTORY NUMBERS')

            # FIXME: Currently no good way to filter on what it is
            painting_regex = '\<p\>Lwd\.\<br\>'
            painting_match = re.search(painting_regex, item_page_data)
            if painting_match:
                metadata['instanceofqid'] = 'Q3305213'
            else:
                metadata['instanceofqid'] = 'Q838948'
                #continue

            title_regex = '\<p\>Datenblatt RMG\d+\<\/p\>\<h2\>([^\<]+)\<'
            title_match = re.search(title_regex, item_page_data)

            title = html.unescape(title_match.group(1)).strip()

            metadata['title'] = { 'de' : title,
                                  }

            creator_regex = 'Großbildansicht zu öffnen\.[\r\n\t\s]*(\<br\>[\r\n\t\s]*\<\/div\>\<br\>\<h3\>|\<\/div\>\<br\>\<h3\>)([^\<]+)\<\/h3\>'
            creator_match = re.search(creator_regex, item_page_data)

            if creator_match:
                name = creator_match.group(2).strip()
                name_regex = '^([^,]+), ([^\(]+) \((.+)\)$'
                name_match = re.match(name_regex, name)

                if name_match:
                    name = '%s %s (%s)' % (name_match.group(2), name_match.group(1), name_match.group(3))
                metadata['creatorname'] = name

                if metadata.get('instanceofqid') == 'Q3305213':
                    metadata['description'] = { 'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'),),
                                                'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                                'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                                }
                elif metadata.get('instanceofqid') == 'Q860861':
                    metadata['description'] = { 'en' : '%s by %s' % ('sculpture', metadata.get('creatorname'),),
                                                }
                else:
                    metadata['description'] = { 'en' : '%s by %s' % ('work of art', metadata.get('creatorname'),),
                                                }

            yield metadata
            continue

            """
            object_type_regex = 'valign\=\"top\"\>Objekttyp\:\s*([^\<]+)\<'
            object_type_match = re.search(object_type_regex, item_page_data)

            material_regex = 'valign\=\"top\"\>Material\/Technik\:\s*\<\/td\>\<td align\=\"left\" valign\=\"top\"\>\<strong\>([^\<]+)\<'
            material_match = re.search(material_regex, item_page_data)

            painting_materials = ['Holz', 'Leinwand', 'Tempera', 'Pappe', 'Schiefer', 'Kupfer', 'Leinwand, oval', 'Aquarell', 'Pastell']

            if object_type_match.group(1)=='Bild' and material_match and material_match.group(1) in painting_materials:
                # It's a painting
                metadata['instanceofqid'] = 'Q3305213'
            elif object_type_match.group(1)=='Büste':
                metadata['instanceofqid'] = 'Q860861' # sculpture
            elif material_match:
                metadata['instanceofqid'] = 'Q838948' # work of art
            else:
                print ('Not a painting, skipping')
                print (object_type_match.group(1))
                if material_match:
                    print (material_match.group(1))
                continue
            """

            yield metadata
            continue


            inv_regex = 'valign\=\"top\"\>Linz-Nr\.\:\s*<\/td\>\<td align\=\"left\" valign\=\"top\"\>\<strong\>(\d[^\<]+)\<'
            inv_match = re.search(inv_regex, item_page_data)
            if not inv_match:
                continue

            metadata['id'] = inv_match.group(1)
            metadata['idpid'] = 'P217'

            acquisition_date_regex = '\<br\>Einlieferung\:\s+[^\<]+\s+(19\d\d)\s+[^\<]+\<'
            acquisition_date_match = re.search(acquisition_date_regex, item_page_data)

            if acquisition_date_match:
                metadata['acquisitiondate'] = acquisition_date_match.group(1)

            inv2_regex = 'valign\=\"top\"\>Mü-Nr\.\:\s*\<\/td\>\<td align\=\"left\" valign\=\"top\"\>\<strong\>([^\<]+) Mü\.-Nummer\<'
            inv2_match = re.search(inv2_regex, item_page_data)

            if inv2_match:
                metadata['extraid2'] = inv2_match.group(1)
                metadata['extracollectionqid2'] = 'Q1053735' # Munich Central Collecting Point

                ## Temp to quickly add the MCCP ID's
                #metadata['artworkidpid'] = 'P10760'
                #metadata['artworkid'] = inv2_match.group(1)



            restitutions = [ {'regex' : '\<br\>Restitution\: Niederlande \(Nederlands Kunstbezit (\d+)\)',
                              'collection' : 'Q28045665',
                              'inventory' : 'NK%s'
                              },
                             {'regex' : '\<br\>Restitution\: Frankreich \(Musées Nationaux de Récupération (\d+)\)',
                              'collection' : 'Q19013512',
                              'inventory' : 'MNR %s'
                              },
                             {'regex' : '\<br\>(Restitution|Verbleib)\: Deutschland \(Kunstbesitz der Bundesrepublik Deutschland',
                              'collection' : 'Q111635246',
                              },
                             {'regex' : '\<br\>Restitution\: Österreich \(\d+ abgegeben, 1996 von Österreich in der Mauerbach-Versteigerung veräußert Katalog Nr\.\s+(\d+)\)\<',
                              'collection' : 'Q111785051',
                              'catalog' : 'Q111793388',
                              'catalog_code' : '%s',
                              },
                             {'regex' : '\<br\>Restitution\: Österreich \(\d+ abgegeben, Bundesdenkmalamt Salzburg',
                              'collection' : 'Q876452',
                              },
                             ]

            for restitution in restitutions:
                inv3_match = re.search(restitution.get('regex'), item_page_data)
                if inv3_match:
                    metadata['extracollectionqid3'] = restitution.get('collection')
                    if restitution.get('inventory'):
                        metadata['extraid3'] = restitution.get('inventory') % (inv3_match.group(1),)
                        #print (metadata['extraid3'])
                    elif restitution.get('catalog') and restitution.get('catalog_code'):
                        metadata['catalog_code'] = restitution.get('catalog_code') % (inv3_match.group(1),)
                        metadata['catalog'] = restitution.get('catalog')





            date_field_regex = 'valign\=\"top\"\>Datierung\: \<\/td\>\<td align\=\"left\" valign\=\"top\"\>\<strong\>([^\<]+)\<'
            date_field_match = re.search(date_field_regex, item_page_data)

            if date_field_match:
                date_field = date_field_match.group(1)
                dateregex = u'^(\d\d\d\d)$'
                datecircaregex = u'^(\d\d\d\d)\s*\(um\)\s*$'
                periodregex = u'^(\d\d\d\d)[-\/](\d\d\d\d)$'
                circaperiodregex = u'(\d\d\d\d)[-\/](\d\d\d\d)\s*\(um\)\s*$' # No hits I think

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

            # I'm not sure about the dimensions
            dimensions_regex = 'valign\=\"top\"\>Maße\: \<\/td\>\<td align\=\"left\" valign\=\"top\"\>\<strong\>([^\<]+)\<'
            dimensions_match = re.search(dimensions_regex, item_page_data)

            if dimensions_match:
                dimensions = dimensions_match.group(1)
                regex_2d = u'(?P<height>\d+(,\d+)?) (x|×) (?P<width>\d+(,\d+)?)\s*$'
                #regex_3d = u'overall\: (?P<height>\d+(\.\d+)?) (x|×) (?P<width>\d+(\.\d+)?) cm (x|×) (?P<depth>\d+(\.\d+)?) cm \([^\)]+\)$'
                match_2d = re.match(regex_2d, dimensions)
                #match_3d = re.match(regex_3d, dimensions)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height')
                    metadata['widthcm'] = match_2d.group(u'width')
                #elif match_3d:
                #    metadata['heightcm'] = match_3d.group(u'height')
                #    metadata['widthcm'] = match_3d.group(u'width')
                #    metadata['depthcm'] = match_3d.group(u'depth')

            # Not that good quality images, but it makes matching a lot easier
            image_regex = '\<img src\=\"(img\.php\?laufnr\=LI\d+)\" alt\=\"LI[^\"]+\" class\=\"card-img\" border\=\"0\"\>'
            image_match = re.search(image_regex, item_page_data)

            if image_match:
                image_url = 'https://www.dhm.de/datenbank/linzdbv2/%s' % (image_match.group(1),)
                # To filter out the placeholders
                imageresponse = requests.get(image_url, stream=True, verify=False)
                if len(imageresponse.text) > 5000:
                    metadata[u'imageurl'] = image_url
                    metadata[u'imageurlformat'] = u'Q2195' #JPEG
                    metadata[u'imageoperatedby'] = 'Q688335'
                    # Could use this later to force
                    # metadata[u'imageurlforce'] = True

            yield metadata


def main(*args):
    collectionid = 'Q2647884'
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-collectionid:'):
            if len(arg) == 14:
                collectionid = pywikibot.input(
                    u'Please enter the collectionid you want to focus on:')
            else:
                collectionid = arg[14:]
        elif arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True
    dict_gen = get_goering_generator(collectionid)

    if dryrun:
        for painting in dict_gen:
            print (painting)
    else:
        art_data_bot = artdatabot.ArtDataBot(dict_gen, create=create)
        art_data_bot.run()

if __name__ == "__main__":
    main()
