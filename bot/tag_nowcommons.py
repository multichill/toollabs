#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Tag images we {{NowCommons}} at the English Wikipedia.
Could later be expanded to work on other sites too
'''
import sys
sys.path.append("../pywikipedia")
import wikipedia, MySQLdb, config

skips = {}
skips['wikipedia'] = {}
skips['wikipedia']['en'] = [u'NowCommons',
			    u'CommonsNow',
			    u'Nowcommons',
			    u'NowCommonsThis',
			    u'Nowcommons2',
			    u'NCT',
			    u'Nowcommonsthis',
			    u'Moved to commons',
			    u'Now Commons',
			    u'Now at commons',
			    u'Db-nowcommons',
			    u'WikimediaCommons',
			    u'Now commons',
			    u'Do not move to Commons',
			    u'KeepLocal',
			    u'Keeplocal',
			    u'NoCommons',
			    u'Nocommons',
			    u'NotMovedToCommons',
			    u'Nmtc',
			    u'Not moved to Commons',
			    u'Notmovedtocommons',
			    ]
skips['wikipedia']['fy'] = [u'NowCommons',
			    u'Nowcommons',
			    ]
skips['_default'] = [u'NowCommons']

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    site = wikipedia.getSite()
    language = site.language()
    family = site.family.name
    conn_start = MySQLdb.connect('sql.toolserver.org', db='toolserver', user = config.db_username, passwd = config.db_password, charset='latin1', use_unicode=True)
    cursor_start = conn_start.cursor()
    
    query_start = u"""SELECT dbname, server FROM wiki WHERE lang='%s' AND family='%s' LIMIT 1"""
    cursor_start.execute(query_start % (language, family))
    (dbname, server) = cursor_start.fetchone() 
    conn_start.close()

    conn = MySQLdb.connect('sql-s' + str(server) + '.toolserver.org', db=dbname, user = config.db_username, passwd = config.db_password, charset='latin1', use_unicode=True)
    cursor = conn.cursor()
    return (conn, cursor)

def getImagesToNowcommons(cursor, limit=100, start=0):
    '''
    Get all images which exist at Commons with the same hash
    '''
    query =u"""SELECT wi.img_name, ci.img_name, ci.img_timestamp FROM image AS wi
               JOIN commonswiki_p.image AS ci
               ON (wi.img_size=ci.img_size AND wi.img_width=ci.img_width AND wi.img_height=ci.img_height AND wi.img_sha1=ci.img_sha1) LIMIT %s, %s"""
    while True:
	cursor.execute(query % (start, limit))
	result = cursor.fetchall()
	if result:
	    start = start + limit
	    for item in result:
		yield item
	else:
	    break
    return
	    

def tagNowCommons(wImage, cImage, timestamp):
    site = wikipedia.getSite()
    language = site.language()
    family = site.family.name

    imagepage = wikipedia.ImagePage(wikipedia.getSite(), wImage)
    if not imagepage.exists() or imagepage.isRedirectPage():
	return

    if skips.get(family) and skips.get(family).get(language):
	localskips = skips.get(family).get(language)
    else:
	localskips = skips.get('_default')

    for template in imagepage.templates():
	title = template.replace(u'_', u' ').strip()
	if title in localskips:
	    return
    text = imagepage.get()
    oldtext = text

    text = u'{{NowCommons|File:%s|date=%s|bot=~~~}}\n' % (cImage.replace(u'_', u' '), timestamp) + text
    comment = u'File is available on Wikimedia Commons.'
    wikipedia.showDiff(oldtext, text)
    try:
	imagepage.put(text, comment)
	#print u'put'
    except wikipedia.LockedPage:
	return

def main():
    '''
    The main loop
    '''
    wikipedia.handleArgs()
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()
    imageList = getImagesToNowcommons(cursor)
    for (wImage, cImage, timestamp) in imageList:
	tagNowCommons(unicode(wImage, 'utf-8'), unicode(cImage, 'utf-8'), timestamp)

    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
