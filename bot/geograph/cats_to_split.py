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
    

def outputCategoriesToSplit(cats):
    page = wikipedia.Page(wikipedia.getSite(), u'Commons:Batch_uploading/Geograph/split')
    comment = u'Updating list of cats to split out'

    text = u'These cats should be split out to the county subcategories:\n'
    for cat in cats:
	text = text + u'*[[:Category:' + cat + u']]\n'
	
    page.put(text, comment) 


def getCategoriesToSplit(cursor, topic):
    result = []
    query = u"""SELECT country.page_title FROM categorylinks AS clA
		JOIN page AS bc ON clA.cl_from=bc.page_id

		JOIN categorylinks AS clB ON bc.page_title=clB.cl_to		
		JOIN page AS uk ON clB.cl_from=uk.page_id

		JOIN categorylinks AS clC ON uk.page_title=clC.cl_to
		JOIN page AS country ON clC.cl_from=country.page_id
		
		JOIN categorylinks AS clD on country.page_title=clD.cl_to
		JOIN page AS county ON clD.cl_from=county.page_id

		WHERE clA.cl_to='%s' AND
		bc.page_title='%s_by_country' AND bc.page_namespace=14 AND bc.page_is_redirect=0 AND
		clB.cl_to='%s_by_country' AND

		uk.page_title LIKE '%s\_%%\_the\_United\_Kingdom' AND uk.page_namespace=14 AND uk.page_is_redirect=0 AND
		clC.cl_to LIKE '%s\_%%\_the\_United\_Kingdom' AND

		(country.page_title LIKE '%s\_%%\_England' OR
		country.page_title LIKE '%s\_%%\_Northern_Ireland' OR
		country.page_title LIKE '%s\_%%\_Scotland' OR
		country.page_title LIKE '%s\_%%\_Wales' 
		)AND country.page_namespace=14 AND country.page_is_redirect=0 AND

		clD.cl_to LIKE '%s\_%%' AND
		county.page_title LIKE '%s\_%%' AND county.page_namespace=14 AND country.page_is_redirect=0

		GROUP BY(country.page_title)
		HAVING COUNT(county.page_title) > 10
		LIMIT 4"""
    #print query % (topic, topic, topic, topic, topic, topic, topic, topic, topic, topic )
    #time.sleep(5)
    cursor.execute(query % (topic, topic, topic, topic, topic, topic, topic, topic, topic, topic, topic))
    
    for (cat,) in cursor.fetchall():
	result.append(cat)
	print cat
    return result

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

    #conn2 = None
    #cursor2 = None
    #(conn2, cursor2) = connectDatabase2('sql-s2.toolserver.org', u'u_multichill_commons_categories_p')

    conn3 = None
    cursor3 = None
    (conn3, cursor3) = connectDatabase2('commonswiki-p.db.toolserver.org', u'commonswiki_p')
    
    topics = getTopics(cursor)
    images = {}
    cats = []
    for (topic,) in topics:
	cats.extend(getCategoriesToSplit(cursor3, topic))

    outputCategoriesToSplit(cats)
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
