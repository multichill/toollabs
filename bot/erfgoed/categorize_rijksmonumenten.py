#!/usr/bin/python
# -*- coding: utf-8  -*-
'''

Bot to move images from http://commons.wikimedia.org/wiki/Category:Rijksmonumenten to subcategories based on the Rijksmonument template and Commonscat links at the nl Wikipedia.

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

def categorizeImage(page, conn, cursor):
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
		
    rijksmonumentenLijst = getList(rijksmonumentid, conn, cursor)
    if not rijksmonumentenLijst:
	return False

    oldtext = page.get()
    currentcats = page.categories()
    newcats = getCategories(rijksmonumentenLijst) 
    if newcats:
	for currentcat in currentcats:
	    if not currentcat.title()==u'Category:Rijksmonumenten':
		newcats.append(currentcat)
	# Remove dupes
	newcats = list(set(newcats))
	newtext = wikipedia.replaceCategoryLinks(oldtext, newcats)

	comment = u'Adding categories based on Rijksmonument identifier'
	wikipedia.showDiff(oldtext, newtext)
	page.put(newtext, comment)


def getList(rijksmonumentid, conn, cursor):
    '''
    Get images both in categoryA and in categoryB
    '''
    result = None

    query = u"""SELECT source FROM monumenten WHERE objrijksnr=%s LIMIT 1""";

    cursor.execute(query % (rijksmonumentid,))

    try:
	row = cursor.fetchone()
	(pagelink,) = row
    except TypeError:
	return False

    regex = u'^http://nl.wikipedia.org/w/index.php\?title=(Lijst_van_rijksmonumenten_.+)&redirect=no&useskin=monobook&oldid=\d+$'
    
    match = re.search(regex, pagelink)
    if not match:
	return False
 
    page_title= match.group(1)
    site = wikipedia.getSite(u'nl', u'wikipedia')

    return wikipedia.Page(site, page_title)

def getCategories(page):
    '''
    Get Commons categories based on page.
    1. If page contains a Commonscat template, use that category
    2. Else pull Commonscat links from upper categories
    '''
    result = []
    if u'Commonscat' in page.templates():
	result.append(getCategoryFromCommonscat(page))
    else:
	for cat in page.categories():
	    if u'Commonscat' in cat.templates():
		result.append(getCategoryFromCommonscat(cat))

    return result


def getCategoryFromCommonscat(page):
    '''
    Get a Commons category based on a page with a Commonscat template
    '''

    for (template, params) in page.templatesWithParams():
        if template==u'Commonscat':
            if len(params)==1:
                cat_title = params[0]
                break
    site = wikipedia.getSite(u'commons', u'commons')
    cat = catlib.Category(site, cat_title)

    return cat

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
	    categorizeImage(page, conn, cursor)

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
