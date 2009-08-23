#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Categorize all files which are uncategorized and in use a gallery with a category with the same name
'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, MySQLdb, config, imagerecat

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect(config.db_hostname, db='commonswiki_p', user = config.db_username, passwd = config.db_password)
    cursor = conn.cursor()
    return (conn, cursor)


def getImagesToCategorize(cursor):
    '''
    Get all images with are in a subcategory of Media needing categories and which are in use in a gallery which has a category with the same name. The gallery should be in the category or the gallery and the category should share the same parent category'

    '''
    query=u"SELECT ipage.page_title AS plaatje, gpage.page_title AS catje FROM page AS ipage JOIN categorylinks ON ipage.page_id=cl_from JOIN imagelinks ON ipage.page_title=il_to JOIN page AS gpage ON il_from=gpage.page_id WHERE ipage.page_namespace=6 AND ipage.page_is_redirect=0 AND gpage.page_namespace=0 AND gpage.page_is_redirect=0 AND cl_to LIKE 'Media\_needing\_categories\_as\_of\_%\_2008' AND (EXISTS(SELECT * FROM categorylinks WHERE gpage.page_id=cl_from AND gpage.page_title=cl_to) OR EXISTS(SELECT * FROM page AS catpage JOIN categorylinks AS ccl ON (catpage.page_id=ccl.cl_from) JOIN categorylinks AS gcl ON (gcl.cl_to=ccl.cl_to ) WHERE catpage.page_title=gpage.page_title AND gpage.page_id=gcl.cl_from AND catpage.page_namespace=14 AND catpage.page_is_redirect=0)) LIMIT 5000"

    cursor.execute(query)
    result = []
    while True:
	try:
	    image, category = cursor.fetchone()
	    result.append((unicode(image, 'utf-8'), unicode(category, 'utf-8')))
	except TypeError:
	    # Limit reached or no more results
	    break
    return result

def categorizeImage(image, category):
    '''
    Replace uncategorized with a category
    '''
    page = wikipedia.Page(wikipedia.getSite(), u'Image:' + image)
    category = category.replace('_', ' ')
    if page.exists():
	newtext = imagerecat.removeTemplates(page.get())
	newtext = newtext + u'\n[[Category:' + category + ']]'
	comment = u'Adding [[:Category:' + category +  u']] from [[' + category + u'|gallery]] to this uncategorized image'
	wikipedia.showDiff(page.get(), newtext)
	page.put(newtext, comment)

def main():
    '''
    The main loop
    '''
    wikipedia.setSite(wikipedia.getSite(u'commons', u'commons'))
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()
    #images = getImagesToCategorize(cursor)

    for (image, category) in getImagesToCategorize(cursor):
	categorizeImage(image, category)
	

    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
