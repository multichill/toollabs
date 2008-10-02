#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Create a list of possible categories to create.
'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, MySQLdb, config

def connectDatabase():
    conn = MySQLdb.connect(config.db_hostname, db='commonswiki_p', user = config.db_username, passwd = config.db_password)
    cursor = conn.cursor()
    return (conn, cursor)

def getCategorySuggestions(cursor):
    query = u"SELECT gallery.page_title AS catje, COUNT(gallery.page_title) AS aantal FROM page AS imagepage JOIN imagelinks ON imagepage.page_title=il_to JOIN page AS gallery ON il_from=gallery.page_id JOIN categorylinks AS imcl ON imagepage.page_id=imcl.cl_from WHERE imcl.cl_to LIKE 'Media_needing_categories_as_of_%' AND imagepage.page_namespace=6 AND imagepage.page_is_redirect=0 AND gallery.page_namespace=0 AND gallery.page_is_redirect=0 GROUP BY(gallery.page_title) HAVING COUNT(gallery.page_title) > 3";

    cursor.execute(query)
    result = []
    while True:
	try:
	    gallery, count, = cursor.fetchone()
	    result.append((unicode(gallery, 'utf-8'), unicode(str(count), 'utf-8')))
	except TypeError:
	    # Limit reached or no more results
	    break
    return result

def outputResult(suggestions):
    resultwiki = u'{{User:Multichill/Category_suggestions/header}}\n'
    page = wikipedia.Page(wikipedia.getSite(u'commons', u'commons'), u'User:Multichill/Category_suggestions')
    comment = u'Updated the list of category suggestions'
    for (gallery, count) in suggestions:
	resultwiki = resultwiki + u'*[[' + gallery.replace(u'_', u' ') + u']] (' + count + u') -> [[:Category:' + gallery.replace(u'_', u' ') + u']]\n'
    page.put(resultwiki, comment)

def main():
    conn = None
    cursor = None
    suggestions = []
    (conn, cursor) = connectDatabase()
    suggestions = getCategorySuggestions(cursor)
    outputResult(suggestions)
    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
