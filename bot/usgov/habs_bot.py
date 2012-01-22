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
import os.path, subprocess
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
    filename = u'/tmp/habs_image.tif'
    f = open(filename, 'wrb')
    f.truncate(0)
    f.write(imageFile)
    f.close()
    return filename

def findDuplicateImages(filename, site = wikipedia.getSite(u'commons', u'commons')):
    '''
    Takes the photo, calculates the SHA1 hash and asks the mediawiki api for a list of duplicates.

    TODO: Add exception handling, fix site thing
    '''
    f = open(filename, 'rb')
    data = f.read()
    hashObject = hashlib.sha1()
    hashObject.update(data) 
    f.close()
    return site.getFilesFromAnHash(base64.b16encode(hashObject.digest()))

def getMetadata(url):
    '''
    Get all the metadata for a single image and store it in the photoinfo dict
    '''
    metadata = {}

    imagePage = urllib.urlopen(url)
    data = imagePage.read()
    soup = BeautifulSoup(data)    
    tiflink = soup.find('a', href=re.compile('http://lcweb2.loc.gov/pnp/habshaer/.*\.tif'))
    if not tiflink:
	#print u'Not found at %s' %(url,)
	return False
    metadata['tifurl'] = tiflink.get('href')
   
    soup = BeautifulSoup(data)
    # imagelinks = soup.findAll('a', href=re.compile('http://www.loc.gov/pictures/collection/hh/item/.*'))
    metafields = soup.findAll('meta')#, attribname=re.compile('dc.*'))

    for metafield in metafields:
	name = metafield.get('name')
	content = metafield.get('content')
	if name:
	    if name==u'dc.identifier' and content.startswith(u'http://hdl.loc.gov/loc.pnp/'):
		metadata[name]=content
		metadata[u'identifier']=content.replace(u'http://hdl.loc.gov/loc.pnp/', u'')

	    elif name.startswith(u'dc.'):
		metadata[name]=content
    # Do something with county extraction
    
    match=re.match(u'^.*,(?P<county>[^,]+),(?P<state>[^,]+)', metadata['dc.title'], re.DOTALL)
    if match:
	metadata[u'county'] = match.group(u'county').strip()
	metadata[u'state'] = match.group(u'state').strip()

    metadata[u'basefilename'] = getBaseTitle(metadata)
    return metadata

def getDescription(metadata):
    '''
    Generate a description for a file
    '''
		    
    description = u'{{subst:User:Multichill/HABS|subst=subst:\n'
    for key, value in metadata.iteritems():
	description = description + u'|' + key + u'=%(' + key + u')s\n'
    description = description + u'}}\n'
	
    return description % metadata

def getBaseTitle(metadata):
    '''
    Build a valid title for the image to be uploaded to.
    '''
    title = metadata['dc.title']
    if len(title)>120:
	title = title[0 : 120]
	title = title.strip()

    if title.startswith(u' - '):
	title = title[3:]
    identifier = metadata['identifier'].replace(u'/', u'.')

    title = u'%s_-_LOC_-_%s' % (title, identifier)

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
    
    return title


def makeJpgFromTif(sourcetif, destjpg):
    if os.path.exists(destjpg):
	# File already exists, delete it
	os.remove(destjpg)
    cmd = [u'convert', sourcetif, '-quality', '100', destjpg]
    subprocess.call(cmd)
    return

