#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Museum Catharijneconvent to Wikidata. Using the same aggregation as the RCE import.

https://data.collectienederland.nl/search/?qf%5B%5D=edm_dataProvider%3AMuseum+Catharijneconvent&qf%5B%5D=dc_type%3Aschildering

Have to do some rewrites of urls to have everything end up in the right location.

Using the v2 dimcon api, see
http://data.collectienederland.nl/api/search/v2/?q=&qf=edm_dataProvider%3AMuseum+Catharijneconvent&qf%5B%5D=dc_type%3Aschildering&format=json&start=1

This bot uses artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re

def getRMCCGenerator():
    """
    Generator to return Catharijneconvent paintings

    """
    basesearchurl = u'http://data.collectienederland.nl/api/search/v2/?q=&qf=edm_dataProvider%%3AMuseum+Catharijneconvent&qf%%5B%%5D=dc_type%%3Aschildering&format=json&start=%s&rows=%s'
    start = 1
    rows = 50
    hasNext = True

    while hasNext:
        searchUrl = basesearchurl % (start, rows)
        print (searchUrl)
        searchPage = requests.get(searchUrl)
        searchJson = searchPage.json()

        start = searchJson.get(u'result').get(u'pagination').get(u'nextPage')
        hasNext = searchJson.get(u'result').get(u'pagination').get(u'hasNext')

        for item in searchJson.get(u'result').get(u'items'):
            itemfields = item.get('item').get(u'fields')
            #print (itemfields)
            metadata = {}

            metadata['url'] = itemfields.get('system').get('about_uri')
            metadata[u'describedbyurl'] = itemfields.get('edm_isShownAt')[0].get('value').replace(u'https://www.catharijneconvent.nl/adlib/', u'http://adlib.catharijneconvent.nl/ais54/Details/collect/')

            collectionid = itemfields.get('delving_spec').get('value')
            if collectionid==u'catharijneconvent':
                metadata['collectionqid'] = u'Q1954426'
                metadata['collectionshort'] = u'RMCC'
                metadata['locationqid'] = u'Q1954426'
            else:
                #Another collection, skip
                print (u'Found other collection %s' % (collectionid,))
                continue

            # Do need to check the type because we include some different types
            validtypes = [u'schildering', u'drieluik', u'icoon', u'grisaille', u'memorietafel', u'wandbord',
                          u'haarschildering', u'fragment', u'schoorsteenstuk', u'retabel', u'tweeluik',
                          u'reliekschildering', u'rouwbord', u'miniatuur']
            invalidtype = u''
            if len(itemfields.get('dc_type') )>0:
                for dctype in itemfields.get('dc_type'):
                    if dctype==u'retabel':
                        invalidtype = u''
                        continue
                    elif dctype.get(u'value') not in validtypes:
                        invalidtype = dctype.get(u'value')
                        continue
            if invalidtype:
                print(u'Found invalid type %s on %s. Skipping it' % (invalidtype, metadata['url'], ))
                continue

            #    #and itemfields.get('dc_type')[0].get('value')!=u'schildering':
            #    continue
            #elif len(itemfields.get('dc_type') )==2:
            #if len(itemfields.get('dc_type') )!=1:
            #    continue

            metadata['instanceofqid'] = u'Q3305213'

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = itemfields.get('dc_identifier')[0].get('value')
            if u'?' in metadata['id']:
                # Some messed up records in there!
                print (u'mess')
                time.sleep(5)
                continue
            metadata['idpid'] = u'P217'

            print (metadata['id'])

            # Add extra collection
            if metadata['id'].startswith('ABM '):
                metadata['extracollectionqid'] = u'Q43655709' # Aartsbisschoppelijk Museum
            elif metadata['id'].startswith('BMH '):
                metadata['extracollectionqid'] = u'Q61942636' # Bisschoppelijk Museum Haarlem
            # Could add OKM -> Oud-Katholiek Museum
            # SPKK -> Stichting Protestantse Kerkelijke Kunst

            if itemfields.get('dc_title'):
                title = itemfields.get('dc_title')[0].get('value')
                if len(title) > 220:
                    title = title[0:200]
                metadata['title'] = { u'nl' : title,
                                    }

            name = u''
            if itemfields.get('dc_creator'):
                if len(itemfields.get('dc_creator'))==1:
                    name = itemfields.get('dc_creator')[0].get('value').replace(u' schilder', u'')
                    if name==u'onbekend':
                        metadata['creatorname'] = u'anonymous'
                        metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                                    u'en' : u'painting by anonymous painter',
                                                    }
                        metadata['creatorqid'] = u'Q4233718'
                    else:
                        if u',' in name:
                            (surname, sep, firstname) = name.partition(u',')
                            name = u'%s %s' % (firstname.strip(), surname.strip(),)
                        metadata['creatorname'] = name
                        metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                                    u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                                    }
                elif len(itemfields.get('dc_creator'))==4:
                    dccreatorfields = { u'ATTRIBUTEDTO' : { u'en' : u'attributed to', u'nl' : u'toegeschreven aan'},
                                        u'CIRCLEOF' : { u'en' : u'circle of', u'nl' : u'omgeving van'},
                                        u'COPYAFTER' : { u'en' : u'copy after', u'nl' : u'kopie naar'},
                                        u'WORKSHOP' : { u'en' : u'workshop', u'nl' : u'atelier'},
                                        }
                    dccreators = []
                    for dcreator in itemfields.get('dc_creator'):
                        dccreators.append(dcreator.get(u'value'))

                    dcreatortype = None
                    for dccreator in dccreators:
                        if dccreator in dccreatorfields:
                            dcreatortype = dccreator
                            continue

                    if not dcreatortype:
                        print(u'Not a valid creator type found')
                        print(dccreators)
                    else:
                        founden = False
                        foundnl = False
                        name = u''
                        for dccreator in dccreators:
                            if dccreator==dcreatortype:
                                pass
                            elif dccreator==dccreatorfields.get(dcreatortype).get(u'en'):
                                founden = True
                            elif dccreator==dccreatorfields.get(dcreatortype).get(u'nl'):
                                foundnl = True
                            else:
                                name = dccreator

                        if founden and foundnl and name:
                            if u',' in name:
                                (surname, sep, firstname) = name.partition(u',')
                                name = u'%s %s' % (firstname.strip(), surname.strip(),)
                            metadata['description'] = { u'en' : u'painting %s %s' % (dccreatorfields.get(dcreatortype).get(u'en'), name,),
                                                        u'nl' : u'schilderij %s %s' % (dccreatorfields.get(dcreatortype).get(u'nl'), name,),
                                                        }

                else:
                    print (u'Weird length of dc_creator: %s' % (len(itemfields.get('dc_creator')),))
                    print (itemfields.get('dc_creator'))

                # FIXME: Do the other cases later

                #for possiblename in itemfields.get('dc_creator'):
                #    if possiblename.get('value')!=u'onbekend':
                #        name = possiblename.get('value')


            # Not available in this collection
            #if itemfields.get('dcterms_medium'):


            if itemfields.get('dcterms_created'):
                inceptionregex = u'(\d\d\d\d) - (\d\d\d\d)'
                inceptionmatch = re.match(inceptionregex, itemfields.get('dcterms_created')[0].get('value'))

                if inceptionmatch:
                    metadata['inceptionstart'] = int(inceptionmatch.group(1))
                    metadata['inceptionend'] = int(inceptionmatch.group(2))
                else:
                    metadata['inception'] = itemfields.get('dcterms_created')[0].get('value')

            dcextenttregex = u'^\s*(breedte|hoogte|diepte)\s*([\d\.]+)\s*cm$'
            if itemfields.get('dcterms_extent') and len(itemfields.get('dcterms_extent')) > 0:
                for dcterm_extent in itemfields.get('dcterms_extent'):
                    if u'max' in dcterm_extent.get(u'value'):
                        continue
                    dcextendmatch = re.match(dcextenttregex, dcterm_extent.get(u'value'))
                    if dcextendmatch:
                        if dcextendmatch.group(1)==u'breedte':
                            metadata['widthcm'] = dcextendmatch.group(2)
                        elif dcextendmatch.group(1)==u'hoogte':
                            metadata['heightcm'] = dcextendmatch.group(2)
                        elif dcextendmatch.group(1)==u'diepte':
                            metadata['depthcm'] = dcextendmatch.group(2)

            #Skipping for now, seems a bit messy
            #
            #if itemfields.get('dc_format'):
            #    for dcformat in itemfields.get('dc_format'):
            #        dcvalue = dcformat.get(u'value')
            #        dcformatmatch = re.match(dcformatregex, dcvalue)
            #        if dcformatmatch:
            #            if dcformatmatch.group(1)==u'breedte':
            #                metadata['widthcm'] = dcformatmatch.group(2)
            #            elif dcformatmatch.group(1)==u'diepte / diameter':
            #                metadata['depthcm'] = dcformatmatch.group(2)
            #            elif dcformatmatch.group(1)==u'hoogte':
            #                metadata['heightcm'] = dcformatmatch.group(2)
            #            else:
            #                print u'Found weird type: %s' % (dcvalue,)

            ## No images
            #if itemfields.get('nave_allowSourceDownload') and itemfields.get('nave_allowSourceDownload')[0].get('value')=='true':
            #    if itemfields.get('nave_thumbLarge'):
            #        imageurl = itemfields.get('nave_thumbLarge')[0].get('value').replace(u'https://images.memorix.nl/rce/thumb/fullsize/', u'https://images.memorix.nl/rce/download/fullsize/')
            #        metadata[u'imageurl'] = imageurl
            #        metadata[u'imagesourceurl'] = itemfields.get('edm_isShownAt')[0].get('value')
            #        metadata[u'imageurlformat'] = u'Q2195' # JPEG
            #        metadata[u'imageurlforce'] = False # Already did a full forced run

            # For now only the SNK collection
            # if metadata.get('extracollectionqid') and metadata.get('extracollectionqid')==u'Q28045665':
            yield metadata


def main():
    # rijksworks = []
    dictGen = getRMCCGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
 main()
