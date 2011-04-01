#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
A program to upload all the images in the Web Gallery of Art website at http://www.wga.hu/

'''
import sys, os.path, glob, re, hashlib, base64, StringIO
import xml.etree.ElementTree
#sys.path.append("/home/multichill/pywikipedia")
sys.path.append("c:/pywikipedia/")
sys.path.append("../")
import wikipedia, config, query, upload
import csv, urllib
import dezoomify
import flickrripper

def downloadPhoto(photoUrl = ''):
    '''
    Download the photo and store it in a StrinIO.StringIO object.

    TODO: Add exception handling
    '''
    imageFile=urllib.urlopen(photoUrl).read()
    return StringIO.StringIO(imageFile)

def findDuplicateImages(photo = None, site = wikipedia.getSite(u'commons', u'commons')):
    '''
    Takes the photo, calculates the SHA1 hash and asks the mediawiki api for a list of duplicates.

    TODO: Add exception handling, fix site thing
    '''
    hashObject = hashlib.sha1()
    hashObject.update(photo.getvalue())
    return site.getFilesFromAnHash(base64.b16encode(hashObject.digest()))

def getDescription(metadata):
    '''
    Generate a description for a file
    '''

    description = u'{{User:Multichill/Europeana\n'
    for key, value in metadata.iteritems():
        description = description + u'|' + key + u'=%(' + key + u')s\n'
    description = description + u'}}\n'
       
    return description % metadata
    
def getTitle(metadata):
    title = u'%(dc:title)s - %(dc:identifier)s' % metadata

    description = metadata.get(u'dc:title')
    identifier = metadata.get(u'dc:identifier')

    if len(description)>120:
        description = description[0 : 120]

    title = u'%s - %s.jpg' % (description, identifier)
    
    return flickrripper.cleanUpTitle(title)

def cleanDate(date):
    # Empty, make it really empty
    if date==u'-':
        return u''
    # TODO: Circa
    # TODO: Period

    return date

def getMetadata(row):
    metadata = {
        u'AUTHOR' : unicode(row.get('AUTHOR'), 'Windows-1252'),
        u'BORN-DIED' : unicode(row.get(u'BORN-DIED'), 'Windows-1252'),
        u'TITLE' : unicode(row.get(u'TITLE'), 'Windows-1252'),
        u'DATE' : unicode(row.get(u'DATE'), 'Windows-1252'),
        u'TECHNIQUE' : unicode(row.get(u'TECHNIQUE'), 'Windows-1252'),
        u'LOCATION' : unicode(row.get(u'LOCATION'), 'Windows-1252'),
        u'URL' : unicode(row.get(u'URL'), 'Windows-1252'),
        u'FORM' : unicode(row.get(u'FORM'), 'Windows-1252'),
        u'TYPE' : unicode(row.get(u'TYPE'), 'Windows-1252'),
        u'SCHOOL' : unicode(row.get(u'SCHOOL'), 'Windows-1252'),
        u'TIMELINE' : unicode(row.get(u'TIMELINE'), 'Windows-1252'),
        }
    # Clean up date
    metadata['DATE'] = cleanDate(metadata.get('DATE'))
    # Split technique
    # Clean up location
    if metadata['LOCATION']==u'-':
        metadata['LOCATION']==u''
    # Get image url
    metadata['IMAGEURL'] = re.sub(u'http://www.wga.hu/html/(.+)\.html', u'http://www.wga.hu/art/\\1.jpg', metadata['URL'])
        
    '''
    metadata = {
        u'link' : unicode(row[0], 'Windows-1252'),
        u'product_name' : unicode(row[1], 'Windows-1252').replace(u'Antique Map: ', u''),
        u'map_title' : unicode(row[2], 'Windows-1252'),
        u'description' : unicode(row[3], 'Windows-1252'),
        u'date' : unicode(row[4], 'Windows-1252'),
        u'cartographer' : unicode(row[5], 'Windows-1252').replace(u'http://www.geographicus.com/mm5/cartographers/', u''),
        u'source' : unicode(row[6], 'Windows-1252'),
        u'image_link' : unicode(row[7], 'Windows-1252'),
        u'id' : unicode(row[8], 'Windows-1252'),
        u'width' : unicode(row[9], 'Windows-1252'),
        u'height' : unicode(row[10], 'Windows-1252'),
        }
    '''
    return metadata

def procesItem(metadata):
    metadata = getEuropeanaMetadata(metadata)

    photo = downloadPhoto(metadata['europeana:object'])
    duplicates = findDuplicateImages(photo)

    # We don't want to upload dupes
    if duplicates:
        wikipedia.output(u'Found duplicate image at %s' % duplicates.pop())
	# The file is at Commons so return True
        return True

    title = getTitle(metadata)
    description = getDescription(metadata)

    # Check of the title already exists
    #site = wikipedia.getSite('commons', 'commons')
    #page = wikipedia.ImagePage(site, title)

    #if page.exists():
    #    wikipedia.output(u'The file %s already exists. Probably already uploaded by me. Skipping' % title)
    #    return False

    wikipedia.output(u'Preparing upload for %s.' % title)    
    wikipedia.output(description)    
                        
    # Download and dezoomify the image
    #tempfile = imageDir + metadata.get('id') + u'.jpg'
    #try:
    #    dezoomify.Dezoomify(url=metadata.get('link'), debug=True, out=tempfile)
    #except IOError as e:
    #    #wikipedia.output(e)
    #    wikipedia.output(u'Dezoomify failed')
    #    return False
        

    # Check for dupe. This probably doesn't work, but it doesn't hurt either.
    #duplicates = findDuplicateImages(tempfile)
    #if duplicates:
    #    wikipedia.output(u'Found duplicate image at %s' % duplicates.pop())
    #    return False
    bot = upload.UploadRobot(metadata['europeana:object'], description=description, useFilename=title, keepFilename=True, verifyDescription=False, targetSite = wikipedia.getSite('commons', 'commons'))
    #bot = upload.UploadRobot(url=tempfile, description=description, useFilename=title, keepFilename=True, verifyDescription=False)
    bot.run()

def getEuropeanaMetadata(metadata):
    xmlFile=StringIO.StringIO(urllib.urlopen(metadata.get('link')).read())

    xml.etree.ElementTree.register_namespace('srw:', 'http://www.loc.gov/standards/sru/sru1-1archive/xml-files/srw-types.xsd')
    xml.etree.ElementTree.register_namespace(u'europeana', u'')
    xml.etree.ElementTree.register_namespace(u'enrichment', u'')
    
    tree = xml.etree.ElementTree.parse(xmlFile)
    root = tree.getroot()
    #xml.etree.ElementTree.dump(root)


    # Begin big evil hack because of namespace problems
    # FIXME!!!!
    for searchRetrieveResponse in root.getchildren():
        #print searchRetrieveResponse.tag
        if searchRetrieveResponse.tag==u'{http://www.loc.gov/zing/srw/}records':
            #print searchRetrieveResponse
            for recordsInfo in searchRetrieveResponse:
                #print recordsInfo
                if recordsInfo.tag==u'{http://www.loc.gov/zing/srw/}record':
                    for recordInfo in recordsInfo:
                        #print recordInfo
                        if recordInfo.tag==u'{http://www.loc.gov/zing/srw/}recordData':
                            #print recordInfo
                            for field in recordInfo[0]:
                                fieldname = field.tag
                                fieldname = fieldname.replace('{http://www.europeana.eu}', 'europeana:')
                                fieldname = fieldname.replace('{http://purl.org/dc/terms/}', 'dc:')
                                fieldname = fieldname.replace('{http://purl.org/dc/elements/1.1/}', 'dc:')
                                fieldname = fieldname.replace('{http://www.europeana.eu/schemas/ese/enrichment/}', 'enrichment:')

                                # FIXME : Make something up for multiple occurences of the same field

                                metadata[fieldname] = field.text

                                #print fieldname
                                #print field
                                #print field.tag
                                #print field.text
                            
                    
                
                            #xml.etree.ElementTree.dump(recordInfo[0])
                    
        #xml.etree.ElementTree.dump(searchRetrieveResponse)    
    
    #dc = root.find('{http://www.loc.gov/zing/srw/}:searchRetrieveResponse').find('{http://www.loc.gov/zing/srw/}:records').find('{http://www.loc.gov/zing/srw/}:record').find('{http://www.loc.gov/zing/srw/}:recordData').find('dc:dc')
    #xml.etree.ElementTree.dump(dc)
    metadata['link'] = metadata.get('europeana:uri')
    metadata['europeana:object'] = metadata.get('europeana:object').replace('http://www.dilibri.de/download/webcache/1000/', 'http://www.dilibri.de/download/webcache/0/')
    return metadata


def main(args):
    print args
    searchstring = args[0]

    url = 'http://api.europeana.eu/api/opensearch.rss?searchTerms=%s&wskey=%s' % (searchstring, config.europeana['api_key'])
    xmlFile=StringIO.StringIO(urllib.urlopen(url).read())
    
    tree = xml.etree.ElementTree.parse(xmlFile)
    
    root = tree.getroot()

    for document in root.getchildren():
        for item in document.findall('item'):
            metadata = {}
            metadata['title'] = item.find('title').text
            metadata['link'] = item.find('link').text
            metadata['description'] = item.find('description').text
            metadata['sourceurl'] = item.find('enclosure').get('url')
            #wikipedia.output(title)
            #wikipedia.output(description)
            #wikipedia.output(link)
            #wikipedia.output(sourceurl)
            procesItem(metadata)
            #print link
            #print description
            #xml.etree.ElementTree.dump(item)
        #print document
    #print root
    
    #print xmlfile
    '''
    mainres = mainc.search(searchstring + u'&wskey=' + apikey)

    for item in mainrc:
        print item

    
    
    database = {}

    reader = csv.DictReader(open(csvFile, "rb"), dialect='excel', delimiter=';')
    for row in reader:
        
        print row
        processFile(row)
        #database[row[0]] = row
        #print row
        #        wikipedia.output(row)

    '''
    
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print "All done!"
