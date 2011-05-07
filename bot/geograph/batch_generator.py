#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot to upload geograph images from the Toolserver to Commons

'''
import sys, os.path, hashlib, base64, MySQLdb, glob, re, urllib, time
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, query
import shutil
import geograph_lib


def findDuplicateImages(filename, site = wikipedia.getSite(u'commons', u'commons')):
    '''
    Takes the photo, calculates the SHA1 hash and asks the mediawiki api for a list of duplicates.

    TODO: Add exception handling, fix site thing
    '''
    f = open(filename, 'rb')

    hashObject = hashlib.sha1()
    hashObject.update(f.read(-1))
    return site.getFilesFromAnHash(base64.b16encode(hashObject.digest()))

def filterSourceFilenames(sourcefilenames):
    '''
    Filter out thumbnail if a original file exists. 
    '''
    for sourcefilename in sourcefilenames:
	if sourcefilename.endswith(u'_original.jpg'):
	    # We have a high res original, remove the down scaled version
	    toremove = sourcefilename.replace(u'_original.jpg', u'.jpg')
	    sourcefilenames.remove(toremove)
	elif sourcefilename.endswith(u'_60XX60.jpg'):
	    # This is a crappy thumb. Just remove it
	    sourcefilenames.remove(sourcefilename)
    sourcefilenames.sort()
    return sourcefilenames

def getFileId(file):
    dirname = os.path.dirname(file)
    filename = os.path.basename(file)
    baseFilename, extension = os.path.splitext(filename)
    (id, sep, remaining) = baseFilename.partition(u'_')
    return int(id)

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

    start_id=0    

    conn = None
    cursor = None
    (conn, cursor) = geograph_lib.connectDatabase()

    conn2 = None
    cursor2 = None
    (conn2, cursor2) = geograph_lib.connectDatabase2('sql-s2.toolserver.org', u'u_multichill_commons_categories_p')

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
		    sourcefilenames = glob.glob(sourcedir + subdir + u"/*.jpg")
		    sourcefilenames = filterSourceFilenames(sourcefilenames)
		    for sourcefilename in sourcefilenames:
			# First get the file id
			fileId = getFileId(sourcefilename)
			if fileId>=start_id:
			    wikipedia.output(str(fileId))

			    duplicates = findDuplicateImages(sourcefilename)
			    if duplicates:
				wikipedia.output(u'Found duplicate image at %s' % duplicates.pop())
			    else:
				#Get metadata
				metadata = geograph_lib.getMetadata(fileId, cursor)

				#Check if we got metadata
				if metadata:

				    #Get description
				    description = geograph_lib.getDescription(metadata)

				    # The hard part, find suitable categories
				    # categories =  geograph_lib.getCategories(metadata, cursor, cursor2)
				    categories = '{{Uncategorized-Geograph|gridref=%s|year={{subst:CURRENTYEAR}}|month={{subst:CURRENTMONTHNAME}}|day={{subst:CURRENTDAY}}}}\n' % (metadata.get('grid_reference'),)
				    #print categories
				    description = description + categories

				    wikipedia.output(description)

				    #Get destinationfilename
				    destinationFilename = geograph_lib.getTitle(metadata)
				
				    #Copy file to destination dir
				    shutil.copy(unicode(sourcefilename), unicode(destinationdir + destinationFilename + u'.jpg'))
				    #And save the description as well
				    outputDescriptionFile(destinationdir + destinationFilename + u'.txt', description)
 
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
