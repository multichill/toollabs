#!/usr/bin/python
# -*- coding: utf-8  -*-
'''

Bot to add topic a topic category to images with only a Rijksmonumenten category.

'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, pagegenerators, catlib
import re, imagerecat
import MySQLdb, config

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect('sql.toolserver.org', db='p_erfgoed_p', user = config.db_username, passwd = config.db_password, use_unicode=True, charset='utf8')
    cursor = conn.cursor()
    return (conn, cursor)

def addTopicCategory(page, conn, cursor):
    wikipedia.output(u'Working on: %s' % page.title())
    
    templates = page.templates()
    if not u'Rijksmonument' in page.templates():
	wikipedia.output(u'Rijksmonument template not found at: %s' % page.title())
	return False

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
		
    oorspr_functie = getOorspronkelijkeFunctie(rijksmonumentid, conn, cursor)
    if not oorspr_functie:
	wikipedia.output(u'No oorspr_functie found')
	return False

    oldtext = page.get()
    newtext = oldtext + u'{{subst:Rijksmonument category|%s|subst=subst:}}' % (oorspr_functie,)
    
    comment = u'Adding [[Template:Rijksmonument category|"%s" category]] based on Rijksmonument identifier' % (oorspr_functie,)
    wikipedia.showDiff(oldtext, newtext)
    page.put(newtext, comment)


def getOorspronkelijkeFunctie(rijksmonumentid, conn, cursor):
    '''
    Get the object type
    Get images both in categoryA and in categoryB
    '''
    result = u''

    query = u"""SELECT oorspr_functie FROM monumenten WHERE type_obj='G' AND objrijksnr=%s LIMIT 1""";

    cursor.execute(query % (rijksmonumentid,))

    try:
	row = cursor.fetchone()
	(result,) = row
    except TypeError:
	return False

    return result

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
	    addTopicCategory(page, conn, cursor)

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
