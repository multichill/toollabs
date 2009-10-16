#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot to upload all images from the site of the US Navy (Navy News Service located at http://www.navy.mil/view_photos_top.asp

http://www.navy.mil/view_single.asp?id=<the id>
The images have ids from 0 to about 77000 in October 2009.
Start and end can be controlled with -start_id and -end_id

Screen scraping is done with BeautifulSoup so this needs to be installed.

'''
import sys, os, StringIO, hashlib, base64
import os.path
import urllib, re
from urllib import FancyURLopener
from datetime import datetime
from BeautifulSoup import BeautifulSoup 
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, upload
import config


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

def getMetadata(photo_id):
    '''
    Get all the metadata for a single image and store it in the photoinfo dict
    '''
    photoinfo = {}
     
    url = 'http://www.navy.mil/view_single.asp?id=' + str(photo_id)
    navyPage = urllib.urlopen(url)

    data = navyPage.read()

    soup = BeautifulSoup(data)
    
    if soup.find("meta", {'name' : 'HI_RES_IMAGE'}):
	photoinfo['url'] = soup.find("meta", {'name' : 'HI_RES_IMAGE'}).get('content')
    if soup.find("meta", {'name' : 'DESCRIPTION'}):
	photoinfo['fulldescription'] = soup.find("meta", {'name' : 'DESCRIPTION'}).get('content')
    if soup.find("meta", {'name' : 'ALT_TAG'}):
	photoinfo['shortdescription'] = soup.find("meta", {'name' : 'ALT_TAG'}).get('content')

    if photoinfo.get('url') and photoinfo.get('fulldescription') and photoinfo.get('shortdescription'):
	photoinfo['navyid'] = getNavyIdentifier(photoinfo['url'])
	#photoinfo['description'] = cleanDescription(photoinfo['fulldescription'])
	photoinfo['date'] = getDate(photoinfo['fulldescription'])
	photoinfo['author'] = getAuthor(photoinfo['fulldescription'])
	photoinfo['location'] = getLocation(photoinfo['fulldescription'])
	
	return photoinfo
    else:
	# Incorrect photo_id
	return False

def getNavyIdentifier(url):
    result = url
    result = result.replace(u'http://www.news.navy.mil/management/photodb/photos/', u'')
    result = result.replace(u'.jpg', u'')
    return result

def getDate(description):
    dateregex = u'\(([^\)]+\d\d\d\d)\)'
    matches = re.search(dateregex, description)
    if matches:
	#Should probably parse it, but that didn't work out	
	#descriptionformat = u'%b. %d, %Y'
    	#isoformat = '%Y-%m-%d'
        #date = datetime.strptime(matches.group(1), descriptionformat)
	#print date.strftime(isoformat)
        #return date.strftime(isoformat)
	return matches.group(1)

    else:
	return u''

def getAuthor(description):
    authorregex = []
    authorregex.append(u'\((U.S. [^\)]+)[\\/]\s?Released\)')
    authorregex.append(u'(U.S. \s?Navy photo by .*)\(RELEASED\)')

    for regex in authorregex:
	matches = re.search(regex, description, re.I)
	if  matches:
	    return matches.group(1)
    
    #Nothing matched
    return u'U.S. Navy photo<!-- Please update this from the description field-->'

def getLocation(description):
    # Assume that the location is before date.
    # Based on dateregex
    locationregex = u'^([^\(^\r^\n]+)\(([^\)]+\d\d\d\d)\)'
    matches = re.search(locationregex, description, re.MULTILINE)
    if matches:
        return matches.group(1)
    else:
	# Unknown location
        return u'unknown'

def buildDescription(photo_id, metadata):
    '''
    Create the description of the image based on the metadata
    '''
    description = u''

    description = description + u'== {{int:filedesc}} ==\n'
    description = description + u'{{Information\n'
    description = description + u'|description={{en|1=' + metadata.get('fulldescription') + u'}}\n'
    description = description + u'|date=' + metadata.get('date') + u'\n' # MM/DD/YYYY
    description = description + u'|source={{Navy News Service|' + str(photo_id) + u'}}\n'
    description = description + u'|author=' + metadata.get('author') + u'\n'
    description = description + u'|permission=\n'
    description = description + u'|other_versions=\n'
    description = description + u'|other_fields=\n'
    description = description + u'}}\n'
    description = description + u'\n'
    description = description + u'== {{int:license}} ==\n'
    description = description + u'{{PD-USGov-Military-Navy}}\n'
    description = description + u'\n'
    description = description + u'[[Category:Images from US Navy, location ' + metadata.get('location') + u']]\n'
    #else:
    #	description = description + u'{{Uncategorized-navy}}\n'
    #description = description + u''

    return description

def buildTitle(photo_id, metadata):
    '''
    Build a valid title for the image to be uploaded to.
    '''
    description = metadata['shortdescription']
    if len(description)>200: description = description[0 : 200]

    title = metadata['navyid'] + u'_' + description + '.jpg'

    title = re.sub(u"[<{\\[]", u"(", title)
    title = re.sub(u"[>}\\]]", u")", title)
    title = re.sub(u"[ _]?\\(!\\)", u"", title)
    title = re.sub(u",:[ _]", u", ", title)
    title = re.sub(u"[;:][ _]", u", ", title)
    title = re.sub(u"[\t\n ]+", u" ", title)
    title = re.sub(u"[\r\n ]+", u" ", title)
    title = re.sub(u"[\n]+", u"", title)
    title = re.sub(u"[?!]([.\"]|$)", u"\\1", title)
    title = re.sub(u"[&#%?!]", u"^", title)
    title = re.sub(u"[;]", u",", title)
    title = re.sub(u"[/+\\\\:]", u"-", title)
    title = re.sub(u"--+", u"-", title)
    title = re.sub(u",,+", u",", title)
    title = re.sub(u"[-,^]([.]|$)", u"\\1", title)
    title = title.replace(u" ", u"_")
    title = title.replace(u"..", u".")
    title = title.replace(u"._.", u".")
    
    #print title
    return title

def processPhoto(photo_id):
    '''
    Work on a single photo at 
    http://www.navy.mil/view_single.asp?id=<photo_id>    
    get the metadata, check for dupes, build description, upload the image
    '''

    # Get all the metadata
    metadata = getMetadata(photo_id)
    
    if not metadata:
        #Incorrect photo_id
        return

    photo = downloadPhoto(metadata['url'])

    duplicates = findDuplicateImages(photo)
    # We don't want to upload tupes
    if duplicates:
        wikipedia.output(u'Found duplicate image at %s' % duplicates.pop())
        return
    
    title = buildTitle(photo_id, metadata)
    description = buildDescription(photo_id, metadata)
    #print description

    bot = upload.UploadRobot(metadata['url'], description=description, useFilename=title, keepFilename=True, verifyDescription=False, targetSite = wikipedia.getSite('commons', 'commons'))
    bot.upload_image(debug=False)

def processPhotos(start_id=0, end_id=80000):
    '''
    Loop over a bunch of images
    '''
    for i in range(start_id, end_id):
        processPhoto(photo_id=i)
        

def main(args):
    '''
    Main loop.
    '''
    start_id = 0
    end_id   = 80000
    for arg in wikipedia.handleArgs():
        if arg.startswith('-start_id'):
            if len(arg) == 9:
                start_id = wikipedia.input(u'What is the id of the photo you want to start at?')
            else:
                start_id = arg[10:]
        elif arg.startswith('-end_id'):
            if len(arg) == 7:
                end_id = wikipedia.input(u'What is the id of the photo you want to end at?')
            else:
                end_id = arg[8:]
                
    processPhotos(int(start_id), int(end_id))
         
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
