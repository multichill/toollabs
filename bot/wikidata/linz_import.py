#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape paintings (and other artworks) from the Linz database (the Führermuseum).

Searching for % seems to return all works. We only take the ones that have a Linz inventory number

"""
import artdatabot
import pywikibot
import urllib3
import requests
import re


def get_linz_generator():
    """
    Search for paintings and loop over it.
    """
    urllib3.disable_warnings()

    search_url = 'https://www.dhm.de/datenbank/linzdbv2/queryresult.php?search%5Bprovenance%5D=&search%5Btitle%5D=&search%5Bartist%5D=%25&search%5Blocation%5D=&Status=0&Treffer=x&submit_search=submit_search'

    search_page = requests.get(search_url, verify=False)
    search_page_data = search_page.text
    search_regex = '\<div onclick\=\"window\.location\=\'(\/datenbank\/linzdbv2\/queryresult\.php\?obj_no\=LI\d+)\'\;\" class\=\"galery-item\"\>'

    for match in list(re.finditer(search_regex, search_page_data))[1:4000]:
        metadata = {}

        url = 'https://www.dhm.de%s' % (match.group(1),)
        print (url)
        metadata['url'] = url

        item_page = requests.get(url, verify=False)
        item_page_data = item_page.text

        collection_regex = 'valign\=\"top\"\>Sammlung\:\s*([^\<]+)\<\/th\>'
        collection_match = re.search(collection_regex, item_page_data)

        if collection_match and collection_match.group(1)== 'Linzer Sammlung':
            metadata['collectionqid'] = 'Q475667'
            metadata['collectionshort'] = 'Linz'
            metadata['locationqid'] = 'Q475667'
        else:
            print('Panic, not in the collection')
            continue

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

        title_regex = 'valign\=\"top\" width\=\"\d+\"\>Titel\: \<\/td\>\<td align\=\"left\" valign\=\"top\" width=\"\d+\"\>\<strong\>([^\<]+)\<'
        title_match = re.search(title_regex, item_page_data)

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

        title = title_match.group(1)

        metadata['title'] = { 'de' : title,
                              }

        creator_regex = '\<td align\=\"left\" valign\=\"top\"\>Künstler: \<\/td\>[\r\n\t\s]*\\<td align\=\"left\" valign\=\"top\"\>\<strong\>([^\<]+)\<'
        creator_match = re.search(creator_regex, item_page_data)

        name = creator_match.group(1).strip()
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
    dict_gen = get_linz_generator()
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
