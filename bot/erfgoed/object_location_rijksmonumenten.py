#!/usr/bin/python
# -*- coding: utf-8  -*-
'''

Bot to add {{Object location dec}} to rijksmonumenten. Location is based on information from the nl Wikipedia.

'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, pagegenerators, catlib
import re, imagerecat
import MySQLdb, config, time

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect('sql.toolserver.org', db='p_erfgoed_p', user = config.db_username, passwd = config.db_password, use_unicode=True, charset='utf8')
    cursor = conn.cursor()
    return (conn, cursor)

def locateImage(page, conn, cursor):
    wikipedia.output(u'Working on: %s' % page.title())
    
    templates = page.templates()

    if u'Location' in page.templates() or u'Location dec' in page.templates() or u'Object location' in page.templates() or u'Object location dec' in page.templates():
	wikipedia.output(u'Location template already found at: %s' % page.title())
	return False

    if not u'Rijksmonument' in page.templates():
	wikipedia.output(u'Rijksmonument template not found at: %s' % page.title())
	return False

    rijksmonumentid=-1
    
    for (template, params) in page.templatesWithParams():
	if template==u'Rijksmonument':
	    if len(params)==1:
		rijksmonumentid = int(params[0])
		break

    if (rijksmonumentid < 0 or 600000 < rijksmonumentid ):
	wikipedia.output(u'Invalid id')
	return False
		
    coordinates = getCoordinates(rijksmonumentid, conn, cursor)
    if not coordinates:
	return False
    
    (lat, lon, source) = coordinates

    locationTemplate = u'{{Object location dec|%s|%s|region:NL_type:landmark_scale:1500}}<!-- Location from %s -->' % (lat, lon, source)

    wikipedia.output(locationTemplate)
    return locationTemplate

def addLocation (page, locationTemplate):
    oldtext = page.get()

    comment = u'Adding object location based on Rijksmonument identifier'
    newtext = oldtext + u'\n' + locationTemplate
    
    wikipedia.showDiff(oldtext, newtext)
    page.put(newtext, comment)
    time.sleep(10)


def getCoordinates(rijksmonumentid, conn, cursor):
    '''
    Get coordinates from the erfgoed database
    '''
    result = None

    query = u"""SELECT lat, lon, source FROM monumenten WHERE objrijksnr=%s LIMIT 1""";

    cursor.execute(query % (rijksmonumentid,))

    try:
	row = cursor.fetchone()
	return row
    except TypeError:
	return False

def main():
    wikipedia.setSite(wikipedia.getSite(u'commons', u'commons'))

    # Connect database, we need that
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()

    generator = None
    genFactory = pagegenerators.GeneratorFactory()

    for arg in wikipedia.handleArgs():
	genFactory.handleArg(arg)

    generator = genFactory.getCombinedGenerator()

    if generator:
	# Get a preloading generator with only images
	pgenerator = pagegenerators.PreloadingGenerator(pagegenerators.NamespaceFilterPageGenerator(generator, [6]))
	for page in pgenerator:
	    locationTemplate = locateImage(page, conn, cursor)
	    if locationTemplate:
		addLocation(page, locationTemplate)

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
