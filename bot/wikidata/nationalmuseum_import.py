#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import Nationalmuseum paintings. Was done before, but not by me.

Using https://api.nationalmuseum.se/api/objects?page=2&limit=10
"""
import artdatabot
import pywikibot
import requests
import re
from html.parser import HTMLParser

def getNationalmuseumGenerator():
    """
    Generator to return Nationalmuseum paintings
    :return:
    """
    basesearchurl = 'https://api.nationalmuseum.se/api/objects?page=%s&limit=100'
    next_page = 1

    htmlparser = HTMLParser()

    missedlocations = {}

    while next_page:
        searchUrl = basesearchurl % (next_page,)
        print (searchUrl)
        searchPage = requests.get(searchUrl)
        searchJson = searchPage.json()
        next_page = searchJson.get('data').get('paging').get('next_page')

        painting_categories = [ 'Målningar (Måleri)',
                                'Måleri (Måleri)',
                                'Måleri',
                                'Ikoner (Måleri)',
                                'Miniatyrer (Måleri)',
                                'Illuminerade handskrifter (Måleri)',
                                ]

        for iteminfo in searchJson.get('data').get('items'):
            found_painting = False
            if iteminfo.get('category') and iteminfo.get('category').get('sv'):
                if iteminfo.get('category').get('sv') in painting_categories and iteminfo.get('inventory_number'):
                    found_painting = True
            if not found_painting:
                continue

            #import json
            #print (json.dumps(iteminfo, sort_keys=True, indent=4))

            metadata = {}
            metadata['instanceofqid'] = 'Q3305213'
            metadata['collectionqid'] = 'Q842858'
            metadata['collectionshort'] = 'Nationalmuseum'
            metadata['locationqid'] = 'Q842858'

            itemid = '%s' % (iteminfo.get('id'),)
            url = 'http://collection.nationalmuseum.se/eMuseumPlus?service=ExternalInterface&module=collection&objectId=%s&viewType=detailView' % (itemid,)
            print (url)
            metadata['url'] = url

            metadata['artworkidpid'] = 'P2539'
            metadata['artworkid'] = itemid
            metadata['idpid'] = 'P217'
            metadata['id'] = iteminfo.get('inventory_number')

            # Title is provided in three languages. Usually Swedish and English
            if iteminfo.get('title'):
                if iteminfo.get('title').get('sv') or iteminfo.get('title').get('en') or iteminfo.get('title').get('de'):
                    metadata['title'] = {}
                    if iteminfo.get('title').get('sv'):
                        svtitle = iteminfo.get('title').get('sv').replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').replace('  ', ' ')
                        if len(svtitle) > 220:
                            svtitle = svtitle[0:200].strip(' ')
                        metadata['title']['sv'] = svtitle
                    if iteminfo.get('title').get('en'):
                        entitle = iteminfo.get('title').get('en').replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').replace('  ', ' ')
                        if len(entitle) > 220:
                            entitle = entitle[0:200].strip(' ')
                        metadata['title']['en'] = entitle
                    if iteminfo.get('title').get('de'):
                        detitle = iteminfo.get('title').get('de').replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').replace('  ', ' ')
                        if len(detitle) > 220:
                            detitle = detitle[0:200].strip(' ')
                        metadata['title']['de'] = detitle

            if iteminfo.get('actors'):
                if len(iteminfo.get('actors')) > 0:
                    # Just only work on the first one
                    actor = iteminfo.get('actors')[0]
                    # Copies have other roles and get skipped now
                    if actor.get('actor_role')=='Konstnär':
                        name = actor.get('actor_full_name')
                        metadata['creatorname'] = name
                        if actor.get('actor_qualifier'):
                            if actor.get('actor_qualifier')=='Tillskriven':
                                metadata['description'] = {'en' : 'painting attributed to %s' % (name, ),
                                                           'nl' : 'schilderij toegeschreven aan %s' % (name, ),
                                                           'sv' : 'målning tillskriven %s' % (name, ),
                                                           }
                            else:
                                metadata['description'] = {'sv' : 'målning %s %s' % (actor.get('actor_qualifier'), name, ),
                                                           }
                        else:
                            metadata['description'] = { 'nl' : 'schilderij van %s' % (name, ),
                                                        'en' : 'painting by %s' % (name, ),
                                                        'de' : 'Gemälde von %s' % (name, ),
                                                        'fr' : 'peinture de %s' % (name, ),
                                                        'sv' : 'målning av %s' % (name, ),
                                                        }
                            if actor.get('links'):
                                for actorlink in actor.get('links'):
                                    # The have Wikidata links!
                                    if actorlink.get('link_type')=='WikiData':
                                        metadata['creatorqid'] = actorlink.get('link').replace('http://www.wikidata.org/entity/', '')

            # Add date. FIXME: Add more cases and figure out circa
            # metadata['inceptioncirca'] = True
            if iteminfo.get('dating'):
                dating = iteminfo.get('dating')[0]
                if dating.get('date_earliest') == dating.get('date_latest'):
                    if dating.get('date_type') in ['Signerad', 'Stämplad', 'Utförd']:
                        metadata['inception'] = int(dating.get('date_earliest'))
                elif dating.get('date_earliest') and dating.get('date_latest'):
                    metadata['inceptionstart'] = int(dating.get('date_earliest'))
                    metadata['inceptionend'] = int(dating.get('date_latest'))

            if iteminfo.get('acquisition_year'):
                metadata['acquisitiondate'] = int(iteminfo.get('acquisition_year'))

            if iteminfo.get('technique_material') and iteminfo.get('technique_material').get('sv'):
                material = iteminfo.get('technique_material').get('sv').strip().lower().strip('.')
                if material == 'olja på duk':
                    metadata['medium'] = 'oil on canvas'
                elif material == 'olja på duk. Med ram':
                    metadata['medium'] = 'oil on canvas'
                elif material == 'olja på trä':
                    metadata['medium'] = 'oil on panel'
                elif material == 'olja på pannå':
                    metadata['medium'] = 'oil on panel'
                elif material == 'olja på ek':
                    metadata['medium'] = 'oil on oak panel'
                elif material == 'olja på papper':
                    metadata['medium'] = 'oil on paper'
                elif material == 'tempera på trä':
                    metadata['medium'] = 'tempera on panel'
                elif material == 'tempera på pannå':
                    metadata['medium'] = 'tempera on panel'
                elif material == 'tempera på trä (poppel)':
                    metadata['medium'] = 'tempera on poplar panel'
                elif material == 'akvarell på papper':
                    metadata['medium'] = 'watercolor on paper'
                else:
                    print('Unable to match material %s' % (material,))

            if iteminfo.get('dimensions'):
                dimensions = iteminfo.get('dimensions')[0]
                if dimensions.get('type') == 'h x b' and dimensions.get('unit') == 'cm' \
                        and dimensions.get('description') == 'Mått':
                    # FIXME: Artdatabot assumes string. That's probably not correct
                    metadata['heightcm'] = '%s' % (dimensions.get('value_1'),)
                    metadata['widthcm'] = '%s' % (dimensions.get('value_2'),)

            # Add the genre!
            genres = { 'landskap' : 'Q191163', # landscape art
                       'porträtt' : 'Q134307', # portrait
                       # 'scen' : 'Q1047337', # This is not genre art, just "scene"
                       'stadsbild' : 'Q1935974', # cityscape
                       'stilleben' : 'Q170571', # still life
                       }
            if iteminfo.get('motive_category'):
                motive_category = iteminfo.get('motive_category').lower()
                if motive_category in genres:
                    metadata['genreqid'] = genres.get(motive_category)
                #else:
                #    print('Genre %s is unknown' % (iteminfo.get('motive_category'),))

            if iteminfo.get('iiif'):
                metadata['iiifmanifesturl'] = '%s/manifest.json' % (iteminfo.get('iiif'),)
                canupload = False
                cannnotupload = False
                if iteminfo.get('iiif_license') and iteminfo.get('iiif_license').get('license') == 'Public Domain':
                    canupload = True
                # Seems to be missing for some images so let's just check how old it is.
                if metadata.get('inception') and int(metadata.get('inception')) > 1923:
                    cannnotupload = True
                elif metadata.get('inceptionend') and int(metadata.get('inceptionend')) > 1923:
                    cannnotupload = True
                # Either marked as public domain or just old
                if canupload or not cannnotupload:
                    metadata['imageurl'] = '%s/full/full/0/default.jpg' % (iteminfo.get('iiif'),)
                    metadata['imageurlformat'] = u'Q2195' #JPEG
                    #    metadata[u'imageurllicense'] = u'Q18199165' # cc-by-sa.40
                    metadata['imageoperatedby'] = u'Q842858'

            yield metadata
            continue

    for missedlocation in sorted(missedlocations, key=missedlocations.get):
        print('* %s - %s' % (missedlocation, missedlocations.get(missedlocation),))


def main(*args):
    dictGen = getNationalmuseumGenerator()
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
