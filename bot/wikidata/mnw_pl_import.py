#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the National Museum in Warsaw to Wikidata.

Just loop over pages like https://cyfrowe.mnw.art.pl/en/catalog?filter=JTdCJTIydHlwZXMlMjI6JTdCJTIybmFtZSUyMjolMjJ0eXBlcyUyMiwlMjJ2YWx1ZSUyMjolNUIlN0IlMjJpZCUyMjoxMjgwNywlMjJ0ZXh0JTIyOiUyMm9icmF6JTIyLCUyMnRpdGxlJTIyOiUyMm9icmF6JTIyJTdEJTVELCUyMmRlc2MlMjI6bnVsbCwlMjJhY3RpdmUlMjI6dHJ1ZSU3RCU3RA%3D%3D
( https://cyfrowe-api.mnw.art.pl/api/search/Object/page/293?filter[types][]=12807&page=293&sort=promoted&maxPerPage=36 )

This bot does uses artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
from html.parser import HTMLParser

def getMNWGenerator():
    """
    Generator to return National Museum in Warsaw paintings
    """
    basesearchurl = 'https://cyfrowe-api.mnw.art.pl/api/search/Object/page/%s?filter[types][]=12807&page=%s&sort=date-asc&maxPerPage=36'
    htmlparser = HTMLParser() # Spotted some html junk in the json (I think?)
    session = requests.Session()

    # 10831, 36 per page
    for i in range(1,302):
        searchurl = basesearchurl % (i,i,)
        print (searchurl)
        searchPage = session.get(searchurl)

        for item in searchPage.json().get('data').get('items'):
            # Main search contains quite a bit, but we're getting the individual objects
            itemid = '%s' % (item.get('id'),)
            url = 'https://cyfrowe.mnw.art.pl/en/catalog/%s' % (itemid,)
            objecturl = 'https://cyfrowe-api.mnw.art.pl/api/object/%s' % (itemid,)

            # Accept-Language does the trick!
            enobjectpage = session.get(objecturl, headers = {'Accept-Language': 'en,en-US,en;q=0.5'} )
            plobjectpage = session.get(objecturl, headers = {'Accept-Language': 'pl,en-US,en;q=0.5'} )

            endata = enobjectpage.json().get('data')
            pldata = plobjectpage.json().get('data')

            metadata = {}

            pywikibot.output (url)

            metadata['url'] = url
            metadata['collectionqid'] = 'Q153306'
            metadata['collectionshort'] = 'MNW'
            metadata['locationqid'] = 'Q153306'

            # Search is for paintings
            metadata['instanceofqid'] = 'Q3305213'

            entitle = htmlparser.unescape(endata.get('title')).strip()
            pltitle = htmlparser.unescape(pldata.get('title')).strip()

            if len(entitle) > 220:
                entitle = entitle[0:200]
            if len(pltitle) > 220:
                pltitle = pltitle[0:200]

            metadata['title'] = { 'en' : entitle,
                                  'pl' : pltitle,
                                  }

            # They seem to provide two inventory numbers? That's going to be fun.....
            metadata['idpid'] = 'P217'
            metadata['id'] = endata.get('extraNumPatterns')[0].get('number')
            #metadata['extraid'] = endata.get('noEvidence') # NO, that does not work!!!!
            #metadata['extracollectionqid'] = 'Q153306'

            if endata.get('authors'):
                creatorregex1 = '^([^,]+),\s*([^,].+),\s*([^\(]+)\([^\)]*\d\d[^\)]*\d\d[^\)]*\)$'
                creatorregex2 = '^([^,]+),\s*([^\(]+)\([^\)]*\d\d[^\)]*\d\d[^\)]*\)$'

                creatorname = endata.get('authors')[0].get('name')
                creatormatch1 = re.match(creatorregex1, creatorname)
                creatormatch2 = re.match(creatorregex2, creatorname)

                if creatormatch1:
                    creatorname = '%s %s %s' % (creatormatch1.group(2).strip(),
                                                creatormatch1.group(1).strip(),
                                                creatormatch1.group(3).strip())
                elif creatormatch2:
                    creatorname = '%s %s' % (creatormatch2.group(2).strip(), creatormatch2.group(1).strip(),)


                metadata['creatorname'] = creatorname.strip()
                metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                            'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                            'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                            'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                            }

            # Extract it from the name. This seems to catch most of it.
            if endata.get('createDates'):
                createdate = endata.get('createDates')[0].get('name')
                dateregex = '^(\d\d\d\d)\s*$'
                datecircaregex = '^ok\.?\s*(\d\d\d\d)\s*$'
                periodregex = '^(\d\d\d\d)[-\/](\d\d\d\d)\s*$'
                circaperiodregex = '^ok\.?\s*(\d\d\d\d)[-\/](\d\d\d\d)\s*$'
                shortperiodregex = '^(\d\d)(\d\d)[-\/](\d\d)\s*$'
                circashortperiodregex = '^ok\.?\s*(\d\d)(\d\d)[-\/](\d\d)\s*$'

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

            # acquisitiondate not available
            # acquisitiondateRegex = u'\<em\>Acknowledgement\<\/em\>\:\s*.+(\d\d\d\d)[\r\n\t\s]*\<br\>'
            #acquisitiondateMatch = re.search(acquisitiondateRegex, itemPageData)
            #if acquisitiondateMatch:
            #    metadata['acquisitiondate'] = acquisitiondateMatch.group(1)

            # The have technique and material!
            if endata.get('techniques') and endata.get('materials'):
                # 9696 = oil and 11159 = canvas
                if endata.get('techniques')[0].get('id')==9696 and endata.get('materials')[0].get('id')==11159:
                    metadata['medium'] = 'oil on canvas'

            if endata.get('tags'):
                for tag in endata.get('tags'):
                    if tag.get('id')==21751 and not metadata.get('genreqid'): # portrety
                        metadata['genreqid'] = 'Q134307' # portrait
                    elif tag.get('id')==21288: # autoportrety
                        metadata['genreqid'] = 'Q192110' # self-portrait
                    elif tag.get('id')==21172 : # sceny religijne
                        metadata['genreqid'] =  'Q2864737' # religious art
                # This is where my Polish ends....

            #elif record.get('genre')=='Landschaft':
            #    metadata['genreqid'] = 'Q191163' # landscape art
            #elif record.get('genre')=='Stillleben':
            #    metadata['genreqid'] = 'Q170571' # still life
            #elif record.get('genre')=='Allegorie':
            #    metadata['genreqid'] = 'Q2839016' # allegory
            #elif record.get('genre')=='Genre':
            #    metadata['genreqid'] = 'Q1047337' # genre art
            #elif record.get('genre')=='Seestück':
            #    metadata['genreqid'] = 'Q158607' # marine art

            if endata.get('dimensionText'):
                # Dimensions are in the text
                regex_2d = '^Wym\.\s*(?P<height>\d+(,\d+)?)\s*[x×x]\s*(?P<width>\d+(,\d+)?)\s*'
                match_2d = re.match(regex_2d, endata.get('dimensionText'))
                if match_2d:
                    metadata['heightcm'] = match_2d.group('height').replace(',', '.')
                    metadata['widthcm'] = match_2d.group('width').replace(',', '.')

            # Everything is marked as public domain, but also as restricted?
            if endata.get('copyrights') and endata.get('copyrights')[0].get('id')==29351:
                if endata.get('image') and endata.get('image').get('filePath') and endata.get('image').get('extension')=='jpg':
                    recentinception = False
                    if metadata.get('inception') and metadata.get('inception') > 1925:
                        recentinception = True
                    if metadata.get('inceptionend') and metadata.get('inceptionend') > 1925:
                        recentinception = True
                    if not recentinception:
                        filepath = endata.get('image').get('filePath')
                        metadata['imageurl'] = 'https://cyfrowe-cdn.mnw.art.pl/upload/multimedia/%s.jpg' % (filepath,)
                        metadata['imageurlformat'] = 'Q2195' # JPEG
                        metadata['imageoperatedby'] = 'Q153306'
                    #   metadata['imageurllicense'] = 'Q6938433' # No license, just public domain
                    ## Use this to add suggestions everywhere
                    #    metadata['imageurlforce'] = True
            yield metadata

def main(*args):
    dictGen = getMNWGenerator()
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
