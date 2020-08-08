#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Royal Collection to Wikidata. Bot only works with python3 at the moment.
This is due to an SSL bug in python2.x

Great search at https://www.royalcollection.org.uk/collection/search#/ that returns json with most of the info.
Also have to retrieve the item page to retrieve some last info.

This bot uses https://api.royalcollection.org.uk/collection/search-api and artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import json
from html.parser import HTMLParser

def getRoyalCollectionGenerator():
    """
    Generator to return Royal Collection paintings
    """
    htmlparser = HTMLParser()
    apiurl = u'https://api.royalcollection.org.uk/collection/search-api'
    apiurl = 'https://www.rct.uk/collection/search-api'
    # All paintings
    postjson = u'{"searchTerm":"","hasImages":false,"orderBy":"relevancy","orderDirection":"desc","page":%s,"searchType":{"who":[],"what":{"object_category":[[{"id":"18","name":"Object category","type":"object_category"},{"id":"49367","name":"Paintings"}]]},"where":[],"when":[],"more":{}},"themeSubject":[],"themePeople":[],"themeType":"","whatsOn":[],"whatsOnDate":"","whatsOnEndDateIsPast":false,"whatsOnAccess":"","excludeNode":"","conservationProcesses":[],"conservationTypes":[],"exhibitionReference":[],"residenceReference":[],"itemsPerPage":8}'
    # All paintings with images before 1900
    # postjson = u'{"searchTerm":"","hasImages":true,"orderBy":"relevancy","orderDirection":"desc","page":%s,"searchType":{"who":[],"what":{"object_category":[[{"id":"18","name":"Object category","type":"object_category"},{"id":"49367","name":"Paintings"}]]},"where":[],"when":[{"start":"0","end":"1900","name":"0 AD - 1900 AD","type":"custom"}],"more":{}},"themeSubject":[],"themePeople":[],"themeType":"","whatsOn":[],"whatsOnDate":"","whatsOnEndDateIsPast":false,"whatsOnAccess":"","excludeNode":"","conservationProcesses":[],"conservationTypes":[],"exhibitionReference":[],"residenceReference":[],"itemsPerPage":8}'

    firstpage = requests.post(apiurl, data=postjson % (1,))

    pages = firstpage.json().get('pages')
    totalObjects = firstpage.json().get('totalObjects')
    pywikibot.output(u'Found a total of %s objects on %s pages' % (totalObjects, pages))

    # To control the loading of individual pages (which is very slow)
    slowrun = False

    for i in range(1, pages+1):
        print(u'On search page %s out of %s' % (i,pages ))
        searchpage = requests.post(apiurl, verify=False, data=postjson % (i,))
        searchjson =  searchpage.json()
        for item in searchjson.get('results'):
            metadata = {}
            url = u'https://www.royalcollection.org.uk/%s' % (item.get('url'),)
            print (url)
            #print(json.dumps(item, indent=4, sort_keys=True))

            metadata['url'] = url

            metadata['collectionqid'] = u'Q1459037'
            metadata['collectionshort'] = u'Royal Collection'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            # They seem to have added the missing RCIN prefix
            metadata['id'] = '%s' % (item.get('inventoryNumber'),)
            metadata['idpid'] = u'P217'

            title = item.get('title').strip()
            ## Chop chop, if we encounter long titles
            #if len(title) > 220:
            #    title = title[0:200]
            metadata['title'] = { u'en' : title,
                                }

            # If the creator string is like 'name (something)' than it's known, other cases it's anonymous
            creatorregex = u'^(.+) \([^\)]+\)\s*$'
            creatormatch = re.match(creatorregex, item.get('creator'))
            if creatormatch:
                name = creatormatch.group(1).strip()
                metadata['creatorname'] = htmlparser.unescape(item.get('creator')).strip().replace('\n', '') # For the image uploads
                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', name,),
                                            u'en' : u'%s by %s' % (u'painting', name,),
                                            }
            else:
                name = htmlparser.unescape(item.get('creator')).strip()
                metadata['creatorname'] = name # For the image uploads
                metadata['description'] = { u'en' : u'%s by %s' % (u'painting', name,),
                                            }
                metadata['creatorqid'] = u'Q4233718'

            # The paintings are all over the place.
            location = item.get('locationDisplay').strip()
            if location:
                if u'The Queen\'s Gallery' in location:
                    metadata['locationqid'] = u'Q1434767'
                elif u'Buckingham Palace' in location:
                    metadata['locationqid'] = u'Q42182'
                elif u'Windsor Castle' in location:
                    metadata['locationqid'] = u'Q42646'
                elif u'Hampton Court' in location:
                    metadata['locationqid'] = u'Q1443802'
                else:
                    # Just set Royal Collection as location
                    metadata['locationqid'] = u'Q1459037'

            # TODO: Add all the circa and period variants like c. 1234-5
            dateregex = u'^(Signed and dated|signed \& dated|Dated|Inscribed)\s*(\d\d\d\d)$'
            simpledateregex = u'^(\d\d\d\d)$'
            datecircaregex = u'^(c\.|circa)\s*(\d\d\d\d)$'
            periodregex = u'^(\d\d\d\d)\s*-\s*(\d\d\d\d)$'
            shortperiodregex = u'^(\d\d)(\d\d)\s*-\s*(\d\d)$'
            circaperiodregex = u'^c\.\s*(\d\d\d\d)\s*-\s*(\d\d\d\d)$'
            circashortperiodregex = u'^c\.\s*(\d\d)(\d\d)\s*-\s*(\d\d)$'
            circaveryshortperiodregex = u'^c\.\s*(\d\d\d)(\d)\s*-\s*(\d)$'

            datematch = re.search(dateregex, item.get('creationDate'), flags=re.IGNORECASE)
            simpledatematch = re.search(simpledateregex, item.get('creationDate'), flags=re.IGNORECASE)
            datecircamatch = re.search(datecircaregex, item.get('creationDate'), flags=re.IGNORECASE)
            periodmatch = re.search(periodregex, item.get('creationDate'), flags=re.IGNORECASE)
            shortperiodmatch = re.search(shortperiodregex, item.get('creationDate'), flags=re.IGNORECASE)
            circaperiodmatch = re.search(circaperiodregex, item.get('creationDate'), flags=re.IGNORECASE)
            circashortperiodmatch = re.search(circashortperiodregex, item.get('creationDate'), flags=re.IGNORECASE)
            circaveryshortperiodmatch = re.search(circaveryshortperiodregex, item.get('creationDate'), flags=re.IGNORECASE)
            #inception = re.sub(u'signed and dated\s*', u'', item.get('creationDate'), flags=re.IGNORECASE).strip()
            if datematch:
                metadata['inception'] = int(datematch.group(2))
            elif simpledatematch:
                metadata['inception'] = int(simpledatematch.group(1))
            elif datecircamatch:
                metadata['inception'] = int(datecircamatch.group(2))
                metadata['inceptioncirca'] = True
            elif periodmatch:
                metadata['inceptionstart'] = int(periodmatch.group(1),)
                metadata['inceptionend'] = int(periodmatch.group(2),)
            elif shortperiodmatch:
                metadata['inceptionstart'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(2),))
                metadata['inceptionend'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(3),))
            elif circaperiodmatch:
                metadata['inceptionstart'] = int(circaperiodmatch.group(1),)
                metadata['inceptionend'] = int(circaperiodmatch.group(2),)
                metadata['inceptioncirca'] = True
            elif circashortperiodmatch:
                metadata['inceptionstart'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(2),))
                metadata['inceptionend'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(3),))
                metadata['inceptioncirca'] = True
            elif circaveryshortperiodmatch:
                metadata['inceptionstart'] = int(u'%s%s' % (circaveryshortperiodmatch.group(1),circaveryshortperiodmatch.group(2),))
                metadata['inceptionend'] = int(u'%s%s' % (circaveryshortperiodmatch.group(1),circaveryshortperiodmatch.group(3),))
                metadata['inceptioncirca'] = True
            else:
                print (u'Could not parse date: "%s"' % (item.get('creationDate'),))

            # Disable this part for a much faster run.
            if slowrun:
                # Need to get a page and parse it to get the last info. Wait a bit to not overload the service
                time.sleep(10)
                itempage = requests.get(u'%s?ajax=true' % (url,))

                # acquisitiondate not found
                # metadata['acquisitiondate'] = acquisitiondatematch.group(1)

                # Only add the medium if it's oil on canvas
                oilcanvasregex = u'\<h4\>Medium and techniques\<\/h4\>[\s\r\t\n]*\<p\>Oil on canvas\<\/p\>'
                oilcanvasmatch = re.search(oilcanvasregex, itempage.text)
                if oilcanvasmatch:
                    metadata['medium'] = u'oil on canvas'

                measurementsregex = u'\<h4\>Measurements\<\/h4\>[\s\r\t\n]*\<p\>([^\<]+)\<\/p\>'
                measurementsmatch = re.search(measurementsregex, itempage.text)
                if measurementsmatch:
                    measurementstext = measurementsmatch.group(1)
                    regex_2d = u'(?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) cm.*'
                    regex_3d = u'(?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) x (?P<depth>\d+(\.\d+)?) cm.*'
                    match_2d = re.match(regex_2d, measurementstext)
                    match_3d = re.match(regex_3d, measurementstext)
                    if match_2d:
                        metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                        metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')
                    elif match_3d:
                        metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
                        metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
                        metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')

            # We're filtering for items with images that are from before 1900
            if item.get('primaryLargeImage') and not 'placeholder' in item.get('primaryLargeImage'):
                metadata[u'imageurl'] = u'https:%s' % (item.get('primaryLargeImage'),)
                metadata[u'imageurlformat'] = u'Q2195' #JPEG
                metadata[u'imageoperatedby'] = u'Q1459037'
                # Used this to add suggestions everywhere
                metadata[u'imageurlforce'] = True
            yield metadata


def main():
    dictGen = getRoyalCollectionGenerator()

    #for painting in dictGen:
    #    print(painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=False)
    artDataBot.run()

if __name__ == "__main__":
    main()
