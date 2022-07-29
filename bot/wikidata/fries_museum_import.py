#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Van Fries Museum to Wikidata.

Uses the Collectie Nederland API which returns EDM (Europeana Data Model) formatted data, see
https://www.collectienederland.nl/search/?qf%5B%5D=edm_dataProvider%3AFries+Museum&qf=dc_type%3Aschilderij&rows=50&format=json&start=1

This data is quite outdated so I should probably switch to:
https://prod.tresoar.hubs.delving.org/api/search/v1/?query=schilderij&facet.field=icn_technique_facet&facet.field=dc_creator_facet&facet.field=icn_productionPeriod_facet&facet.field=icn_subjectDepicted_facet&hqf[]=delving_spec:friesmuseum&page=1&format=json

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
    basesearchurl = 'https://www.collectienederland.nl/search/?qf%%5B%%5D=edm_dataProvider%%3AFries+Museum&qf=dc_type%%3Aschilderij&format=json&start=%s&rows=%s'
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
            #print (itemfields)
            metadata = {}

            if itemfields.get('legacy').get('delving_collection') == 'fries-museum':
                metadata['collectionqid'] = 'Q848313'
                metadata['collectionshort'] = 'Fries Museum'
                metadata['locationqid'] = 'Q848313'
            else:
                #Another collection, skip
                continue

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = 'Q3305213'

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = itemfields.get('dc_identifier')[0].get('value')
            metadata['idpid'] = u'P217'

            if itemfields.get('dc_title'):
                title = itemfields.get('dc_title')[0].get('value')
                metadata['title'] = {'nl': title, }

            metadata['refurl'] = itemfields.get('entryURI')

            # This points to the old very broken website
            # metadata['url'] = itemfields.get('edm_isShownAt')[0].get('value')
            metadata['url'] = 'https://collectie.friesmuseum.nl/?diw-id=tresoar_friesmuseum_%s' % (metadata['id'],)

            name = itemfields.get('dc_creator')[0].get('value')
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
                                           }

            paints = {'olieverf': 'oil',
                      'waterverf': 'watercolor',
                      'acrylverf': 'acrylic',

                      }
            surfaces = {'doek': 'canvas',
                        'paneel': 'panel',
                        'panel': 'panel',
                        'papier': 'paper',
                        'karton': 'cardboard',
                        }
            paint = None
            surface = None

            if itemfields.get('dcterms_medium') and len(itemfields.get('dcterms_medium')) >= 2:
                material_1 = itemfields.get('dcterms_medium')[0].get('value').strip()
                material_2 = itemfields.get('dcterms_medium')[1].get('value').strip()

                for material in (material_1, material_2):
                    if material in paints:
                        paint = paints.get(material)
                    elif material in surfaces:
                        surface = surfaces.get(material)
                    else:
                        print('Unknown material %s' % (material,))

            if paint and surface:
                metadata['medium'] = '%s on %s' % (paint, surface)

            if itemfields.get('dcterms_created'):
                date = itemfields.get('dcterms_created')[0].get('value')
                year_regex = '^(\d\d\d\d)$'
                date_circa_regex = '^ca?\.\s*(\d\d\d\d)$'
                period_regex = '^(\d\d\d\d)\s*[--\/]\s*(\d\d\d\d)$'
                circa_period_regex = '^ca?\.\s*(\d\d\d\d)\s*[--\/]\s*(\d\d\d\d)$'
                short_period_regex = '^(\d\d)(\d\d)[--\/](\d\d)$'
                circa_short_period_regex = '^ca?\.\s*(\d\d)(\d\d)[-–/](\d\d)$'

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
                    print('Could not parse date: "%s"' % (date,))

            if itemfields.get('edm_hasview'):
                recentinception = False
                if metadata.get('inception') and metadata.get('inception') > 1924:
                    recentinception = True
                if metadata.get('inceptionend') and metadata.get('inceptionend') > 1924:
                    recentinception = True
                if not recentinception:
                    metadata['imageurl'] = '%s000' % (itemfields.get('edm_hasview')[0].get('value'))
                    metadata['imageurlformat'] = 'Q2195'  # JPEG
                    metadata['imageoperatedby'] = 'Q1766396'  # Rijksdienst voor het Cultureel Erfgoed (Q1766396)

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
