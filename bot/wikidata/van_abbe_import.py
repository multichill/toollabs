#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Van Abbe Museum to Wikidata.

Using the v2 dimcon api, see
http://www.dimcon.nl/api/search/v2/?q=&qf=edm_dataProvider%3AVan+Abbemuseum&qf=dc_type%3Aacrylic+on+canvas&qf=dc_type%3Aoil%20on%20canvas&format=json&start=1

This bot uses artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re

def getVanAbbeGenerator():
    """
    Generator to return Groninger Museum paintings

    
    """
    basesearchurl = u'http://www.dimcon.nl/api/search/v2/?q=&qf=edm_dataProvider%%3AVan+Abbemuseum&qf=dc_type%%3Aacrylic+on+canvas&qf=dc_type%%3Aoil%%20on%%20canvas&format=json&start=%s&rows=%s'
    start = 1
    rows = 50
    hasNext = True


    while hasNext:
        searchUrl = basesearchurl % (start, rows)
        searchPage = requests.get(searchUrl)
        searchJson = searchPage.json()

        start = searchJson.get(u'result').get(u'pagination').get(u'nextPage')
        hasNext = searchJson.get(u'result').get(u'pagination').get(u'hasNext')

        for item in searchJson.get(u'result').get(u'items'):
            itemfields = item.get('item').get(u'fields')
            #print itemfields
            metadata = {}

            if itemfields.get('legacy').get('delving_collection')==u'Van Abbemuseum':
                metadata['collectionqid'] = u'Q1782422'
                metadata['collectionshort'] = u'Van Abbe'
                metadata['locationqid'] = u'Q1782422'
            else:
                #Another collection, skip
                continue

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = itemfields.get('dc_identifier')[0].get('value')
            metadata['idpid'] = u'P217'

            if itemfields.get('dc_title'):
                title = itemfields.get('dc_title')[0].get('value')
                metadata['title'] = { u'nl' : title,
                                    }

            metadata['refurl'] = itemfields.get('foaf_primaryTopic')[0].get('value')

            museumpage = requests.get(itemfields.get('edm_isShownAt')[0].get('value'))
            metadata['url'] = museumpage.url.replace(u'[', u'%5B').replace(u']', u'%5D')

            metadata['creatorname'] = itemfields.get('dc_creator')[0].get('value')

            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                      }

            for dc_type in itemfields.get('dc_type'):
                if dc_type.get('value') == u'olieverf op doek' or dc_type.get('value') == u'oil on canvas':
                    # FIXME : This will only catch oil on canvas
                    metadata['medium'] = u'oil on canvas'
                elif dc_type.get('value').endswith(u' cm'):
                    regex_2d = u'(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) cm'
                    regex_3d = u'(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) x (?P<depth>\d+(,\d+)?) cm'
                    match_2d = re.match(regex_2d, dc_type.get('value'))
                    match_3d = re.match(regex_3d, dc_type.get('value'))
                    if match_2d:
                        metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                        metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')
                    elif match_3d:
                        metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
                        metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
                        metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')

            metadata['inception'] = itemfields.get('dc_date')[0].get('value')

            yield metadata

    return
    
def main():
    dictGen = getVanAbbeGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
