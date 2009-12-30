#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Update the stats at http://commons.wikimedia.org/wiki/User:Multichill/Categorization_stats
'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, MySQLdb, config
from datetime import datetime

new_marker = u'<!-- Add new categorization stats here -->'

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect('commonswiki-p.db.toolserver.org', db='commonswiki_p', user = config.db_username, passwd = config.db_password)
    cursor = conn.cursor()
    return (conn, cursor)

def getCount(cursor, query):
    '''
    Return the result of the query
    '''
    cursor.execute(query)
    
    count, = cursor.fetchone()
    return count

def updateStats(date, uncatCount, checkCount, totalCount):
    '''
    Update the stats
    '''
    page = wikipedia.Page(wikipedia.getSite(), u'User:Multichill/Categorization_stats')
    
    newstats = u'|-\n|' + str(date) + u'\n|' + str(uncatCount) + u'\n|' + str(checkCount) + u'\n|' + str(totalCount) + u'\n' 
    newtext = page.get()

    if newtext.find(new_marker)==-1:
	wikipedia.output(u'No marker found!')
	newtext = newtext + newstats + new_marker
    else:
	newtext = newtext.replace(new_marker, newstats + new_marker)

    comment = u'Updating stats: ' + str(uncatCount) + u' uncategorized files, ' + str(checkCount) + u' files to be checked, ' + str(totalCount) + u' files in total'
    wikipedia.output(comment)
    wikipedia.showDiff(page.get(), newtext)
    page.put(newtext = newtext, comment = comment)

def main():
    '''
    The main loop
    '''
    wikipedia.setSite(wikipedia.getSite(u'commons', u'commons'))
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()
    
    # Get datetime
    date = datetime.utcnow().strftime('%Y%m%d%H%M')

    # Get number of uncategorized files
    uncatQuery=u"SELECT COUNT(DISTINCT(page_title)) FROM page JOIN categorylinks ON page_id=cl_from WHERE page_namespace=6 AND page_is_redirect=0 AND cl_to LIKE 'Media\_needing\_categories\_as\_of\_%'"
    uncatCount = getCount(cursor, uncatQuery)

    # Get number of files to be checked
    checkQuery=u"SELECT COUNT(DISTINCT(page_title)) FROM page JOIN categorylinks ON page_id=cl_from WHERE page_namespace=6 AND page_is_redirect=0 AND cl_to LIKE 'Media\_needing\_category\_review\_as\_of\_%'"
    checkCount = getCount(cursor, checkQuery)

    # Get total
    totalCount = int(uncatCount) + int(checkCount)

    # Update the stats page with this number
    updateStats(date, uncatCount, checkCount, totalCount)
    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
