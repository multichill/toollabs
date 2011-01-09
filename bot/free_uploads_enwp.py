#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Program to update http://en.wikipedia.org/wiki/User:Multichill/Free_uploads
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
    conn = MySQLdb.connect('enwiki-p.db.toolserver.org', db='enwiki_p', user = config.db_username, passwd = config.db_password, use_unicode=True)

    cursor = conn.cursor()
    return (conn, cursor)

def dailyFreeUploadsPage(images, day):
    '''
    Create, update or blank a daily free upload page
    '''
    site = wikipedia.getSite(u'en', u'wikipedia')
    daypage = wikipedia.Page(site, u'User:Multichill/Free_uploads/%d-%02d-%02d' % (day.year, day.month, day.day))

    wikipedia.output(u'Working on %s' % (daypage.title(),))
    if daypage.exists():
	oldtext = daypage.get()
    else:
	oldtext = u''

    if images:
	# Should probably make some sort of pretty header
	text = u'<gallery>\n'
	for image in images:
	    text = text + u'File:%s\n' % (image,)
	text = text + u'</gallery>\n'
	comment = u'Updating list of free images, %d images left' % (len(images),)
	if not(oldtext.strip()==text.strip()):
	    wikipedia.showDiff(oldtext, text)
	    wikipedia.output(comment)
	    daypage.put(text, comment)

	return daypage.title()

    # Images is empty
    else:
	# Should do something if the page is blank for x days
	if daypage.exists() and not oldtext==u'':
	    text = u''
	    comment = u'No images left. Blanking the page'
	    wikipedia.showDiff(oldtext, text)
	    wikipedia.output(comment)
	    daypage.put(text, comment)

	# No page so return nothing
	return u''

def dailyFreeUploadsQuery(cursor, day):
    '''
    Get the free images uploaded on a certain day
    '''
    query = u"""SELECT page_title FROM image 
    JOIN page ON img_name=page_title 
    JOIN categorylinks AS cl1 ON page_id=cl_from
    WHERE img_timestamp LIKE '%d%02d%02d______'
    AND page_namespace=6
    AND cl_to='All_free_media' 
    AND NOT EXISTS(
    SELECT * FROM categorylinks AS cl2
    WHERE cl_from=page_id
    AND (cl_to='All_non-free_media'
    OR cl_to='All_Wikipedia_files_with_unknown_copyright_status'
    OR cl_to='All_Wikipedia_files_with_unknown_source'
    OR cl_to='All_Wikipedia_files_with_no_copyright_tag'
    OR cl_to='All_possibly_unfree_Wikipedia_files'
    OR cl_to='Non-free_Wikipedia_files_with_valid_backlink'
    OR cl_to='Uploaded_from_Commons_main_page_images'
    OR cl_to LIKE 'Wikipedia\_files\_with\_the\_same\_name\_on\_Wikimedia\_Commons%%'
    OR cl_to LIKE 'Wikipedia\_files\_with\_a\_different\_name\_on\_Wikimedia\_Commons%%'))
    ORDER BY page_title ASC"""

    images = []
    cursor.execute(query % (day.year, day.month, day.day))
    result = cursor.fetchall()
    
    for (image,) in result:
	images.append(unicode(image, 'utf-8'))

    return images

def writeMainFreeUploads(subpages):
    site = wikipedia.getSite(u'en', u'wikipedia')
    page = wikipedia.Page(site, u'User:Multichill/Free_uploads')
    oldtext = page.get()
    text = u'__TOC__\n'
    text = text + u'== Links to day pages ==\n'
    text = text + u'{{Special:PrefixIndex/User:Multichill/Free uploads/20}}\n'
    text = text + u'== Days ==\n'

    for subpage in subpages:
	date = subpage.replace(u'User:Multichill/Free uploads/', u'')
	text = text + u'===[[%s|%s]]===\n' % (subpage, date)
	text = text + u'{{%s}}\n' % (subpage,)

    comment = u'Updating list, %d subpages contain images' % (len(subpages),)
    wikipedia.showDiff(oldtext, text)
    wikipedia.output(comment)
    page.put(text, comment)

def main():
    startdate = datetime(2010, 12, 29)
    today = datetime.utcnow()
    subpages = []

    (conn, cursor) = connectDatabase()

    day = startdate
    while day < today:
	images = dailyFreeUploadsQuery(cursor, day)
	subpage = dailyFreeUploadsPage(images, day)
	if subpage:
	    subpages.append(subpage)
	day = day + timedelta(days=+1)

    writeMainFreeUploads(subpages)

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
