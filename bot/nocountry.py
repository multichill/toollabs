#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Generate a list of categories which appear to be related to a country, but not a subcategory of this country.
Put the list at http://commons.wikimedia.org/wiki/User:Multichill/No_country
'''
import sys
import wikipedia, MySQLdb, config

def connectDatabase():
    conn = MySQLdb.connect(u'commonswiki.labsdb', db='u_multichill_commons_categories_p', user = config.db_username, passwd = config.db_password)
    cursor = conn.cursor()
    return (conn, cursor)

def getCountryList(cursor):
    '''
    Get the list of countries
    '''
    query = u"SELECT pl_title FROM commonswiki_p.page JOIN commonswiki_p.pagelinks ON page_id=pl_from WHERE page_namespace=2 AND page_is_redirect=0 AND page_title = 'Multichill/Countries' AND pl_namespace=14"
    cursor.execute(query)
    result = []
    while True:
	try:
	    country, = cursor.fetchone()
	    result.append(unicode(country, 'utf-8'))
	except TypeError:
	    # Limit reached or no more results
	    break
    return result

def getNoCountry(cursor, country):
    '''
    Get a list of categories which end with <country> which are not category redirects and where the parent does not end with <country>,
    the parent of this parent does not end with <country> and the parent of this parent does not end with <country>. (so we travel up 3 levels)
    '''
    cursor.execute(u"SELECT DISTINCT(c1.child) FROM cats AS c1 WHERE c1.child LIKE %s AND NOT EXISTS(SELECT * FROM cats AS c2 JOIN cats AS c3 ON (c2.parent=c3.child) JOIN cats AS c4 ON (c3.parent=c4.child) WHERE c1.child=c2.child AND (c2.parent LIKE %s OR c3.parent LIKE %s OR c4.parent LIKE %s OR c2.parent='Category_redirects')) AND NOT c1.child=%s", ('%_' + country, '%' + country + '%', '%' + country + '%', '%' + country + '%', country))
    result = []
    while True:
	try:
	    cat, = cursor.fetchone()
	    cat = unicode(cat, 'utf-8')
	    #print cat + country
	    result.append((cat, country))
	except TypeError:
	    # Limit reached or no more results
	    break
    return result

def outputResult(missingCatsTotal):
    '''
    Ouput the result to Commons
    '''
    resultwiki = u''
    page = wikipedia.Page(wikipedia.getSite(u'commons', u'commons'), u'User:Multichill/No_country')
    comment = u'A list categories which should be subcategories of some country'
    for (cat, country) in missingCatsTotal:
	resultwiki = resultwiki +  u'*[[:Category:' + cat + u']] should be a subcategory of [[:Category:' + country + u']]\n'
    resultwiki = resultwiki.replace(u'_', u' ')
    page.put(resultwiki, comment)

def main():
    conn = None
    cursor = None
    missingCatsTotal = []
    (conn, cursor) = connectDatabase()
    countries = getCountryList(cursor)
    

    for country in countries:
    	missingCats = getNoCountry(cursor, country)
    	if missingCats:
    	    missingCatsTotal = missingCatsTotal + missingCats
    for (a, b) in missingCatsTotal:
    	print a + ' should be in ' + b

    outputResult(missingCatsTotal)
    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
