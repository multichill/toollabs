#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Lib with Geograph functions shared by multiple programs

'''
import sys, os.path, hashlib, base64, MySQLdb, glob, re, urllib, time
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, query, socket
import xml.etree.ElementTree, shutil
import imagerecat, pagegenerators
import MySQLdb.converters

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
    conn = MySQLdb.connect(server, db=db, user = config.db_username, passwd = config.db_password, charset='utf8', use_unicode=True)
    cursor = conn.cursor()
    return (conn, cursor)

def getDescription(metadata):
    '''
    Create the description of the image based on the metadata
    '''
    description = u''

    description = description + u'== {{int:filedesc}} ==\n'
    description = description + u'{{Information\n'
    description = description + u'|description={{en|1=' + metadata.get('title')
    if not metadata['comment']==u'':
	description = description + u' ' + metadata['comment']
    description = description + u'}}\n'
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

def getCategories(metadata, cursor, cursor2, currentCategories=[]):
    '''
    Produce one or more suitable Commons categories based on the metadata
    '''
    result = u''
    locationEFNCategories = getExtendedFindNearbyCategories(metadata, cursor, cursor2)
    print u'locationEFNCategories'
    print locationEFNCategories

    locationOSMcategories = getOpenStreetMapCategories(metadata, cursor, cursor2)
    print u'locationOSMcategories'
    print locationOSMcategories

    categories = locationEFNCategories + locationOSMcategories
    
    #Third try to get a topic category
    topicCategories = getTopicCategories(metadata.get('imageclass'), categories, cursor, cursor2)

    for topic in topicCategories:
	if not topic==u'':
	    topic = topic.strip().replace(u' ', u'_')
	    categories.append(topic)
    #categories.extend(topicCategories)
    categories = filterCategories(categories, cursor2)

    if set(currentCategories)==set(categories):
	return False

    for currentCat in currentCategories:
	categories.append(currentCat)
    
    if categories:
	result = u'{{Check categories-Geograph|year={{subst:CURRENTYEAR}}|month={{subst:CURRENTMONTHNAME}}|day={{subst:CURRENTDAY}}|lat=' + str(metadata.get('wgs84_lat'))  + u'|lon=' + str(metadata.get('wgs84_long'))  + u'|Geographcategory=' + metadata.get('imageclass')  + '}}\n'
	categories = filterCategories(categories, cursor2)
	if set(currentCategories)==set(categories):
	    return False
	for category in categories:
	    if category:
		result = result + u'[[Category:' + category.replace(u'_', u' ') + u']]\n'
    else:
	result = u'{{Subst:Unc}}'
    return result

def getExtendedFindNearbyCategories(metadata, cursor, cursor2):
    '''
    Get a list of location categories based on the extended find nearby tool
    '''
    result = []
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

    for location in locationList:
	if location.get('category') and not location.get('category')==u'':
	    result.append(location.get('category')) 
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
    return result

def getOpenStreetMapCategories(metadata, cursor, cursor2):
    '''
    Get a list of location categories based on the extended find nearby tool
    '''
    result = []
    locationList = getOpenStreetMap(metadata.get('wgs84_lat'), metadata.get('wgs84_long'))
    for i in range(0, len(locationList)):
	print 'Working on ' + locationList[i]
	if i <= len(locationList)-3:
	    category = getCategoryByName(name=locationList[i], parent=locationList[i+1], grandparent=locationList[i+2], cursor2=cursor2)
	elif i == len(locationList)-2:
            category = getCategoryByName(name=locationList[i], parent=locationList[i+1], cursor2=cursor2)
	else:
            category = getCategoryByName(name=locationList[i], cursor2=cursor2)
	if category and not category==u'':
	    result.append(category)
    #print result
    return result


def getOpenStreetMap(lat, lon):
    '''
    Get the result from http://nominatim.openstreetmap.org/reverse
    and put it in a list of tuples to play around with
    '''
    result = []
    gotInfo = False
    parameters = urllib.urlencode({'lat' : lat, 'lon' : lon})
    while(not gotInfo):
	try:
	    page = urllib.urlopen("http://nominatim.openstreetmap.org/reverse?format=xml&%s" % parameters)
	    et = xml.etree.ElementTree.parse(page)
	    gotInfo=True
	except IOError:
	    wikipedia.output(u'Got an IOError, let\'s try again')
	    time.sleep(30)
	except socket.timeout:
	    wikipedia.output(u'Got a timeout, let\'s try again')
	    time.sleep(30)
    validParts = [u'hamlet', u'village', u'city', u'county', u'country']
    invalidParts = [u'path', u'road', u'suburb', u'state', u'country_code']
    addressparts = et.find('addressparts')
    #xml.etree.ElementTree.dump(et)

    for addresspart in addressparts.getchildren():
	if addresspart.tag in validParts:
	    result.append(addresspart.text)
	elif addresspart.tag in invalidParts:
	    wikipedia.output(u'Dropping %s, %s' % (addresspart.tag, addresspart.text))
	else:
	    wikipedia.output(u'WARNING %s, %s is not in addressparts lists' % (addresspart.tag, addresspart.text))
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
    title = re.sub(u"[&]", u"and", title)
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

    return result

def categorizeImage(page, id, cursor, cursor2):
    # get metadata
    metadata = getMetadata(id, cursor)
    # get current text
    oldtext = page.get()
    # get current categories
    currentCategories =[]
    for cat in page.categories():
	currentCategories.append(cat.titleWithoutNamespace().strip().replace(u' ', u'_'))
    # remove templates
    cleanDescription = wikipedia.removeCategoryLinks(imagerecat.removeTemplates(page.get()), wikipedia.getSite())
    # get new categories
    categories = getCategories(metadata, cursor, cursor2, currentCategories)

    if categories and not set(currentCategories)==set(categories):
	description = cleanDescription + u'\n\n' +  categories
	comment = u'Trying to find better categories for this [[Commons:Batch uploading/Geograph|Geograph]] image'
	wikipedia.output(description)
	wikipedia.showDiff(oldtext, description)
	page.put(description, comment)

def getTopics(cursor):
    result = []
    query = u"""SELECT DISTINCT commons FROM categories WHERE NOT commons='' ORDER BY commons"""
    cursor.execute(query)
    result = cursor.fetchall()
    return result

