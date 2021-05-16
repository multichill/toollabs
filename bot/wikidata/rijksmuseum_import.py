#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Rijksmuseum to Wikidata. This is the third one already!
First bot used Europeana as source, second one used the Rijksmuseum API, but was an integer loop and not based on artdatabot

This bot does use artdatabot to upload it to Wikidata and just asks the API for all it's paintings.

Manual at http://rijksmuseum.github.io/

"""
import artdatabot
import pywikibot
import requests
import re
import json

def getRijksmuseumGenerator():
    """
    Generator to return Groninger Museum paintings
    
    """
    apikey=u'NJwVKOnk' # Should generate a new on and put it in my configuration file. This one is all over github

    basesearchurl = u'https://www.rijksmuseum.nl/api/nl/collection?key=%s&format=json&type=schilderij&ps=%s&p=%s'
    appendurl = u'?key=%s&format=json'
    limit = 100

    for i in range(1,49):
        searchurl = basesearchurl % (apikey, limit, i,)
        print (searchurl)
        searchPage = requests.get(searchurl)
        searchJson = searchPage.json()

        for searchrecord in searchJson.get('artObjects'):
            metadata = {}
            itemurl = searchrecord.get('links').get('self') + appendurl % (apikey,)
            url =  searchrecord.get('links').get('web').replace(u'http:', u'https:')

            metadata['url'] = url
            itempage = requests.get(itemurl)
            try:
                itemjson = itempage.json()
            except json.decoder.JSONDecodeError:
                print (u'No JSON found on %s'  %(itemurl,))
                continue

            record = itemjson.get('artObject')

            metadata['collectionqid'] = u'Q190804'
            metadata['collectionshort'] = u'Rijksmuseum'
            metadata['locationqid'] = u'Q190804'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = record[u'objectNumber']
            metadata['idpid'] = u'P217'

            if record.get('title'):
                # Chop chop, several very long titles
                if len(record.get('title')) > 220:
                    title = record.get('title')[0:200]
                else:
                    title = record.get('title')
                metadata['title'] = { u'nl' : title,
                                    }
                enurl = itemurl.replace(u'https://www.rijksmuseum.nl/api/nl/collection/', u'https://www.rijksmuseum.nl/api/en/collection/')
                print (enurl)
                if itemurl!=enurl:
                    enrecord = requests.get(enurl).json().get('artObject')
                    if enrecord.get('title'):
                        if len(enrecord.get('title')) > 220:
                            entitle = enrecord.get('title')[0:200]
                        else:
                            entitle = enrecord.get('title')
                        metadata['title'][u'en'] = entitle

            print (itemurl)
            if record.get('principalOrFirstMaker')==u'anoniem':
                metadata['creatorname'] = u'anonymous'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
                metadata['creatorqid'] = u'Q4233718'
            else:
                # Already normalized
                #name = record.get('principalOrFirstMaker')
                #if u',' in name:
                #    (surname, sep, firstname) = name.partition(u',')
                #    name = u'%s %s' % (firstname.strip(), surname.strip(),)
                metadata['creatorname'] = record.get('principalOrFirstMaker')

                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            u'de' : u'%s von %s' % (u'Gemälde', metadata.get('creatorname'),),
                                            u'fr' : u'%s de %s' % (u'peinture', metadata.get('creatorname'),),
                                            }
            # FIXME : This will only catch oil on canvas
            if record.get('physicalMedium'):
                if record.get('physicalMedium')==u'olieverf op doek':
                    metadata['medium'] = u'oil on canvas'
                elif record.get('physicalMedium')==u'olieverf op paneel':
                    metadata['medium'] = u'oil on panel'

            # Set the inception only if start only start or if start and end are the same
            if record.get('dating') and \
                record.get('dating').get('sortingDate'):
                proddate = record.get('dating').get('sortingDate')
                if record.get('dating').get('yearEarly') and record.get('dating').get('yearLate'):
                    if proddate == record.get('dating').get('yearEarly') == record.get('dating').get('yearLate'):
                        metadata['inception'] = proddate
                    else:
                        if 1000 < record.get('dating').get('yearEarly') < 2500 and \
                                                1000 < record.get('dating').get('yearLate') < 2500:
                            metadata['inceptionstart'] = record.get('dating').get('yearEarly')
                            metadata['inceptionend'] = record.get('dating').get('yearLate')
                elif record.get('dating').get('yearEarly') and proddate == record.get('dating').get('yearEarly'):
                    if record.get('dating').get('yearEarly')=='ca. %s' % (proddate,):
                        metadata['inception'] = proddate
                        metadata['inceptioncirca'] = True

            # Provenance.
            if record.get('acquisition'):
                if record.get('acquisition').get('date'):
                    # This is not going to work yet. Artdatabot only understands years
                    acquisitiondateRegex = u'^(\d\d\d\d)-01-01T00:00:00Z$'
                    acquisitiondateMatch = re.match(acquisitiondateRegex, record.get('acquisition').get('date'))
                    if acquisitiondateMatch:
                        metadata['acquisitiondate'] = acquisitiondateMatch.group(1)
                    else:
                        metadata[u'acquisitiondate'] = u'+%s' % (record.get('acquisition').get('date'),)
                if record.get('acquisition').get('creditLine'):
                    if record.get('acquisition').get('creditLine')==u'Bruikleen van de gemeente Amsterdam (legaat A. van der Hoop)':
                        metadata['extracollectionqid'] = u'Q19750488'

            # Made in. Only add it if one location is given
            if record.get('productionPlaces') and len(record.get('productionPlaces'))==1:
                productionPlace = record.get('productionPlaces')[0]

                # Based on the facets in the search output
                madein = { 'Amsterdam' : 'Q727',
                           'Antwerpen (stad)' : 'Q12892',
                           'Batavia' : 'Q1199713',
                           'Brugge' : 'Q12994',
                           'Brussel (stad)' : 'Q239',
                           'Den Haag' : 'Q36600',
                           'Dordrecht' : 'Q26421',
                           'Duitsland' : 'Q183',
                           'Florence' : 'Q2044',
                           'Frankrijk' : 'Q142',
                           'Haarlem' : 'Q9920',
                           'Istanboel' : 'Q406',
                           'Italië' : 'Q38',
                           'Jogjakarta' : 'Q7568',
                           'Lage Landen' : 'Q476033',
                           'Leiden' : 'Q43631',
                           'Londen' : 'Q84',
                           'Holland' : 'Q102911',
                           'Nederland' : 'Q55',
                           'Noordelijke Nederlanden' : 'Q27996474',
                           'Parijs' : 'Q90',
                           'Utrecht' : 'Q803',
                           'Rome' : 'Q220',
                           'Siena' : 'Q2751',
                           'Venetië' : 'Q641',
                           'Zuidelijke Nederlanden' : 'Q6581823',
                           }
                if productionPlace in madein:
                    metadata['madeinqid'] = madein.get(productionPlace)

            # Get the dimensions
            if record.get('dimensions'):
                for dimension in record.get('dimensions'):
                    if dimension.get('unit') == u'cm' and \
                       dimension.get('type') == u'hoogte' and \
                       (dimension.get('part') == u'drager' or dimension.get('part') == u'origineel') and \
                       dimension.get('value') :
                        metadata['heightcm'] = dimension.get('value').replace(u',', u'.')
                    elif dimension.get('unit') == u'cm' and \
                         dimension.get('type') == u'breedte' and \
                         (dimension.get('part') == u'drager' or dimension.get('part') == u'origineel') and \
                         dimension.get('value') :
                        metadata['widthcm'] = dimension.get('value').replace(u',', u'.')
                if not metadata.get('heightcm') and not metadata.get('widthcm') and len(record.get('dimensions'))==2:
                    height = record.get('dimensions')[0]
                    width = record.get('dimensions')[1]
                    if height.get('unit') == u'cm' and height.get('type') == u'hoogte' and height.get('part') == None:
                        metadata['heightcm'] = height.get('value').replace(u',', u'.')
                    if width.get('unit') == u'cm' and width.get('type') == u'breedte' and width.get('part') == None:
                        metadata['widthcm'] = width.get('value').replace(u',', u'.')
            if record.get(u'hasImage') and not record.get(u'copyrightHolder') and record.get(u'webImage'):
                imageurl = record.get(u'webImage').get(u'url')
                metadata[u'imageurl'] = imageurl
                metadata[u'imageurlformat'] = u'Q2195' #JPEG
                metadata['imageoperatedby'] = 'Q190804'
            yield metadata
    return
    
def main(*args):
    dictGen = getRijksmuseumGenerator()
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True

    if dryrun:
        for painting in dictGen:
            print (painting)
    else:
        artDataBot = artdatabot.ArtDataBot(dictGen, create=create)
        artDataBot.run()

if __name__ == "__main__":
    main()
