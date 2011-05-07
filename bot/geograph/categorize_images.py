#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot to categorize images already uploaded to Commons

'''
import sys, os.path, hashlib, base64, MySQLdb, glob, re, urllib, time
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, query
import xml.etree.ElementTree, shutil
import imagerecat, pagegenerators
import MySQLdb.converters
import geograph_lib

def getImagesWithTopic(cursor, topic):
    '''
    Get a list of image with geograph id for a certain topic
    '''
    result = []
    query = u"""SELECT DISTINCT page_title,
    REPLACE(el_to, 'http://www.geograph.org.uk/photo/', '') FROM page
    JOIN categorylinks AS geocat ON page_id=geocat.cl_from
    JOIN categorylinks AS topiccat ON page_id=topiccat.cl_from
    JOIN externallinks ON page_id=el_from
    WHERE page_namespace=6 AND page_is_redirect=0 AND
    geocat.cl_to LIKE 'Images\_from\_Geograph\_needing\_category\_review\_as\_of\_%%' AND
    topiccat.cl_to=%s AND
    el_to LIKE 'http://www.geograph.org.uk/photo/%%' LIMIT 1000"""
    cursor.execute(query, (topic, ))
    result = cursor.fetchall()
    return result

def getTopics(cursor):
    '''
    Get the list of topics we put in the database
    '''
    result = []
    query = u"""SELECT DISTINCT commons FROM categories WHERE NOT commons='' ORDER BY commons"""
    cursor.execute(query)
    result = cursor.fetchall()
    return result
    
def getGeographId(page):
    '''
    Extract the Geograph image id from a Commons imagepage
    '''
    idMatch = re.search(u'\{\{Geograph\|(\d+)\|[^|}]+\}\}', page.get())
    if idMatch:
	return idMatch.group(1)
    else:
	return False

def main(args):
    '''
    Main loop.
    '''
    site = wikipedia.getSite(u'commons', u'commons')
    wikipedia.setSite(site)

    conn = None
    cursor = None
    (conn, cursor) = geograph_lib.connectDatabase()

    conn2 = None
    cursor2 = None
    (conn2, cursor2) = geograph_lib.connectDatabase2('sql-s2.toolserver.org', u'u_multichill_commons_categories_p')

    conn3 = None
    cursor3 = None
    (conn3, cursor3) = geograph_lib.connectDatabase2('commonswiki-p.db.toolserver.org', u'commonswiki_p')
    
    generator = None
    genFactory = pagegenerators.GeneratorFactory()

    for arg in wikipedia.handleArgs():
	genFactory.handleArg(arg)

    generator = genFactory.getCombinedGenerator()
    if generator:
	for page in generator:
	    if page.exists() and page.namespace()==6 and not page.isRedirectPage():
		wikipedia.output(page.title())
		id = getGeographId(page)
		if id:
		    geograph_lib.categorizeImage(page, id, cursor, cursor2)
    else:
	topics = getTopics(cursor)
	for (topic,) in topics:
	    images = getImagesWithTopic(cursor3, topic)
	    for (imageName, id) in images:
		try:
		    page = wikipedia.ImagePage(wikipedia.getSite(), u'File:' + imageName)
		    if page.exists() and page.namespace()==6 and not page.isRedirectPage():
			wikipedia.output(page.title())
			geograph_lib.categorizeImage(page, id, cursor, cursor2)
		except UnicodeDecodeError:
		    print "UnicodeDecodeError, can't find the source. yah! :-("
		    pass

if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
