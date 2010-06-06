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

def connectDatabase(server='sql.toolserver.org', db='u_multichill_geograph_p'):
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    my_conv = MySQLdb.converters.conversions
    del my_conv[MySQLdb.converters.FIELD_TYPE.DATE]
    #print my_conv
    conn = MySQLdb.connect(server, db=db, user = config.db_username, passwd = config.db_password, conv =my_conv , use_unicode=True)
    cursor = conn.cursor()
    return (conn, cursor)

def connectDatabase2(server='sql.toolserver.org', db='u_multichill_geograph_p'):
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect(server, db=db, user = config.db_username, passwd = config.db_password, use_unicode=True)
    cursor = conn.cursor()
    return (conn, cursor)



def findDuplicateImages(filename, site = wikipedia.getSite(u'commons', u'commons')):
    '''
    Takes the photo, calculates the SHA1 hash and asks the mediawiki api for a list of duplicates.

    TODO: Add exception handling, fix site thing
    '''
    f = open(filename, 'rb')

    hashObject = hashlib.sha1()
    hashObject.update(f.read(-1))
    return site.getFilesFromAnHash(base64.b16encode(hashObject.digest()))

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

def getCategories(metadata, cursor, cursor2):
    '''
    Produce one or more suitable Commons categories based on the metadata
    '''
    result = u''
    locationList =getExtendedFindNearby(metadata.get('wgs84_lat'), metadata.get('wgs84_long')) 

    for i in range(0, len(locationList)):
	#First try to get the location category based on the id
	category = getCategoryByGeonameId(locationList[i].get('geonameId'), cursor)
	if category:
	    #print locationList[i].get('geonameId') + u' - ' + category
	    locationList[i]['category'] = category
	#Second try to get the location category based on the name
	else:
	    if i > 1:
		category = getCategoryByName(name=locationList[i]['name'], parent=locationList[i-1]['name'], grandparent=locationList[i-2]['name'], cursor2=cursor2)
	    elif i > 0:
		category = getCategoryByName(name=locationList[i]['name'], parent=locationList[i-1]['name'], cursor2=cursor2)
	    else:
		category = getCategoryByName(name=locationList[i]['name'], cursor2=cursor2)
	    locationList[i]['category'] = category
	    #print locationList[i].get('geonameId')
	#print locationList[i].get('geonameId') + u' - ' + locationList[i].get('category')
    categories = []
    for location in locationList:
	if location.get('category') and not location.get('category')==u'':
	    categories.append(location.get('category')) 
    #Third try to get a topic category
    topicCategories = getTopicCategories(metadata.get('imageclass'), categories, cursor, cursor2)

    for topic in topicCategories:
	if not topic==u'':
	    topic = topic.replace(u'_', u' ').strip()
	    categories.append(topic)
    #categories.extend(topicCategories)

    if categories:
	result = u'{{Check categories-Geograph|year={{subst:CURRENTYEAR}}|month={{subst:CURRENTMONTHNAME}}|day={{subst:CURRENTDAY}}|lat=' + str(metadata.get('wgs84_lat'))  + u'|lon=' + str(metadata.get('wgs84_long'))  + u'|Geographcategory=' + metadata.get('imageclass')  + '}}\n'
	categories = filterCategories(categories, cursor2)
	for category in categories:
	    if category:
		result = result + u'[[Category:' + category.replace(u'_', u' ') + u']]\n'
    else:
	result = u'{{Subst:Unc}}'
    return result

def getExtendedFindNearby(lat, lng):
    '''
    Get the result from http://ws.geonames.org/extendedFindNearby
    and put it in a list of dictionaries to play around with
    '''
    result = [] 
    gotInfo = False
    parameters = urllib.urlencode({'lat' : lat, 'lng' : lng})
    while(not gotInfo):
	try:
	    page = urllib.urlopen("http://ws.geonames.org/extendedFindNearby?%s" % parameters)
	    et = xml.etree.ElementTree.parse(page)
	    gotInfo=True
        except IOError:
            wikipedia.output(u'Got an IOError, let\'s try again')
	    time.sleep(30)
        except socket.timeout:
            wikipedia.output(u'Got a timeout, let\'s try again')
	    time.sleep(30)
	    
    for geoname in et.getroot().getchildren():
	geonamedict = {}
	if geoname.tag=='geoname':
	    for element in geoname.getchildren():
		geonamedict[element.tag]=element.text
	    result.append(geonamedict)
    #print result
    return result

def getCategoryByGeonameId(geonameId, cursor):
    '''
    Return the name of a category based on a geonameId
    '''
    result = u''
    query = u"SELECT category from geonames WHERE geonameId=%s LIMIT 1"
    cursor.execute(query, (geonameId,))
    row = cursor.fetchone()
    if row:
	(result,) = row

    return result

