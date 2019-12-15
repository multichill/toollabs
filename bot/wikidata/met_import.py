#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the  Metropolitan Museum of Art (Q160236) to Wikidata.

Clone https://github.com/tategallery/collection/tree/master/artworks . This bot works on those files.

usage:

 python pwb.py /path/to/code/toollabs/bot/wikidata/tate_import.py /path/to/tate/artworks/

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import json
import pywikibot.data.sparql
#import HTMLParser
#import os
#import csv
#import codecs
##from xml.sax.saxutils import escape


def metWorksOnWikidata():
    '''
    Just return all the RKD images as a dict
    :return: Dict
    '''
    result = {}
    sq = pywikibot.data.sparql.SparqlQuery()
    query = u'SELECT ?item ?id WHERE { ?item wdt:P3634 ?id  } LIMIT 10000009'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = qid
    print (len(result))
    return result

def currentCommonsFiles():
    '''
    Get the list of current Commons filenames with spaces, not underscores:
    u'Diptyc MET ep1975.1.22.r.bw.R.jpg'
    '''
    result = []
    site = pywikibot.Site(u'commons', u'commons')
    pagetitle = u'Template:TheMet'
    templatepage = pywikibot.Page(site, title=pagetitle)
    references =templatepage.getReferences(onlyTemplateInclusion=True, namespaces=[6,])
    for page in references:
        result.append(page.title(withNamespace=False,))
    return result

def getImageUrls(metid, title):

    meturl = u'http://www.metmuseum.org/api/Collection/additionalImages?crdId=%s' % (metid,)

    searchPage = requests.get(meturl, verify=False)
    searchJson = searchPage.json()

    print (searchJson)

    regex =u'^http\:\/\/images\.metmuseum\.org\/CRDImages\/[^\/]+\/original\/(.+).jpe?g\s*$'

    result = []
    notallowedchars = [u':', u'[', u']', u'#', u'|']

    if searchJson.get(u'results'):
        for fileinfo in searchJson.get(u'results'):
            if fileinfo.get(u'isOasc'):
                fileurl = fileinfo.get(u'originalImageUrl')
                print (fileurl)
                match = re.match(regex,fileurl, re.I)
                if match:
                    title = title.strip().replace(u'  ', u' ')
                    for toreplace in notallowedchars:
                        title = title.replace(toreplace, u'-')
                    metfilename = match.group(1).strip().replace(u'_', u' ')
                    if title:
                        filename = u'%s MET %s' % (title, metfilename)
                    else:
                        filename = u'MET %s' % (metfilename,)

                    result.append((fileurl, filename))

    return result

