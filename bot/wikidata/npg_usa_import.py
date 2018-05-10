#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the National Portrait Gallery in Washington.

Pulling data from Github. See:

https://github.com/american-art/npg

"""

import pywikibot
import artdatabot
#import re
#import HTMLParser
import requests
import csv

def getNPGPaintingGenerator():
    """
    Generator to return NPG paintings

    Using CSV files on github. Might be slightly outdated

    """

    # ObjectID,ObjectNumber,Classification,Medium,Dated,DateBegin,DateEnd,Dimensions,CreditLine,Edition,Exhibitions
    objectsurl = u'https://raw.githubusercontent.com/american-art/npg/master/NPGObjects/NPGObjects3.csv'

    # ObjectID,ObjectNumber,URL
    linkurl = u'https://raw.githubusercontent.com/american-art/npg/master/NPGObjURLs/NPGWebObjectURLs.csv'
    linkpage = requests.get(linkurl)
    linkreader = csv.DictReader(linkpage.iter_lines())
    links = {}
    for link in linkreader:
        links[link.get(u'ObjectID')] = link

    # ObjectID,Title,DisplayOrder
    titleurl = u'https://raw.githubusercontent.com/american-art/npg/master/NPGObjTitles/NPGObjTitles3.csv'
    titlepage = requests.get(titleurl)
    titlereader = csv.DictReader(titlepage.iter_lines())
    titles = {}
    for title in titlereader:
        titles[title.get(u'ObjectID')] = title

    # ConXrefID,ObjectID,ConstituentID,RoleID,DisplayOrder,Displayed,Prefix,Suffix
    xrefurl = u'https://raw.githubusercontent.com/american-art/npg/master/NPGObjConXrefs/NPGObjConXrefs3.csv'
    xrefpage = requests.get(xrefurl)
    xrefreader = csv.DictReader(xrefpage.iter_lines())
    xrefs = {}
    for xref in xrefreader:
        # Only artists
        if int(xref.get(u'RoleID'))==1:
            xrefs[xref.get(u'ObjectID')] = xref

    ## ConstituentID,ObjectID,Maker,DisplayName,DisplayDate,DisplayOrder,Role,Prefix,Suffix,AlphaSort,Displayed,LastName,FirstName,NameTitle,allartists,objectnumber
    #makerurl = u'https://raw.githubusercontent.com/american-art/SAAM/master/WebMakers_view/WebMakers_view.csv'
    #makerpage = requests.get(makerurl)
    #makerreader = csv.DictReader(makerpage.iter_lines())
    #makers = {}
    #for maker in makerreader:
    #    makers[maker.get(u'ObjectID')] = maker

    """
    # HeightCM,HeightIN,WidthCM,WidthIN,DepthCM,DepthIN,DiamCM,DiamIN,LenCM,LenIN,Label,Element,ObjID,WeightCM,WeightIN,Method,Description,ISN,ObjectID,objectnumber
    dimensionsurl = u'https://raw.githubusercontent.com/american-art/SAAM/master/Objects/WebObjDimensions_view.csv'
    dimensionspage = requests.get(dimensionsurl)
    dimensionsreader = csv.DictReader(dimensionspage.iter_lines())
    dimensions = {}
    for dimension in dimensionsreader:
        dimensions[dimension.get(u'ObjectID')] = dimension
    """

    # ConstituentID,AlphaSort,LastName,FirstName,DisplayName,BeginDate,EndDate,DisplayDate,Code,Nationality,Suffix,NameTitle,ConstituentType
    constituentsurl = u'https://raw.githubusercontent.com/american-art/npg/master/NPGConstituents/NPGConstituents3.csv'
    constituentspage = requests.get(constituentsurl)
    constituentsreader = csv.DictReader(constituentspage.iter_lines())
    constituents = {}
    for constituent in constituentsreader:
        constituents[constituent.get(u'ConstituentID')] = constituent


    # ObjectID,Accession Number,Main Image Filename,Web Image Address,Size Notes,Image Credit/Caption,Image Rights Statement
    objectimagesurl = u'https://raw.githubusercontent.com/american-art/npg/master/NPGWebImageURLs/NPGWebImageURLs.csv'
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
        url =  links.get(object.get('ObjectID')).get(u'URL')

        print url
        metadata['url'] = url

        metadata['collectionqid'] = u'Q1967614'
        metadata['collectionshort'] = u'NPG'

        metadata['locationqid'] = u'Q1967614'

        #No need to check, I'm actually searching for paintings.
        metadata['instanceofqid'] = u'Q3305213'

        # Get the ID (inventory number)
        metadata['id'] = unicode(object.get(u'ObjectNumber'), u'utf-8')
        metadata['idpid'] = u'P217'

        # No property for NPG
        #metadata['artworkid'] = unicode(object.get('ObjectID'), u'utf-8')
        #metadata['artworkidpid'] = u'P4704'

        title = unicode(titles.get(object.get('ObjectID')).get(u'Title'), u'utf-8')

        # Chop chop, several very long titles
        if title > 220:
            title = title[0:200]

        metadata['title'] = { u'en' : title,
                            }

        if unicode(object.get('Medium'), u'utf-8').lower()==u'oil on canvas':
            metadata['medium'] = u'oil on canvas'
        # TODO: Implement circa
        if object.get('Dated')==object.get('DateBegin') and object.get('Dated')==object.get('DateEnd'):
            metadata['inception'] = unicode(object.get('Dated'), u'utf-8')
        elif object.get('DateBegin')==object.get('DateEnd'):
            metadata['inception'] = unicode(object.get('DateBegin'), u'utf-8')


        constituentid = xrefs[object.get('ObjectID')].get(u'ConstituentID')
        name = unicode(constituents[constituentid].get(u'DisplayName'), u'utf-8')

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
        """
        #FIXME: Implement later
        dimension = dimensions.get(object.get('ObjectID'))
        if dimension:
            if not dimension.get('HeightCM')=='0' and not dimension.get('WidthCM')=='0':
                metadata['heightcm'] = dimension.get('HeightCM')
                metadata['widthcm'] = dimension.get('WidthCM')
                if not dimension.get('DepthCM')=='0':
                    metadata['depthcm'] = dimension.get('DepthCM')
        """
        # acquisitiondate available is hiding in the provenance


        # See if we can find an image. Only do works with inception < 1923
        # If inception is not available, only artists that died before 1923
        # Could probably set wider, but this should all be free

        canupload = False
        if metadata.get('inception'):
            if int(metadata.get('inception')) < 1923:
                canupload = True
        elif object.get('dateend'):
            if int(object.get('DateEnd')) < 1923:
                canupload = True
        else:
            constituent = constituents.get(constituentid)
            # If they don't know the date of death, it's date of birth + 100
            if 0 < int(constituent.get(u'EndDate')) < 1923:
                canupload = True

        if canupload:
            objectimage = objectimages.get(object.get('ObjectID'))
            if objectimage:
                imageurl = objectimage.get(u'Web Image Address')
                if imageurl.endswith(u'.tiff'):
                    imageurl = imageurl.replace(u'.tiff', u'.jpg')
                elif imageurl.endswith(u'.tif'):
                    imageurl = imageurl.replace(u'.tif', u'.jpg')
                metadata[u'imageurl'] = imageurl
                metadata[u'imageurlformat'] = u'Q2195' #JPEG

        yield metadata

    return
        

def main():
    paintingGen = getNPGPaintingGenerator()

    #for painting in paintingGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(paintingGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
