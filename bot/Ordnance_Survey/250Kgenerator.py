#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot to upload geograph images from the Toolserver to Commons

'''
import sys, os.path, hashlib, base64, MySQLdb, glob, re, urllib, time
import OSlib
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, query
import xml.etree.ElementTree, shutil
import imagerecat
import MySQLdb.converters

def main(args):
    '''
    Main loop.
    '''
    site = wikipedia.getSite(u'commons', u'commons')
    wikipedia.setSite(site)

    sourcedir=u'/mnt/user-store/OS_OpenData/1_250_000_Scale_Raster/data/'
    destinationdir=u'/mnt/user-store/OS_OpenData/1_250_000_Scale_Raster/output/'
    basefilename=u'Ordnance_Survey_1-250000_-_'
    scale=u'250.000'
    squares = []

    for sourcefilename in glob.glob(sourcedir + u"*.tif"):
	square = sourcefilename.replace(sourcedir, u'').replace(u'.tif', u'')
	squares.append(square)

    for square in squares:
	print square
	OSlib.processSquare(square, squares, scale, sourcedir, basefilename, destinationdir)
	

    '''

    if(len(args) >1):
	if len(args) > 2:
	    start_id=int(args[2])
	sourcedir = args[0]
	destinationdir = args[1]
	if os.path.isdir(sourcedir) and os.path.isdir(destinationdir):
	    #print sourcedir
	    for subdir in os.listdir(sourcedir):
		#print subdir
		if os.path.isdir(sourcedir + subdir):
		    #print subdir
		    for sourcefilename in glob.glob(sourcedir + subdir + u"/*.jpg"):
			# First get the file id
			fileId = getFileId(sourcefilename)
			if fileId>=start_id:
			    wikipedia.output(str(fileId))

			    duplicates = findDuplicateImages(sourcefilename)
			    if duplicates:
				wikipedia.output(u'Found duplicate image at %s' % duplicates.pop())
			    else:
				#Get metadata
				metadata = getMetadata(fileId, cursor)

				#Check if we got metadata
				if metadata:

				    #Get description
				    description = getDescription(metadata)

				    # The hard part, find suitable categories
				    categories =  getCategories(metadata, cursor, cursor2)
				    #print categories
				    description = description + categories

				    wikipedia.output(description)

				    #Get destinationfilename
				    destinationFilename = getTitle(metadata)
				
				    #Copy file to destination dir
				    shutil.copy(unicode(sourcefilename), unicode(destinationdir + destinationFilename + u'.jpg'))
				    #And save the description as well
				    outputDescriptionFile(destinationdir + destinationFilename + u'.txt', description)

    '''
 
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
