#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
We imported a lot of files to Wikimedia Commons, see :
https://commons.wikimedia.org/wiki/Category:Images_from_Metropolitan_Museum_of_Art

Turns out that the numbers don't add up. This piece of code is used to hunt down the missing files

Make some lookup tables before we start.

Loop over the id's at https://collectionapi.metmuseum.org/public/collection/v1/objects

If it's in the public domain, check if we uploaded all the files

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


class MetFileUploadBot:
    """

    """
    def __init__(self, generator):
        """

        """
        self.generator = generator
        self.metWorksOnWikidata = self.getMetWorksOnWikidata()
        self.commonsFiles = self.getCurrentCommonsFiles()
        self.commonsIds = self.getCurrentCommonsIds()
        self.commonsShortFilenames = self.getCurrentCommonsShortFilenames()
        self.xmldata=filesFound = {}
        self.alreadyUploaded = []

        #self.repo = pywikibot.Site().data_repository()

    def getMetWorksOnWikidata(self):
        '''
        Just return all the MET id's as a dict
        :return: Dict
        '''
        result = {}
        query = u'SELECT ?item ?id WHERE { ?item wdt:P3634 ?id  } LIMIT 10000009'
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[resultitem.get('id')] = qid
        print len(result)
        return result

    def getCurrentCommonsFilesTransclusion(self):
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

    def getCurrentCommonsFiles(self):
        '''
        Get the list of current Commons filenames with spaces, not underscores:
        u'Diptyc MET ep1975.1.22.r.bw.R.jpg'
        '''
        result = []
        urlpage = requests.get(u'https://tools.wmflabs.org/multichill/queries/commons/met_files.txt', verify=False)
        regex =u'^\* File\:(.+)$'
        for match in re.finditer(regex, urlpage.text, re.M):
            # Might crash on non-integer
            result.append(match.group(1).replace(u'_', u' '))
        return result

    def getCurrentCommonsIds(self):
        '''
        Get the list of current Commons filenames with spaces, not underscores:
        u'Diptyc MET ep1975.1.22.r.bw.R.jpg'
        '''
        resultFiles = []
        resultids = []
        urlpage = requests.get(u'https://tools.wmflabs.org/multichill/queries/commons/met_urls.txt', verify=False)
        regex =u'^\* File\:(.+) - https\:\/\/www\.metmuseum\.org\/art\/collection\/search\/(\d+)$'
        for match in re.finditer(regex, urlpage.text, re.M):
            # Might crash on non-integer
            resultFiles.append(match.group(1).replace(u'_', u' '))
            resultids.append(match.group(2))
        return (resultFiles,resultids)

    def getCurrentCommonsShortFilenames(self):
        '''
        Get the list of current Commons filenames with spaces, not underscores:
        u'Diptyc MET ep1975.1.22.r.bw.R.jpg'
        '''
        result= {}
        urlpage = requests.get(u'https://tools.wmflabs.org/multichill/queries/commons/met_urls.txt', verify=False)
        regex =u'^\* File\:.*[ _]?MET[ _](.+)\.(jpg|jpeg) - https\:\/\/www\.metmuseum\.org\/art\/collection\/search\/(\d+)$'
        for match in re.finditer(regex, urlpage.text, re.M|re.I):
            # Might crash on non-integer
            result[(match.group(1).replace(u' ', u'_'))] = match.group(3)
        return result

    def run(self):
        '''

        :return:
        '''
        self.xmlBase = '/home/mdammers/metmuseum/MetObjectsMissingChristmas2018_%s.xml'
        self.xmlcounter = 1
        self.xmlentries = 0
        self.maxentries = 10000

        self.xmlFile = self.xmlBase % (self.xmlcounter, )
        self.xmlData = codecs.open(self.xmlFile, "w", "utf-8")
        self.xmlData.write('<?xml version="1.0"?>' + "\n")
        self.xmlData.write('<csv_data>' + "\n")

        for metObject in self.generator:
            self.processMetObject(metObject)

        self.xmlData.write('</csv_data>' + "\n")
        self.xmlData.close()

    def processMetObject(self, metobject):
        '''

        :return:
        '''
        if metobject.get('primaryImage'):
            self.processMetImage(metobject.get('primaryImage'), metobject)

        for image in metobject.get('additionalImages'):
            self.processMetImage(image, metobject)

    def processMetImage(self, image, metobject):
        '''

        :param image:
        :return:
        '''
        title = self.generateCommonsTitle(image, metobject)
        if not title:
            return
        fullfilename = u'%s.jpg' % (title, )
        fullfilenamee = u'%s.jpeg' % (title, )
        if fullfilename in self.commonsFiles:
            self.alreadyUploaded.append(fullfilename)
            pywikibot.output(u'Already uploaded %s' % (fullfilename,))
            return
        elif fullfilenamee in self.commonsFiles:
            self.alreadyUploaded.append(fullfilenamee)
            pywikibot.output(u'Already uploaded %s' % (fullfilenamee,))
            return
        pywikibot.output(u'Probably going to upload %s' % (fullfilenamee,))
        self.outputXML(image, title, metobject)

    def generateCommonsTitle(self, image, metobject):
        regex =u'^https\:\/\/images\.metmuseum\.org\/CRDImages\/[^\/]+\/original\/(.+).jpe?g\s*$'

        notallowedchars = [u':', u'[', u']', u'#', u'|']

        match = re.match(regex, image, re.I)
        if match:
            title = metobject.get('title').strip().replace(u'  ', u' ')
            for toreplace in notallowedchars:
                title = title.replace(toreplace, u'-')
            metfilename = match.group(1).strip().replace(u'_', u' ')
            if title:
                filename = u'%s MET %s' % (title, metfilename, )
            else:
                filename = u'MET %s' % (metfilename, )
            return filename

    def outputXML(self, imageurl, filename, metobject):
        '''

        :param filename:
        :param metobject:
        :return:
        '''
        toignore = [u'primaryImage',
                    u'primaryImageSmall',
                    u'additionalImages',
                    u'constituents']
        self.xmlData.write('<row>' + "\n")
        for key, value in metobject.iteritems():
            if key not in toignore:
                xmlkey = key.replace(u' ', u'_')
                self.xmlData.write('    ' + '<' + xmlkey + '>' \
                                + escape(u'%s' % (value,)) + '</' + xmlkey + '>' + "\n")
        self.xmlData.write('    ' + '<Image_Url>' \
                        + escape(imageurl).replace(u' ', u'%20').replace(u'–', u'%E2%80%93') + '</Image_Url>' + "\n")
        #self.xmlData.write('    ' + '<wikidata>' \
        #                + wikidata + '</wikidata>' + "\n")
        self.xmlData.write('    ' + '<Filename>' \
                        + escape(filename) + '</Filename>' + "\n")
        self.xmlData.write('</row>' + "\n")
        self.xmlentries = self.xmlentries + 1
        if self.xmlentries > self.maxentries:
            # Time to close the file and start a new one
            self.xmlData.write('</csv_data>' + "\n")
            self.xmlData.close()
            self.xmlcounter = self.xmlcounter + 1

            self.xmlFile = self.xmlBase % (self.xmlcounter, )
            self.xmlData = codecs.open(self.xmlFile, "w", "utf-8")
            self.xmlData.write('<?xml version="1.0"?>' + "\n")
            self.xmlData.write('<csv_data>' + "\n")

            self.xmlentries = 0



