#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from Arthub Flanders https://arthub.vlaamsekunstcollectie.be/nl/catalog
* This will loop over a bunch of collections and for each collection
Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import json
import random
import re

def geArthubFlGenerator(collectioninfo):
    """
    Generator to return Arthub Flanders paintings

    Collectioninfo should be a dict with:
    * repository - Name of the repository (like 'Museum voor Schone Kunsten Gent'), used in the search
    * collectionqid - qid of the collection to fill the dict
    * collectionshort - Abbreviation of the collection to fill the dict
    * locationqid - qid of the location (usually same as collection) to fill the dict
    * artwork_type - Name of artwork type (like 'schilderingen') , used in the search
    * instanceofqid - qid of the instance of (should match with artwork_type) to fill the dict
    """
    baseSearchUrl = u'https://arthub.vlaamsekunstcollectie.be/nl/catalog.json?f[artwork_type][]=%s&f[repository][]=%s&page=%s'

    # The artwork categories to a genre
    artwork_categories = { u'portretten' : u'Q134307', # https://arthub.vlaamsekunstcollectie.be/nl/catalog?f%5Bartwork_category%5D%5B%5D=portretten -> portrait
                           u'religieuze voorstellingen' : u'Q2864737', # https://arthub.vlaamsekunstcollectie.be/nl/catalog?f%5Bartwork_category%5D%5B%5D=religieuze+voorstellingen -> religious art
                           u'landschappen' : u'Q191163', # https://arthub.vlaamsekunstcollectie.be/nl/catalog?f%5Bartwork_category%5D%5B%5D=landschappen -> landscape art
                           u'stadsgezichten' : u'Q1935974', # https://arthub.vlaamsekunstcollectie.be/nl/catalog?f%5Bartwork_category%5D%5B%5D=stadsgezichten -> cityscape
                           u'zelfportretten' : u'Q192110', # https://arthub.vlaamsekunstcollectie.be/nl/catalog?f%5Bartwork_category%5D%5B%5D=zelfportretten -> self-portrait
               }

    # Use the returned number in the API
    nextpage = True
    i = 0
    while nextpage:
        searchurl = baseSearchUrl % (collectioninfo.get(u'artwork_type'),
                                     collectioninfo.get(u'repository'),
                                     i,)
        searchpage = requests.get(searchurl)

        # Stop condition for the loop
        if not searchpage.json().get(u'response').get(u'pages').get(u'next_page'):
            nextpage = False
        i += 1

        for item in searchpage.json().get(u'response').get(u'docs'):

            # Use the generic url for links, this will resolve to English for most of us
            url = u'https://arthub.vlaamsekunstcollectie.be/nl/catalog/%s' % (item.get('id'),)
            pywikibot.output (url)

            metadata = {}
            metadata['url'] = url

            metadata['collectionqid'] = collectioninfo['collectionqid']
            metadata['collectionshort'] = collectioninfo['collectionshort']
            metadata['locationqid'] = collectioninfo['locationqid']

            # Search is for paintings
            metadata['instanceofqid'] = collectioninfo['instanceofqid']

            title = item.get(u'title_display')

            if len(title) > 220:
                title = title[0:200]
            # Leave out the title for now until we figure out the multilingual part
            #metadata['title'] = { u'nl' : title,
            #                      }

            # Inventory number
            metadata['idpid'] = u'P217'
            metadata['id'] = item.get('object_number')

            # And own id
            if collectioninfo.get(u'artworkidpid') and collectioninfo.get(u'workprefix'):
                if item.get(u'work_pid').startswith(collectioninfo.get(u'workprefix')):
                    metadata['artworkidpid'] = collectioninfo['artworkidpid']
                    metadata['artworkid'] = item.get(u'work_pid').replace(collectioninfo.get(u'workprefix'), u'')



            name = item.get('creator_display')[0]
            if u',' in name:
                (surname, sep, firstname) = name.partition(u',')
                name = u'%s %s' % (firstname.strip(), surname.strip(),)
            metadata['creatorname'] = name

            metadata['creatorname'] = name
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        u'de' : u'%s von %s' % (u'Gemälde', metadata.get('creatorname'), ),
                                        u'fr' : u'%s de %s' % (u'peinture', metadata.get('creatorname'), ),
                                        }

            # That's not in the normal output, have to switch to extended
            #print (item.get('production_date'))
            #print (json.dumps(item, indent = 2, separators=(',', ': ')))
            if item.get('production_date'):
                datefield = item.get('production_date')[0]
                print (datefield)
                print (datefield)
                print (datefield)
                print (datefield)

                dateregex = u'^(\d\d\d\d)$'
                datecircaregex = u'^circa (\d\d\d\d)$'
                periodregex = u'^(\d\d\d\d)\s*-\s*(\d\d\d\d)$'
                circaperiodregex = u'^circa (\d\d\d\d) - circa (\d\d\d\d)'

                datematch = re.match(dateregex, datefield)
                datecircamatch = re.match(datecircaregex, datefield)
                periodmatch = re.match(periodregex, datefield)
                circaperiodmatch = re.match(circaperiodregex, datefield)

                if datematch:
                    metadata['inception'] = datematch.group(1).strip()
                elif datecircamatch:
                    metadata['inception'] = datecircamatch.group(1).strip()
                    metadata['inceptioncirca'] = True
                elif periodmatch:
                    metadata['inceptionstart'] = int(periodmatch.group(1))
                    metadata['inceptionend'] = int(periodmatch.group(2))
                elif circaperiodmatch:
                    metadata['inceptionstart'] = int(circaperiodmatch.group(1))
                    metadata['inceptionend'] = int(circaperiodmatch.group(2))
                    metadata['inceptioncirca'] = True
                else:
                    print (u'Could not parse date: "%s"' % (datefield,))
                    print (u'Could not parse date: "%s"' % (datefield,))
                    print (u'Could not parse date: "%s"' % (datefield,))
                    print (u'Could not parse date: "%s"' % (datefield,))
                    print (u'Could not parse date: "%s"' % (datefield,))

            # acquisitiondate not available
            # acquisitiondateRegex = u'\<em\>Acknowledgement\<\/em\>\:\s*.+(\d\d\d\d)[\r\n\t\s]*\<br\>'
            #acquisitiondateMatch = re.search(acquisitiondateRegex, itemPageData)
            #if acquisitiondateMatch:
            #    metadata['acquisitiondate'] = acquisitiondateMatch.group(1)

            if item.get(u'material_display') and len(item.get(u'material_display'))==2:
                if item.get(u'material_display')[0]==u'olieverf' and (item.get(u'material_display')[1]==u'doek' or item.get(u'material_display')[1]==u'doek[drager]'):
                    metadata['medium'] = u'oil on canvas'
                elif (item.get(u'material_display')[0]==u'doek' or item.get(u'material_display')[0]==u'doek[drager]') and item.get(u'material_display')[1]==u'olieverf':
                    metadata['medium'] = u'oil on canvas'

            # Add the genre
            if item.get(u'artwork_category'):
                if len (item.get(u'artwork_category'))==1:
                    artwork_category = item.get(u'artwork_category')[0].lower()
                    if artwork_category in artwork_categories:
                        metadata[u'genreqid'] = artwork_categories.get(artwork_category)
                else:
                    print (u'Found multiple categories %s' % (item.get(u'artwork_category'),))

            if item.get(u'dimensions') and len(item.get(u'dimensions'))==2:
                heightteregex = u'^h\s*(\d+(\.\d+)?)\s*cm$'
                widthteregex = u'^b\s*(\d+(\.\d+)?)\s*cm$'

                heightmatch = re.match(heightteregex, item.get(u'dimensions')[0])
                widthmatch = re.match(widthteregex, item.get(u'dimensions')[1])

                if heightmatch and widthmatch:
                    metadata['heightcm'] = heightmatch.group(1)
                    metadata['widthcm'] = widthmatch.group(1)

            ## Looks like they don't have free images yet, but do have iiif, but CORS is not allowed so disabled for now
            #metadata['iiifmanifesturl'] = u'https://arthub.vlaamsekunstcollectie.be/nl/iiif/2/%s/manifest.json' % (item.get('id'),)
            yield metadata

