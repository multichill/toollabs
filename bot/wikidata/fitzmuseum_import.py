#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from The Fitzwilliam Museum, University of Cambridge to Wikidata.

Using their api, see http://data.fitzmuseum.cam.ac.uk/api/docs/

This bot uses artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re
try:
    from html.parser import HTMLParser
except ImportError:
    import HTMLParser

def getFWGenerator():
    """
    Generator to return Fitzwilliam Museum paintings
    
    """
    htmlparser = HTMLParser()
    basesearchurl = u'http://data.fitzmuseum.cam.ac.uk/api/?query=Category:painting&size=%s&from=%s&fields=all'
    size = 100
    for i in range(0, 1800, size):
        searchUrl = basesearchurl % (size, i)
        print (searchUrl)
        searchPage = requests.get(searchUrl)
        searchJson = searchPage.json()

        for item in searchJson.get(u'results'):
            priref = item.get('priref')
            url = u'http://data.fitzmuseum.cam.ac.uk/id/object/%s' % (priref,)
            print (url)

            #itemPage = requests.get(itemurl)
            #itemJson = itemPage.json()
            metadata = {}

            metadata['collectionqid'] = u'Q1421440'
            metadata['collectionshort'] = u'Fitzwilliam'
            metadata['locationqid'] = u'Q1421440'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['url'] = url

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = item.get('ObjectNumber')
            metadata['idpid'] = u'P217'

            if item.get('Title'):
                title = htmlparser.unescape(item.get('Title'))
            else:
                title = u'(without title)'
            metadata['title'] = { u'en' : title,
                                }

            name =  htmlparser.unescape(item.get('Maker'))
            if u',' in name:
                (surname, sep, firstname) = name.partition(u',')
                name = u'%s %s' % (firstname.strip(), surname.strip(),)
            metadata['creatorname'] = name

            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }
            #else:
            ##    metadata['creatorname'] = u'anonymous'
            #    metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
            #                                u'en' : u'painting by anonymous painter',
            #                                }
            #    metadata['creatorqid'] = u'Q4233718'

            if item.get('DateEarly') and item.get('DateLate') and item.get('DateEarly')==item.get('DateLate'):
                metadata['inception'] = item.get('DateEarly')

            if item.get('TechniqueDescription')==u'oil on canvas':
                metadata['medium'] = u'oil on canvas'

            # They have dimension information, but not in the api
            # I could ask them or just scrape it.
            #if itemJson.get('object').get('proxies')[0].get(u'dctermsExtent'):
            #    dimensions = itemJson.get('object').get('proxies')[0].get(u'dctermsExtent').get('def')[0]
            #    regex_2d = u'^výška (?P<height>\d+(\.\d+)?)\s*cm\;šírka\s*(?P<width>\d+(\.\d+)?)\s*cm$'
            #    match_2d = re.match(regex_2d, dimensions)
            #    if match_2d:
            #        metadata['heightcm'] = match_2d.group(u'height')
            #        metadata['widthcm'] = match_2d.group(u'width')


            # Plenty of PD images, but they claim copyright.
            #
            #        metadata[u'imageurl'] = itemJson.get('object').get('aggregations')[0].get('edmIsShownBy')
            #        metadata[u'imageurlformat'] = u'Q2195' #JPEG
            #        #metadata[u'imageurllicense'] = u'Q6938433' # no license, it's cc public domain mark
            yield metadata

    return

def main():
    dictGen = getFWGenerator()

    #for painting in dictGen:
    #     print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