def currentMetShortFilenamesGenerator():
    '''

    :return:
    '''
    unicodeerrors = 0
    with open(u'/home/mdammers/metmuseum/filenameiddump.csv', 'rb') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                shortfilename = unicode(row.get('FileName'), u'utf-8').replace(u' ', u'_').replace(u'.jpg',u'').replace(u'.JPG',u'').replace(u'.jpeg',u'')
                yield (shortfilename, row.get('ObjectId'))
            except UnicodeDecodeError:
                unicodeerrors = unicodeerrors + 1
                pass
    print u'Number of unicode errors encountered: %s' % (unicodeerrors,)

def getImageUrls(metid, title):

    getmore = True
    i = 1
    perpage = 10
    while getmore:
        meturl = u'http://www.metmuseum.org/api/Collection/additionalImages?crdId=%s&page=%s&perPage=%s' % (metid,i, perpage)

        searchPage = requests.get(meturl, verify=False)
        searchJson = searchPage.json()

        if searchJson.get(u'totalResults') < i * perpage:
            getmore = False
        i = i + 1

        print searchJson

        regex =u'^https\:\/\/images\.metmuseum\.org\/CRDImages\/[^\/]+\/original\/(.+).jpe?g\s*$'

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

def getMETGenerator2(csvlocation, metworks, missingids):
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

    xmlBase = '/home/mdammers/metmuseum/MetObjectsMissingChristmas_%s.xml'
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

            if cleanedrow.get('Object ID') not in missingids:
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
            if len(title) > 220:
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
                                      + escape(imageurl).replace(u' ', u'%20').replace(u'–', u'%E2%80%93') + '</Image_Url>' + "\n")
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


