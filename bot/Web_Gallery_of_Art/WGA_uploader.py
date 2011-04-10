#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
A program to upload all the images in the Web Gallery of Art website at http://www.wga.hu/

'''
import sys, os.path, glob, re, hashlib, base64, StringIO
#sys.path.append("/home/multichill/pywikipedia")
sys.path.append("D:/Wikipedia/pywikipedia/")
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

    description = u'{{User:Multichill/WGA\n'
    for key, value in metadata.iteritems():
        description = description + u'|' + key + u'=%(' + key + u')s\n'
    description = description + u'}}\n'
       
    return description % metadata
    
def getTitle(metadata):
    title = u'%(AUTHOR)s - %(TITLE)s - WGA.jpg' % metadata

    '''
    record=database.get(baseFilename)
    description = unicode(record[2], 'utf-8').strip()

    if len(description)>120:
        description = description[0 : 120]

    title = u'%s - %s.jpg' % (description, baseFilename)
    '''
    
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

    # Get the creator
    (surname, sep, firstname) = metadata['AUTHOR'].partition(',')
    surname = surname.strip().capitalize()
    firstname = firstname.strip().capitalize()
    metadata['creator'] = u'%s %s ' % (firstname, surname)
        
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

def processFile(row):
    metadata = getMetadata(row)

    if not metadata['FORM']==u'painting':
        wikipedia.output(u'Not a painting, skipping')
        return False
    
    photo = downloadPhoto(metadata['IMAGEURL'])
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
    bot = upload.UploadRobot(metadata['IMAGEURL'], description=description, useFilename=title, keepFilename=True, verifyDescription=False, targetSite = wikipedia.getSite('commons', 'commons'))
    #bot = upload.UploadRobot(url=tempfile, description=description, useFilename=title, keepFilename=True, verifyDescription=False)
    bot.run()

def main(args):
    csvFile = u'catalog.csv'

    database = {}

    reader = csv.DictReader(open(csvFile, "rb"), dialect='excel', delimiter=';')
    for row in reader:
        
        print row
        processFile(row)
        #database[row[0]] = row
        #print row
        #        wikipedia.output(row)

    
    
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print "All done!"