def getMETGenerator2(csvlocation):
    """
    Generator to return Museum of New Zealand Te Papa Tongarewa paintings
    """
    pubcount = 0
    paintingcount = 0
    pubpaintingcount = 0
    i = 0
    #htmlparser = HTMLParser.HTMLParser()

    classifications = {}

    mappings = {u'' : u'Q29382606',
                u'Ceramics-Pottery': u'Q17379525',
                u'Photographs': u'Q125191',
                u'Glass': u'Q11469',
                u'Metalwork-Sculpture': u'Q860861',
                u'Furniture': u'Q14745',
                u'Wood-Sculpture': u'Q860861',
                u'|': u'Q29382606',
                u'Paintings': u'Q3305213',
                u'Stone-Sculpture': u'Q860861',
                u'Gold and Silver': u'Q29382731',
                u'Vases': u'Q191851',
                u'Bronzes': u'Q928357',
                u'Textiles-Tapestries': u'Q184296',
                u'Woodwork-Furniture': u'Q14745',
                u'Textiles-Rugs': u'Q163446',
                u'Swords': u'Q12791',
                u'Manuscripts and Illuminations': u'Q48498',
                u'Sculpture-Bronze': u'Q928357',
                u'Stone Sculpture': u'Q860861',
                u'Chordophone-Lute-plucked-fretted': u'Q180733',
                u'Glass-Stained': u'Q1473346',
                u'Metalwork-Silver': u'Q29382731',
                u'Sculpture-Stone': u'Q860861',
                u'Sculpture': u'Q860861',
                u'Prints': u'Q11060274',
                u'Ivories': u'Q351853',
                u'Drawings': u'Q93184',
                u'Codices': u'Q213924',
                u'Helmets': u'Q173603',
                u'Textiles-Woven': u'Q5295538',
                u'Ceramics-Sculpture': u'Q860861',
                }

    '''


    xmlreadFile = '/home/mdammers/metmuseum/MetObjects_ContentHighlightSets-wFILENAMES.xml'

    xmlReadData = codecs.open(xmlreadFile, "r", "utf-8")

    idimageurlregex = u'\<Object_ID\>(?P<id>\d+)\<\/Object_ID\>((?!row).)*\<Image_Url\>(?P<url>http\:\/\/images[^\<]+)\</Image_Url\>\s*\n\s*<Filename\>(?P<filename>[^\<]+)\</Filename\>'

    imageurls = {}

    for idimagematch in re.finditer(idimageurlregex, xmlReadData.read(),flags=re.S):
        imageid = u'%s' % idimagematch.group(u'id')
        fileurl = idimagematch.group(u'url')
        filename = idimagematch.group(u'filename')
        if not imageid in imageurls:
            imageurls[imageid] = []
        imageurls[imageid].append((fileurl, filename))
    #print imageurls
    '''

    #xmlFile = '/home/mdammers/metmuseum/MetObjectsSculpture.xml'
    #xmlData = codecs.open(xmlFile, "w", "utf-8")
    #xmlData.write('<?xml version="1.0"?>' + "\n")
    #xmlData.write('<csv_data>' + "\n")

    #currentcommons = currentCommonsFiles()
    #print currentcommons

    foundit = True

    with open(csvlocation, 'rb') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Running into fun encoding problems!
            cleanedrow = {}
            for key, value in row.iteritems():
                if u'Object Number' in unicode(key, u'utf-8'):
                    cleanedrow[u'Object Number'] = unicode(value, u'utf-8')
                else:
                    cleanedrow[unicode(key, u'utf-8')] = unicode(value, u'utf-8')
            #print cleanedrow
            # We process the fields in the order of the CSV
            # Object Number,Is Highlight,Is Public Domain,Object ID,Department,Object Name,Title,Culture,Period,Dynasty,
            # Reign,Portfolio,Artist Role,Artist Prefix,Artist Display Name,Artist Display Bio,Artist Suffix,
            # Artist Alpha Sort,Artist Nationality,Artist Begin Date,Artist End Date,
            # Object Date,Object Begin Date,Object End Date,Medium,Dimensions,Credit Line,
            # Geography Type,City,State,County,Country,Region,Subregion,Locale,Locus,Excavation,River,
            # Classification,Rights and Reproduction,Link Resource,Metadata Date,Repository
            metadata = {}

            metadata['collectionqid'] = u'Q160236'
            metadata['collectionshort'] = u'MET'
            metadata['locationqid'] = u'Q160236'

            metadata['idpid'] = u'P217'
            metadata['id'] = cleanedrow.get('Object Number')

            metadata['instanceofqid'] = u'Q3305213'

            #wikidata = u''
            #if cleanedrow.get('Object ID') in metworks:
            #    wikidata = metworks[cleanedrow.get('Object ID')]

            #print metworks

                #time.sleep(5)

            # 'Is Public Domain' can be used later for uploading
            if cleanedrow.get('Is Public Domain')==u'True':
                pubcount = pubcount + 1
            i = i + 1
            # 'Object ID' is part of the url, but not inventory number
            # 'Department' could be used for categorization on Commons
            # 'Object Name' contaings something like "Painting"

            title = cleanedrow.get('Title')
            # Chop chop, in case we have very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                  }

            metadata['creatorname'] = cleanedrow.get('Artist Display Name')

            if cleanedrow.get('Classification')==u'Paintings':
                metadata['instanceofqid'] = u'Q3305213'
                if metadata['creatorname']==u'Unidentified Artist':
                    metadata['creatorqid'] = u'Q4233718'
                    metadata['creatorname'] = u'anonymous'
                    metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                                u'en' : u'painting by anonymous painter',
                                                }
                else:
                    metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                                u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                                }
            elif cleanedrow.get('Classification') in [u'Metalwork-Sculpture',
                                                    u'Wood-Sculpture',
                                                    u'Stone-Sculpture',
                                                    u'Sculpture-Bronze',
                                                    u'Sculpture-Stone',
                                                    u'Sculpture']:
                metadata['instanceofqid'] = mappings[cleanedrow.get('Classification')]
                if metadata['creatorname']==u'Unidentified Artist':
                    metadata['creatorqid'] = u'Q4233718'
                    metadata['creatorname'] = u'anonymous'
                    metadata['description'] = { u'en' : u'sculpture by anonymous sculptor',
                                                }
                else:
                    metadata['description'] = { u'en' : u'%s by %s' % (u'sculpture', metadata.get('creatorname'),),
                                                }
            elif cleanedrow.get('Classification')==u'Drawings':
                metadata['instanceofqid'] = mappings[cleanedrow.get('Classification')]
                if metadata['creatorname']==u'Unidentified Artist':
                    metadata['creatorqid'] = u'Q4233718'
                    metadata['creatorname'] = u'anonymous'
                    metadata['description'] = { u'en' : u'drawing by anonymous artist',
                                                }
                else:
                    metadata['description'] = { u'en' : u'%s by %s' % (u'drawing', metadata.get('creatorname'),),
                                                }
            elif cleanedrow.get('Classification')==u'Prints':
                metadata['instanceofqid'] = mappings[cleanedrow.get('Classification')]
                if metadata['creatorname']==u'Unidentified Artist':
                    metadata['creatorqid'] = u'Q4233718'
                    metadata['creatorname'] = u'anonymous'
                    metadata['description'] = { u'en' : u'print by anonymous artist',
                                                }
                else:
                    metadata['description'] = { u'en' : u'%s by %s' % (u'print', metadata.get('creatorname'),),
                                                }
            elif (cleanedrow.get('Classification')==u'' or cleanedrow.get('Classification')==u'|') and cleanedrow.get('Department')==u'The Libraries':
                metadata['instanceofqid'] = u'Q571' # Book
                if metadata['creatorname']==u'Unidentified Artist':
                    metadata['creatorqid'] = u'Q4233718'
                    metadata['creatorname'] = u'anonymous'
                    metadata['description'] = { u'en' : u'book by anonymous writer',
                                                }
                else:
                    bookdescription = u'%s by %s' % (u'book', metadata.get('creatorname').replace(u'|', u', '),)
                    if len(bookdescription) > 220:
                        bookdescription = bookdescription[0:200]
                    metadata['description'] = { u'en' : bookdescription,
                                                }

            else:
                if cleanedrow.get('Classification') in mappings:
                    metadata['instanceofqid'] = mappings[cleanedrow.get('Classification')]
                else:
                    metadata['instanceofqid'] = mappings[u'']
                whatisit = cleanedrow.get('Classification').lower().replace(u'|', u' ').strip()
                if not whatisit:
                    whatisit = u'object'
                metadata['description'] = { u'en' : u'%s highlighted in The MET collection' % (whatisit,),
                                                }

            if cleanedrow.get('Object Date')==cleanedrow.get(u'Object Begin Date') \
                    and cleanedrow.get('Object Date')==cleanedrow.get(u'Object End Date'):
                metadata['inception']=cleanedrow.get('Object Date')

            if cleanedrow.get('Medium')==u'Oil on canvas':
                metadata['medium'] = u'oil on canvas'

            dimensiontext = cleanedrow.get('Dimensions')
            regex_2d = u'^.+in\. \((?P<height>\d+(\.\d+)?) x (?P<width>\d+(.\d+)?) cm\)$'
            regex_3d = u'^.+in\. \((?P<height>\d+(\.\d+)?) x (?P<width>\d+(.\d+)?) x (?P<depth>\d+(,\d+)?) cm\)$'
            match_2d = re.match(regex_2d, dimensiontext)
            match_3d = re.match(regex_3d, dimensiontext)
            if match_2d:
                metadata['heightcm'] = match_2d.group(u'height')
                metadata['widthcm'] = match_2d.group(u'width')
            elif match_3d:
                metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
                metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
                metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')
            #else:
            #    pywikibot.output(u'No match found for %s' % (dimensiontext,))

            # 'Credit Line' can be used for image upload
            metadata['creditline'] = cleanedrow.get('Credit Line')

            acquisitiondateregex = u'^.+, (\d\d\d\d)$'
            acquisitiondatematch = re.match(acquisitiondateregex, cleanedrow.get('Credit Line'))
            if acquisitiondatematch:
                metadata['acquisitiondate'] = acquisitiondatematch.group(1)

            metadata['url'] = cleanedrow.get('Link Resource')

            #filename = u'%s - %s - MET - %s - %s' % (metadata['creatorname'],
            #                                         title,
            #                                         metadata['id'],
            #                                         u'somefilename.jpg')

            #if cleanedrow.get('Object ID')==u'438032':
            #    foundit = True

            if cleanedrow.get('Is Public Domain')==u'True' and cleanedrow.get('Is Highlight')==u'True':
                if cleanedrow.get('Classification') not in classifications:
                    classifications[cleanedrow.get('Classification')] = 1
                else:
                    classifications[cleanedrow.get('Classification')] = classifications[cleanedrow.get('Classification')] + 1
                yield metadata
            '''

            if cleanedrow.get('Classification')!=u'Paintings'and cleanedrow.get('Classification')==u'Sculpture':
                #metadata['instanceofqid'] = u'Q3305213'
                if cleanedrow.get('Is Public Domain')==u'True' and cleanedrow.get('Is Highlight')!=u'True': # and cleanedrow.get('Object ID') in imageurls:
                    for (imageurl, filename) in getImageUrls(cleanedrow.get('Object ID'), cleanedrow.get('Title')):
                    #pubpaintingcount = pubpaintingcount + 1
                        fullfilename = u'%s.jpg' % (filename,)
                        fullfilenamee = u'%s.jpeg' % (filename,)
                        # FIXED: Underscores probably mess things up here, and strip too
                        if fullfilename not in currentcommons and fullfilenamee not in currentcommons:
                            xmlData.write('<row>' + "\n")
                            for key, value in cleanedrow.iteritems():
                                xmlkey = key.replace(u' ', u'_')
                                xmlData.write('    ' + '<' + xmlkey + '>' \
                                              + escape(value) + '</' + xmlkey + '>' + "\n")
                            xmlData.write('    ' + '<Image_Url>' \
                                      + escape(imageurl) + '</Image_Url>' + "\n")
                            xmlData.write('    ' + '<wikidata>' \
                                          + wikidata + '</wikidata>' + "\n")
                            xmlData.write('    ' + '<Filename>' \
                                          + escape(filename) + '</Filename>' + "\n")
                            xmlData.write('</row>' + "\n")
                        else:
                            print u'The file %s is already on commons' % (filename,)

                paintingcount = paintingcount + 1
                #for key, value in cleanedrow.iteritems():
                #    #if key in [u'Object Number',]:
                #    print u'%s : %s' % (key, value)
                yield metadata
            '''

    #xmlData.write('</csv_data>' + "\n")
    #pywikibot.output(u'Processed %s items and %s are marked as public domain' % (i, pubcount))
    #pywikibot.output(u'Processed %s paintings and %s are marked as public domain' % (paintingcount, pubpaintingcount))
    print (classifications)


