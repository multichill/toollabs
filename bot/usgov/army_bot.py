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

def getMetadata(photo):
    '''
    Get all the metadata for a single image and store it in the photoinfo dict
    '''
    photoinfo = photo
     
    armyPage = urllib.urlopen(photo.get('url'))

    data = armyPage.read()

    soup = BeautifulSoup(data)

    if soup.find("title"):
	if soup.find("title").contents:
	    photoinfo['title'] = soup.find("title").contents[0]
	else:
	    photoinfo['title'] = u''
    if soup.find("meta", {'name' : 'description'}):
	photoinfo['description'] = soup.find("meta", {'name' : 'description'}).get('content')
    if soup.find("meta", {'name' : 'author'}):
        photoinfo['author'] = soup.find("meta", {'name' : 'author'}).get('content')
    if soup.find("meta", {'name' : 'imageURL'}):
        photoinfo['imageURL'] = soup.find("meta", {'name' : 'imageURL'}).get('content')
    if soup.find("meta", {'name' : 'date'}):
        photoinfo['date'] = soup.find("meta", {'name' : 'date'}).get('content')
    
    if photoinfo.get('description') and photoinfo.get('author') and photoinfo.get('imageURL'):
	photoinfo['orgimage'] = photoinfo.get('imageURL'). replace(u'size4-', '') 
	#print photoinfo
	return photoinfo
    else:
	# Incorrect photo_id
	return False

def buildDescription(metadata):
    '''
    Create the description of the image based on the metadata
    '''
    description = u''

    description = description + u'== {{int:filedesc}} ==\n'
    description = description + u'{{Information\n'
    description = description + u'|description={{en|1=' + metadata.get('description') + u'}}\n'
    description = description + u'|date=' + metadata.get('date') + u'\n' # Isoformat
    description = description + u'|source=[' + metadata.get('url') + ' United States Army]\n'
    if not (metadata.get('author')==u''):
	description = description + u'|author=' + metadata.get('author') + u'\n'
    else:
	description = description + u'|author=Photo Courtesy of U.S. Army\n'
    description = description + u'|permission=\n'
    description = description + u'|other_versions=\n'
    description = description + u'|other_fields=\n'
    description = description + u'}}\n'
    description = description + u'\n'
    description = description + u'== {{int:license}} ==\n'
    description = description + u'{{PD-USGov-Military-Army}}\n'
    description = description + u'\n'
    description = description + u'{{Uncategorized-Army|year={{subst:CURRENTYEAR}}|month={{subst:CURRENTMONTHNAME}}|day={{subst:CURRENTDAY}}}}\n'

    return description

def buildTitle(metadata):
    '''
    Build a valid title for the image to be uploaded to.
    '''
    if not (metadata['title'] == u''):
	description = metadata['title']
    else:
	description = metadata['description']
    if len(description)>200:
	description = description[0 : 200]

    title = u'US_Army_' + metadata['id'] + u'_' + description + '.jpg'

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
    
    return title

def processPhoto(photo):
    '''
    Work on a single photo at 
    http://www.army.mil/-images/<year>/<month>/<day>/<id>/
    get the metadata, check for dupes, build description, upload the image
    '''
    #print photo.get('url')

    # Get all the metadata
    metadata = getMetadata(photo)

    if not metadata:
        #Incorrect photo_id
        return

    photo = downloadPhoto(metadata['orgimage'])

    duplicates = findDuplicateImages(photo)
    #duplicates = False
    # We don't want to upload tupes
    if duplicates:
        wikipedia.output(u'Found duplicate image at %s' % duplicates.pop())
        return
    
    title = buildTitle(metadata)
    description = buildDescription(metadata)

    #wikipedia.output(title)
    #wikipedia.output(description)

    try:
	bot = upload.UploadRobot(metadata['orgimage'], description=description, useFilename=title, keepFilename=True, verifyDescription=False, targetSite = wikipedia.getSite('commons', 'commons'))
	bot.upload_image(debug=False)
    except wikipedia.PageNotFound:
	#Image missing? Just skip it
	pass

def getLinksInGallery(per=100, page=1):
    result = []
    url = 'http://search.ahp.us.army.mil/search/images/?per=' + str(per) + '&page=' + str(page)

    gotData = False

    while not gotData:
	try:
	    galleryPage = urllib.urlopen(url)

	    data = galleryPage.read()
	    gotData = True
	except socket.error:
	    #Sleep 10 seconds
	    wikipedia.output(u'Socket error while loading gallery. Zzzzzz')
	    time.sleep(10)
	
    linkregex = u'<a href="(?P<url>http://www.army.mil/-images/(?P<year>\d\d\d\d)/(?P<month>\d\d)/(?P<day>\d\d)/(?P<id>\d+)/)">'
    matches = re.finditer(linkregex, data)
    if matches:
	for match in matches:
	    imagepage = {}
	    imagepage['url'] = match.group('url')
	    imagepage['year'] = match.group('year')
	    imagepage['month'] = match.group('month')
	    imagepage['day'] = match.group('day')
	    imagepage['id'] = match.group('id')
	    result.append(imagepage)
    return result
    #soup = BeautifulSoup(data)

def processGalleries(start_page=1, end_page=500, per=100):
    for i in range(start_page, end_page):
	for photo in getLinksInGallery(per, i):
	    processPhoto(photo) 

def main(args):
    '''
    Main loop.
    '''
    start_page = 0
    end_page = 5
    per = 100
    for arg in wikipedia.handleArgs():
        if arg.startswith('-start_page'):
            if len(arg) == 11:
                start_page = wikipedia.input(u'What is the id of the photo you want to start at?')
            else:
                start_page = arg[12:]
        elif arg.startswith('-end_page'):
            if len(arg) == 9:
                end_page = wikipedia.input(u'What is the id of the photo you want to end at?')
            else:
                end_page = arg[10:]
	elif arg.startswith('-per'):
	    if len(arg) == 4:
		per = wikipedia.input(u'How much images per page?')
	    else:
		per = arg[5:]

    processGalleries(int(start_page), int(end_page), int(per))
         
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
