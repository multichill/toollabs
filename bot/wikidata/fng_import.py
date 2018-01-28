#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to upload the paintings of the Finnish National Gallery

The JSON file is at http://kokoelmat.fng.fi/api/v2support/docs/#/download

"""
import json
import artdatabot
import pywikibot
import re
import requests

def getFNGPaintingGenerator(jsonlocation):
    '''
    Generate the paintings based on the JSON file you can find at http://kokoelmat.fng.fi/api/v2support/docs/#/download

    Yield the dict items suitable for artdatabot
    '''
    session = requests.Session()

    jsonfile = open(jsonlocation, u'r')
    #for line in jsonfile:
    #    print line
    jsondata = json.load(jsonfile)
    for paintingMetadata in jsondata.get('descriptionSet'):
        metadata = {}
        metadata['collectionqid'] = u'Q2983474'
        metadata['collectionshort'] = u'FNG'
        foundpainting = False
        for typefield in paintingMetadata.get('type'):
            if typefield.get(u'artwork-class'):
                if typefield.get(u'artwork-class')==u'maalaus':
                    foundpainting=True
        if foundpainting:
            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'
            # Grab the titles in multiple possible languages
            metadata['title'] = {}
            if paintingMetadata.get('title'):
                for titlefield in paintingMetadata.get('title'):
                    if titlefield.get(u'en'):
                        metadata[u'title']['en'] = titlefield.get(u'en')
                    elif titlefield.get(u'se'):
                        metadata[u'title']['sv'] = titlefield.get(u'se')
                    elif titlefield.get(u'fi'):
                        metadata[u'title']['fi'] = titlefield.get(u'fi')
            else:
                metadata[u'title']['en'] = u'<no title given>'

            metadata['idpid'] = u'P217'
            for identifierfield in paintingMetadata.get('identifier'):
                if identifierfield.get(u'id'):
                    metadata[u'id'] = identifierfield.get(u'id')
                elif identifierfield.get(u'uri'):
                    metadata[u'url'] = identifierfield.get(u'uri')

            if paintingMetadata.get('creator'):
                creatorraw = paintingMetadata.get('creator')[0].get('value')
                (surname, sep, givenname) = creatorraw.partition(',')
                if givenname:
                    metadata['creatorname'] = u'%s %s' % (givenname.strip(), surname.strip())
                else:
                    metadata['creatorname'] = creatorraw

                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            }
            else:
                metadata['creatorname'] = u'anonymous'
                metadata['creatorqid'] = 'Q4233718'
                metadata['description'] = { u'nl' : u'painting by anonymous painter',
                                            u'en' : u'schilderij van anonieme schilder',
                                            }

            for publisherfield in paintingMetadata.get('publisher'):
                if publisherfield.get(u'unit'):
                    if publisherfield.get(u'unit')==u'Ateneum':
                        metadata['locationqid'] = u'Q754507'
                    elif publisherfield.get(u'unit')==u'Kiasma':
                        metadata['locationqid'] = u'Q1633361'
                    elif publisherfield.get(u'unit')==u'Sinebrychoffin taidemuseo':
                        metadata['locationqid'] = u'Q1393952'
                    #Some other results might turn up. Just ignoring them
            urldatereqex = u'^http\:\/\/kansallisgalleria\.fi\/E52\.Time-Span_(\d\d\d\d)_(\d\d)_(\d\d)$'
            if paintingMetadata.get('date'):
                for datefield in paintingMetadata.get('date'):
                    if datefield.get(u'creation'):
                        metadata[u'inception'] = datefield.get(u'creation')
                    elif datefield.get(u'acquisition'):
                        urldatematch = re.match(urldatereqex, datefield.get(u'acquisition'))
                        if urldatematch:
                            metadata[u'acquisitiondate'] = u'%s-%s-%s' % (urldatematch.group(1),
                                                                          urldatematch.group(2),
                                                                          urldatematch.group(3),
                                                                          )
                        else:
                            metadata[u'acquisitiondate'] = datefield.get(u'acquisition')

            widthregex = u'^leveys (\d+,\d\d) cm'
            heightregex = u'^korkeus (\d+,\d\d) cm'

            if paintingMetadata.get('format'):
                foundcanvas = False
                foundoil = False
                for formatfield in paintingMetadata.get('format'):
                    if formatfield.get('material'):
                        if formatfield.get('material')==u'pohjamateriaali kangas':
                            foundcanvas = True
                        elif formatfield.get('material')==u'materiaali öljy':
                            foundoil = True
                    elif formatfield.get('dimension'):
                        widthmatch = re.match(widthregex, formatfield.get('dimension'))
                        heightmatch = re.match(heightregex, formatfield.get('dimension'))
                        if widthmatch:
                            metadata['widthcm'] = widthmatch.group(1).replace(u',', u'.')
                        elif heightmatch:
                            metadata['heightcm'] = heightmatch.group(1).replace(u',', u'.')
                if foundoil and foundcanvas:
                    metadata['medium'] = u'oil on canvas'

            # So we don't have to pull each page
            if metadata.get('inception') and metadata.get('inception').isnumeric() and int(metadata.get('inception')) > 1923:
                pass
            else:
                itempage = session.get(metadata[u'url'])
                if u'https://creativecommons.org/publicdomain/zero/1.0/deed.fi' in itempage.text:
                    imageurlregex = u'\<div class\=\"bigurl\"\>\?action\=image\&amp\;iid\=([^\&]+)\&amp\;profile\=CC0full'
                    imageurlMatch = re.search(imageurlregex, itempage.text)
                    imageurl = u'http://kokoelmat.fng.fi/app?action=image&iid=%s&profile=CC0full' % (imageurlMatch.group(1))
                    metadata[u'imageurl'] = imageurl
                    metadata[u'imageurlformat'] = u'Q2195' #JPEG
                    metadata[u'imageurllicense'] = u'Q6938433' # cc-zero

            yield metadata


def main(*args):
    jsonlocation = u''
    for arg in pywikibot.handle_args(args):
        jsonlocation = arg

    if not jsonlocation:
        pywikibot.output(u'Need to have the location of the fng-data-dc.json')
        return

    paintingGen = getFNGPaintingGenerator(jsonlocation)

    #for painting in paintingGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(paintingGen, create=False)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