def getMETpaintingsOnWikikidataGenerator():
    '''
    Return the integer id's of the met
    '''
    query = u'SELECT ?item ?id WHERE { ?item wdt:P3634 ?id . ?item wdt:P31 wd:Q3305213 } ORDER BY xsd:integer(?id)'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        yield int(resultitem.get('id'))


def getMETGenerator():
    '''
    Use the API at https://metmuseum.github.io/ to get works
    :return: Yields dictionaries with the metadata per work suitable for ArtDataBot
    '''
    idurl = u'https://collectionapi.metmuseum.org/public/collection/v1/objects'
    idurl = u'https://collectionapi.metmuseum.org/public/collection/v1/search?q=Painting'
    idpage = requests.get(idurl, verify=False)

    pywikibot.output(u'The MET query returned %s works' % (idpage.json().get('total')))

    session = requests.Session()

    foundit= True
    lookingfor = 65594

    metids = sorted(idpage.json().get('objectIDs'), reverse=True)

    for metid in metids:
    #for metid in getMETpaintingsOnWikikidataGenerator():
        if metid == lookingfor:
            foundit = True

        metadata = {}

        if not foundit:
            continue
        meturl = u'https://collectionapi.metmuseum.org/public/collection/v1/objects/%s' % (metid,)
        print (meturl)
        metpage = session.get(meturl, verify=False)
        # Only work on paintings
        try:
            metjson = metpage.json()
        except ValueError:
            print (metpage.text)
            continue

        foundPainting = False

        if metjson.get(u'objectName') and metjson.get(u'objectName')==u'Painting':
            foundPainting = True

        if metjson.get(u'classification') and metjson.get(u'classification')==u'Paintings':
            foundPainting = True

        if not foundPainting:
            continue

        print(json.dumps(metjson, indent=4, sort_keys=True))

        metadata['url'] = metjson.get('objectURL')

        metadata['collectionqid'] = u'Q160236'
        metadata['collectionshort'] = u'MET'
        metadata['locationqid'] = u'Q160236'

        metadata['idpid'] = u'P217'
        metadata['id'] = metjson.get(u'accessionNumber')

        metadata['instanceofqid'] = u'Q3305213'

        metadata['artworkidpid'] = u'P3634'
        metadata['artworkid'] = u'%s' % (metid,)

        title = metjson.get('title')
        # Chop chop, in case we have very long titles
        if len(title) > 220:
            title = title[0:200]
        metadata['title'] = { u'en' : title,
                              }
        if metjson.get('artistDisplayName'):
            metadata['creatorname'] = metjson.get('artistDisplayName')

        if not metjson.get('artistDisplayName')  or metjson.get('artistDisplayName')==u'Unidentified Artist':
            metadata['creatorqid'] = u'Q4233718'
            metadata['creatorname'] = u'anonymous'
            metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                        u'en' : u'painting by anonymous painter',
                                        u'es' : u'cuadro de autor desconocido'
                                        }
        elif metadata.get(u'creatorname'):
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        u'de' : u'%s von %s' % (u'Gemälde', metadata.get('creatorname'),),
                                        u'es' : u'%s de %s' % (u'cuadro', metadata.get('creatorname'),),
                                        }

        datecircaregex = u'^ca\.\s*(\d\d\d\d)$'
        datecircamatch = re.match(datecircaregex, metjson.get('objectDate'))

        if metjson.get('objectDate')==str(metjson.get(u'objectBeginDate')) \
                    and metjson.get('objectDate')==str(metjson.get(u'objectEndDate')):
            metadata['inception']=int(metjson.get('objectDate'))
        elif datecircamatch:
            metadata['inception'] = int(datecircamatch.group(1))
            metadata['inceptioncirca'] = True
        elif metjson.get(u'objectBeginDate') and metjson.get(u'objectEndDate') and \
            metjson.get(u'objectBeginDate') > 1000 and metjson.get(u'objectEndDate') > metjson.get(u'objectBeginDate'):
            metadata['inceptionstart'] = int(metjson.get(u'objectBeginDate'))
            metadata['inceptionend'] = int(metjson.get(u'objectEndDate'))

        # If the credit line ends with a year, we'll take it
        acquisitiondateregex = u'^.+, (\d\d\d\d)$'
        acquisitiondatematch = re.match(acquisitiondateregex, metjson.get(u'creditLine'))
        if acquisitiondatematch:
            metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

        if metjson.get('medium')==u'Oil on canvas':
            metadata['medium'] = u'oil on canvas'

        dimensiontext = metjson.get('dimensions')
        regex_2d = u'^.+in\. \((?P<height>\d+(\.\d+)?) x (?P<width>\d+(.\d+)?) cm\)$'
        regex_3d = u'^.+in\. \((?P<height>\d+(\.\d+)?) x (?P<width>\d+(.\d+)?) x (?P<depth>\d+(,\d+)?) cm\)$'
        match_2d = re.match(regex_2d, dimensiontext)
        match_3d = re.match(regex_3d, dimensiontext)
        if match_2d:
            metadata['heightcm'] = match_2d.group(u'height')
            metadata['widthcm'] = match_2d.group(u'width')
        elif match_3d:
            metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
            metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
            metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')

        # portrait (Q134307)
        # religious art (Q2864737)
        # landscape art (Q191163)
        # still life (Q170571)
        # self-portrait (Q192110)

        genres = { u'Saints' : u'Q2864737', # religious art (Q2864737)
                   u'Christ' : u'Q2864737',
                   u'Jesus' : u'Q2864737',
                   u'Angels' : u'Q2864737',
                   u'Portraits' : u'Q134307', # portrait (Q134307)
                   u'Landscapes' : u'Q191163', # landscape art (Q191163)
                   u'Self-portraits' : u'Q192110', # self-portrait (Q192110)
                   u'Still Life' : u'Q170571', # still life (Q170571)
                   }

        # Can loop over tags to add genre
        foundgenre = u''
        genrecollision = u''

        for tag in metjson.get('tags'):
            if tag in genres:
                if not foundgenre:
                    foundgenre = genres.get(tag)
                elif foundgenre:
                    if genres.get(tag)!=foundgenre:
                        genrecollision = genres.get(tag)
                        continue

        if foundgenre and not genrecollision:
            metadata['genreqid'] = foundgenre

        madelocations = {u'China' : u'Q29520',
                         u'India' : u'Q668',
                         u'Iran' : u'Q794',
                         u'Japan' : u'Q17',
                         u'Nepal' : u'Q837',
                         }

        if metjson.get('country') and metjson.get('country') in madelocations:
            metadata['madeinqid'] = madelocations.get(metjson.get('country'))
        elif metjson.get('culture'):
            for madelocation in madelocations:
                if metjson.get('culture').startswith(madelocation):
                    metadata['madeinqid'] = madelocations.get(madelocation)
                    break

        # No IIIF
        # Most images are uploaded already
        if metjson.get('isPublicDomain') and metjson.get('primaryImage'):
            metadata[u'imageurl'] = metjson.get('primaryImage')
            metadata[u'imageurlformat'] = u'Q2195' #JPEG
            metadata[u'imageurllicense'] = u'Q6938433' # CC0
            metadata[u'imageoperatedby'] = u'Q160236'

        yield metadata

def main(*args):
    dictGen = getMETGenerator() #, metworks)

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
