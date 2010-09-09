#!/usr/bin/python
# -*- coding: utf-8  -*-
'''

Make a gallery of unused photos so people can add them

'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, pagegenerators, catlib
import re, imagerecat
import MySQLdb, config, time

def connectDatabase():
    '''
    Connect to the rijksmonumenten mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect('sql.toolserver.org', db='p_erfgoed_p', user = config.db_username, passwd = config.db_password, use_unicode=True, charset='utf8')
    cursor = conn.cursor()
    return (conn, cursor)

def connectDatabase2():
    '''
    Connect to the commons mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect('commonswiki-p.db.toolserver.org', db='commonswiki_p', user = config.db_username, passwd = config.db_password, use_unicode=True, charset='utf8')
    cursor = conn.cursor()
    return (conn, cursor)

def getRijksmonumentenWithoutPhoto(conn, cursor):
    result = {}

    query = u"""SELECT objrijksnr, source FROM monumenten WHERE image=''""";


    cursor.execute(query)

    while True:
	try:
	    row = cursor.fetchone()
	    (objrijksnr, source) = row
	    result[objrijksnr] = source
	except TypeError:
	    break

    return result

def getRijksmonumentenPhotos(conn, cursor):
    result = {}

    query = u"""SELECT page_title, cl_sortkey FROM page JOIN categorylinks ON page_id=cl_from WHERE page_namespace=6 AND page_is_redirect=0 AND cl_to='Rijksmonumenten_with_known_IDs'""";

    cursor.execute(query)

    while True:
        try:
            row = cursor.fetchone()
            (image, objrijksnr) = row
            result[objrijksnr] = image
        except TypeError:
            break

    return result


def main():
    # Connect database, we need that
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()
    (conn2, cursor2) = connectDatabase2()

    withoutPhoto = getRijksmonumentenWithoutPhoto(conn, cursor)
    photos = getRijksmonumentenPhotos(conn2, cursor2)

    text = u'<gallery>\n'
    for objrijksnr in sorted(photos.keys()):
	try:
	    if int(objrijksnr) in withoutPhoto:
		wikipedia.output(u'Key %s returned a result' % (objrijksnr,))
		wikipedia.output(withoutPhoto.get(int(objrijksnr)))
		wikipedia.output(photos.get(objrijksnr))
		text = text + u'File:%s|[%s %s]\n' % (photos.get(objrijksnr), withoutPhoto.get(int(objrijksnr)), int(objrijksnr))
	except ValueError:
	    wikipedia.output(u'Got value error for %s' % (objrijksnr,))
	    
    text = text + u'</gallery>' 
    comment = u'Plaatjes om in te voegen'
    
    site = wikipedia.getSite(u'nl', u'wikipedia')
    page = wikipedia.Page(site, u'Wikipedia:Wikiproject/Erfgoed/Nederlandse_Erfgoed_Inventarisatie/Ongebruikte_foto\'s')
    page.put(text, comment)

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
