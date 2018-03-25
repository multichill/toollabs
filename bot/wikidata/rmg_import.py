#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from Royal Museums Greenwich to Wikidata.
National Maritime Museum is part of the Royal Museums Greenwich and seems to contain all the paintings

Using their api, see http://collections.rmg.co.uk/page/76fd680cdfa46b8848f3a719e15a6772.html

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

def getRMGGenerator():
    """
    Generator to return Royal Museums Greenwich paintings
    
    """
    htmlparser = HTMLParser()
    # Drop the object later or NOT
    #basesearchurl = u'http://collections.rmg.co.uk/solr?q=collectionReference:subject-90248%%20AND%%20type:(object)&start=%s&rows=%s&wt=json'
    basesearchurl = u'http://collections.rmg.co.uk/solr?q=collectionReference:subject-90248&start=%s&rows=%s&wt=json'
    size = 100
    for i in range(0, 4100, size):
        searchUrl = basesearchurl % (i, size)
        print (searchUrl)
        searchPage = requests.get(searchUrl)
        searchJson = searchPage.json()

        for item in searchJson.get(u'response').get('docs'):
            if item.get('uri'):
                url = item.get('uri')
            else:
                url = item.get('dataUri')
            print (url)

            #itemPage = requests.get(itemurl)
            #itemJson = itemPage.json()
            metadata = {}

            metadata['collectionqid'] = u'Q7374509'
            metadata['collectionshort'] = u'RMG'
            metadata['locationqid'] = u'Q1199924'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['url'] = url

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = item.get('primaryId')
            metadata['idpid'] = u'P217'

            if item.get('primaryTitle'):
                title = htmlparser.unescape(item.get('primaryTitle'))
            else:
                title = u'(without title)'
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                }

            #if item.get('makerRelation')[0] == u'Artist':
            if item.get('maker'):
                name = item.get('maker')[0]
            elif item.get('makerString'):
                name = item.get('makerString')[0]
            metadata['creatorname'] = name

            # TODO: Something with anonymous

            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }
            #else:
            ##    metadata['creatorname'] = u'anonymous'
            #    metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
            #                                u'en' : u'painting by anonymous painter',
            #                                }
            #    metadata['creatorqid'] = u'Q4233718'

            if item.get(u'displayDate'):
                metadata['inception'] = item.get('displayDate')

            if item.get('primaryMaterial')==u'oil on canvas':
                metadata['medium'] = u'oil on canvas'

            if item.get(u'measurements'):
                dimensions = item.get(u'measurements')[0]
            # They have dimension information, but not in the api
            # I could ask them or just scrape it.
            #if itemJson.get('object').get('proxies')[0].get(u'dctermsExtent'):
            #    dimensions = itemJson.get('object').get('proxies')[0].get(u'dctermsExtent').get('def')[0]
                regex_2d = u'^Painting\: (?P<height>\d+) (mm )?x (?P<width>\d+) mm(\;.*)?$'
                match_2d = re.match(regex_2d, dimensions)
                if match_2d:
                    metadata['heightcm'] = str(float(match_2d.group(u'height'))/10)
                    metadata['widthcm'] = str(float(match_2d.group(u'width'))/10)


            # Plenty of PD images, but they claim copyright.
            #
            #        metadata[u'imageurl'] = itemJson.get('object').get('aggregations')[0].get('edmIsShownBy')
            #        metadata[u'imageurlformat'] = u'Q2195' #JPEG
            #        #metadata[u'imageurllicense'] = u'Q6938433' # no license, it's cc public domain mark
            yield metadata

    return

def main():
    dictGen = getRMGGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
