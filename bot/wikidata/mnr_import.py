#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to get the MNR paintings like  https://www.pop.culture.gouv.fr/notice/mnr/MNR00852

MNR provides JSON so that shouldn't be too hard.
"""
import artdatabot
import pywikibot
import requests
import re

def get_mnr_generator():
    """
    Loop over the MNR records

    """

    base_url = 'https://www.pop.culture.gouv.fr/notice/mnr/MNR%05d'
    base_api_url = 'https://api.pop.culture.gouv.fr/mnr/MNR%05d'

    for i in range(1,1100):
        url = base_url % (i,)
        api_url = base_api_url % (i,)
        print (url)
        print (api_url)
        api_page = requests.get(api_url)
        record = api_page.json()
        if record.get('msg') and record.get('msg')=='Notice introuvable.':
            continue

        metadata = {}
        mnrid = record.get('REF')
        url = 'https://www.pop.culture.gouv.fr/notice/mnr/%s' % (mnrid,)
        metadata['url'] = url
        metadata['artworkidpid'] = 'P10039'
        metadata['artworkid'] = mnrid

        metadata['collectionqid'] = 'Q19013512'
        metadata['collectionshort'] = 'MNR'
        #metadata['locationqid'] = 'Q19013512' No location set

        # Double check for paintings
        if record.get('DOMN') and record.get('DOMN')[0] and record.get('DOMN')[0]=='Peinture':
            metadata['instanceofqid'] = 'Q3305213'
        else:
            print('This is not a painting')
            continue

        # Get the ID (inventory number). This needs to burn if it's not available
        metadata['id'] = record['INV']
        metadata['idpid'] = 'P217'

        if record.get('TITR'):
            # Chop chop, several very long titles
            if len(record.get('TITR')) > 220:
                title = record.get('TITR')[0:200]
            else:
                title = record.get('TITR')
            metadata['title'] = { 'fr' : title,
                                  }

        # Damn you people. Why do you mess up the name like this?
        if record.get('AUTR') and record.get('AUTR')[0]:
            name = record.get('AUTR')[0]
            name_attribution_regex = '^([A-Z\s]+) (.+) \(([^\)]+)\)$'
            name_regex = '^([A-Z\s]+) (.+)$'

            name_attribution_match = re.match(name_attribution_regex, name)
            name_match = re.match(name_regex, name)
            if name_attribution_match:
                name = '%s %s %s' % (name_attribution_match.group(3), name_attribution_match.group(2), name_attribution_match.group(1).capitalize())
                metadata['creatorname'] = name
                metadata['description'] = { 'fr' : '%s %s' % ('peinture', metadata.get('creatorname'), ),
                                            }
            elif name_match:
                name = '%s %s' % (name_match.group(2), name_match.group(1).capitalize())
                metadata['creatorname'] = name
                metadata['description'] = { 'nl' : '%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            'en' : '%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                            }
            else:
                metadata['creatorname'] = name
                metadata['description'] = { 'en' : '%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                            }

        # Get some of the extra inventory numbers
        if record.get('NUMS'):
            inv2_regex = '(\d+)\s*:\s*numéro du musée de Linz'
            inv3_regex = '(\d+(\/\d+)?)\s*\:\s*numéro du Central Collecting Point de Munich'

            inv2_match = re.search(inv2_regex, record.get('NUMS'))
            inv3_match = re.search(inv3_regex, record.get('NUMS'))

            if inv2_match:
                metadata['extraid2'] = inv2_match.group(1)
                metadata['extracollectionqid2'] = 'Q475667' # Linzer Sammlung (Führermuseum)

            if inv3_match:
                metadata['extraid3'] = inv3_match.group(1)
                metadata['extracollectionqid3'] = 'Q1053735' # Munich Central Collecting Point

        yield metadata
        continue
        if False:
            metadata['creatorname'] = record.get('attribution')


            # Artdatabot should be able to handle these
            if record.get('medium'):
                metadata['medium'] = record.get('medium')

            # Artdatabot will take care of this
            if record.get('displaydate'):
                dateregex = u'^(\d\d\d\d)$'
                datecircaregex = u'^c\.\s*(\d\d\d\d)$'
                periodregex = u'^(\d\d\d\d)[-\/](\d\d\d\d)$'
                circaperiodregex = u'^c\.\s*(\d\d\d\d)[-\/](\d\d\d\d)$'

                datematch = re.match(dateregex, record.get('displaydate'))
                datecircamatch = re.match(datecircaregex, record.get('displaydate'))
                periodmatch = re.match(periodregex, record.get('displaydate'))
                circaperiodmatch = re.match(circaperiodregex, record.get('displaydate'))

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
                    print (u'Could not parse date: "%s"' % (record.get('displaydate'),))

            # Data not available
            # record.get('acquisition')

            if record.get('creditline'):
                if record.get('creditline')==u'Samuel H. Kress Collection':
                    metadata['extracollectionqid'] = u'Q2074027'
                elif record.get('creditline')==u'Andrew W. Mellon Collection':
                    metadata['extracollectionqid'] = u'Q46596638'
                elif record.get('creditline').startswith(u'Corcoran Collection'):
                    metadata['extracollectionqid'] = u'Q768446'

            # Get the dimensions
            if record.get('dimensions1'):
                regex_2d = u'overall\: (?P<height>\d+(\.\d+)?) (x|×) (?P<width>\d+(\.\d+)?) cm \([^\)]+\)$'
                regex_3d = u'overall\: (?P<height>\d+(\.\d+)?) (x|×) (?P<width>\d+(\.\d+)?) cm (x|×) (?P<depth>\d+(\.\d+)?) cm \([^\)]+\)$'
                match_2d = re.match(regex_2d, record.get('dimensions1'))
                match_3d = re.match(regex_3d, record.get('dimensions1'))
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height')
                    metadata['widthcm'] = match_2d.group(u'width')
                elif match_3d:
                    metadata['heightcm'] = match_3d.group(u'height')
                    metadata['widthcm'] = match_3d.group(u'width')
                    metadata['depthcm'] = match_3d.group(u'depth')

            if record.get('iiifManifestURL'):
                metadata['iiifmanifesturl'] = record.get('iiifManifestURL')

            # Already have most of the images. Could take imagepath and replace the !130,130 with full
            # It seems to be quite hard to figure out if it's PD-art or not
            # https://images.nga.gov/en/page/openaccess.html
            # Just get some of the missing ones uploaded
            if record.get('imagepath'):
                if (metadata.get(u'inception') and metadata.get(u'inception') < 1900) or \
                        (metadata.get(u'inceptionend') and metadata.get(u'inceptionend') < 1900):
                    metadata[u'imageurl'] = record.get('imagepath').replace(u'/!130,130/', u'/full/')
                    metadata[u'imageurlformat'] = u'Q2195' #JPEG
                    # Could use this later to force
                    metadata[u'imageurlforce'] = False

            yield metadata


def main(*args):
    dictGen = get_mnr_generator()
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
        art_data_bot = artdatabot.ArtDataBot(dictGen, create=create)
        art_data_bot.run()

if __name__ == "__main__":
    main()