def getCategoryByName(name, parent=u'', grandparent=u'', cursor2=None):

    if not parent==u'':
	work = name.strip() + u',_' + parent.strip()
	if categoryExists(work, cursor2):
	    return work
    if not grandparent==u'':
        work = name.strip() + u',_' + grandparent.strip()
        if categoryExists(work, cursor2):
            return work
    work = name.strip()
    if categoryExists(work, cursor2):
	return work

    return u''
    '''
    # Try simple name
    page = wikipedia.Page(title=u'Category:' + name.strip(), site = site)
    if page.exists():
	return page.titleWithoutNamespace()
    elif not parent==u'':
	page = wikipedia.Page(title=u'Category:' + name.strip() + u',_' + parent.strip(), site = site)
	if page.exists():
	    return page.titleWithoutNamespace()
    if not grandparent==u'':
	page = wikipedia.Page(title=u'Category:' + name.strip() + u',_' + grandparent.strip(), site= site)
	if page.exists():
	    return page.titleWithoutNamespace()

    return u''
    '''
def getTopicCategories(topic, categories, cursor, cursor2):
    result = []
    commonsCategory = getGeographToCommonsCategory(topic, cursor)
    if not commonsCategory ==u'':
	subjects = [commonsCategory]
    else:
	subjects = [topic, topic + u's', topic + u'es']
    betweens = [u'', u' in', u' of', u' on']
    thes = [u' ', u' the ']
    workcategories = [u'']
    for cat in categories:
	workcategories.append(cat)
    for subject in subjects:
	for between in betweens:
	    for the in thes:
		for category in workcategories:
		    work = subject + between + the + category
		    if categoryExists(work, cursor2):
			result.append(work)

    return result

def getGeographToCommonsCategory(topic, cursor):
    result = u''
    topic = topic.strip().replace(u' ', u'_')
    query = u"SELECT commons FROM categories WHERE geograph=%s LIMIT 1"
    cursor.execute(query, (topic,))
    row = cursor.fetchone()
    if row: 
	(result,) = row

    return result

def categoryExists(category, cursor2):
    category = category.strip()
    category = category.replace(' ', '_')
    query = u"SELECT * FROM cats WHERE child=%s LIMIT 1"
    #print query, (category,)

    cursor2.execute(query, (category,))
    row = cursor2.fetchone()
    if row:
	return True
    return False

def filterCategories(categories, cursor2):
    '''
    Filter the categories
    '''
    #First filter the parents to quickly reduce the number of categories
    if len(categories) > 1:
	result = filterParents(categories, cursor2)
    else:
	result = categories
    #Remove disambiguation categories
    result = imagerecat.filterDisambiguation(result)
    #And follow the redirects
    result = imagerecat.followRedirects(result)
    #And filter again for parents now we followed the redirects
    if len(result) > 1:
	result = filterParents(result, cursor2)
    return result

def filterParents(categories, cursor2):
    '''
    Filter out overcategorization.
    This is a python version of http://toolserver.org/~multichill/filtercats.php
    '''
    result = []
    query = u"SELECT c1.parent AS c1p, c2.parent AS c2p, c3.parent AS c3p, c4.parent AS c4p, c5.parent AS c5p, c6.parent AS c6p FROM cats AS c1 JOIN cats AS c2 ON c1.parent=c2.child JOIN cats AS c3 ON c2.parent=c3.child JOIN cats AS c4 ON c3.parent=c4.child JOIN cats AS c5 ON c4.parent=c5.child JOIN cats AS c6 ON c5.parent=c6.child WHERE "
    for i in range(0, len(categories)):
	categories[i] = categories[i].replace(u' ', u'_')
	query = query + u"c1.child='" + categories[i].replace(u"\'", "\\'") + u"'" 
	if(i+1 < len(categories)):
	     query = query + u" OR "

    #print query
    cursor2.execute(query)

    parentCats = set()
    while True:
	try:
	    row = cursor2.fetchone()
	    (c1p, c2p, c3p, c4p, c5p, c6p)= row
	    parentCats.add(c1p)
            parentCats.add(c2p)
            parentCats.add(c3p)
            parentCats.add(c4p)
            parentCats.add(c5p)
            parentCats.add(c6p)
	except TypeError:
	    #No more results
	    break
    #print parentCats
    for currentCat in categories:
	if not currentCat in parentCats and not currentCat in result:
	    result.append(currentCat) 

    return result

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
        
def getMetadata(fileId, cursor):
    result = {}
    query = u"SELECT user_id, realname, title, imagetaken, grid_reference, x, y, wgs84_lat, wgs84_long, imageclass, comment, view_direction FROM gridimage_base LEFT JOIN gridimage_text ON gridimage_base.gridimage_id=gridimage_text.gridimage_id LEFT JOIN gridimage_geo ON gridimage_base.gridimage_id=gridimage_geo.gridimage_id WHERE gridimage_base.gridimage_id=%s LIMIT 1"
    cursor.execute(query, (fileId,))
    row = cursor.fetchone()
    if row:
	result['id'] = fileId
	(result['user_id'],
	 result['realname'],
	 result['title'],
	 result['imagetaken'],
	 result['grid_reference'],
	 result['x'],
	 result['y'],
	 result['wgs84_lat'],
	 result['wgs84_long'],
	 result['imageclass'],
	 result['comment'],
	 result['view_direction']) = row
	#print result

    return result

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
