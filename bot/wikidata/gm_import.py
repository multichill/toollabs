#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Gemeentemuseum Den Haag (GM)

Second version now based on their api:

* https://www.gemeentemuseum.nl/nl/api/v1/search?origin=gm&facets[]=object:Schilderij&page=0&_format=json

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re

def getGMGenerator():
    """
    Generator to return Gemeentemuseum.

    Don't use the fulltext fields! Stuff gets messed up in there.
    
    """
    basesearchurl=u'https://www.gemeentemuseum.nl/nl/api/v1/search?origin=gm&facets[]=object:Schilderij&page=%s&_format=json'

    hasNext = True
    page = 0

    while hasNext:
        searchUrl = basesearchurl % (page,)
        print (searchUrl)
        searchPage = requests.get(searchUrl)
        searchJson = searchPage.json()

        page += 1
        hasNext = searchJson.get(u'search_results').get(u'more_results')

        for item in searchJson.get(u'search_results').get(u'rows'):
            metadata = {}
            metadata['collectionqid'] = u'Q1499958'
            metadata['collectionshort'] = u'GM'
            metadata['locationqid'] = u'Q1499958'
            metadata['instanceofqid'] = u'Q3305213'

            metadata['id'] = item.get(u'field_adlib_object_number')
            metadata['idpid'] = u'P217'

            url = u'https://www.gemeentemuseum.nl%s' % (item.get(u'url'),)
            metadata[u'url'] = url
            if item.get(u'field_adlib_title'):
                metadata[u'title'] = { u'nl' : item.get(u'field_adlib_title').strip(),
                                       }
            name = item.get(u'creator')
            if u',' in name:
                (surname, sep, firstname) = name.partition(u',')
                name = u'%s %s' % (firstname.strip(), surname.strip(),)
            metadata['creatorname'] = name

            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }

            if item.get(u'field_adlib_production_date'):
                circaperiodregex = u'^circa\s*(\d\d\d\d)-(\d\d\d\d)$'
                periodregex = u'^(\d\d\d\d)-(\d\d\d\d).*$'
                circaregex = u'^circa\s*(\d\d\d\d)$'

                circaperiodmatch = re.match(circaperiodregex, item.get(u'field_adlib_production_date'))
                periodmatch = re.match(periodregex, item.get(u'field_adlib_production_date'))
                circamatch = re.match(circaregex, item.get(u'field_adlib_production_date'))

                if circaperiodmatch:
                    metadata['inceptionstart'] = int(circaperiodmatch.group(1),)
                    metadata['inceptionend'] = int(circaperiodmatch.group(2),)
                    metadata['inceptioncirca'] = True
                elif periodmatch:
                    metadata['inceptionstart'] = int(periodmatch.group(1),)
                    metadata['inceptionend'] = int(periodmatch.group(2),)
                elif circamatch:
                    metadata['inception'] = circamatch.group(1)
                    metadata['inceptioncirca'] = True
                else:
                    metadata['inception'] = item.get(u'field_adlib_production_date')

            if item.get('field_adlib_material')==u'olieverf op doek':
                metadata['medium'] = u'oil on canvas'

            if item.get('field_adlib_dimensions'):
                measurementstext = item.get('field_adlib_dimensions')
                regex_2d = u'hoogte\s*(?P<height>\d+(,\d+)?)\s*cm\s*\n\s*breedte\s*(?P<width>\d+(,\d+)?)\s*cm'
                match_2d = re.match(regex_2d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height').replace(',', '.')
                    metadata['widthcm'] = match_2d.group(u'width').replace(',', '.')

            yield metadata

def main():
    dictGen = getGMGenerator()

    #for painting in dictGen:
    #    print(painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
