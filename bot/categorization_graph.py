#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Generate stats to create a nice diagram
'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, MySQLdb, config
from datetime import datetime
from datetime import timedelta

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect(config.db_hostname, db='commonswiki_p', user = config.db_username, passwd = config.db_password)
    cursor = conn.cursor()
    return (conn, cursor)

def getCount(cursor, query, dates):
    '''
    Return the result of the query
    '''
    cursor.execute(query, dates)
    
    count, = cursor.fetchone()
    return count


def getDayStats(cursor, date):
    '''
    Date should be in the form 20081231
    '''
    queryDeletedImages = "SELECT COUNT(DISTINCT(fa_name)) FROM filearchive WHERE %s <= fa_timestamp AND fa_timestamp < %s"
    queryTotalImages = "SELECT COUNT(DISTINCT(img_name)) FROM image WHERE %s <= img_timestamp AND img_timestamp < %s"
    queryUncategorizedImages = "SELECT COUNT(DISTINCT(img_name)) FROM image JOIN page ON img_name=page_title JOIN templatelinks ON page_id=tl_from WHERE %s <= img_timestamp AND img_timestamp < %s AND page_namespace=6 AND page_is_redirect=0 AND tl_namespace=10 AND (tl_title ='Uncategorized' OR tl_title='Uncategorized-BArch')"
    queryToBeCheckedImages = "SELECT COUNT(DISTINCT(img_name)) FROM image JOIN page ON img_name=page_title JOIN templatelinks ON page_id=tl_from WHERE %s <= img_timestamp AND img_timestamp < %s AND page_namespace=6 AND page_is_redirect=0 AND tl_namespace=10 AND tl_title ='Check_categories'"


    #Get deleted images
    deletedImages = getCount(cursor, queryDeletedImages, (str(date) + u'000000', str(date) + u'999999'))
    #Get total images
    totalImages = getCount(cursor, queryTotalImages, (str(date) + u'000000', str(date) + u'999999'))
    #Get uncategorized images
    uncategorizedImages = getCount(cursor, queryUncategorizedImages, (str(date) + u'000000', str(date) + u'999999'))
    #Get images to be checked
    toBeCheckedImages = getCount(cursor, queryToBeCheckedImages, (str(date) + u'000000', str(date) + u'999999'))

    okImages = totalImages - uncategorizedImages - toBeCheckedImages

    return (deletedImages, okImages, uncategorizedImages, toBeCheckedImages)

def main():
    '''
    The main loop
    '''
    wikipedia.setSite(wikipedia.getSite(u'commons', u'commons'))
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()
    
    # Get datetime to start with
    date = datetime(2008, 12, 01)

    # Print the header
    print 'Date, deleted, ok, uncategorized, to be checked'
    while(date < datetime.utcnow()):
	(deletedImages, okImages, uncategorizedImages, toBeCheckedImages) = getDayStats(cursor, date.strftime('%Y%m%d'))
	print date.strftime('%Y%m%d') + u', ' + str(deletedImages) + u', ' + str(okImages) + u', ' + str(uncategorizedImages) + u', ' + str(toBeCheckedImages)
	date = date + timedelta(days=1)
    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
