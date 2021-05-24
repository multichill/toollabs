#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the National Museum in Kraków to Wikidata.

Just loop over pages like https://zbiory.mnk.pl/en/search-result/advance?sortBy=default&advFilter=JTdCJTIydWlEYXRhJTIyOiU3QiUyMnBhcmFtcyUyMjolNUIlN0IlMjJuYW1lJTIyOiUyMm1vZGVsJTIyLCUyMnR5cGUlMjI6JTIydHJlZSUyMiwlMjJtb2RlJTIyOiUyMm11c3QlMjIsJTIycGhyJTIyOiUyMiUyMiwlMjJ0eHQlMjI6JTIyT2JqZWN0LnR5cGUlMjIsJTIyZXhjbHVkZU1vZGVzJTIyOiU1QiU1RCwlMjJkYXRhJTIyOiU1QiU3QiUyMmlkJTIyOjEwMDQ4OSwlMjJuYW1lJTIyOiUyMnBhaW50aW5nJTIyLCUyMmNvbW1lbnQlMjI6bnVsbCU3RCU1RCU3RCU1RCwlMjJvbmx5SW1hZ2VDaGVjayUyMjpudWxsJTdEJTdE
( https://zbiory.mnk.pl/api/query/page/2?maxPerPage=20&sort=date-desc )

This bot does uses artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
from html.parser import HTMLParser
import json

def getMNKGenerator():
    """
    Generator to return National Museum in Kraków paintings
    """
    basesearchurl = 'https://zbiory.mnk.pl/api/query/page/%s?filter[types][]=100489&page=%s&sort=date-asc&maxPerPage=20'
    postjson = '{"phrase":"","viewType":"box","must":{"objectTypes":[100489]},"should":{},"must_not":{},"onlyImage":false}'
    htmlparser = HTMLParser() # Spotted some html junk in the json (I think?)
    session = requests.Session()

    # 2333, 20 per page
    for i in range(1,118):
        searchurl = basesearchurl % (i,i,)
        print (searchurl)
        # Needs to be posted to work (otherwise a 405 method not allowed)
        searchPage = session.post(searchurl, data=postjson)

        for item in searchPage.json().get('data').get('items'):
            # Main search contains quite a bit, but we're getting the individual objects
            itemid = '%s' % (item.get('id'),)
            url = 'https://zbiory.mnk.pl/en/search-result/advance/catalog/%s' % (itemid,)
            objecturl = 'https://zbiory.mnk.pl/api/museum_object_card/%s' % (itemid,)

            # Accept-Language does the trick!
            enobjectpage = session.get(objecturl, headers = {'Accept-Language': 'en,en-US,en;q=0.5'} )
            plobjectpage = session.get(objecturl, headers = {'Accept-Language': 'pl,en-US,en;q=0.5'} )

            endata = enobjectpage.json().get('data')
            pldata = plobjectpage.json().get('data')

            metadata = {}

            pywikibot.output (url)

            metadata['url'] = url
            metadata['collectionqid'] = 'Q195311'
            metadata['collectionshort'] = 'MNK'
            metadata['locationqid'] = 'Q195311'

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
            #metadata['id'] = endata.get('extraNumPatterns')[0].get('number') # This one works for the MNW
            metadata['id'] = endata.get('noEvidence') # This one works for the MNK

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
                if creatorname=='unknown':
                    metadata['creatorqid'] = 'Q4233718'
                    metadata['description'] = { 'nl' : 'schilderij van anonieme schilder',
                                                'en' : 'painting by anonymous painter',
                                                }
                else:
                    metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                                'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                                'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                                'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                                }

            # Extract it from the name. This seems to catch most of it.
            if endata.get('createDates'):
                createdate = endata.get('createDates')[0].get('name')
                dateregex = '^(\d\d\d\d)\s*$'
                datecircaregex = '^około\.?\s*(\d\d\d\d)\s*$'
                periodregex = '^między\s*(\d\d\d\d)\s*[-\/a]\s*(\d\d\d\d)\s*$'
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

            # The have technique and material! Using material
            if endata.get('materials') and len(endata.get('materials'))==2:
                material1 = endata.get('materials')[0].get('name').lower()
                material2 = endata.get('materials')[1].get('name').lower()

                paintsurface = { ('oil paint','canvas') :  'oil on canvas',
                                 ('oil paint','panel') :  'oil on panel',
                                 ('oil paint','plank (wood)') :  'oil on panel',
                                 ('oil paint','wood') :  'oil on panel',
                                 ('oil paint','wood (plant material)') :  'oil on panel',
                                 ('oil paint','oakwood board') :  'oil on oak panel',
                                 ('oil paint','pinewood board') :  'oil on pine panel',
                                 ('oil paint','poplar board') :  'oil on poplar panel',
                                 ('oil paint','paper') :  'oil on paper',
                                 ('oil paint','copper') :  'oil on copper',
                                 ('tempera','canvas') :  'tempera on canvas', # They use distemper?????
                                 ('tempera','panel') :  'tempera on panel',
                                 ('tempera','plank (wood)') :  'tempera on panel',
                                 ('tempera','wood') :  'tempera on panel',
                                 ('tempera','wood (plant material)') :  'tempera on panel',
                                 ('tempera','oakwood board') :  'tempera on oak panel',
                                 ('tempera','pinewood wood board') :  'tempera on pine panel',
                                 ('tempera','poplar wood board') :  'tempera on poplar panel',
                                 ('tempera','paper') :  'tempera on paper',
                                 ('acrylic','canvas') :  'acrylic paint on canvas',
                                 ('acrylic','panel') :  'acrylic paint on panel',
                                 ('water colour','paper') :  'watercolor on paper',
                                 }
                if (material1, material2) in paintsurface:
                    metadata['medium'] = paintsurface.get((material1, material2))
                elif (material2, material1) in paintsurface:
                    metadata['medium'] = paintsurface.get((material2, material1))
                else:
                    print('Unable to match technique %s and material %s' % (material1, material2))

            if endata.get('tags'):
                for tag in endata.get('tags'):
                    if tag.get('id')==98712 and not metadata.get('genreqid'): # portrety
                        metadata['genreqid'] = 'Q134307' # portrait
                    elif tag.get('id')==114161: # autoportret
                        metadata['genreqid'] = 'Q192110' # self-portrait
                    #elif tag.get('id')==21172 : # sceny religijne
                    #    metadata['genreqid'] =  'Q2864737' # religious art
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

            # Only get dimensions if it's not about the frame or something else
            if endata.get('sizes') and endata.get('sizes')[0].get('id')==None and endata.get('sizes')[0].get('name')==None:
                if len(endata.get('sizes')[0].get('dimensions'))>=2:
                    heightinfo = endata.get('sizes')[0].get('dimensions')[0]
                    widthinfo = endata.get('sizes')[0].get('dimensions')[1]
                    if heightinfo.get('name')=='height' and heightinfo.get('unit')=='cm':
                        heightcm = heightinfo.get('value').replace(',', '.')
                        try:
                            float(heightcm)
                            metadata['heightcm'] = heightcm
                        except ValueError:
                            pass
                    if widthinfo.get('name')=='width' and widthinfo.get('unit')=='cm':
                        widthcm = widthinfo.get('value').replace(',', '.')
                        try:
                            float(widthcm)
                            metadata['widthcm'] = widthcm
                        except ValueError:
                            pass
                #print (endata.get('sizes')[0])


            # They maked the free images as "CC0 – Public domain"!
            if endata.get('copyrights') and endata.get('copyrights')[0].get('id')==74188:
                if endata.get('image') and endata.get('image').get('filePath') and endata.get('image').get('extension')=='jpg':
                   imageid = endata.get('image').get('id')
                   metadata['imageurl'] = 'https://zbiory.mnk.pl/api/multimedium/%s/img' % (imageid,)
                   metadata['imageurlformat'] = 'Q2195' # JPEG
                   metadata['imageoperatedby'] = 'Q195311'
                   metadata['imageurllicense'] = 'Q6938433' # CC0!
                   ## Use this to add suggestions everywhere
                   #    metadata['imageurlforce'] = True
            yield metadata

def main(*args):
    dictGen = getMNKGenerator()
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
