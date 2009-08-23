#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Do some checks on Commons templates
'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, MySQLdb, config
from datetime import datetime

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect(config.db_hostname, db='commonswiki_p', user = config.db_username, passwd = config.db_password, charset='utf8')
    cursor = conn.cursor()
    return (conn, cursor)

def getLangs(cursor):
    '''
    Get a list of valid language codes from http://commons.wikimedia.org/wiki/Special:PrefixIndex/MediaWiki:Lang/
    '''
    query = u"""SELECT page_title FROM page WHERE page_title LIKE 'Lang/%' AND page_namespace=8 AND page_is_redirect=0"""

    cursor.execute(query)
    result = []

    while True:
	try:
	    lang, =cursor.fetchone()
	    result.append(unicode(lang, 'utf-8').replace(u'Lang/', u''))
	except TypeError:
	    # Limit reached or no more results
	    break
    return result

def getBaseTemplates(cursor):
    '''
    Get a list of base templates from http://commons.wikimedia.org/wiki/Commons:Template_i18n (and subpages)
    '''
    query = u"""SELECT DISTINCT(pl_title) FROM page JOIN pagelinks ON page_id=pl_from WHERE page_title LIKE 'Template\_i18n/%' 
             AND page_namespace=4 AND page_is_redirect=0 AND pl_namespace=10 AND NOT pl_title LIKE '%/%' ORDER BY pl_title ASC"""

    cursor.execute(query)
    result = []

    while True:
        try:
            template, =cursor.fetchone()
            result.append(unicode(template, 'utf-8'))
        except TypeError:
            # Limit reached or no more results
            break
    return result

def getMissingLangs(cursor, baseTemplate):
    '''
    '''
    query =  u"""SELECT page_title FROM page AS lang WHERE lang.page_title LIKE %s
		AND NOT lang.page_title=%s
		AND NOT lang.page_title=%s
		AND NOT lang.page_title=%s
		AND lang.page_namespace=10
		AND lang.page_is_redirect=0
		AND NOT EXISTS(SELECT pl_title FROM page AS langpage
		JOIN pagelinks ON langpage.page_id=pl_from
		WHERE langpage.page_title=%s
		AND langpage.page_namespace=10
		AND langpage.page_is_redirect=0
		AND pl_namespace=10
		AND pl_title=lang.page_title)"""
    cursor.execute(query, (baseTemplate + u'/%', baseTemplate + u'/doc', baseTemplate + u'/layout', baseTemplate + u'/lang', baseTemplate + u'/lang'))
    result = []

    while True:
        try:
            template, =cursor.fetchone()
            result.append(unicode(template, 'utf-8').replace(baseTemplate + u'/', u''))
        except TypeError:
            # Limit reached or no more results
            break
    return result

def checkTemplate(cursor, baseTemplate, langs):
    docOK = checkDoc(cursor, baseTemplate)
    layoutOK = checkLayout(cursor, baseTemplate)
    langOK = checkLang(cursor, baseTemplate, langs)
    return docOK and layoutOK and langOK

def checkDoc(cursor, baseTemplate):
    return True

def checkLayout(cursor, baseTemplate):
    return True

def checkLang(cursor, baseTemplate, langs):
    foundMissing = False
    missingLangs = getMissingLangs(cursor, baseTemplate)
    for missingLang in missingLangs:
	if missingLang in langs:
	    #wikipedia.output(baseTemplate + u'/' +  missingLang)
	    foundMissing = True
	elif missingLang.replace(u'heading/', u'') in langs:
	    foundMissing = foundMissing
	else:
	    wikipedia.output(baseTemplate + u'/' +  missingLang)
    return foundMissing

def main():
    '''
    The main loop
    '''
    wikipedia.setSite(wikipedia.getSite(u'commons', u'commons'))
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()

    langs = getLangs(cursor)

    for baseTemplate in getBaseTemplates(cursor):
	#print baseTemplate
	checkTemplate(cursor, baseTemplate, langs)

    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
