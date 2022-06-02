#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to get paintings from the Minneapolis Institute of Art  website.
ARTSMIA provides JSON search API these days for search so that made it a lot easier!

https://search.artsmia.org/*?size=300&filters=classification%3A%22paintings%22
"""
import artdatabot
import pywikibot
import requests
import re

def get_artsmia_generator():
    """
    Use the search API to get all the paintings
    :return:
    """
    # Simple lookup table for madeinqid (location of creation) and to split the queries
    locations = { 'Australia' : 'Q408',
                  'Austria' : 'Q40',
                  'Belgium' : 'Q31',
                  'Canada' : 'Q16',
                  'China' : 'Q29520',
                  'Denmark' : 'Q35',
                  'England' : 'Q21',
                  'Finland' : 'Q33',
                  'France' : 'Q142',
                  'Germany' : 'Q183',
                  'India' : 'Q668',
                  'Iran' : 'Q794',
                  'Italy' : 'Q38',
                  'Japan' : 'Q17',
                  'Korea' : 'Q18097',
                  'Nepal' : 'Q837',
                  'Netherlands' : 'Q55',
                  'Norway' : 'Q20',
                  'Portugal' : 'Q45',
                  'Russia' : 'Q159',
                  'Spain' : 'Q29',
                  'Sweden' : 'Q34',
                  'Switzerland' : 'Q39',
                  'Tibet' : 'Q17252',
                  'United States' : 'Q30',
                  }
    missed_locations = {}

    base_search_url = 'https://search.artsmia.org/*?size=%s&from=%s&filters=classification%%3A%%22paintings%%22'

    search_page = requests.get(base_search_url % (1,1))
    search_json = search_page.json()
    total = search_json.get('hits').get('total')
    interval = 100

    for i in range(0, total + interval, interval):
        search_url = base_search_url % (interval, i)
        print (search_url)
        search_page = requests.get(search_url)
        search_json = search_page.json()
        for big_record in search_json.get('hits').get('hits'):
            record = big_record.get('_source')

            metadata = {}
            artsmia_id = record.get('id')
            url = 'https://collections.artsmia.org/art/%s/' % (artsmia_id,)
            metadata['url'] = url
            metadata['artworkidpid'] = 'P4712'
            metadata['artworkid'] = '%s' % (artsmia_id, )

            metadata['collectionqid'] = 'Q1700481'
            metadata['collectionshort'] = 'Artsmia'
            metadata['locationqid'] = 'Q1700481'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = 'Q3305213'

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = record['accession_number']
            metadata['idpid'] = 'P217'

            if record.get('title'):
                # Chop chop, several very long titles
                if len(record.get('title')) > 220:
                    title = record.get('title')[0:200]
                else:
                    title = record.get('title')
                metadata['title'] = { 'en' : title,
                                      }

            # Some without an artist
            if record.get('artist'):
                name = record.get('artist')
                if name.startswith('Artist: '):
                    name = name.replace('Artist: ', '', 1)

                metadata['creatorname'] = name

                metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                            'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                            'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'),),
                                            'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                            }
            else:
                if record.get('country'):
                    metadata['creatorname'] = 'unknown artist, %s' % (record.get('country'),)
                else:
                    metadata['creatorname'] = 'unknown artist'
                metadata['description'] = { 'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),}
                metadata['creatorqid'] = 'Q4233718'

            # Artdatabot should be able to handle these
            if record.get('medium'):
                metadata['medium'] = record.get('medium')

            # Artdatabot will take care of this
            if record.get('dated'):
                date = record.get('dated')
                date_regex = '^(\d\d\d\d)$'
                date_circa_regex = '^c\.\s*(\d\d\d\d)$'
                period_regex = '^(\d\d\d\d)[--\/](\d\d\d\d)$'
                circa_period_regex = '^c\.\s*(\d\d\d\d)[--\/](\d\d\d\d)$'
                short_period_regex = '^(\d\d)(\d\d)[--\/](\d\d)$'
                circa_short_period_regex = '^c\.\s*(\d\d)(\d\d)[--\/](\d\d)$'

                date_match = re.match(date_regex, date)
                date_circa_match = re.match(date_circa_regex, date)
                period_match = re.match(period_regex, date)
                circa_period_match = re.match(circa_period_regex, date)
                short_period_match = re.match(short_period_regex, date)
                circa_short_period_match = re.match(circa_short_period_regex, date)

                if date_match:
                    # Don't worry about cleaning up here.
                    metadata['inception'] = int(date_match.group(1))
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
                    print ('Could not parse date: "%s"' % (date,))
                    print ('Could not parse date: "%s"' % (date,))
                    print ('Could not parse date: "%s"' % (date,))
                    print ('Could not parse date: "%s"' % (date,))

            if record.get('country'):
                if record.get('country') in locations:
                    metadata['madeinqid'] = locations.get(record.get('country'))
                else:
                    if record.get('country') not in missed_locations:
                        missed_locations[record.get('country')]=0
                    missed_locations[record.get('country')]+=1

            # Data not available
            # record.get('acquisition')

            ## The dimensions are very unstructured. Could have a shot at it later
            #if record.get('dimensions1'):
            #    regex_2d = u'overall\: (?P<height>\d+(\.\d+)?) (x|×) (?P<width>\d+(\.\d+)?) cm \([^\)]+\)$'
            #    regex_3d = u'overall\: (?P<height>\d+(\.\d+)?) (x|×) (?P<width>\d+(\.\d+)?) cm (x|×) (?P<depth>\d+(\.\d+)?) cm \([^\)]+\)$'
            #    match_2d = re.match(regex_2d, record.get('dimensions1'))
            #    match_3d = re.match(regex_3d, record.get('dimensions1'))
            #    if match_2d:
            #        metadata['heightcm'] = match_2d.group(u'height')
            #        metadata['widthcm'] = match_2d.group(u'width')
            #    elif match_3d:
            #        metadata['heightcm'] = match_3d.group(u'height')
            #        metadata['widthcm'] = match_3d.group(u'width')
            #        metadata['depthcm'] = match_3d.group(u'depth')

            # They seem to have something iiif at https://iiif.dx.artsmia.org/3352.jpg/info.json , but it times out
            #if record.get('iiifManifestURL'):
            #    metadata['iiifmanifesturl'] = record.get('iiifManifestURL')

            # Already have most of the images. Could take imagepath and replace the !130,130 with full
            # It seems to be quite hard to figure out if it's PD-art or not
            # https://images.nga.gov/en/page/openaccess.html
            # Just get some of the missing ones uploaded
            if not record.get('image_copyright') and record.get('image')=='valid':
                if not record.get('restricted') and record.get('public_access'):
                    if record.get('rights_type') == 'Public Domain' or record.get('rights_type') == 'No Copyright–United States':
                        if record.get('rights_type') == 'Public Domain':
                            metadata['imageurl'] = 'https://1.api.artsmia.org/full/%s.jpg' % (artsmia_id,)
                        elif record.get('rights_type') == 'No Copyright–United States':
                            metadata['imageurl'] = 'https://1.api.artsmia.org/800/%s.jpg' % (artsmia_id,)
                        metadata['imageurlformat'] = 'Q27996264' #JPEG
                        metadata['imageurllicense'] = 'Q20007257' # https://new.artsmia.org/copyright-and-image-access/
                        metadata['imageoperatedby'] = 'Q1700481'
                        # Could use this later to force
                        metadata['imageurlforce'] = False

            yield metadata
    for missed_location in sorted(missed_locations, key=missed_locations.get):
        print('* %s - %s' % (missed_location, missed_locations.get(missed_location),))

def main(*args):
    dictGen = get_artsmia_generator()
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
