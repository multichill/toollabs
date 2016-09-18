#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Noordbrabants Museum (nbm) to Wikidata

Adlib API at http://nbm-asp.adlibhosting.com/wwwopacx/wwwopac.ashx?database=collect&search=object_name=schilderij&output=json&limit=100

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests

def getNBMGenerator():
    """
    Generator to return Noordbrabants Museum paintings

    
    """
    limit = 100
    basesearchurl = u'http://nbm-asp.adlibhosting.com/wwwopacx/wwwopac.ashx?database=collect&search=object_name=schilderij&output=json&limit=%s&startfrom=%s'
    baseitemurl = u'http://nbm-asp.adlibhosting.com/wwwopacx/wwwopac.ashx?database=collect&search=priref=%s&output=json'
    baseurl = u'http://collectie.hetnoordbrabantsmuseum.nl/Details/collect/%s'

    for i in range(0,11):
        searchurl = basesearchurl % (limit, limit * i,)
        searchPage = requests.get(searchurl)
        searchJson = searchPage.json()

        for searchrecord in searchJson.get('adlibJSON').get('recordList').get('record'):
            metadata = {}
            priref = searchrecord.get('@attributes').get('priref')
            itemurl = baseitemurl % (priref,)
            url =  baseurl % (priref,)

            metadata['url'] = url

            itempage = requests.get(itemurl)
            itemjson = itempage.json()
            record = itemjson.get('adlibJSON').get('recordList').get('record')[0]

            metadata['collectionqid'] = u'Q12013217'
            metadata['collectionshort'] = u'NBM'
            metadata['locationqid'] = u'Q12013217'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = record['object_number'][0]
            metadata['idpid'] = u'P217'

            if record.get('Title'):
                metadata['title'] = { u'nl' : record.get('Title')[0].get('title')[0].get('value')[0],
                                    }
            # Dimensions are available!
            # Material is available

            if record.get('Production') and record.get('Production')[0].get('creator')[0]:
                name = record.get('Production')[0].get('creator')[0].get('value')[0]
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
            yield metadata

    return
    
def main():
    dictGen = getNBMGenerator()

    # for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
