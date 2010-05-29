#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot to upload all images from the site of FEMA located at http://www.photolibrary.fema.gov/photolibrary/photo_search.do
The images have ids from 0 to about 43000 in October 2009.
Start and end can be controlled with -start_id and -end_id

Screen scraping is done with BeautifulSoup so this needs to be installed.

The bot skips images with a caption containing a line break.
See for example http://www.photolibrary.fema.gov/photolibrary/photo_details.do?id=9515

'''
import sys, os, StringIO, hashlib, base64
import os.path
import urllib, re
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

def getDate(datestring):
    '''
    Try to get a date from the string or return the string
    '''

    #MM/DD/YYYY
    usformat = u'%m/%d/%Y'
    isoformat = '%Y-%m-%d'
    if datestring:
	date = datetime.strptime(datestring, usformat)
	return date.strftime(isoformat)
    else:
	return u''

def getMetadata(photo_id):
    '''
    Get all the metadata for a single image and store it in the photoinfo dict
    '''
    photoinfo = {}
    photoinfo['Categories:'] = []
     
    params = {'id' : photo_id }
    tosend = urllib.urlencode(params)
    femaPage = urllib.urlopen("http://www.photolibrary.fema.gov/photolibrary/photo_details.do", tosend)
    data = femaPage.read()
    soup = BeautifulSoup(data)
    if soup.find('div', {'class' : 'caption'}) and soup.find('div', {'class' : 'caption'}).string:
        #print soup.find('div', {'class' : 'caption'}).string.strip()
        photoinfo['caption'] = soup.find('div', {'class' : 'caption'}).string.strip()
        photoinfo['title'] = soup.find('h1').string.strip()

        photoinfo2 = soup.find('div', {'class' : 'photoinfo2'}).find('table', {'summary' : 'table used for layout purposes only'})
        for row in photoinfo2.findAll("tr"):
            ths = row.findAll("th")
            tds = row.findAll("td")
            #print ths
            #print tds
            if ths[0] and tds[0]:
                if ths[0].string and tds[0].string:
                    photoinfo[ths[0].string] = tds[0].string
                    #print ths[0].string + ' - ' +  tds[0].string
		if len(ths) > 1 and len(tds) > 1:
                    if ths[1].string and tds[1].string:
                        photoinfo[ths[1].string] = tds[1].string
                        #print ths[1].string + ' - ' +  tds[1].string
                #Disasters or Categories
                else:
                    if row.th.string == u'Disasters:':
                        photoinfo[row.th.string] = row.td.a.string
                        #print row.th.string
                        #print row.td.a.string
                    if row.th.string == u'Categories:':
                        #print row.th.string
                        for item in row.td.contents:
                            if item.string:
                                if item.string.strip():                                    
                                    photoinfo['Categories:'].append(item.string.strip())

        return photoinfo
    else:
	#No caption found
        return False

def buildDescription(photo_id, metadata):
    '''
    Create the description of the image based on the metadata
    '''
    description = u''

    description = description + u'== {{int:filedesc}} ==\n'
    description = description + u'{{Information\n'
    description = description + u'|description={{en|1=' + metadata.get('caption') + u'}}\n'
    description = description + u'|date=' + getDate(metadata.get('Photo Date:')) + u'\n' # MM/DD/YYYY
    description = description + u'|source={{FEMA Photo Library|' + str(photo_id) + u'}}\n'
    description = description + u'|author=' + metadata.get('Photographer:') + u'\n'
    description = description + u'|permission=\n'
    description = description + u'|other_versions=\n'
    description = description + u'|other_fields=\n'
    description = description + u'}}\n'
    description = description + u'\n'
    description = description + u'== {{int:license}} ==\n'
    description = description + u'{{PD-USGov-FEMA}}\n'
    description = description + u'\n'
    if metadata.get('Disasters:'):    
        description = description + u'[[Category:Images from FEMA, disaster ' + metadata.get('Disasters:') + u']]\n'
    for cat in metadata.get('Categories:'):
        description = description + u'[[Category:Images from FEMA, category ' + cat + u']]\n'
    description = description + u''
    description = description + u''
    description = description + u''

    return description

def buildTitle(photo_id, metadata):
    '''
    Build a valid title for the image to be uploaded to.
    '''
    title = u'FEMA - ' + str(photo_id) + u' - ' + metadata['title'] + '.jpg'

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
    
    return title

def processPhoto(photo_id):
    '''
    Work on a single photo at 
    http://www.photolibrary.fema.gov/photolibrary/photo_details.do?id=<photo_id>    
    get the metadata, check for dupes, build description, upload the image
    '''
    print "Working on: " + str(photo_id)
    # Get all the metadata
    metadata = getMetadata(photo_id)
    if not metadata:
	print "Didn't find metadata at http://www.photolibrary.fema.gov/photolibrary/photo_details.do?id=" + str(photo_id)
        #Incorrect photo_id
        return

    photoUrl = u'http://www.fema.gov/photodata/original/' + str(photo_id) + '.jpg'
    photo = downloadPhoto(photoUrl)

    duplicates = findDuplicateImages(photo)
    # We don't want to upload tupes
    if duplicates:
        wikipedia.output(u'Found duplicate image at %s' % duplicates.pop())
        return
    
    title = buildTitle(photo_id, metadata)
    description = buildDescription(photo_id, metadata)

    bot = upload.UploadRobot(photoUrl, description=description, useFilename=title, keepFilename=True, verifyDescription=False, targetSite = wikipedia.getSite('commons', 'commons'))
    bot.upload_image(debug=False)

def processPhotos(start_id=0, end_id=45000):
    '''
    Loop over a bunch of images
    '''
    for i in range(start_id, end_id):
        processPhoto(photo_id=i)

def processLatestPhotos():
    '''
    Upload the photos at http://www.photolibrary.fema.gov/photolibrary/rss.do
    '''
    url = 'http://www.photolibrary.fema.gov/photolibrary/rss.do'
    latestPage = urllib.urlopen(url)
    data = latestPage.read()

    regex = u'<guid>http://www.photolibrary.fema.gov/photolibrary/photo_details.do\?id=(\d+)</guid>'
    
    for match in re.finditer (regex, data):
        processPhoto(int(match.group(1)))


def main(args):
    '''
    Main loop.
    '''
    start_id = 0
    end_id   = 45000
    latest = False
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
	elif arg==u'-latest':
            latest = True
    
    if latest:
	processLatestPhotos()
    else:
	processPhotos(int(start_id), int(end_id))
         
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
