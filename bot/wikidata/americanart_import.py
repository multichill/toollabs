#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape paintings from the Smithsonian American Art Museum website.

http://americanart.si.edu/collections/search/artwork/results/index.cfm?rows=10&q=&page=1&start=0&fq=object_type:%22Paintings%22

Was used in the first version. Now pulling data from Github. See:

https://github.com/american-art/SAAM

"""

import pywikibot
import artdatabot
#import re
#import HTMLParser
import requests
import csv

def getSAAMPaintingGenerator():
    """
    Generator to return Smithsonian American Art Museum paintings

    Using CSV files on github. Might be slightly outdated

    """

    # NPG has the same options, not working on that right now
    # ObjectID,ObjectNumber,Classification,Medium,Dated,DateBegin,DateEnd,Dimensions,CreditLine,Edition,Exhibitions
    # objectsurl = u'https://raw.githubusercontent.com/american-art/npg/master/NPGObjects/NPGObjects3.csv'
    #ObjectStatus,ObjectID,objectnumber,Classification,SubClassification,Title,Medium,dated,datebegin,dateend,Creditline,Dimensions,CreditLineRepro,ImageCreditCaption,linkedDataLink,objectDetailsWebPage
    objectsurl = u'https://raw.githubusercontent.com/american-art/SAAM/master/WebObjCaption/WebObjCaption.csv'

    # ConstituentID,ObjectID,Maker,DisplayName,DisplayDate,DisplayOrder,Role,Prefix,Suffix,AlphaSort,Displayed,LastName,FirstName,NameTitle,allartists,objectnumber
    makerurl = u'https://raw.githubusercontent.com/american-art/SAAM/master/WebMakers_view/WebMakers_view.csv'
    makerpage = requests.get(makerurl)
    makerreader = csv.DictReader(makerpage.iter_lines())
    makers = {}
    for maker in makerreader:
        makers[maker.get(u'ObjectID')] = maker

    # HeightCM,HeightIN,WidthCM,WidthIN,DepthCM,DepthIN,DiamCM,DiamIN,LenCM,LenIN,Label,Element,ObjID,WeightCM,WeightIN,Method,Description,ISN,ObjectID,objectnumber
    dimensionsurl = u'https://raw.githubusercontent.com/american-art/SAAM/master/Objects/WebObjDimensions_view.csv'
    dimensionspage = requests.get(dimensionsurl)
    dimensionsreader = csv.DictReader(dimensionspage.iter_lines())
    dimensions = {}
    for dimension in dimensionsreader:
        dimensions[dimension.get(u'ObjectID')] = dimension

    # ConstituentID,AlphaSort,LastName,FirstName,DisplayName,BeginDate,EndDate,DisplayDate,Code,Nationality,Suffix,NameTitle,ConstituentType
    constituentsurl = u'https://raw.githubusercontent.com/american-art/SAAM/master/WebConstituents_person_view/WebConstituents_person_view.csv'
    constituentspage = requests.get(constituentsurl)
    constituentsreader = csv.DictReader(constituentspage.iter_lines())
    constituents = {}
    for constituent in constituentsreader:
        constituents[constituent.get(u'ConstituentID')] = constituent

    # ObjectID,ObjectNumber,RenditionNumber,Rank,PrimaryDisplay,MediaView,MediaType,FileName,imageUrl
    objectimagesurl = u'https://raw.githubusercontent.com/american-art/SAAM/master/WebObjectImages/WebObjectImages.csv'
    objectimagespage = requests.get(objectimagesurl)
    objectimagesreader = csv.DictReader(objectimagespage.iter_lines())
    objectimages = {}
    for objectimage in objectimagesreader:
        objectimages[objectimage.get(u'ObjectID')] = objectimage

    objectspage = requests.get(objectsurl)
    objectreader = csv.DictReader(objectspage.iter_lines())

    for object in objectreader:
        if object.get('Classification') != u'Painting':
            continue

        metadata = {}
        url =  object.get('objectDetailsWebPage')

        print url
        metadata['url'] = url

        metadata['collectionqid'] = u'Q1192305'
        metadata['collectionshort'] = u'SAAM'

        metadata['locationqid'] = u'Q1192305'

        #No need to check, I'm actually searching for paintings.
        metadata['instanceofqid'] = u'Q3305213'

        # Get the ID (inventory number)
        metadata['id'] = unicode(object.get(u'objectnumber'), u'utf-8')
        metadata['idpid'] = u'P217'

        # Get the ID (used on website)
        metadata['artworkid'] = unicode(object.get('ObjectID'), u'utf-8')
        metadata['artworkidpid'] = u'P4704'

        title = unicode(object.get('Title'), u'utf-8')

        # Chop chop, several very long titles
        if len(title) > 220:
            title = title[0:200]

        metadata['title'] = { u'en' : title,
                            }

        if object.get('Medium').lower()==u'oil on canvas':
            metadata['medium'] = u'oil on canvas'
        # TODO: Implement circa
        if object.get('dated')==object.get('datebegin') and object.get('dated')==object.get('dateend'):
            metadata['inception'] = unicode(object.get('dated'), u'utf-8')

        name = unicode(makers[object.get('ObjectID')].get(u'DisplayName'), u'utf-8')

        if name==u'Unidentified':
            metadata['creatorname'] = u'anonymous'
            metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                        u'en' : u'painting by anonymous painter',
                                        }
            metadata['creatorqid'] = u'Q4233718'
        else:
            metadata['creatorname'] = name

            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }
        dimension = dimensions.get(object.get('ObjectID'))
        if dimension:
            if not dimension.get('HeightCM')=='0' and not dimension.get('WidthCM')=='0':
                metadata['heightcm'] = dimension.get('HeightCM')
                metadata['widthcm'] = dimension.get('WidthCM')
                if not dimension.get('DepthCM')=='0':
                    metadata['depthcm'] = dimension.get('DepthCM')

        # No acquisitiondate available

        # See if we can find an image. Only do works with inception < 1923
        # If inception is not available, only artists that died before 1923
        # Could probably set wider, but this should all be free

        canupload = False
        if metadata.get('inception'):
            if int(metadata.get('inception')) < 1923:
                canupload = True
        elif object.get('dateend'):
            if int(object.get('dateend')) < 1923:
                canupload = True
        else:
            constituentid = makers[object.get('ObjectID')].get(u'ConstituentID')
            constituent = constituents.get(constituentid)
            # If they don't know the date of death, it's date of birth + 100
            if int(constituent.get(u'EndDate')) < 1923:
                canupload = True

        if canupload:
            objectimage = objectimages.get(object.get('ObjectID'))
            if objectimage:
                metadata[u'imageurl'] = objectimage.get(u'imageUrl')
                metadata[u'imageurlformat'] = u'Q2195' #JPEG
        yield metadata

    return
        

def main():
    paintingGen = getSAAMPaintingGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(paintingGen, create=False)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
