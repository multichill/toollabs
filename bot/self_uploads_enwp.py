#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Program to generate galleries for all users at https://en.wikipedia.org/wiki/User:Multichill/top_self_uploaders
'''
import sys
sys.path.append("/home/multichill/pywikipedia/")
import wikipedia, MySQLdb, config
from datetime import datetime
from datetime import timedelta

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect('enwiki-p.rrdb.toolserver.org', db='enwiki_p', user = config.db_username, passwd = config.db_password, use_unicode=True)

    cursor = conn.cursor()
    return (conn, cursor)

def processUser(cursor, userpage):
    site = userpage.site()
    username = userpage.title(withNamespace=False)
    subpage = wikipedia.Page(site, u'User:Multichill/top_self_uploaders/%s' % (username,))
    images = userSelfUploadsQuery(cursor, username)

    wikipedia.output(u'Working on %s' % (subpage.title(),))
    if subpage.exists():
	oldtext = subpage.get()
    else:
	oldtext = u''

    if images:
	# Should probably make some sort of pretty header
	text = u'<gallery>\n'
	for image in images:
	    text = text + u'File:%s\n' % (image,)
	text = text + u'</gallery>\n'
	comment = u'Updating list of self made free images, %d images left' % (len(images),)
	if not(oldtext.strip()==text.strip()):
	    wikipedia.showDiff(oldtext, text)
	    wikipedia.output(comment)
	    subpage.put(text, comment)

	return subpage.title()

    # Images is empty
    else:
	# Should do something if the page is blank for x days
	if subpage.exists() and not oldtext==u'':
	    text = u''
	    comment = u'No images left. Blanking the page'
	    wikipedia.showDiff(oldtext, text)
	    wikipedia.output(comment)
	    subpage.put(text, comment)

	# No page so return nothing
	return u''

def userSelfUploadsQuery(cursor, username):
    '''
    Get the list of self-published works by an uploader
    '''
    query = u"""SELECT page_title FROM image
    JOIN page on img_name=page_title
    JOIN categorylinks AS free ON page_id=free.cl_from
    JOIN categorylinks AS self ON page_id=self.cl_from
    WHERE page_namespace=6 AND 
    page_is_redirect=0 
    AND free.cl_to='All_free_media'
    AND self.cl_to='Self-published_work'
    AND NOT EXISTS(SELECT * FROM categorylinks WHERE page_id=cl_from AND cl_to='All_possibly_unfree_Wikipedia_files')
    AND img_user_text='%s'
    ORDER BY page_title ASC
    LIMIT 350"""

    images = []
    cursor.execute(query % (username,))
    result = cursor.fetchall()
    
    for (image,) in result:
	images.append(unicode(image, 'utf-8'))

    return images

def main():

    (conn, cursor) = connectDatabase()

    site = wikipedia.getSite('en', 'wikipedia')
    basepage = wikipedia.Page(site, u'User:Multichill/top self uploaders')

    for userpage in basepage.linkedPages():
	print 
	if userpage.namespace()==2 and not '/' in userpage.title():
	    processUser(cursor, userpage)

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
