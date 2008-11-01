#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Create a list of possible categories to create based on uncategorized images which are in use in one or more galleries.
'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, MySQLdb, config
'''
todo = [u'Media_needing_categories_as_of_27_July_2008',
	u'Media_needing_categories_as_of_28_July_2008',
	u'Media_needing_categories_as_of_29_July_2008',
	u'Media_needing_categories_as_of_30_July_2008',
	u'Media_needing_categories_as_of_31_July_2008',
	]
'''
todo = [u'Media_needing_category_review_as_of_16_August_2008',
	u'Media_needing_category_review_as_of_17_August_2008',
	u'Media_needing_category_review_as_of_19_August_2008',
	u'Media_needing_category_review_as_of_20_August_2008',
	u'Media_needing_category_review_as_of_21_August_2008',
	u'Media_needing_category_review_as_of_22_August_2008',
	u'Media_needing_category_review_as_of_23_August_2008',
	]


def connectDatabase():
    conn = MySQLdb.connect(config.db_hostname, db='commonswiki_p', user = config.db_username, passwd = config.db_password)
    cursor = conn.cursor()
    return (conn, cursor)

def getCategorySuggestions(cursor, cat):
    query = u"SELECT img.page_title AS image, gal.page_title AS gallery, galcat.cl_to AS category FROM page AS img JOIN categorylinks AS ccl ON page_id=ccl.cl_from JOIN imagelinks ON img.page_title=il_to  JOIN page AS gal ON il_from=gal.page_id JOIN categorylinks AS galcat ON gal.page_id=galcat.cl_from WHERE img.page_namespace=6 AND img.page_is_redirect=0 AND ccl.cl_to=%s AND gal.page_namespace=0 AND gal.page_is_redirect=0"

    cursor.execute(query, (cat,))
    result = []
    while True:
	try:
	    image, gallery, category, = cursor.fetchone()
	    result.append(((unicode(image, 'utf-8')), (unicode(gallery, 'utf-8')), (unicode(category, 'utf-8'))))
	except TypeError:
	    # Limit reached or no more results
	    break
    return result

def outputResult(uncat, suggestions):
    page = wikipedia.Page(wikipedia.getSite(u'commons', u'commons'), u'User:Multichill/Category_suggestions2')
    resultwiki = page.get()
    resultwiki = resultwiki + u'\n==[[:Category:' + uncat + u']]==\n'
    resultwiki = resultwiki + u'{{User:Multichill/Category_suggestions2/header}}\n'
    comment = u'Added a the list of category suggestions for images in [[:Category' + uncat + u']]'
    lastimage = u''
    lastgallery = u''
    for (image, gallery, category) in suggestions:
	resultwiki = resultwiki + u'|-\n'
	if (image != lastimage):
	    resultwiki = resultwiki + u'| style="background-color:#ffff00;" | [[:Image:' + image.replace(u'_', u' ') + u'|' + image.replace(u'_', u' ')  + u']]\n'
	    lastgallery = u''
	else:
	    resultwiki = resultwiki + u'|\n'
	lastimage = image
	if (gallery != lastgallery):
	    resultwiki = resultwiki + u'| style="background-color:#ffff00;" | [[' + gallery.replace(u'_', u' ') + u']]\n'
	else:
	    resultwiki = resultwiki + u'|\n'
	lastgallery = gallery
	resultwiki = resultwiki + u'| style="background-color:#ffff00;" | [[:Category:' + category.replace(u'_', u' ') + u'|' + category.replace(u'_', u' ')  + u']]\n'
    resultwiki = resultwiki + u'|}\n'
    page.put(resultwiki, comment)

def main():
    conn = None
    cursor = None
    suggestions = []
    uncat = u'Media_needing_categories_as_of_27_July_2008'
    (conn, cursor) = connectDatabase()
    for cat in todo:
	suggestions = getCategorySuggestions(cursor, cat)
	outputResult(cat, suggestions)
    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
