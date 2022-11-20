#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Van Fries Museum to Wikidata.

Updated to use the tresoar API instead of the Collectie Nederland API see
https://prod.tresoar.hubs.delving.org/api/search/v1/?query=schilderij&hqf[]=delving_spec:friesmuseum&start=61&rows=10&format=json

This bot uses artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re

def getFriesGenerator():
    """
    Generator to return Fries Museum paintings
    """
    basesearchurl = 'https://prod.tresoar.hubs.delving.org/api/search/v1/?query=schilderij&hqf[]=delving_spec:friesmuseum&format=json&start=%s&rows=%s'
    start = 1
    rows = 50
    hasNext = True

    while hasNext:
        searchUrl = basesearchurl % (start, rows)
        searchPage = requests.get(searchUrl)
        searchJson = searchPage.json()

        start = searchJson.get('result').get('pagination').get('nextPage')
        hasNext = searchJson.get('result').get('pagination').get('hasNext')

        for item in searchJson.get('result').get('items'):
            itemfields = item.get('item').get('fields')
            # print (itemfields)
            metadata = {}

            if itemfields.get('delving_collection')[0] == 'friesmuseum':
                metadata['collectionqid'] = 'Q848313'
                metadata['collectionshort'] = 'Fries Museum'
                metadata['locationqid'] = 'Q848313'
            else:
                print('# Another collection, skip')
                continue

            if itemfields.get('icn_objectSoort') and len(itemfields.get('icn_objectSoort')) == 1 and \
                    itemfields.get('icn_objectSoort')[0] == 'schilderij':
                metadata['instanceofqid'] = 'Q3305213'
            else:
                print('# Not a painting, skip')
                continue

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = itemfields.get('icn_objectNumber')[0]
            metadata['idpid'] = u'P217'

            if itemfields.get('dc_title') and len(itemfields.get('dc_title')) == 1:
                title = itemfields.get('dc_title')[0]
                metadata['title'] = {'nl': title, }

            # Tresoar url is broken
            # metadata['refurl'] =

            # This points to the old very broken website
            metadata['url'] = 'https://collectie.friesmuseum.nl/?diw-id=%s' % (item.get('item').get('doc_id'),)

            if itemfields.get('dc_creator') and len(itemfields.get('dc_creator')) == 1:
                name = itemfields.get('dc_creator')[0]
                if u',' in name:
                    (surname, sep, firstname) = name.partition(u',')
                    name = '%s %s' % (firstname.strip(), surname.strip(),)
                metadata['creatorname'] = name

                if metadata['creatorname'] == 'onbekend':
                    metadata['creatorname'] = 'anonymous'
                    metadata['description'] = {'nl': 'schilderij van anonieme schilder',
                                               'en': 'painting by anonymous painter',
                                               }
                    metadata['creatorqid'] = 'Q4233718'
                else:
                    metadata['description'] = {'nl': '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                               'en': '%s by %s' % ('painting', metadata.get('creatorname'),),
                                               'de': '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                               'fr': '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                               }

            if itemfields.get('icn_material'):
                materials = set()
                for material in itemfields.get('icn_material'):
                    materials.add(material)

                if materials == {'olieverf', 'doek'} or materials == {'olieverf', 'canvas'} :
                    metadata['medium'] = 'oil on canvas'
                elif materials == {'olieverf', 'paneel'}:
                    metadata['medium'] = 'oil on panel'
                elif materials == {'olieverf', 'koper'}:
                    metadata['medium'] = 'oil on copper'
                    #elif (material1 == 'papier' and material2 == 'olieverf') or (material1 == 'olieverf' and material2 == 'papier'):
                    #    metadata['medium'] = 'oil on paper'
                    #elif (material1 == 'doek' and material2 == 'tempera') or (material1 == 'tempera' and material2 == 'doek'):
                    #    metadata['medium'] = 'tempera on canvas'
                    #elif (material1 == 'paneel' and material2 == 'tempera') or (material1 == 'tempera' and material2 == 'paneel'):
                    #    metadata['medium'] = 'tempera on panel'
                    #elif (material1 == 'doek' and material2 == 'acrylverf') or (material1 == 'acrylverf' and material2 == 'doek'):
                    #    metadata['medium'] = 'acrylic paint on canvas'
                elif materials == {'acryl', 'doek'}:
                    metadata['medium'] = 'acrylic paint on canvas'
                    #elif (material1 == 'paneel' and material2 == 'acrylverf') or (material1 == 'acrylverf' and material2 == 'paneel'):
                    #    metadata['medium'] = 'acrylic paint on panel'
                    #elif (material1 == 'papier' and material2 == 'aquarel') or (material1 == 'aquarel' and material2 == 'papier'):
                    #    metadata['medium'] = 'watercolor on paper'
                    #else:
                    #    print('Unable to match %s & %s' % (material1, material2,))
                elif materials == {'olieverf', 'doek', 'paneel'}:
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
                    print('Unable to match %s' % (materials,))

            try:
                if itemfields.get('icn_productionStart') and itemfields.get('icn_productionEnd'):
                    period = '%s - %s' % (itemfields.get('icn_productionStart')[0], itemfields.get('icn_productionEnd')[0])
                    if itemfields.get('icn_productionPeriod') and itemfields.get('icn_productionPeriod')[0] == period:
                        metadata['inceptionstart'] = int(itemfields.get('icn_productionStart')[0])
                        metadata['inceptionend'] = int(itemfields.get('icn_productionEnd')[0])
                    elif itemfields.get('icn_productionStart') == itemfields.get('icn_productionEnd'):
                        metadata['inception'] = int(itemfields.get('icn_productionStart')[0])
            except ValueError:
                # Weird date
                pass

            if itemfields.get('europeana_hasView'):
                recentinception = False
                if metadata.get('inception') and metadata.get('inception') > 1924:
                    recentinception = True
                if metadata.get('inceptionend') and metadata.get('inceptionend') > 1924:
                    recentinception = True
                if not recentinception:
                    metadata['imageurl'] = itemfields.get('europeana_hasView')[0]
                    metadata['imageurlformat'] = 'Q2195'  # JPEG
                    metadata['imageoperatedby'] = 'Q2267622'  # Tresoar

            yield metadata

    return
    
def main(*args):
    dictGen = getFriesGenerator()
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True

    if dryrun:
        for painting in dictGen:
            print(painting)
    else:
        artDataBot = artdatabot.ArtDataBot(dictGen, create=create)
        artDataBot.run()

if __name__ == "__main__":
    main()
