#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Update the stats at 

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
    conn = MySQLdb.connect('nlwiki-p.db.toolserver.org', db='nlwiki_p', user = config.db_username, passwd = config.db_password, use_unicode=True)
    cursor = conn.cursor()
    return (conn, cursor)

def getNumberOfItems(cursor):
    '''
    Get the number of items on each Lijst_van rijksmonumenten_in_.... page
    '''
    query = u"""SELECT page_title, COUNT(el_to) AS count FROM page
		LEFT JOIN externallinks ON page_id=el_from
		WHERE page_title LIKE 'Lijst\_van\_rijksmonumenten\_in\_%' 
		AND page_namespace=0 AND page_is_redirect=0 
		AND el_to LIKE 'http://nl.rijksmonumenten.wikia.com/wiki/Rijksmonumentnummer%'
		GROUP BY(page_title)
		ORDER BY page_title ASC"""
    cursor.execute(query)
    result = {}

    while True:
	try:
	    row = cursor.fetchone()
	    (pageTitle, count) = row
	    result[pageTitle] = count
	except TypeError:
	    break
    return result
    

def getNumberOfImages(cursor):
    '''
    Get the number of images on each Lijst_van rijksmonumenten_in_.... page
    '''
    query = u"""SELECT page_title, COUNT(foto.il_to) AS count FROM page
		LEFT JOIN imagelinks AS foto ON page_id=foto.il_from 
		WHERE page_title LIKE 'Lijst\_van\_rijksmonumenten\_in\_%' 
		AND page_namespace=0 AND page_is_redirect=0 
		AND NOT EXISTS(SELECT * FROM page 
		JOIN imagelinks AS plaatje ON page_id=plaatje.il_from 
		WHERE page_namespace=10 
		AND page_is_redirect=0 
		AND page_title='Tabelrij_rijksmonument' 
		AND foto.il_to=plaatje.il_to) 
		GROUP BY(page_title)"""    
    cursor.execute(query)
    result = {}

    while True:
        try:
            row = cursor.fetchone()
            (pageTitle, count) = row
            result[pageTitle] = count
        except TypeError:
            break
    return result

def updateStats(items, images):
    '''
    Update the stats
    '''
    page = wikipedia.Page(wikipedia.getSite(), u'Wikipedia:Wikiproject/Erfgoed/Afbeeldingen_rijksmonumenten')

    newtext = u'{{Wikipedia:Wikiproject/Erfgoed/Afbeeldingen_rijksmonumenten/Header}}\n'

    totalItems = 0
    totalImages = 0

    pages = items.keys()
    pages.sort()

    for key in pages:
	newtext = newtext + u'{{Wikipedia:Wikiproject/Erfgoed/Afbeeldingen_rijksmonumenten/Row'
	newtext = newtext + u'|plaats=' + key.replace(u'Lijst_van_rijksmonumenten_in_', '') 
	newtext = newtext + u'|items=' + str(items.get(key))
	totalItems = totalItems + items.get(key)
	if images.get(key):
	    newtext = newtext + u'|images=' + str(images.get(key)) + u'}}\n'
	    totalImages = totalImages + images.get(key)
	else:
	    newtext = newtext + u'|images=0}}\n'

    newtext = newtext + u'{{Wikipedia:Wikiproject/Erfgoed/Afbeeldingen_rijksmonumenten/Footer'
    newtext = newtext + u'|items=' + str(totalItems)
    newtext = newtext + u'|images=' + str(totalImages)
    newtext = newtext + u'}}\n'
    
    comment = u'Bijwerken statistieken: ' + str(totalItems) + u' monumenten met ' + str(totalImages) + u' afbeeldingen'
    wikipedia.output(comment)
    wikipedia.showDiff(page.get(), newtext)
    page.put(newtext = newtext, comment = comment)

def main():
    '''
    The main loop
    '''
    wikipedia.setSite(wikipedia.getSite(u'nl', u'wikipedia'))
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()

    items = getNumberOfItems(cursor)
    images = getNumberOfImages(cursor)

    updateStats(items, images)
    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
