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
    if soup.find("meta", {'name' : 'MED_RES_IMAGE'}):
	photoinfo['url_medium'] = soup.find("meta", {'name' : 'MED_RES_IMAGE'}).get('content')
	
    if soup.find("meta", {'name' : 'DESCRIPTION'}):
	photoinfo['fulldescription'] = soup.find("meta", {'name' : 'DESCRIPTION'}).get('content')
    if soup.find("meta", {'name' : 'ALT_TAG'}):
	photoinfo['shortdescription'] = soup.find("meta", {'name' : 'ALT_TAG'}).get('content')

    if photoinfo.get('url') and photoinfo.get('fulldescription') and photoinfo.get('shortdescription'):
	photoinfo['navyid'] = getNavyIdentifier(photoinfo['url'])
	photoinfo['description'] = re.sub(u'\w*-\w*-\w*-\w*[\r\n\s]+', u'', photoinfo['fulldescription'])
	#photoinfo['description'] = cleanDescription(photoinfo['fulldescription'])
	photoinfo['author'] = getAuthor(photoinfo['fulldescription'])
	(photoinfo['date'], photoinfo['location']) = getDateAndLocation(photoinfo['fulldescription'])
	photoinfo['ship'] = getShip(photoinfo['fulldescription'])
	
	return photoinfo
    else:
	# Incorrect photo_id
	return False

def getNavyIdentifier(url):
    result = url
    result = result.replace(u'http://www.news.navy.mil/management/photodb/photos/', u'')
    result = result.replace(u'.jpg', u'')
    return result

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

def getShip(description):
    # Try to find a USS ...(...) ship
    shipRegex = u'USS [^\(]{1,25}\([^\)]+\)'

    matches = re.search(shipRegex, description, re.I)
    if matches:
	#print matches.group(0)
        return matches.group(0)
    else:
	# No ship found
        return u''

def getDateAndLocation(description):
    '''
    Get date and location.
    Is one regex so I might as well build one function for it
    '''
    date = u''
    location = u'unknown'
    #dateregex = u'\(([^\)]+\d\d\d\d)\)'
    #locationregex = u'^([^\(^\r^\n]+)\(([^\)]+\d\d\d\d)\)'
    regexlist = []
    regexlist.append(u'^([^\(^\r^\n]+)\(([^\)]+\d\d\d\d)\)')
    regexlist.append(u'^([^\r^\n]+)\s([^\s]* \d{1,2}, \d\d\d\d)\s+(-|--|&ndash)')
    #matches = re.search(regex, description, re.MULTILINE)
    for regex in regexlist:
        matches = re.search(regex, description, re.MULTILINE)
        if  matches:
	    date = matches.group(2)
	    location = matches.group(1)
	    location = location.strip()
	    location = location.rstrip(',')
	    location = re.sub(u'\w*-\w*-\w*-\w*\s', u'', location)
            return (date, location)
    return (date, location)


def buildDescription(photo_id, metadata):
    '''
    Create the description of the image based on the metadata
    '''
    description = u''

    description = description + u'== {{int:filedesc}} ==\n'
    description = description + u'{{Information\n'
    description = description + u'|description={{en|1=' + metadata.get('description') + u'}}\n'
    description = description + u'|date=' + metadata.get('date') + u'\n' # MM/DD/YYYY
    #description = description + u'|source={{Navy News Service|' + str(photo_id) + u'}}\n'
    description = description + u'|source={{ID-USMil|' + metadata.get('navyid') + u'|Navy|url=http://www.navy.mil/view_single.asp?id=' + str(photo_id) + u'}}\n'
    description = description + u'|author=' + metadata.get('author') + u'\n'
    description = description + u'|permission=\n'
    description = description + u'|other_versions=\n'
    description = description + u'|other_fields=\n'
    description = description + u'}}\n'
    description = description + u'\n'
    description = description + u'== {{int:license}} ==\n'
    description = description + u'{{PD-USGov-Military-Navy}}\n'
    description = description + u'\n'
    if not metadata.get('ship')==u'':
	description = description + getShipCategory(metadata.get('ship')) + u'\n'
    else:
	description = description + u'[[Category:Images from US Navy, location ' + metadata.get('location') + u']]\n'
    #else:
    #	description = description + u'{{Uncategorized-navy}}\n'
    #description = description + u''

    return description

