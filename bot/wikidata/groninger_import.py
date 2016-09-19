#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Groninger Museum to Wikidata

Adlib API at http://collectie.groningermuseum.nl/wwwopacx/wwwopac.ashx?database=ChoiceCollect&search=object_name=schilderijen&output=json&limit=10

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests

def getGroningerGenerator():
    """
    Generator to return Groninger Museum paintings

    
    """
    limit = 100
    basesearchurl = u'http://collectie.groningermuseum.nl/wwwopacx/wwwopac.ashx?database=ChoiceCollect&search=object_name=schilderijen&output=json&limit=%s&startfrom=%s'
    baseitemurl = u'http://collectie.groningermuseum.nl/wwwopacx/wwwopac.ashx?database=ChoiceCollect&search=priref=%s&output=json'
    baseurl = u'http://collectie.groningermuseum.nl/dispatcher.aspx?action=detail&database=ChoiceCollect&priref=%s'

    for i in range(0,22):
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

            metadata['collectionqid'] = u'Q1542668'
            metadata['collectionshort'] = u'Groninger'
            metadata['locationqid'] = u'Q1542668'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = record['object_number'][0]
            metadata['idpid'] = u'P217'

            if record.get('Title'):
                metadata['title'] = { u'nl' : record.get('Title')[0].get('title')[0].get('value')[0],
                                    }
            print itemurl
            if record.get('Production') and record.get('Production')[0].get('creator')[0]:
                name = record.get('Production')[0].get('creator')[0]
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

            # Dimensions are available!
            # Material is available

            # Set the inception only if start only start or if start and end are the same
            if record.get('Production_date') and \
                record.get('Production_date')[0].get('production.date.start'):
                proddate = record.get('Production_date')[0].get('production.date.start')[0]
                if not record.get('Production_date')[0].get('production.date.end'):
                    metadata['inception'] = proddate
                elif proddate == record.get('Production_date')[0].get('production.date.end')[0]:
                    metadata['inception'] = proddate

            yield metadata

    return
    
def main():
    dictGen = getGroningerGenerator()

    # for painting in dictGen:
    #     print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
