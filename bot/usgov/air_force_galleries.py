#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot to scrape all the air force galleries and to create a category structure.

The galleries are in this form:

http://www.af.mil/photos/mediagallery.asp?galleryID=12

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


def getMetadata(gallery_id):
    '''
    Get all the metadata for a single image and store it in the photoinfo dict
    '''
    metadata = {}
     
    url = 'http://www.af.mil/photos/mediagallery.asp?galleryID=' + str(gallery_id)
    galleryPage = urllib.urlopen(url)

    data = galleryPage.read()

    soup = BeautifulSoup(data)

    if not data.decode('UTF-8').find(u'There are no images in this gallery.')==-1:
	return
    
    ptag = []
    ptag.append(soup.find("a", {'class' : 'gallery_search_results' }))
    if ptag[0] and ptag[0].findNext("a", {'class' : 'gallery_search_results' }):
	ptag.append(ptag[0].findNext("a", {'class' : 'gallery_search_results' }))
	if ptag[1] and ptag[1].findNext("a", {'class' : 'gallery_search_results' }):
	    ptag.append(ptag[1].findNext("a", {'class' : 'gallery_search_results' }))
	    if ptag[2] and ptag[2].findNext("a", {'class' : 'gallery_search_results' }):
		ptag.append(ptag[2].findNext("a", {'class' : 'gallery_search_results' }))
   
    if ptag[0] and not ptag[0].string==u'Error Retrieving Gallery Name':
	metadata['id'] = ptag[len(ptag)-1].get('href').replace(u'/photos/mediagallery.asp?galleryID=', '')
	
	if len(ptag)==1:
	    metadata['title'] = ptag[0].string

	elif len(ptag)==2:
	    metadata['parent'] = ptag[0].string
	    metadata['title'] = ptag[1].string

	elif len(ptag)==3:
	    metadata['grandparent'] = ptag[0].string
	    metadata['parent'] = ptag[1].string
	    metadata['title'] = ptag[2].string

	elif len(ptag)==3:
	    metadata['greatgrandparent'] = ptag[0].string
	    metadata['grandparent'] = ptag[1].string
	    metadata['parent'] = ptag[2].string
	    metadata['title'] = ptag[3].string
	if metadata.get('title'):
	    return metadata

def processGallery(gallery_id):
    '''
    Work on a single gallery at
    http://www.af.mil/photos/mediagallery.asp?galleryID=<gallery_id> 
    get the metadata, build title, build description, create the category
    '''

    # Get all the metadata
    metadata = getMetadata(gallery_id)
    
    if not metadata:
        #Incorrect gallery_id
        return
    site = wikipedia.getSite('commons', 'commons')
    title = u'Category:Images from the US Air Force, ' + metadata.get('title')
    page = wikipedia.Page(site, title)
    comment = u'Creating temporary US Air Force category'

    if page.exists():
	return    

    description = u'{{Air Force header\n'
    description = description + u'|title=' + metadata.get('title') + u'\n'
    description = description + u'|id=' + metadata.get('id') + u'\n'
    if metadata.get('parent'):
	description = description + u'|parent=' + metadata.get('parent') + u'\n'
    if metadata.get('grandparent'):
	description = description + u'|grandparent=' + metadata.get('grandparent') + u'\n'
    if metadata.get('greatgrandparent'):
	description = description + u'|greatgrandparent=' + metadata.get('greatgrandparent') + u'\n'
    description = description + u'|subject=\n'
    description = description + u'}}\n'

    #wikipedia.output(title)
    #wikipedia.output(description)
    page.put(description, comment)

def processGalleries(start_id=0, end_id=9000):
    '''
    Loop over a bunch of galleries
    '''
    for i in range(start_id, end_id):
        processGallery(gallery_id=i)
        

def main(args):
    '''
    Main loop.
    '''
    start_id = 0
    end_id   = 9000
    for arg in wikipedia.handleArgs():
        if arg.startswith('-start_id'):
            if len(arg) == 9:
                start_id = wikipedia.input(u'What is the id of the gallery you want to start at?')
            else:
                start_id = arg[10:]
        elif arg.startswith('-end_id'):
            if len(arg) == 7:
                end_id = wikipedia.input(u'What is the id of the gallery you want to end at?')
            else:
                end_id = arg[8:]
                
    processGalleries(int(start_id), int(end_id))
         
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
