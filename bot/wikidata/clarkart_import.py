#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Clark Art Institute to Wikidata.

Just loop over pages like https://www.clarkart.edu/artpiece/search?limit=20&offset=0&collectionIds=1095,1096,1097,1118

This bot does uses artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
from html.parser import HTMLParser
import json

def getClarkArtGenerator():
    """
    Generator to return Clark Art Institute paintings
    """
    basesearchurl = 'https://www.clarkart.edu/artpiece/search?limit=20&offset=%s&collectionIds=1095,1096,1097,1118'
    htmlparser = HTMLParser()
    session = requests.Session()

    # 545 (to start with), 20 per page
    for i in range(1, 550,20):
        searchurl = basesearchurl % (i,)
        print (searchurl)
        searchPage = session.get(searchurl)

        for item in searchPage.json().get('results'):
            # Main search contains quite a bit, but we're getting the individual objects
            #itemid = '%s' % (item.get('id'),)
            url = 'https://www.clarkart.edu%s' % (item.get('Url'),)

            itempage = session.get(url)

            metadata = {}

            pywikibot.output (url)

            metadata['url'] = url
            metadata['collectionqid'] = 'Q1465805'
            metadata['collectionshort'] = 'Clark Art'
            metadata['locationqid'] = 'Q1465805'

            # Search is for paintings
            metadata['instanceofqid'] = 'Q3305213'

            title = item.get('Title').strip()

            if len(title) > 220:
                title = title[0:200]

            metadata['title'] = { 'en' : title,
                                  }

            creatorname = item.get('Artist').strip()
            metadata['creatorname'] = creatorname
            metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                        'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                        'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                        'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                        }



            metadata['idpid'] = 'P217'
            invregex = '\<strong\>Object Number\<\/strong\>[\r\n\s\t]*\<\/td\>[\r\n\s\t]*\<td\>[\r\n\s\t]*([^\<]+)[\r\n\s\t]*\<\/td\>'
            invmatch = re.search(invregex, itempage.text)
            metadata['id'] = invmatch.group(1).strip()

            # Year contains the date in various variants
            if item.get('Year'):
                createdate = item.get('Year')
                dateregex = '^(\d\d\d\d)\s*$'
                datecircaregex = '^c\.\s*(\d\d\d\d)\s*$'
                periodregex = '^(\d\d\d\d)\s*[-–]\s*(\d\d\d\d)\s*$'
                circaperiodregex = '^c\.\s\s*(\d\d\d\d)[-\/](\d\d\d\d)\s*$'
                shortperiodregex = '^(\d\d)(\d\d)[-–](\d\d)\s*$'
                circashortperiodregex = '^c\.\s*(\d\d)(\d\d)[-–](\d\d)\s*$'

                datematch = re.search(dateregex, createdate)
                datecircamatch = re.search(datecircaregex, createdate)
                periodmatch = re.search(periodregex, createdate)
                circaperiodmatch = re.search(circaperiodregex, createdate)
                shortperiodmatch = re.search(shortperiodregex, createdate)
                circashortperiodmatch = re.search(circashortperiodregex, createdate)

                if datematch:
                    metadata['inception'] = int(datematch.group(1).strip())
                elif datecircamatch:
                    metadata['inception'] = int(datecircamatch.group(1).strip())
                    metadata['inceptioncirca'] = True
                elif periodmatch:
                    metadata['inceptionstart'] = int(periodmatch.group(1))
                    metadata['inceptionend'] = int(periodmatch.group(2))
                elif circaperiodmatch:
                    metadata['inceptionstart'] = int(circaperiodmatch.group(1))
                    metadata['inceptionend'] = int(circaperiodmatch.group(2))
                    metadata['inceptioncirca'] = True
                elif shortperiodmatch:
                    metadata['inceptionstart'] = int('%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(2),))
                    metadata['inceptionend'] = int('%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(3),))
                elif circashortperiodmatch:
                    metadata['inceptionstart'] = int('%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(2),))
                    metadata['inceptionend'] = int('%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(3),))
                    metadata['inceptioncirca'] = True
                else:
                    print ('Could not parse date: "%s"' % (createdate,))

            # acquisitiondate is available
            acquisitiondateRegex = '\<strong\>Acquisition\<\/strong\>[\r\n\s\t]*\\<\/td\>[\r\n\s\t]*\<td\>[\r\n\s\t]*[^\<]+, (\d\d\d\d)[\r\n\s\t]*\<\/td\>'
            acquisitiondateMatch = re.search(acquisitiondateRegex, itempage.text)
            if acquisitiondateMatch:
                metadata['acquisitiondate'] = int(acquisitiondateMatch.group(1))

            mediumRegex = '\<strong\>Medium\<\/strong\>[\r\n\s\t]*\\<\/td\>[\r\n\s\t]*\<td\>[\r\n\s\t]*Oil on canvas[\r\n\s\t]*\<\/td\>'
            mediumMatch = re.search(mediumRegex, itempage.text)
            if mediumMatch:
                metadata['medium'] = 'oil on canvas'

            # Dimensions is a mix of types and also Inches and cm

            # Free images! See https://www.clarkart.edu/museum/collections/image-resources
            imageRegex = '\<h6 class\=\"text-center\"\>TIFF \(up to 500 MB\)\<\/h6\>[\r\n\s\t]*\<a href\=\"#\" data-href\=\"(https\:\/\/media\.clarkart\.edu\/hires\/[^\"]+\.tif)\"'
            imageMatch = re.search(imageRegex, itempage.text)

            if imageMatch:
                metadata['imageurl'] = imageMatch.group(1).replace(' ', '%20')
                metadata['imageurlformat'] = 'Q215106' # TIFF
                metadata['imageoperatedby'] = 'Q1465805'
                #   metadata['imageurllicense'] = 'Q6938433' # Just free use
                ## Use this to add suggestions everywhere
                metadata['imageurlforce'] = True
            yield metadata

def main(*args):
    dictGen = getClarkArtGenerator()
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
