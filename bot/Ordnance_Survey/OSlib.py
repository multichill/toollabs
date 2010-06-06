#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Library of functions used by the Ordnance Survey bots
'''
import sys, os.path, hashlib, base64, MySQLdb, glob, re, urllib, time
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, query
import xml.etree.ElementTree, shutil
import imagerecat
import MySQLdb.converters

def getNextSquare(currentSquare=u'', direction='s'):
    '''
    Get the next grid square on the same scale
    '''
    mat500 = [[u'H', u'J'],
	      [u'N', u'O'],
	      [u'S', u'T']]

    mat100 = [[u'A', u'B', u'C', u'D', u'E'],
	      [u'F', u'G', u'H', u'J', u'K'],
	      [u'L', u'M', u'N', u'O', u'P'],
              [u'Q', u'R', u'S', u'T', u'U'],
              [u'V', u'W', u'X', u'Y', u'Z']]

    #mat10 is nummeric, first is x <->, second is y |
    mat10  = [[u'09', u'19', u'29', u'39', u'49', u'59', u'69', u'79', u'89', u'99'],
              [u'08', u'18', u'28', u'38', u'48', u'58', u'68', u'78', u'88', u'98'],
              [u'07', u'17', u'27', u'37', u'47', u'57', u'67', u'77', u'87', u'97'],
              [u'06', u'16', u'26', u'36', u'46', u'56', u'66', u'76', u'86', u'96'],
              [u'05', u'15', u'25', u'35', u'45', u'55', u'65', u'75', u'85', u'95'],
              [u'04', u'14', u'24', u'34', u'44', u'54', u'64', u'74', u'84', u'94'],
              [u'03', u'13', u'23', u'33', u'43', u'53', u'63', u'73', u'83', u'93'],
              [u'02', u'12', u'22', u'32', u'42', u'52', u'62', u'72', u'82', u'92'],
              [u'01', u'11', u'21', u'31', u'41', u'51', u'61', u'71', u'81', u'91'],
              [u'00', u'10', u'20', u'30', u'40', u'50', u'60', u'70', u'80', u'90']]

    matPart = [[u'nw', u'ne'],
	       [u'sw', u'se']]

    mat500current=u''
    mat100current=u''
    mat10current=u''
    matPartcurrent=u''
  
    # Get all the fields 
    if len(currentSquare)==6:
	matPartcurrent=currentSquare[4:6]
    if len(currentSquare)>=4:
	mat10current=currentSquare[2:4]
    if len(currentSquare)>=2:
	mat100current=currentSquare[1]
    if len(currentSquare)>=1:
	mat500current=currentSquare[0]

    # Figure out the next field
    rollover = False

    mat500new=mat500current
    mat100new=mat100current
    mat10new=mat10current
    matPartnew=matPartcurrent

    if len(currentSquare)==6:
	(matPartnew, rollover) = getNextPosition(matPartcurrent, matPart, direction) 

    if len(currentSquare)==4 or rollover:
	(mat10new, rollover) = getNextPosition(mat10current, mat10, direction)

    if len(currentSquare)==2 or rollover:
	(mat100new, rollover) = getNextPosition(mat100current, mat100, direction)

    if len(currentSquare)==1 or rollover:
	(mat500new, rollover) = getNextPosition(mat500current, mat500, direction)

    result = mat500new + mat100new + mat10new + matPartnew
    return result

def getNextPosition(currentPosition, matrix, direction=u's'):
    (i, j) = findPosition(currentPosition, matrix)
    newi = i
    newj = j
    if i==0 and direction==u'n':
	newi = len(matrix)-1
	rollover = True
    elif i==len(matrix)-1 and direction==u's':
	newi = 0
	rollover = True
    elif j==0 and direction==u'w':
	newj = len(matrix[0])-1
	rollover = True
    elif j==len(matrix[0])-1 and direction==u'e':
	newj = 0
	rollover = True
    else:
	rollover = False
	if direction==u'n':
	    newi = i -1
	elif direction==u's':
	    newi = i + 1
	elif direction==u'w':
	    newj = j - 1
	elif direction==u'e':
	    newj = j + 1
    return (matrix[newi][newj], rollover)

def findPosition(position, matrix):
    for i in range(len(matrix)):
	for j in range(len(matrix[i])):
	    if matrix[i][j] == position:
		return (i, j)

def outputDescriptionFile(filename, description):
    f = open(filename, "w")
    f.write(description.encode("UTF-8"))
    f.close()
    return

def main(args):
    '''
    Main loop.
    '''
    print getNextSquare(currentSquare=getNextSquare(currentSquare=u'SD', direction=u'e'), direction='n')
    print getNextSquare(currentSquare=u'SE80nw', direction='e')
    print getNextSquare(currentSquare=u'SE80nw', direction='s')
    print getNextSquare(currentSquare=u'SE80nw', direction='w')

    '''
    site = wikipedia.getSite(u'commons', u'commons')
    wikipedia.setSite(site)

    start_id=0    

    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()

    conn2 = None
    cursor2 = None
    (conn2, cursor2) = connectDatabase2('sql-s2.toolserver.org', u'u_multichill_commons_categories_p')

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
