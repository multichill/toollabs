#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Slovak National Gallery to Wikidata.

Using the v2 Europeana api, see
https://www.europeana.eu/portal/en/search?q=europeana_collectionName%3A07101%2A&qf%5B%5D=what%3APainting&view=grid

This bot uses artdatabot to upload it to Wikidata

Not sure if Europeana contains all the works so might have to redo this based on the museum website.

"""
import artdatabot
import pywikibot
import requests
import re

def getSNGGenerator():
    """
    Generator to return Slovak National Gallery paintings
    
    """
    basesearchurl = u'https://www.europeana.eu/api/v2/search.json?wskey=1hfhGH67Jhs&profile=minimal&start=%s&rows=%s&query=europeana_collectionName%%3A07101*%%20AND%%20what%%3APainting'
    start = 1
    end = 2050
    rows = 50

    for i in range (start, end, rows):
        searchUrl = basesearchurl % (i, rows)
        print (searchUrl)
        searchPage = requests.get(searchUrl)
        searchJson = searchPage.json()

        for item in searchJson.get(u'items'):
            itemurl = item.get('link')
            print (itemurl)

            itemPage = requests.get(itemurl)
            itemJson = itemPage.json()
            metadata = {}

            metadata['collectionqid'] = u'Q1744024'
            metadata['collectionshort'] = u'SNG'
            metadata['locationqid'] = u'Q1744024'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['refurl'] = itemJson.get('object').get('europeanaAggregation').get(u'edmLandingPage')
            metadata['url'] = itemJson.get('object').get('aggregations')[0].get(u'webResources')[0].get('about')

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = itemJson.get('object').get('proxies')[0].get('dcIdentifier').get(u'def')[0]
            metadata['idpid'] = u'P217'

            title = itemJson.get('object').get('proxies')[0].get(u'dcTitle').get('def')[0].strip()
            metadata['title'] = { u'sk' : title,
                                }
            if itemJson.get('object').get('proxies')[0].get(u'dcTitle').get('en'):
                metadata['title']['en'] = itemJson.get('object').get('proxies')[0].get(u'dcTitle').get('en')[0].strip()

            if itemJson.get('object').get('proxies')[0].get(u'dcCreator'):
                name = itemJson.get('object').get('proxies')[0].get(u'dcCreator').get('def')[0]
                if u',' in name:
                    (surname, sep, firstname) = name.partition(u',')
                    name = u'%s %s' % (firstname.strip(), surname.strip(),)
                metadata['creatorname'] = name

                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            }
            else:
                metadata['creatorname'] = u'anonymous'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
                metadata['creatorqid'] = u'Q4233718'

            if itemJson.get('object').get('proxies')[0].get(u'dctermsExtent'):
                dimensions = itemJson.get('object').get('proxies')[0].get(u'dctermsExtent').get('def')[0]
                regex_2d = u'^výška (?P<height>\d+(\.\d+)?)\s*cm\;šírka\s*(?P<width>\d+(\.\d+)?)\s*cm$'
                match_2d = re.match(regex_2d, dimensions)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height')
                    metadata['widthcm'] = match_2d.group(u'width')

            if itemJson.get('object').get('proxies')[0].get(u'dcDate'):
                metadata['inception'] = itemJson.get('object').get('proxies')[0].get(u'dcDate').get('def')[0]

            if itemJson.get('object').get('proxies')[0].get(u'dctermsMedium') and \
                itemJson.get('object').get('proxies')[0].get(u'dctermsMedium').get('eng') and \
                itemJson.get('object').get('proxies')[0].get(u'dctermsMedium').get('eng')[0] == u'canvas' and \
                itemJson.get('object').get('proxies')[0].get(u'dcFormat') and \
                itemJson.get('object').get('proxies')[0].get(u'dcFormat').get('eng') and \
                itemJson.get('object').get('proxies')[0].get(u'dcFormat').get('eng')[0] == u'oil':
                # FIXME : This will only catch oil on canvas
                metadata['medium'] = u'oil on canvas'

            if itemJson.get('object').get('aggregations')[0].get('edmRights') and \
                    itemJson.get('object').get('aggregations')[0].get('edmRights').get(u'def')[0]==u'http://creativecommons.org/publicdomain/mark/1.0/' and \
                    itemJson.get('object').get('aggregations')[0].get('edmIsShownBy'):

                    metadata[u'imageurl'] = itemJson.get('object').get('aggregations')[0].get('edmIsShownBy')
                    metadata[u'imageurlformat'] = u'Q2195' #JPEG
                    #metadata[u'imageurllicense'] = u'Q6938433' # no license, it's cc public domain mark
            yield metadata

    return

def main():
    dictGen = getSNGGenerator()

    #for painting in dictGen:
    #     print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
