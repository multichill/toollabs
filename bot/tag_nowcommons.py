#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Tag images we {{NowCommons}} at the English Wikipedia.
Could later be expanded to work on other sites too
'''
import sys
sys.path.append("../pywikipedia")
import wikipedia, MySQLdb, config

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect('enwiki-p.db.toolserver.org', db='enwiki_p', user = config.db_username, passwd = config.db_password, charset='utf8', use_unicode=True)
    cursor = conn.cursor()
    return (conn, cursor)


def getImagesToNowcommons(cursor):
    '''
    Get all images which exist at Commons with the same hash
    '''
    query =u"""SELECT wi.img_name, ci.img_name FROM enwiki_p.image AS wi
               JOIN commonswiki_p.image AS ci
               ON (wi.img_size=ci.img_size AND wi.img_width=ci.img_width AND wi.img_height=ci.img_height AND wi.img_sha1=ci.img_sha1) """

    
    cursor.execute(query)
    result = cursor.fetchall()
    return result
	    

def tagNowCommons(wImage, cImage):
    imagepage = wikipedia.ImagePage(wikipedia.getSite(), wImage)
    if not imagepage.exists() or imagepage.isRedirectPage():
	return
    skips = [u'NowCommons',
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
             u'NotMovedToCommons',
             u'Nmtc',
             u'Not moved to Commons',
             u'Notmovedtocommons',
	    ]
    for template in imagepage.templates():
	title = template.replace(u'_', u' ').strip()
	if title in skips:
	    return
    text = imagepage.get()
    oldtext = text

    text = u'{{NowCommons|File:' + cImage.replace(u'_', u' ') + u'|bot=~~~}}\n' + text
    comment = u'File is available on Wikimedia Commons.'
    wikipedia.showDiff(oldtext, text)
    try:
	imagepage.put(text, comment)
    except wikipedia.LockedPage:
	return

def main():
    '''
    The main loop
    '''
    wikipedia.setSite(wikipedia.getSite(u'en', u'wikipedia'))
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()
    imageList = getImagesToNowcommons(cursor)
    for (wImage, cImage) in imageList:
	tagNowCommons(unicode(wImage, 'utf-8'), unicode(cImage, 'utf-8'))

    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
