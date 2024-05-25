#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Metropolitan Museum of Art (Q160236) to Wikidata.

Clone https://github.com/tategallery/collection/tree/master/artworks . This bot works on those files.

usage:

 python pwb.py /path/to/code/toollabs/bot/wikidata/tate_import.py /path/to/tate/artworks/

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import json

def getMETGenerator():
    """
    Use the API at https://metmuseum.github.io/ to get works
    :return: Yields dictionaries with the metadata per work suitable for ArtDataBot
    """
    idurl = u'https://collectionapi.metmuseum.org/public/collection/v1/objects'
    idurl = u'https://collectionapi.metmuseum.org/public/collection/v1/search?q=Painting'
    idpage = requests.get(idurl)

    pywikibot.output(u'The MET query returned %s works' % (idpage.json().get('total')))

    session = requests.Session()

    foundit= True
    lookingfor = 671052

    metids = sorted(idpage.json().get('objectIDs'), reverse=True)

    for metid in metids:
        if metid == lookingfor:
            foundit = True

        metadata = {}

        if not foundit:
            continue
        meturl = u'https://collectionapi.metmuseum.org/public/collection/v1/objects/%s' % (metid,)
        print (meturl)
        metpage = session.get(meturl)
        # Only work on paintings
        try:
            metjson = metpage.json()
        except ValueError:
            print (metpage.text)
            continue

        foundPainting = False

        if metjson.get(u'objectName') and metjson.get(u'objectName')==u'Painting':
            foundPainting = True

        if metjson.get(u'classification') and metjson.get(u'classification')==u'Paintings':
            foundPainting = True

        if not foundPainting:
            print(metjson.get(u'objectName'))
            continue
        metadata['instanceofqid'] = u'Q3305213'

        print(json.dumps(metjson, indent=4, sort_keys=True))

        metadata['url'] = metjson.get('objectURL')

        metadata['collectionqid'] = u'Q160236'
        metadata['collectionshort'] = u'MET'
        metadata['locationqid'] = u'Q160236'

        metadata['idpid'] = u'P217'
        metadata['id'] = metjson.get(u'accessionNumber')

        metadata['artworkidpid'] = u'P3634'
        metadata['artworkid'] = u'%s' % (metid,)

        # Empty titles exist:
        if metjson.get('title'):
            title = metjson.get('title').replace(u'\n', u'')
            # Chop chop, in case we have very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                  }

        if metjson.get('artistDisplayName'):
            metadata['creatorname'] = metjson.get('artistDisplayName')

        if not metjson.get('artistDisplayName')  or metjson.get('artistDisplayName')==u'Unidentified Artist':
            metadata['creatorqid'] = u'Q4233718'
            metadata['creatorname'] = u'anonymous'
            metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                        u'en' : u'painting by anonymous painter',
                                        u'es' : u'cuadro de autor desconocido'
                                        }
        elif metadata.get(u'creatorname'):
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        u'de' : u'%s von %s' % (u'Gemälde', metadata.get('creatorname'),),
                                        u'es' : u'%s de %s' % (u'cuadro', metadata.get('creatorname'),),
                                        }

        if metjson.get('artistWikidata_URL'):
            metadata['creatorqid'] = metjson.get('artistWikidata_URL').replace('https://www.wikidata.org/wiki/', '')

        datecircaregex = u'^ca\.\s*(\d\d\d\d)$'
        datecircamatch = re.match(datecircaregex, metjson.get('objectDate'))

        if metjson.get('objectDate')==str(metjson.get(u'objectBeginDate')) \
                    and metjson.get('objectDate')==str(metjson.get(u'objectEndDate')):
            metadata['inception']=int(metjson.get('objectDate'))
        elif datecircamatch:
            metadata['inception'] = int(datecircamatch.group(1))
            metadata['inceptioncirca'] = True
        elif metjson.get(u'objectBeginDate') and metjson.get(u'objectEndDate') and \
            metjson.get(u'objectBeginDate') > 1000 and metjson.get(u'objectEndDate') > metjson.get(u'objectBeginDate'):
            metadata['inceptionstart'] = int(metjson.get(u'objectBeginDate'))
            metadata['inceptionend'] = int(metjson.get(u'objectEndDate'))

        # If the credit line ends with a year, we'll take it
        acquisitiondateregex = u'^.+, (\d\d\d\d)$'
        acquisitiondatematch = re.match(acquisitiondateregex, metjson.get(u'creditLine'))
        if acquisitiondatematch:
            metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

        if metjson.get('medium'):
            metadata['medium'] = metjson.get('medium').lower()

        dimensiontext = metjson.get('dimensions')
        regex_2d = u'^.+in\. \((?P<height>\d+(\.\d+)?) x (?P<width>\d+(.\d+)?) cm\)$'
        regex_3d = u'^.+in\. \((?P<height>\d+(\.\d+)?) x (?P<width>\d+(.\d+)?) x (?P<depth>\d+(,\d+)?) cm\)$'
        match_2d = re.match(regex_2d, dimensiontext)
        match_3d = re.match(regex_3d, dimensiontext)
        if match_2d:
            metadata['heightcm'] = match_2d.group(u'height')
            metadata['widthcm'] = match_2d.group(u'width')
        elif match_3d:
            metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
            metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
            metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')

        # portrait (Q134307)
        # religious art (Q2864737)
        # landscape art (Q191163)
        # still life (Q170571)
        # self-portrait (Q192110)

        genres = { u'Saints' : u'Q2864737', # religious art (Q2864737)
                   u'Christ' : u'Q2864737',
                   u'Jesus' : u'Q2864737',
                   u'Angels' : u'Q2864737',
                   u'Portraits' : u'Q134307', # portrait (Q134307)
                   u'Landscapes' : u'Q191163', # landscape art (Q191163)
                   u'Self-portraits' : u'Q192110', # self-portrait (Q192110)
                   u'Still Life' : u'Q170571', # still life (Q170571)
                   }

        # Can loop over tags to add genre
        foundgenre = u''
        genrecollision = u''

        # System changed, disabled for now
        # See for example https://collectionapi.metmuseum.org/public/collection/v1/objects/901617
        #if metjson.get('tags'):
        #    for tag in metjson.get('tags'):
        #        if tag in genres:
        #            if not foundgenre:
        #                foundgenre = genres.get(tag)
        #            elif foundgenre:
        #                if genres.get(tag)!=foundgenre:
        #                    genrecollision = genres.get(tag)
        #                    continue

        if foundgenre and not genrecollision:
            metadata['genreqid'] = foundgenre

        madelocations = {u'China' : u'Q29520',
                         u'India' : u'Q668',
                         u'Iran' : u'Q794',
                         u'Japan' : u'Q17',
                         u'Nepal' : u'Q837',
                         }

        if metjson.get('country') and metjson.get('country') in madelocations:
            metadata['madeinqid'] = madelocations.get(metjson.get('country'))
        elif metjson.get('culture'):
            for madelocation in madelocations:
                if metjson.get('culture').startswith(madelocation):
                    metadata['madeinqid'] = madelocations.get(madelocation)
                    break

        # No IIIF
        # Most images are uploaded already
        if metjson.get('isPublicDomain') and metjson.get('primaryImage'):
            metadata[u'imageurl'] = metjson.get('primaryImage').replace(u' ', u'%20') # Damn spaces
            metadata[u'imageurlformat'] = u'Q2195' #JPEG
            metadata[u'imageurllicense'] = u'Q6938433' # CC0
            metadata[u'imageoperatedby'] = u'Q160236'

        yield metadata


def main(*args):
    dictGen = getMETGenerator()
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