def getShipCategory(ship):
    '''
    Try to find a ship category based on the ship's name
    '''
    cleanedUpShip = re.sub(u'(USS.*)\((\w+)\s(\w+)\)', u'\\1(\\2-\\3)', ship)
    shipPage = wikipedia.Page(wikipedia.getSite('commons', 'commons'), u'Category:' + cleanedUpShip)
    if shipPage.exists():
	return u'[[Category:' + cleanedUpShip + u']]'	
    # No category found, add temp one
    return u'[[Category:Images from US Navy, ship ' + ship + u']]'

def buildTitle(photo_id, metadata):
    '''
    Build a valid title for the image to be uploaded to.
    '''
    description = metadata['shortdescription']
    if len(description)>200:
	description = description[0 : 200]
    #elif len(description) < 10:
    #	#Stupid title blacklist
    #	description = u'navy_' + description

    title = u'US_Navy_' + metadata['navyid'] + u'_' + description + '.jpg'

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
    title = title.replace(u"__", u"_")
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
        return False

    photo = downloadPhoto(metadata['url'])

    duplicates = findDuplicateImages(photo)
    #duplicates = False
    # We don't want to upload tupes
    if duplicates:
        wikipedia.output(u'Found duplicate image at %s' % duplicates.pop())
	# The file is at Commons so return True
        return True
    
    title = buildTitle(photo_id, metadata)
    description = buildDescription(photo_id, metadata)

    wikipedia.output(title)
    #wikipedia.output(description)

    try:
	bot = upload.UploadRobot(metadata['url'], description=description, useFilename=title, keepFilename=True, verifyDescription=False, targetSite = wikipedia.getSite('commons', 'commons'))
	bot.upload_image(debug=False)
	return True
    except wikipedia.PageNotFound:
	#High res is missing, just skip it
	pass
    return False

def processPhotos(start_id=0, end_id=80000):
    '''
    Loop over a bunch of images
    '''
    last_id = start_id
    for i in range(start_id, end_id):
        success = processPhoto(photo_id=i)
	if success:
	    last_id=i
    return last_id

def processLatestPhotos():
    '''
    Upload the photos at http://www.navy.mil/view_photos_top.asp?sort_type=0&sort_row=8
    '''
    url = 'http://www.navy.mil/view_photos_top.asp?sort_type=0&sort_row=8'
    latestPage = urllib.urlopen(url)
    data = latestPage.read()

    regex = u'<td valign="bottom"><a href="view_single.asp\?id=(\d+)"><img border=0'

    for match in re.finditer (regex, data):
	processPhoto(int(match.group(1)))

def main(args):
    '''
    Main loop.
    '''
    start_id = 0
    end_id   = 80000
    single_id = 0
    latest = False
    updaterun = False
    site = wikipedia.getSite('commons', 'commons')
    updatePage = wikipedia.Page(site, u'User:BotMultichillT/Navy_latest') 
    interval=100

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
	elif arg.startswith('-id'):
	    if len(arg) == 3:
		single_id = wikipedia.input(u'What is the id of the photo you want to transfer?')
	    else:
		single_id = arg[4:]
	elif arg==u'-latest':
	    latest = True
	elif arg==u'-updaterun':
	    updaterun = True
	elif arg.startswith('-interval'):
	    if len(arg) == 9:
		interval = wikipedia.input(u'What interval do you want to use?')
	    else:
		interval = arg[10:]

    if single_id > 0:
	processPhoto(photo_id=int(single_id))
    elif latest:
	processLatestPhotos()
    else:
	if updaterun:
	    start_id = int(updatePage.get())
	    end_id = start_id + int(interval)
                
	last_id = processPhotos(int(start_id), int(end_id))

	if updaterun:
	    comment = u'Worked from ' + str(start_id) + u' to ' + str(last_id)
	    updatePage.put(str(last_id), comment)
         
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
