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
import HTMLParser
import os
import csv
import codecs
from xml.sax.saxutils import escape


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
    print len(result)
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


def currentCommonsIds():
    '''
    Get the list of current Commons filenames with spaces, not underscores:
    u'Diptyc MET ep1975.1.22.r.bw.R.jpg'
    '''
    resultFiles = []
    resultids = []
    urlpage = requests.get(u'https://tools.wmflabs.org/multichill/queries/commons/met_urls.txt', verify=False)
    regex =u'^\* File\:(.+) - http\:\/\/www\.metmuseum\.org\/art\/collection\/search\/(\d+)$'
    for match in re.finditer(regex, urlpage.text, re.M):
        # Might crash on non-integer
        resultFiles.append(match.group(1).replace(u'_', u' '))
        resultids.append(match.group(2))
    return (resultFiles,resultids)

def getImageUrls(metid, title):

    meturl = u'http://www.metmuseum.org/api/Collection/additionalImages?crdId=%s' % (metid,)

    searchPage = requests.get(meturl, verify=False)
    searchJson = searchPage.json()

    print searchJson

    regex =u'^http\:\/\/images\.metmuseum\.org\/CRDImages\/[^\/]+\/original\/(.+).jpe?g\s*$'

    result = []
    notallowedchars = [u':', u'[', u']', u'#', u'|']

    if searchJson.get(u'results'):
        for fileinfo in searchJson.get(u'results'):
            if fileinfo.get(u'isOasc'):
                fileurl = fileinfo.get(u'originalImageUrl')
                print fileurl
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

def getMETGenerator(csvlocation, metworks, ):
    """
    Generator to return Museum of New Zealand Te Papa Tongarewa paintings
    """
    pubcount = 0
    paintingcount = 0
    pubpaintingcount = 0
    i = 0
    #htmlparser = HTMLParser.HTMLParser()

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

    xmlBase = '/home/mdammers/metmuseum/MetObjectsMissing_%s.xml'
    xmlcounter = 1

    xmlFile = xmlBase % (xmlcounter, )
    xmlData = codecs.open(xmlFile, "w", "utf-8")
    xmlData.write('<?xml version="1.0"?>' + "\n")
    xmlData.write('<csv_data>' + "\n")

    xmlentries = 0
    maxentries = 10000

    (currentcommons,currentIds) = currentCommonsIds()

    #currentcommons = currentCommonsFiles()
    #currentcommons = []
    #print currentcommons

    foundit = False

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

            if cleanedrow.get('Object ID') in currentIds:
                #print u'Already have %s' % (cleanedrow.get('Object ID'),)
                continue

            metadata['idpid'] = u'P217'
            metadata['id'] = cleanedrow.get('Object Number')

            wikidata = u''
            if cleanedrow.get('Object ID') in metworks:
                wikidata = metworks[cleanedrow.get('Object ID')]

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
            if title > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                  }

            metadata['creatorname'] = cleanedrow.get('Artist Display Name')

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

            #if cleanedrow.get('Object ID')==u'742255':
            #    foundit = True

            if True:

            #if cleanedrow.get('Classification')!=u'Paintings'and cleanedrow.get('Classification')!=u'Sculpture' \
            #        and cleanedrow.get('Classification')!=u'Miniatures'and \
            #                cleanedrow.get('Classification')!=u'Paintings-Panels' and foundit:
                #metadata['instanceofqid'] = u'Q3305213'
                if cleanedrow.get('Is Public Domain')==u'True': # and cleanedrow.get('Is Highlight')!=u'True': # and cleanedrow.get('Object ID') in imageurls:
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
                            xmlentries = xmlentries + 1
                            if xmlentries > maxentries:
                                # Time to close the file and start a new one
                                xmlData.write('</csv_data>' + "\n")
                                xmlData.close()
                                xmlcounter = xmlcounter + 1

                                xmlFile = xmlBase % (xmlcounter, )
                                xmlData = codecs.open(xmlFile, "w", "utf-8")
                                xmlData.write('<?xml version="1.0"?>' + "\n")
                                xmlData.write('<csv_data>' + "\n")

                                xmlentries = 0
                        else:
                            print u'The file %s is already on commons' % (filename,)

                paintingcount = paintingcount + 1
                #for key, value in cleanedrow.iteritems():
                #    #if key in [u'Object Number',]:
                #    print u'%s : %s' % (key, value)
                yield metadata
    xmlData.write('</csv_data>' + "\n")
    pywikibot.output(u'Processed %s items and %s are marked as public domain' % (i, pubcount))
    pywikibot.output(u'Processed %s paintings and %s are marked as public domain' % (paintingcount, pubpaintingcount))


def main(*args):
    csvlocation = u''
    for arg in pywikibot.handle_args(args):
        csvlocation = arg

    print csvlocation
    #metworks = {}
    metworks = metWorksOnWikidata()
    dictGen = getMETGenerator(csvlocation, metworks)

    for painting in dictGen:
        pass
        #print painting

    #artDataBot = artdatabot.ArtDataBot(dictGen, create=False)
    #artDataBot.run()

if __name__ == "__main__":
    main()
