#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
test
'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, MySQLdb, config

def connectDatabase():
    conn = MySQLdb.connect(config.db_hostname, db='u_multichill', user = config.db_username, passwd = config.db_password)
    cursor = conn.cursor()
    return (conn, cursor)

def getCountryList(cursor):
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
    cursor.execute(u"SELECT DISTINCT(c1.child), c6.child FROM cats AS c1 JOIN cats AS c5 ON c1.parent=c5.child JOIN cats AS c6 ON c5.parent = c6.parent WHERE c1.child LIKE %s AND NOT EXISTS(SELECT * FROM cats AS c2 JOIN cats AS c3 ON (c2.parent=c3.child) JOIN cats AS c4 ON (c3.parent=c4.child) WHERE c1.child=c2.child AND (c2.parent LIKE %s OR c3.parent LIKE %s OR c4.parent LIKE %s OR c2.parent='Category_redirects')) AND NOT c1.child=%s AND c5.child LIKE %s AND c5.parent LIKE %s AND c6.child LIKE %s", ('%_' + country, '%' + country + '%', '%' + country + '%', '%' + country + '%', country, '%_by_country', '%_by_country', '%' + country))
    result = []
    while True:
	try:
	    cat, cathint = cursor.fetchone()
	    cat = unicode(cat, 'utf-8')
	    print cat + cathint + country
	    result.append((cat, cathint, country))
	except TypeError:
	    # Limit reached or no more results
	    break
    return result

def outputResult(missingCatsTotal):
    resultscript = u'#!/usr/pkg/bin/bash\n'
    page = wikipedia.Page(wikipedia.getSite(u'commons', u'commons'), u'User:Multichill/No_country')
    comment = u'A list categories which should be subcategories of some country'
    for (cat, cathint, country) in missingCatsTotal:
	resultscript = resultscript + u'python2.4 add_text.py -always -lang:commons -family:commons -page:"Category:' + cat + u'" -text:"[[Category:' + cathint.replace(u'_', u' ') + u']]" -summary:"Adding [[Category:' + cathint.replace(u'_', u' ') + u']]"\n' 
    f = file("/home/multichill/queries/nocountryhints.txt", 'w')
    f.write(resultscript.encode('utf-8'))
    f.close()

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

    outputResult(missingCatsTotal)
    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