def processCollection(collectioninfo, dryrun=False, create=False):

    dictGen = geArthubFlGenerator(collectioninfo)

    if dryrun:
        for painting in dictGen:
            print (painting)
    else:
        artDataBot = artdatabot.ArtDataBot(dictGen, create=create)
        artDataBot.run()


def main(*args):
    collections = { u'Q2365880': { u'repository' : u'Museum voor Schone Kunsten Gent',
                                   u'collectionqid' : u'Q2365880',
                                   u'collectionshort' : u'MSK Gent',
                                   u'locationqid' : u'Q2365880',
                                   u'artwork_type' : u'schilderingen',
                                   u'instanceofqid' : u'Q3305213',
                                   u'artworkidpid' : u'P2511', # MSK Gent work PID
                                   u'workprefix' : u'http://mskgent.be/collection/work/id/',
                                   },
                    }
    collectionid = None
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-collectionid:'):
            if len(arg) == 14:
                collectionid = pywikibot.input(
                        u'Please enter the collectionid you want to work on:')
            else:
                collectionid = arg[14:]
        elif arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True

    if collectionid:
        if collectionid not in collections.keys():
            pywikibot.output(u'%s is not a valid collectionid!' % (collectionid,))
            return
        processCollection(collections[collectionid], dryrun=dryrun, create=create)
    else:
        collectionlist = collections.keys()
        random.shuffle(collectionlist) # Different order every time we run
        for collectionid in collectionlist:
            processCollection(collections[collectionid], dryrun=dryrun, create=create)

if __name__ == "__main__":
    main()
