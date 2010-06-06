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

def processSquare(square, squares, scale, sourcedir, basefilename, destinationdir):
    '''
    Generate a description (same for jpg and tif) and copy all the files
    '''
    description = getDescription(square, squares, scale, basefilename)
    print description

    time.sleep(10)
    #outputDescriptionFile(destinationdir + basefilename + square + u'.txt', description) 

    # Copy the tif file
    #shutil.copy(unicode(sourcedir + square + u'.tif'), unicode(destinationdir + basefilename + square + u'.tif'))

    # Copy the jpg file
    #shutil.copy(unicode(sourcedir + square + u'.jpg'), unicode(destinationdir + basefilename + square + u'.jpg'))

def getDescription(square, squares, scale, basefilename):
    '''
    Create the description of the image based on the metadata
    '''
    description = u''
    
    description = description + u'{{subst:Commons:Batch uploading/Ordnance Survey/Template\n'
    description = description + u'|subst=subst:\n'
    description = description + u'|square=' + square + '\n'
    description = description + u'|scale=' + scale + '\n'
    description = description + u'|scale=' + basefilename.replace(u'_', u' ') + '\n'
    description = description + u'|nw_square=' + getNextSquare(getNextSquare(square, 'n'), u'w')  + '\n'
    description = description + u'|n_square=' + getNextSquare(currentSquare=square, direction='n')  + '\n'
    description = description + u'|ne_square=' + getNextSquare(getNextSquare(square, 'n'), u'e')  + '\n'
    description = description + u'|w_square=' + getNextSquare(square, 'w')  + '\n'
    description = description + u'|e_square=' + getNextSquare(square, 'e')  + '\n'
    description = description + u'|sw_square=' + getNextSquare(getNextSquare(square, 's'), u'w')  + '\n'
    description = description + u'|s_square=' + getNextSquare(square, 's')  + '\n'
    description = description + u'|se_square=' + getNextSquare(getNextSquare(square, 's'), u'e')  + '\n'
    description = description + u'}}\n'

    return description
    

def outputDescriptionFile(filename, description):
    f = open(filename, "w")
    f.write(description.encode("UTF-8"))
    f.close()
    return


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
	processSquare(square, squares, scale, sourcedir, basefilename, destinationdir)
	

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
