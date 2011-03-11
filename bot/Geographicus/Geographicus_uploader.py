#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
A program do generate descriptions for KIT (Tropenmuseum) images and to upload them right away.

'''
import sys, os.path, glob, re, hashlib, base64
#sys.path.append("/home/multichill/pywikipedia")
sys.path.append("D:/Wikipedia/pywikipedia/")
sys.path.append("../")
import wikipedia, config, query, upload
import csv
import dezoomify
#import flickrripper


def getDescription(metadata):
    '''
    Generate a description for a file
    '''

    description = u'{{subst:User:Multichill/Geographicus\n'
    description = description + u'|link=%(link)s\n'
    description = description + u'|product_name=%(product_name)s\n'
    description = description + u'|map_title=%(map_title)s\n'
    description = description + u'|description=%(description)s\n'
    description = description + u'|date=%(date)s\n'
    description = description + u'|cartographer=%(cartographer)s\n'
    description = description + u'|source=%(source)s\n'
    description = description + u'|image_link=%(image_link)s\n'
    description = description + u'|id=%(id)s\n'
    description = description + u'|width=%(width)s\n'
    description = description + u'|height=%(height)s\n'
    description = description + u'}}\n'
       
    return description % metadata
    
def findDuplicateImages(filename):
    '''
    Takes the photo, calculates the SHA1 hash and asks the mediawiki api for a list of duplicates.

    TODO: Add exception handling, fix site thing
    '''
    f = open(filename, 'rb')
    
    result = []
    hashObject = hashlib.sha1()
    hashObject.update(f.read(-1)) 
    #f.close()
    sha1Hash = base64.b16encode(hashObject.digest())
    
    params = {
    'action'    : 'query',
        'list'      : 'allimages',
        'aisha1'    : sha1Hash,
        'aiprop'    : '',
    }
    data = query.GetData(params, site=wikipedia.getSite(), useAPI = True, encodeTitle = False)

    for image in data['query']['allimages']:
        result.append(image['name'])
    return result

def getTitle(metadata):
    title = u'%(product_name)s - Geographicus - %(id)s.jpg' % metadata

    '''
    record=database.get(baseFilename)
    description = unicode(record[2], 'utf-8').strip()

    if len(description)>120:
        description = description[0 : 120]

    title = u'%s - %s.jpg' % (description, baseFilename)
    '''
    
    return title

def getMetadata(row):
    metadata = {
        u'link' : unicode(row.get('link'), 'Windows-1252'),
        u'product_name' : unicode(row.get(u'product_name'), 'Windows-1252').replace(u'Antique Map: ', u''),
        u'map_title' : unicode(row.get(u'map_title'), 'Windows-1252'),
        u'description' : unicode(row.get(u'description'), 'Windows-1252'),
        u'date' : unicode(row.get(u'date'), 'Windows-1252'),
        u'cartographer' : unicode(row.get(u'cartographer'), 'Windows-1252').replace(u'http://www.geographicus.com/mm5/cartographers/', u''),
        u'source' : unicode(row.get(u'source'), 'Windows-1252'),
        u'image_link' : unicode(row.get(u'image_link'), 'Windows-1252'),
        u'id' : unicode(row.get(u'id'), 'Windows-1252'),
        u'width' : unicode(row.get(u'width'), 'Windows-1252'),
        u'height' : unicode(row.get(u'height'), 'Windows-1252'),
        }

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

def processFile(row, imageDir):
    metadata = getMetadata(row)
    title = getTitle(metadata)
    description = getDescription(metadata)
    wikipedia.output(title)
    wikipedia.output(description)
    # Check of the title already exists

    # Download and dezoomify the image
    tempfile = imageDir + metadata.get('id') + u'.jpg'
    dezoomify.Dezoomify(url=metadata.get('link'), debug=True, out=tempfile)
    bot = upload.UploadRobot(url=tempfile, description=description, useFilename=title, keepFilename=True, verifyDescription=False)
    bot.run()

def main(args):


    #directory = u'D:/Wikipedia/nationaal archief/WeTransfer-VjTrJQOD/'
    csvFile = u'D:/Wikipedia/Geographicus/geographicus-wikimedia.csv'
    imageDir = u'D:/Wikipedia/Geographicus/images/'

    database = {}

    reader = csv.DictReader(open(csvFile, "rb"), dialect='excel')
    for row in reader:
        print row
        processFile(row, imageDir)
        #database[row[0]] = row
        #print row
        #        wikipedia.output(row)
    '''
    if os.path.isdir(directory):
        for filename in glob.glob(directory + "/*.jpg"):
            #print filename
            duplicates = findDuplicateImages(filename)
            if duplicates:
                wikipedia.output(u'Found duplicate image at %s' % duplicates.pop())
            else:
                print 'bla'
                dirname = os.path.dirname(filename)
                basename = os.path.basename(filename)
                baseFilename, extension = os.path.splitext(basename)

                description = generateDescription(baseFilename, database)
                title = getTitle(baseFilename, database)

                wikipedia.output(description)
                wikipedia.output(title)
                bot = upload.UploadRobot(url=filename.decode(sys.getfilesystemencoding()), description=description, useFilename=title, keepFilename=True, verifyDescription=False)
                bot.run()
                #time.sleep(30)
    '''
    
    
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print "All done!"
