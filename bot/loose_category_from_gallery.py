#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, MySQLdb, config, imagerecat

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect(config.db_hostname, db='commonswiki_p', user = config.db_username, passwd = config.db_password)
    cursor = conn.cursor()
    return (conn, cursor)


def getImagesToCategorize(cursor, uncat):
    '''
    Get all images with are in a subcategory of Media needing categories and which are in use in a gallery which has a category with the same name. The gallery should be in the category or the gallery and the category should share the same parent category'

    '''
    query=u"SELECT ipage.page_title AS img, gpage.page_title AS gal, galcl.cl_to AS cat FROM page AS ipage JOIN categorylinks AS uncl ON ipage.page_id=uncl.cl_from JOIN imagelinks ON ipage.page_title=il_to JOIN page AS gpage ON il_from=gpage.page_id JOIN categorylinks AS galcl ON gpage.page_id=galcl.cl_from WHERE ipage.page_namespace=6 AND ipage.page_is_redirect=0 AND gpage.page_namespace=0 AND gpage.page_is_redirect=0 AND uncl.cl_to = %s"
    
    result = []
    lastimage = ''
    lastgal = ''
    lastcat = ''

    gals = []
    cats = []

    cursor.execute(query, (uncat.replace(' ', '_'),))
    while True:
	try:
	    image, gal, cat = cursor.fetchone()
	    #The start
	    if(lastimage==''):
		lastimage = image
		gals.append((unicode(gal, 'utf-8')))
		cats.append((unicode(cat, 'utf-8')))
	    elif(lastimage==image):
		gals.append((unicode(gal, 'utf-8')))
                cats.append((unicode(cat, 'utf-8')))
	    else:
		#Add the previous image and do some cleanup
		result.append((unicode(lastimage, 'utf-8'), list(set(gals)), list(set(cats))))
		lastimage= ''
		gals = []
		cats = []
		# Start over
                lastimage = image
                gals.append((unicode(gal, 'utf-8')))
                cats.append((unicode(cat, 'utf-8')))
	except TypeError:
	    # Limit reached or no more results
	    if(lastimage!=''):
		result.append((unicode(lastimage, 'utf-8'), list(set(gals)), list(set(cats))))
	    break
    return result

def categorizeImage(image, gals, cats):
    '''
    Replace uncategorized with a category
    '''
    page = wikipedia.Page(wikipedia.getSite(), u'Image:' + image)
    #category = category.replace('_', ' ')
    if (page.exists() and gals and cats):
	newtext = imagerecat.removeTemplates(page.get())
	newtext = newtext + imagerecat.getCheckCategoriesTemplate([], gals)
	for category in cats:
	    newtext = newtext + u'[[Category:' + category.replace('_', ' ') + u']]\n'
	comment = u'Adding one or more categories (based on gallery information) to this uncategorized image'
	wikipedia.showDiff(page.get(), newtext)
	page.put(newtext, comment)

def main():
    '''
    The main loop
    '''
    wikipedia.setSite(wikipedia.getSite(u'commons', u'commons'))
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()

    imagerecat.initLists()
    generator = None
    for arg in wikipedia.handleArgs():
        if arg.startswith('-page'):
            if len(arg) == 5:
                generator = [wikipedia.Page(wikipedia.getSite(), wikipedia.input(u'What page do you want to use?'))]
            else:
                generator = [wikipedia.Page(wikipedia.getSite(), arg[6:])]
        else:
            generator = genFactory.handleArg(arg)
    if generator:
        for page in generator:
	    if((page.namespace() == 14) and (page.title().startswith(u'Category:Media needing categories as of'))):
		for (image, gals, cats) in getImagesToCategorize(cursor, page.titleWithoutNamespace()):
		    categorizeImage(image, gals, imagerecat.applyAllFilters(cats))
	

    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