def processPhoto(url):
    '''
    Work on a single photo at 
    http://www.navy.mil/view_single.asp?id=<photo_id>    
    get the metadata, check for dupes, build description, upload the image
    '''
    print url

    # Get all the metadata (this includes the suggested title)
    metadata = getMetadata(url)
    if not metadata:
	# No image at the page
	return False

    site = wikipedia.getSite('commons', 'commons')

    # Check if the .tif exists
    tiffilename = metadata[u'basefilename'] + u'.tif'
    tifImagePage = wikipedia.Page(site, u'File:' + tiffilename)
    tifImageExists = tifImagePage.exists()
    wikipedia.output(tiffilename)

    # Check if the .jpg exists
    jpgfilename = metadata[u'basefilename'] + u'.jpg'
    jpgImagePage = wikipedia.Page(site, u'File:' + jpgfilename)
    jpgImageExists = jpgImagePage.exists()
    wikipedia.output(jpgfilename)

    # If both exist with our names, just return
    if tifImageExists and jpgImageExists:
	wikipedia.output(u'The .tif and .jpg file already exist, skipping')
	return True

    if jpgImageExists:
	wikipedia.output(u'The .jpg file already exist, assuming the .tif is also online already, skipping')
	return True

    # Download the tif file to a temp dir
    tmptiffile = downloadPhoto(metadata['tifurl'])

    # If the tif already exists under our name or another name, store it
    if not tifImageExists:
	duplicates = findDuplicateImages(tmptiffile)
	if duplicates:
	    tiffilename = duplicates.pop()
	    wikipedia.output(u'Found duplicate image at %s' % tiffilename)
	    tifImageExists = True

    # If both exists with the tif a different name, just return
    if tifImageExists and jpgImageExists:
	wikipedia.output(u'The .tif exists with a diferent name and the .jpg file already exists too, skipping')
	return True

    # Update the metadata with the filenames we figured out. This is used for other_versions
    metadata['tiffilename'] = tiffilename.replace(u'_', u' ')
    metadata['jpgfilename'] = jpgfilename.replace(u'_', u' ')

    # Time to build the description
    description = getDescription(metadata)


    # If the tif image is not already online, upload it:
    if not tifImageExists:
	tifbot = upload.UploadRobot(tmptiffile, description=description, useFilename=tiffilename, keepFilename=True, verifyDescription=False, targetSite = site)
	#wikipedia.output(met)
	#wikipedia.output(description)
	tifbot.upload_image(debug=False)
    # If the jpg image is not already online, convert it and upload it:
    if not jpgImageExists:
	makeJpgFromTif(tmptiffile, u'/tmp/habs_image.jpg')
	jpgbot = upload.UploadRobot(u'/tmp/habs_image.jpg', description=description, useFilename=jpgfilename, keepFilename=True, verifyDescription=False, targetSite = site)
	wikipedia.output(metadata['jpgfilename'])
	wikipedia.output(description)
	jpgbot.upload_image(debug=False)

    #wikipedia.output(title)
    #wikipedia.output(description)

    #bot = upload.UploadRobot(metadata['tifurl'], description=description, useFilename=title, keepFilename=True, verifyDescription=False, targetSite = wikipedia.getSite('commons', 'commons'))
    #bot.upload_image(debug=False)
    #return True

def processSearchPage(page_id):
    #url = 'http://www.loc.gov/pictures/collection/hh/item/ak0003.color.570352c/'
    url = 'http://www.loc.gov/pictures/search/?fa=displayed%%3Aanywhere&sp=%s&co=hh&st=list' %(str(page_id),)
    #url = 'http://www.loc.gov/pictures/search/?fa=displayed%3Aanywhere&sp=18473&co=hh&st=list'

    imageurls = set()

    searchPage = urllib.urlopen(url)
    data = searchPage.read()
    soup = BeautifulSoup(data)
    #allTags = soup.findAll(True)
    imagelinks = soup.findAll('a', href=re.compile('http://www.loc.gov/pictures/collection/hh/item/.*'))
    
    # First collect all links. Set will remove the dupes
    for imagelink in imagelinks:
	imageurls.add(imagelink.get('href'))
    # Now work on the actual urls
    for imageurl in imageurls:
	processPhoto(imageurl)


def processSearchPages(start_id=1, end_id=20000):
    '''
    Loop over a bunch of images
    '''
    last_id = start_id
    for i in range(start_id, end_id):
        success = processSearchPage(page_id=i)
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
    start_id = 1
    end_id   = 18473
    single_id = 0
    #latest = False
    #updaterun = False
    site = wikipedia.getSite('commons', 'commons')
    #updatePage = wikipedia.Page(site, u'User:BotMultichillT/Navy_latest') 
    #interval=100

    for arg in wikipedia.handleArgs():
        if arg.startswith('-start_id'):
            if len(arg) == 9:
                start_id = wikipedia.input(u'What is the id of the search page you want to start at?')
            else:
                start_id = arg[10:]
        elif arg.startswith('-end_id'):
            if len(arg) == 7:
                end_id = wikipedia.input(u'What is the id of the search page you want to end at?')
            else:
                end_id = arg[8:]
	elif arg.startswith('-id'):
	    if len(arg) == 3:
		single_id = wikipedia.input(u'What is the id of the search page you want to transfer?')
	    else:
		single_id = arg[4:]

    if single_id > 0:
	processSearchPage(page_id=int(single_id))
    else:       
	last_id = processSearchPages(int(start_id), int(end_id))

         
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
