#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot to upload all image from the site of the US Air Force ( http://www.af.mil/photos/mediagallery.asp )

Single image:
http://www.af.mil/photos/media_view.asp?id=<the id>

Two modes:
1. Work on one or more galleries at Commons
2. Work from 0 to a very high number (no categorization)

Screen scraping is done with BeautifulSoup so this needs to be installed.

'''
import sys, os, StringIO, hashlib, base64
import os.path
import urllib, re
from urllib import FancyURLopener
from datetime import datetime
from BeautifulSoup import BeautifulSoup 
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, upload, pagegenerators
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
    metadata = {}
     
    url = 'http://www.af.mil/photos/media_view.asp?id=' + str(photo_id)
    baseurl = u'http://www.af.mil'
    afidRegex = u'/shared/media/photodb/photos/(.*)\.[jJ][pP][gG]'
    imagePage = urllib.urlopen(url)

    data = imagePage.read()

    soup = BeautifulSoup(data)

    if soup.find("a", {'class' : 'mainlink_xxlarge'}):
	if soup.find("a", {'class' : 'mainlink_xxlarge'}).get('href'):
	    path = soup.find("a", {'class' : 'mainlink_xxlarge'}).get('href')
	    metadata['url'] = baseurl + path
	    metadata['afid'] = re.sub(afidRegex, u'\\1', path) 
	if soup.find("a", {'class' : 'mainlink_xxlarge'}).string:
	    metadata['title'] = soup.find("a", {'class' : 'mainlink_xxlarge'}).string
	if soup.find("span", {'class' : 'maintext_large'}):
	    if soup.find("span", {'class' : 'maintext_large'}).string:
		metadata['description'] = soup.find("span", {'class' : 'maintext_large'}).string
	if metadata.get('description'):
	    metadata['author'] = getAuthor(metadata.get('description'))
	return metadata

    else:
	# Incorrect photo_id
	return False

def getAuthor(description):
    authorregex = []
    authorregex.append(u'^.*\(([^\)]+)\)$')
    authorregex.append(u'^.*(U.S. Air Force Photo.*)$')

    for regex in authorregex:
	match = re.match(regex, description.strip(), re.IGNORECASE|re.DOTALL)
	if match:
	    return match.group(1)

    #Nothing matched
    return u'U.S. Air Force photo<!-- Please update this from the description field-->'

def buildDescription(photo_id, metadata, category):
    '''
    Create the description of the image based on the metadata
    '''
    description = u''

    description = description + u'== {{int:filedesc}} ==\n'
    description = description + u'{{Information\n'
    description = description + u'|description={{en|1=' + metadata.get('description') + u'}}\n'
    description = description + u'|date=\n' # No dates known
    description = description + u'|source={{ID-USMil|' + metadata.get('afid') + u'|Air Force|url=http://www.af.mil/photos/media_view.asp?id=' + str(photo_id) + u'}}\n'
    description = description + u'|author=' + metadata.get('author') + u'\n'
    description = description + u'|permission=\n'
    description = description + u'|other_versions=\n'
    description = description + u'|other_fields=\n'
    description = description + u'}}\n'
    description = description + u'\n'
    description = description + u'== {{int:license}} ==\n'
    description = description + u'{{PD-USGov-Military-Air_Force}}\n'
    description = description + u'\n'
    description = description + u'[[Category:' + category + u']]\n'

    return description

def buildTitle(photo_id, metadata):
    '''
    Build a valid title for the image to be uploaded to.
    '''
    title = u'US_Air_Force ' + metadata.get('afid').strip()

    if metadata.get('title'):
	title = title + u'_' +  metadata.get('title').strip() + u'.jpg'
    elif metadata.get('description'):
	description = get('description') 
	if len(description)>200:
	    description = description[0 : 200]
	title = title + u'_' +  description.strip() + u'.jpg'
    else:
	title = title + u'.jpg'

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

def processGallery(id, category):
    '''
    Process the gallery with id.
    '''
    page = 1
    count = 100
    ids = []

    imageIdRegex = u'\<a class\="mainlink_medium" href\="http://www.af.mil/photos/media_email.asp?id\=(\d)+"\>E-mail a friend\</a\>'
    imageIdRegex = u'\<a class\="mainlink_medium" href\="http://www.af.mil/photos/media_email.asp\?id\=(\d+)"\>E-mail a friend\</a\>'

    more = True

    while more:
	# Pull the page
	url = 'http://www.af.mil/photos/mediagallery.asp?id=' + str(id) + '&page=' + str(page) + u'&count=' + str(count)
	galleryPage = urllib.urlopen(url)
	data = galleryPage.read()
	# Extract the ids and add them to the listi
	if re.search(imageIdRegex, data.decode('UTF-8')):
	    for match in re.finditer(imageIdRegex, data.decode('UTF-8')):
		imageId = match.group(1)
		ids.append(imageId)
	else:
	    more = False
	    # No matches
	    break

	# Raise page
	page = page + 1
    
    for imageId in ids:
	processPhoto(imageId, category)

def processCategory(page):
    '''
    Process a single category
    '''
    templates = page.templatesWithParams()
    fields = {}
    for (template, params) in templates:
	if template==u'Air Force header':
	    for param in params:
		#Split at =
		(field, sep, value) = param.partition(u'=')
		if not value==u'':
		    fields[field]=value.strip()
    # Process a gallery at the US Air Force site
    if fields.get('id'):
	if fields.get('subject'):
	    target = fields.get('subject')
	else:
	    target = page.titleWithoutNamespace()
    
	processGallery(fields.get('id'), target)

	# Mark the category as done so we can skip it later on
	oldtext = page.get()
	newtext = re.sub(u'\{\{Air Force header', u'{{Air Force header\n|done=~~~~', oldtext)
	comment = u'Transfered all images from http://www.af.mil/photos/mediagallery.asp?id=' + fields.get('id') + u' to [[Category:' + target + u']]'
	wikipedia.showDiff(oldtext, newtext)
	page.put(newtext, comment)

def processPhoto(photo_id, category=u''):
    '''
    Work on a single photo at 
    http://www.af.mil/photos/media_view.asp?id=<photo_id>    
    get the metadata, check for dupes, build description, upload the image
    '''

    # Get all the metadata
    metadata = getMetadata(photo_id)
    
    if not metadata:
        #Incorrect photo_id
        return False

    if metadata.get('author') and re.search(u'Courtesy', metadata.get('author'), re.I):
	#Courtesy photos are probably copyvios
	return False
    
    photo = downloadPhoto(metadata['url'])

    duplicates = findDuplicateImages(photo)
    #duplicates = False
    # We don't want to upload dupes
    if duplicates:
        wikipedia.output(u'Found duplicate image at %s' % duplicates.pop())
	# The file is at Commons so return True
        return True
    
    title = buildTitle(photo_id, metadata)

    description = buildDescription(photo_id, metadata, category)

    #wikipedia.output(title)
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

def main(args):
    '''
    Main loop.
    '''

    genFactory = pagegenerators.GeneratorFactory()    

    start_id = 0
    end_id   = 0
    updaterun = False
    site = wikipedia.getSite('commons', 'commons')
    wikipedia.setSite(site)
    updatePage = wikipedia.Page(site, u'User:BotMultichillT/Air_Force_latest') 
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
	elif arg==u'-updaterun':
	    updaterun = True
	elif arg.startswith('-interval'):
	    if len(arg) == 9:
		interval = wikipedia.input(u'What interval do you want to use?')
	    else:
		interval = arg[10:]
	else:
	    genFactory.handleArg(arg)
    generator = genFactory.getCombinedGenerator()
    # Do we have a pagenerator?
    if generator:
	for page in generator:
	    if page.namespace()==14:
		processCategory(page)

    # Is updaterun set?
    elif updaterun:
	start_id = int(updatePage.get())
	end_id = start_id + int(interval)
	last_id = processPhotos(int(start_id), int(end_id))
	comment = u'Worked from ' + str(start_id) + u' to ' + str(last_id)
	updatePage.put(str(last_id), comment)
	
    # Do we have a start_id and a end_id
    elif int(start_id) > 0 and int(end_id) > 0:
	last_id = processPhotos(int(start_id), int(end_id))
    # Use the default generator
    else:
	print "Screw this, will implement later"
         
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
