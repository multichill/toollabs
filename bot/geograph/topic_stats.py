#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot to upload geograph images from the Toolserver to Commons

'''
import sys, os.path, hashlib, base64, MySQLdb, glob, re, urllib, time
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, query
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
    
    if set(currentCategories)==set(categories):
	return False

    for currentCat in currentCategories:
	categories.append(currentCat)
    
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

def getComments(text):
    '''
    Extract the comments from the table
    '''
    regex=u'^\{\{Commons:Batch uploading/Geograph/cats to clean up/row\|([^\|]*)\|(\d*)\|(\d*)\|(.*)\|(.*)\}\}$'
    result = {}
    matches = re.finditer(regex, text, re.MULTILINE)
    for match in matches:
	topic = match.group(1)
	commentBot = match.group(4)
	commentCleaned = match.group(5)
	result[topic] = (commentBot, commentCleaned)
    return result
    

def outputStats(topics, images):
    page = wikipedia.Page(wikipedia.getSite(), u'Commons:Batch uploading/Geograph/cats to clean up')
    oldtext = page.get()
    comments = getComments(oldtext)
    comment = u'Updating clean up page'
    totalTopics = 0
    totalImages = 0
    totalGeographImages = 0
    totalCommentsBot = 0
    totalCommentsCleaned = 0

    text = u'{{Commons:Batch uploading/Geograph/cats to clean up/header}}\n'
    for (topic,) in topics:
	outputTopic = topic.replace(u'_', u' ')
	((total,), (geograph,)) = images.get(topic)
	if comments.get(outputTopic):
	    (commentBot, commentCleaned) = comments.get(outputTopic)
	else:
	    commentBot = u''
	    commentCleaned = u''

	if commentBot==u'' and geograph==0:
	    commentBot=u'No Geograph images left'
	if commentCleaned==u'' and geograph==0:
	    commentCleaned=u'No Geograph images left'

	text = text + u'{{Commons:Batch uploading/Geograph/cats to clean up/row|' + outputTopic + u'|' + str(total) + u'|' + str(geograph) + u'|' + commentBot + u'|' + commentCleaned + u'}}\n'
	#update the stats
	totalTopics = totalTopics + 1
	totalImages = totalImages + int(total)
	totalGeographImages = totalGeographImages + int(geograph)
	if not commentBot==u'':
	    totalCommentsBot = totalCommentsBot + 1
	if not commentCleaned==u'':
	    totalCommentsCleaned = totalCommentsCleaned + 1
	
    text = text + u'{{Commons:Batch uploading/Geograph/cats to clean up/footer|' + str(totalTopics) + u'|' + str(totalImages) + u'|' + str(totalGeographImages) + u'|' + str(totalCommentsBot) + u'|'+ str(totalCommentsCleaned) + u'}}\n'
    #wikipedia.output(text) 
    page.put(text, comment) 



def getImagesWithTopicCount(cursor, topic):
    total = 0
    geograph = 0
    
    queryTotal = u"""SELECT COUNT(DISTINCT page_title) FROM page
    JOIN categorylinks AS topiccat ON page_id=topiccat.cl_from
    WHERE page_namespace=6 AND page_is_redirect=0 AND
    topiccat.cl_to=%s"""

    queryGeograph = u"""SELECT COUNT(DISTINCT page_title) FROM page
    JOIN categorylinks AS geocat ON page_id=geocat.cl_from
    JOIN categorylinks AS topiccat ON page_id=topiccat.cl_from
    JOIN externallinks ON page_id=el_from
    WHERE page_namespace=6 AND page_is_redirect=0 AND
    geocat.cl_to='Images_from_the_Geograph_British_Isles_project' AND
    topiccat.cl_to=%s AND
    el_to LIKE 'http://www.geograph.org.uk/photo/%%'"""
    
    cursor.execute(queryTotal, (topic, ))
    total = cursor.fetchone()
    
    cursor.execute(queryGeograph, (topic, ))
    geograph = cursor.fetchone()

    return (total, geograph)

def getTopics(cursor):
    result = []
    query = u"""SELECT DISTINCT commons FROM categories WHERE NOT commons='' ORDER BY commons"""
    cursor.execute(query)
    result = cursor.fetchall()
    return result

def main(args):
    '''
    Main loop.
    '''
    site = wikipedia.getSite(u'commons', u'commons')
    wikipedia.setSite(site)

    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()

    conn2 = None
    cursor2 = None
    (conn2, cursor2) = connectDatabase2('sql-s2.toolserver.org', u'u_multichill_commons_categories_p')

    conn3 = None
    cursor3 = None
    (conn3, cursor3) = connectDatabase2('commonswiki-p.db.toolserver.org', u'commonswiki_p')
    
    topics = getTopics(cursor)
    images = {}
    for (topic,) in topics:
    	images[topic] = getImagesWithTopicCount(cursor3, topic)
    	print images[topic]

    outputStats(topics, images)
    '''
    imageSet = getImagesToCorrect(cursor2)
    #print imageSet
    for (pageName, fileId) in imageSet:
	wikipedia.output(pageName)
	if not pageName==u'' and not fileId==u'':
	    #Get page contents
	    page = wikipedia.Page(site, pageName)
	    if page.exists():
		categories = page.categories()

		#Get metadata
		metadata = getMetadata(fileId, cursor)

		#Check if we got metadata
		if metadata:
		    #Get description
		    description = getDescription(metadata)

		    description = wikipedia.replaceCategoryLinks(description, categories, site)
		    comment= u'Fixing description of Geograph image with broken template'
		    wikipedia.output(description)
		    page.put(description, comment)
    '''
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
