#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Dordrechts Museum to Wikidata.

Using the v2 dimcon api, see
http://www.dimcon.nl/api/search/v2/?q=&qf=edm_dataProvider%3ADordrechts+Museum&qf=dc_type%3Aschilderij&rows=50&format=json&start=1

This bot uses artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re

def getDordrechtsGenerator():
    """
    Generator to return Groninger Museum paintings

    
    """
    basesearchurl = u'http://www.dimcon.nl/api/search/v2/?q=&qf=edm_dataProvider%%3ADordrechts+Museum&qf=dc_type%%3Aschilderij&format=json&start=%s&rows=%s'
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

            if itemfields.get('legacy').get('delving_collection')==u'Dordrechts Museum':
                metadata['collectionqid'] = u'Q2874177'
                metadata['collectionshort'] = u'Dordrechts Museum'
                metadata['locationqid'] = u'Q2874177'
            else:
                #Another collection, skip
                continue

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = itemfields.get('dc_identifier')[0].get('value')
            if u'?' in metadata['id']:
                # Some messed up records in there!
                continue
            metadata['idpid'] = u'P217'

            if itemfields.get('dc_title'):
                title = itemfields.get('dc_title')[0].get('value')
                metadata['title'] = { u'nl' : title,
                                    }

            metadata['refurl'] = itemfields.get('foaf_primaryTopic')[0].get('value')

            # Is this enough or do we need to use requests to see if all urls point somewhere?
            metadata['url'] = metadata['refurl'].replace(u'http://data.collectienederland.nl/resource/aggregation/dordrechts-museum/', u'https://www.dordrechtsmuseum.nl/objecten/id/')

            if itemfields.get('dc_creator'):
                name = itemfields.get('dc_creator')[0].get('value')
            else:
                metadata['creatorname'] = u'onbekend'

            if u',' in name:
                (surname, sep, firstname) = name.partition(u',')
                name = u'%s %s' % (firstname.strip(), surname.strip(),)
            metadata['creatorname'] = name

            # Don't think we'll find onbekend, but doesn't hurt
            if metadata['creatorname'] == u'onbekend':
                metadata['creatorname'] = u'anonymous'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
                metadata['creatorqid'] = u'Q4233718'
            else:
                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                          }

            if itemfields.get('nave_material') and \
                itemfields.get('nave_material')[0].get('value') == u'olieverf' and \
                itemfields.get('nave_material')[1].get('value') == u'doek':
                metadata['medium'] = u'oil on canvas'

            if itemfields.get('dc_date'):
                metadata['inception'] = itemfields.get('dc_date')[0].get('value')

            yield metadata

    return
    
def main():
    dictGen = getDordrechtsGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
