#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Amsterdam Museum to Wikidata

This is the second attempt. First (successful) attempt was based on data in Europeana

Adlib API at http://amdata.adlibsoft.com/wwwopac.ashx?database=AMcollect&search=object_name=schilderij&output=json&limit=100

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests

def getAmsterdamGenerator():
    """
    Generator to return Amsterdam Museum paintings
    * search=object_name=schilderij returns 2958 hits
    * search=object_category=schilderijencollectie 2878 hits

    """
    limit = 100
    basesearchurl = u'http://amdata.adlibsoft.com/wwwopac.ashx?database=AMcollect&search=object_name=schilderij&output=json&limit=%s&startfrom=%s'
    baseitemurl = u'http://amdata.adlibsoft.com/wwwopac.ashx?database=AMcollect&search=priref=%s&output=json'
    baseurl = u'http://am.adlibhosting.com/amonline/details/collect/%s'

    for i in range(0,30):
        searchurl = basesearchurl % (limit, limit * i,)
        print (searchurl)
        searchPage = requests.get(searchurl)
        searchJson = searchPage.json()

        for searchrecord in searchJson.get('adlibJSON').get('recordList').get('record'):
            metadata = {}
            priref = searchrecord.get('@attributes').get('priref')
            itemurl = baseitemurl % (priref,)
            url =  baseurl % (priref,)

            metadata['url'] = url

            print (itemurl)
            itempage = requests.get(itemurl)
            itemjson = itempage.json()
            record = itemjson.get('adlibJSON').get('recordList').get('record')[0]

            metadata['collectionqid'] = u'Q1820897'
            metadata['collectionshort'] = u'AM'
            metadata['locationqid'] = u'Q1820897'

            # FIXME: Add the extra collection van der Hoop and fix artdatabot
            if record.get('collection') and record.get('collection')[0]==u'Hoop, collectie Adriaan van der':
                metadata['extracollectionqid'] = u'Q19750488'

            #acquisitiondate
            if record.get('acquisition.date'):
                metadata['acquisitiondate'] = record.get('acquisition.date')[0]

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = record['object_number'][0]
            metadata['idpid'] = u'P217'

            if record.get('title'):
                metadata['title'] = { u'nl' : record.get('title')[0].strip(),
                                      }

            if record.get('maker'):
                if record.get('maker')[0].get('creator')[0]:
                    name = record.get('maker')[0].get('creator')[0]
                    if u',' in name:
                        (surname, sep, firstname) = name.partition(u',')
                        name = u'%s %s' % (firstname.strip(), surname.strip(),)
                    metadata['creatorname'] = name

                    if name==u'onbekend':
                        metadata['creatorname'] = u'anonymous'
                        metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                                    u'en' : u'painting by anonymous painter',
                                                    }
                        metadata['creatorqid'] = u'Q4233718'
                    else:
                        metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                                    u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                                    u'de' : u'%s von %s' % (u'Gemälde', metadata.get('creatorname'), ),
                                                    u'fr' : u'%s de %s' % (u'peinture', metadata.get('creatorname'), ),
                                                    }
            else:
                metadata['creatorname'] = u'anonymous'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
                metadata['creatorqid'] = u'Q4233718'

            # Dimensions are available!
            if record.get('dimension'):
                for dimension in record.get('dimension'):
                    # We want cm and don't want to have frames and other things
                    if dimension.get('dimension.unit') and dimension.get('dimension.unit')[0]=='cm' and dimension.get('dimension.type') and not dimension.get('dimension.part'):
                        if dimension.get('dimension.type')[0]==u'hoogte':
                            metadata['heightcm'] = dimension.get('dimension.value')[0].replace(u',', u'.')
                        elif dimension.get('dimension.type')[0]==u'breedte':
                            metadata['widthcm'] = dimension.get('dimension.value')[0].replace(u',', u'.')

            # Material is available
            if record.get('material'):
                oil = False
                canvas = False
                for material in record.get('material'):
                    if material.get(u'term'):
                        term = material.get(u'term')[0]
                        if term==u'olieverf':
                            oil = True
                        elif term==u'doek':
                            canvas = True
                if oil and canvas:
                    metadata['medium'] = u'oil on canvas'

            # Set the inception only if start only start or if start and end are the same
            if record.get('production.date.start'):
                if not record.get('production.date.end'):
                    metadata['inception'] = int(record.get('production.date.start')[0])
                elif record.get('production.date.start')[0] == record.get('production.date.end')[0]:
                    metadata['inception'] = int(record.get('production.date.start')[0])
                elif record.get('production.date.start')[0] != record.get('production.date.end')[0]:
                    metadata['inceptionstart'] = int(record.get('production.date.start')[0])
                    metadata['inceptionend'] = int(record.get('production.date.end')[0])

            # They provide the different genres in the api
            genres = { u'bijbelse voorstelling' : u'Q2864737',
                       u'dierstuk' : u'Q16875712',
                       u'genre' : u'Q1047337',
                       u'geschiedenis (iconografie)' : u'Q742333',
                       u'kerkinterieur' : u'Q21074330',
                       u'landschap' : u'Q191163',
                       u'mythologie' : u'',
                       u'portret' : u'Q134307',
                       u'stadsgezicht' : u'Q1935974',
                       u'stilleven' : u'Q170571',
                       u'zeegezicht' : u'Q158607',
                       }

            if record.get('content.motif.general'):
                for motif in record.get('content.motif.general'):
                    term = motif.get('term')[0]
                    if term in genres:
                        metadata[u'genreqid'] = genres.get(term)
                        break

            # Get the image!
            if record.get('copyright') and record.get('copyright')[0]==u'Public Domain':
                print (u'public domain')
                if record.get('reproduction') and type(record.get('reproduction')[0])==dict:
                    repro = record.get('reproduction')[0].get(u'reproduction.identifier_URL')[0].lower()
                    print (repro)
                    if repro.startswith(u'..\\..\\dat\\collectie\\images\\'):
                        filename = repro.replace(u'..\\..\\dat\\collectie\\images\\', u'')
                        imageurl = u'https://am-web.adlibhosting.com/wwwopacx_images/wwwopac.ashx?command=getcontent&server=images&value=%s' % (filename)
                        metadata[u'imageurl'] = imageurl
                        metadata[u'imageurlformat'] = u'Q2195' #JPEG
                        metadata[u'imageoperatedby'] = u'Q1820897'
            yield metadata

    return

def main():
    dictGen = getAmsterdamGenerator()

    #for painting in dictGen:
    #     print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()