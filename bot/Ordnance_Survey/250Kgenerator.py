#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot to upload geograph images from the Toolserver to Commons

'''
import sys, os.path, hashlib, base64, MySQLdb, glob, re, urllib, time
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, query
import xml.etree.ElementTree, shutil
import imagerecat
import MySQLdb.converters

def getDescription(metadata):
    '''
    Create the description of the image based on the metadata
    '''
    description = u''

    description = description + u'== {{int:filedesc}} ==\n'
    description = description + u'{{Information\n'
    informationDescription = metadata.get('title').strip()
    if informationDescription[-1:].isalnum():
	informationDescription = informationDescription + u'.'
    if not metadata['comment']==u'':
	informationDescription = informationDescription + u' ' + metadata['comment']
    description = description + u'|description={{en|1=' +informationDescription + u'}}\n'
    description = description + u'|date='
    if metadata.get('imagetaken') and not metadata.get('imagetaken')==u'0000-00-00':
	description = description + metadata.get('imagetaken').replace(u'-00', u'') + u'\n'
    else:
	description = description + u'{{Unknown}}\n'
    description = description + u'|source=From [http://www.geograph.org.uk/photo/' + str(metadata.get('id')) + u' geograph.org.uk]\n'
    description = description + u'|author=[http://www.geograph.org.uk/profile/' + str(metadata.get('user_id')) + u' ' + metadata.get('realname') + u']\n'
    description = description + u'|permission=\n'
    description = description + u'|other_versions=\n'
    description = description + u'}}\n'
    # Location, add heading
    description = description + u'{{Location dec|' + str(metadata.get('wgs84_lat'))
    description = description + u'|' + str(metadata.get('wgs84_long'))
    # ADD HEADING HERE
    if not metadata.get('view_direction') == -1:
	description = description + u'|heading:' + str(metadata.get('view_direction'))
    description = description + u'}}\n'
    description = description + u'\n'
    description = description + u'== {{int:license}} ==\n'
    description = description + u'{{Geograph|' + str(metadata.get('id'))
    description = description + u'|' + metadata.get('realname') +'}}\n'
    description = description + u'\n'

    return description

def getTitle(metadata):
    '''
    Build a valid title for the image to be uploaded to.
    '''
    title = metadata.get('title') + u' - geograph.org.uk - ' + str(metadata.get('id'))

    title = re.sub(u"[<{\\[]", u"(", title)
    title = re.sub(u"[>}\\]]", u")", title)
    title = re.sub(u"[ _]?\\(!\\)", u"", title)
    title = re.sub(u",:[ _]", u", ", title)
    title = re.sub(u"[;:][ _]", u", ", title)
    title = re.sub(u"[\t\n ]+", u" ", title)
    title = re.sub(u"[\r\n ]+", u" ", title)
    title = re.sub(u"[\n]+", u"", title)
    title = re.sub(u"[?!]([.\"]|$)", u"\\1", title)
    title =  re.sub(u"[&]", u"and", title)
    title = re.sub(u"[#%?!]", u"^", title)
    title = re.sub(u"[;]", u",", title)
    title = re.sub(u"[/+\\\\:]", u"-", title)
    title = re.sub(u"--+", u"-", title)
    title = re.sub(u",,+", u",", title)
    title = re.sub(u"[-,^]([.]|$)", u"\\1", title)
    title = title.replace(u" ", u"_")   
    
    return title
        


def getFileId(file):
    dirname = os.path.dirname(file)
    filename = os.path.basename(file)
    baseFilename, extension = os.path.splitext(filename)
    return int(baseFilename)

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

    gridsquares = []

    for sourcefilename in glob.glob(sourcedir + u"*.tif"):
	square = sourcefilename.replace(sourcedir, u'').replace(u'.tif', u'')
	gridsquares.append(square)

    for square in gridsquares:
	print square
	#processSquare(square, squares, sourcedir, destinationdir)
	

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