def findMissingIdentifiers():
    """
    Grab the list of current Commons filenames and the list of MET filenames

    Process these and return a list of identifiers for which we have missing files.
    This can be used as a filter to process the whole csv and to generate the XML
    :return:

    """
    commonsfiles = currentCommonsShortFilenames()
    metgenerator = currentMetShortFilenamesGenerator()
    foundit = 0
    foundsameid = 0
    founddifferentid = 0
    notfound = 0
    missingids = {}
    for (shortfilename, identifier) in metgenerator:
        if shortfilename not in commonsfiles:
            #print u'The file with name "%s" and id "%s" was not found' % (shortfilename, identifier)
            notfound = notfound + 1
            #imageurls = getImageUrls(identifier, shortfilename)
            #for imageurl in imageurls:
            #    print imageurl
            if identifier not in missingids:
                missingids[identifier] = 0
            missingids[identifier] = missingids[identifier] + 1
        else:
            foundit = foundit + 1
            if identifier == commonsfiles.get(shortfilename):
                foundsameid = foundsameid + 1
            else:
                founddifferentid = founddifferentid + 1

    print u'Total files found: %s' % (foundit,)
    print u'Of these total files, the files with the same id: %s' % (foundsameid,)
    print u'Of these total files, the files with a different id: %s' % (founddifferentid,)
    print u'Total files not found: %s' % (notfound,)
    print u'Number of ids not found: %s' % (len(missingids.keys()),)

    print u'Most used id\'s top 25:'
    topidsum = 0
    for identifier in sorted(missingids, key=missingids.get, reverse=True)[:25]:
        print u'* https://www.metmuseum.org/art/collection/search/%s - %s'  % (identifier, missingids[identifier])
        topidsum = topidsum + missingids[identifier]
    print u'Total number of files in this top 25: %s' % (topidsum,)

    return missingids.keys()


def getMETGenerator(isPublicDomain=None, objectName=None, metadataDate=None):
    '''
    Use the API at https://metmuseum.github.io/ to get works
    :param isPublicDomain - If this is set, works will be filtered so that only public domain works are returned
    :param objectName - If this is set, works will be filtered so for example only paintings are returned
    :param metadataDate: - If it's set, only return recently updated objects
    :return: Yields dictionaries with the metadata per work
    '''
    if metadataDate:
        idurl = u'https://collectionapi.metmuseum.org/public/collection/v1/objects?metadataDate=%s' % (metadataDate,)
    else:
        idurl = u'https://collectionapi.metmuseum.org/public/collection/v1/objects'

    idpage = requests.get(idurl)

    pywikibot.output(u'The MET query returned %s works' % (idpage.json().get('total')))

    session = requests.Session()

    for metid in idpage.json().get('objectIDs'):
        meturl = u'https://collectionapi.metmuseum.org/public/collection/v1/objects/%s' % (metid,)
        metpage = session.get(meturl)
        # Only work on public domain works if that is set
        if isPublicDomain and metpage.json().get(u'isPublicDomain')!=isPublicDomain:
            continue
        # Only work on certain type of objects if that is set
        if objectName and metpage.json().get(u'objectName')!=objectName:
            continue
        yield metpage.json()

def main(*args):

    generator = getMETGenerator(metadataDate='2018-12-13')

    metFileUploadBot = MetFileUploadBot(generator)
    metFileUploadBot.run()

    """
    missingids = findMissingIdentifiers()

    csvlocation = u'/home/mdammers/metmuseum/MetObjects_20171226.csv'
    for arg in pywikibot.handle_args(args):
        csvlocation = arg

    print csvlocation
    metworks = metWorksOnWikidata()
    dictGen = getMETGenerator(csvlocation, metworks, missingids)

    for painting in dictGen:
        pass
    #    #print painting

    #artDataBot = artdatabot.ArtDataBot(dictGen, create=False)
    #artDataBot.run()
    """
if __name__ == "__main__":
    main()
