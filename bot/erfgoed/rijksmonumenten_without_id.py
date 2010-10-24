#!/usr/bin/python
# -*- coding: utf-8  -*-
'''

Make a gallery of rijksmonumenten without an id at Commons

FIXME: Encoding issues.

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

def getRijksmonumentenWithPhoto(conn, cursor):
    result = {}

    query = u"""SELECT image, objrijksnr FROM monumenten WHERE NOT image=''""";


    cursor.execute(query)

    while True:
	try:
	    row = cursor.fetchone()
	    (image, objrijksnr) = row
	    result[image.replace(u' ', u'_')] = objrijksnr
	except TypeError:
	    break

    return result

def getRijksmonumentenWithoutTemplate(conn, cursor):
    result = []

    query = u"""SELECT DISTINCT(page_title) FROM page JOIN categorylinks ON page_id=cl_from WHERE page_namespace=6 AND page_is_redirect=0 AND (cl_to='Rijksmonumenten' OR cl_to LIKE 'Rijksmonumenten\_in\_%') AND NOT EXISTS(SELECT * FROM templatelinks WHERE page_id=tl_from AND tl_namespace=10 AND tl_title='Rijksmonument') ORDER BY page_title ASC"""

    cursor.execute(query)

    while True:
        try:
            row = cursor.fetchone()
            (image,) = row
            result.append(image.decode('utf-8'))
        except TypeError:
            break

    return result


def getRijksmonumentenWitIncorrectTemplate(conn, cursor):
    result = []
    query = u"""SELECT DISTINCT(page_title) FROM categorylinks JOIN page ON cl_from=page_id WHERE cl_to='Rijksmonumenten_with_known_IDs' AND (cl_sortkey=' 000000-1' OR cl_sortkey=' 00000000' OR cl_sortkey=' 0000000?' OR cl_sortkey=' onbekend') AND page_namespace=6 AND page_is_redirect=0 ORDER BY page_title ASC"""

    cursor.execute(query)

    while True:
        try:
            row = cursor.fetchone()
            (image,) = row
            result.append(image.decode('utf-8'))
        except TypeError:
            break

    return result

def main():
    # Connect database, we need that
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()
    (conn2, cursor2) = connectDatabase2()

    withPhoto = getRijksmonumentenWithPhoto(conn, cursor)
    withoutTemplate = getRijksmonumentenWithoutTemplate(conn2, cursor2)
    incorrectTemplate = getRijksmonumentenWitIncorrectTemplate(conn2, cursor2)

    text = u'<gallery>\n'
    for image in withoutTemplate + incorrectTemplate:
	if withPhoto.get(image):
	    text = text + u'File:%s|{{tl|Rijksmonument|%s}}\n' % (image, withPhoto.get(image))
	else:
	     text = text + u'File:%s\n' % (image,)
	    
    text = text + u'</gallery>' 
    comment = u'Plaatjes om id bij te zoeken'
    
    site = wikipedia.getSite(u'nl', u'wikipedia')
    page = wikipedia.Page(site, u'Wikipedia:Wikiproject/Erfgoed/Nederlandse Erfgoed Inventarisatie/Foto\'s zonder id')
    page.put(text, comment)

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
