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

def getRijksmonumentid(page, conn, cursor):
    
    regex = u'\d{5,20}'
    match = re.search(regex, page.titleWithoutNamespace())

    if match:
	wikipedia.output(u'Working on: %s' % page.title())
	wikipedia.output(match.group(0))
	return match.group(0)

    return False
    
    '''


    rijksmonumentid=-1
    
    for (template, params) in page.templatesWithParams():
	if template==u'Rijksmonument':
	    if len(params)==1:
		try:
		    rijksmonumentid = int(params[0])
		except ValueError:
		    wikipedia.output(u'Unable to extract a valid id')
		break

    if (rijksmonumentid < 0 or 600000 < rijksmonumentid ):
	wikipedia.output(u'Invalid id')
	return False
		
    coordinates = getCoordinates(rijksmonumentid, conn, cursor)
    if not coordinates:
	return False
    
    (lat, lon, source) = coordinates

    locationTemplate = u'{{Object location dec|%s|%s|region:NL_type:landmark_scale:1500}}<!-- Location from %s -->' % (lat, lon, source)

    return locationTemplate
    '''

def addRijksmonumentid(page, rijksmonumentid):
    oldtext = page.get()

    comment = u'Adding Rijksmonument id %s based on filename' % (rijksmonumentid,)

    newtext = u'{{Rijksmonument|%s}}\n' % (rijksmonumentid,) + oldtext
    
    wikipedia.showDiff(oldtext, newtext)
    page.put(newtext, comment)

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

def putAfterTemplate (page, template, toadd, loose=True):
    '''
    Try to put text after template.
    If the template is not found return False if loose is set to False
    If loose is set to True: Remove interwiki's, categories, add template, restore categories, restore interwiki's.

    Based on cc-by-sa-3.0 code by Dschwen
    '''
    oldtext = page.get()
    newtext = u''

    templatePosition = oldtext.find(u'{{%s' % (template,))

    if templatePosition >= 0:
	previousChar = u''
	currentChar = u''
	templatePosition += 2
	curly = 1
	square = 0
	
	while templatePosition < len(oldtext):
	    currentChar = oldtext[templatePosition]

	    if currentChar == u'[' and previousChar == u'[' :
		square += 1
                previousChar = u''
            if currentChar == u']' and previousChar == u']' :
                square -= 1
                previousChar = u''
            if currentChar == u'{' and previousChar == u'{' :
                curly += 1
                previousChar = u''
            if currentChar == u'}' and previousChar == u'}' :
                curly -= 1
                previousChar = u''

	    previousChar = currentChar
	    templatePosition +=1

	    if curly == 0 and square <= 0 :
		# Found end of template
		break
	newtext = oldtext[:templatePosition] + u'\n' + toadd + oldtext[templatePosition:]
    
    else:
	if loose:
	    newtext = oldtext
	    cats = wikipedia.getCategoryLinks(newtext)
	    ll = wikipedia.getLanguageLinks(newtext)
	    nextext = wikipedia.removeLanguageLinks (newtext)
	    newtext = wikipedia.removeCategoryLinks(newtext)
	    newtext = newtext + u'\n' + toadd
	    newtext = wikipedia.replaceCategoryLinks(newtext, cats)
	    newtext = wikipedia.replaceLanguageLinks(newtext, ll)
    
    return newtext


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
	    rijksmonumentid = getRijksmonumentid(page, conn, cursor)
	    if rijksmonumentid:
	    	addRijksmonumentid(page, rijksmonumentid)

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
