#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape paintings from the NGA website.
NGA provides JSON these days for search so that made it a lot easier!
"""
import artdatabot
import pywikibot
import requests
import re


def getNGAGenerator():
    '''
    Search for paintings and loop over it. Got 4165 results. Could probably use that for the paging
    '''

    baseurl = u'https://www.nga.gov/collection-search-result/jcr:content/parmain/facetcomponent/parList/collectionsearchresu.pageSize__10.pageNumber__%s.lastFacet__classification.json?classification=painting'

    for i in range(1,425):
        searchurl = baseurl % (i,)
        print (searchurl)
        searchPage = requests.get(searchurl)
        searchJson = searchPage.json()
        for record in searchJson.get('results'):
            metadata = {}
            ngaid = record.get('id')
            url = 'https://www.nga.gov/content/ngaweb/Collection/art-object-page.%s.html' % (ngaid,)
            metadata['url'] = url
            metadata['artworkidpid'] = 'P4683'
            metadata['artworkid'] = '%s' % (ngaid,) # I want this to be a string

            metadata['collectionqid'] = 'Q214867'
            metadata['collectionshort'] = 'NGA'
            metadata['locationqid'] = 'Q214867'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = 'Q3305213'

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = record['accessionnumber']
            metadata['idpid'] = 'P217'

            if record.get('title'):
                # Chop chop, several very long titles
                if len(record.get('title')) > 220:
                    title = record.get('title')[0:200]
                else:
                    title = record.get('title')
                metadata['title'] = { 'en' : title,
                                      }
            metadata['creatorname'] = record.get('attribution')

            metadata['description'] = { 'nl' : '%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        'en' : '%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }
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
    dictGen = getNGAGenerator()
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
