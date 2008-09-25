#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
test
'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, MySQLdb, config

def connectDatabase():
    conn = MySQLdb.connect(config.db_hostname, db='commonswiki_p', user = config.db_username, passwd = config.db_password)
    cursor = conn.cursor()
    return (conn, cursor)

def getCountryList(cursor):
    query = u"SELECT pl_title FROM page JOIN pagelinks ON page_id=pl_from WHERE page_namespace=2 AND page_is_redirect=0 AND page_title = 'Multichill/Countries' AND pl_namespace=14"
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

def getByCountryList(cursor, startSubject):
    query = u"SELECT cat.page_title, bc.page_title FROM page AS bc JOIN categorylinks ON bc.page_id = cl_from JOIN page AS cat ON (cl_to=cat.page_title AND bc.page_title=CONCAT(cat.page_title, '_by_country')) WHERE bc.page_namespace=14 AND bc.page_is_redirect=0 AND bc.page_title LIKE '%by_country' AND cat.page_namespace=14 AND cat.page_is_redirect=0"
    cursor.execute(query)
    result = []
    while True:
	try:
	    subject, subjectByCountry = cursor.fetchone()
	    #print subject + ' ' + subjectByCountry
	    result.append((unicode(subject, 'utf-8'), unicode(subjectByCountry, 'utf-8')))
	except TypeError:
	    # Limit reached or no more results
	    break
    return result

def getMissingByCountry(cursor, subject, subjectByCountry, countries):
    cursor.execute(u"SELECT page_title FROM page WHERE page_namespace=14 AND page_is_redirect=0 AND page_title LIKE %s AND NOT EXISTS(SELECT * FROM categorylinks WHERE cl_from=page_id AND cl_to = %s) AND NOT EXISTS(SELECT * FROM templatelinks WHERE page_id=tl_from AND tl_title ='Category_redirect')", (subject + '_%' , subjectByCountry))
    result = []
    while True:
	try:
	    country = None
	    cat, = cursor.fetchone()
	    cat = unicode(cat, 'utf-8')
	    #print "bla"
	    country = isCountryCategory(cat, subject, countries)
	    if country:
		result.append((cat, subjectByCountry, country))
		#print cat + ' should be in ' + subjectByCountry
	    #print cat
	except TypeError:
	    # Limit reached or no more results
	    break
    #print "bla!" + result
    return result

def isCountryCategory(cat, subject, countries):
    for country in countries:
	if cat.endswith(country):
	    if (cat == subject + u'_from_' + country) or (cat == subject + u'_from_the_' + country):
		return country
	    elif (cat == subject + u'_in_' + country) or (cat == subject + u'_in_the_' + country):
		return country
	    elif (cat == subject + u'_of_' + country) or (cat == subject + u'_of_the_' + country):
		return country
    return None

def outputResult(missingCatsTotal):
    resultwiki = u''
    resultscript = u'#!/usr/pkg/bin/bash\n'
    page = wikipedia.Page(wikipedia.getSite(u'commons', u'commons'), u'User:Multichill/By_country_to_fix')
    comment = u'A list of categories to fix'
    for (cat, subjectByCountry, country) in missingCatsTotal:
	resultwiki = resultwiki +  u'*[[:Category:' + cat + u']] should be in [[:Category:' + subjectByCountry + u']]\n'
	resultscript = resultscript + u'python2.4 add_text.py -always -lang:commons -family:commons -page:"Category:' + cat + u'" -text:"[[Category:' + subjectByCountry.replace(u'_', u' ') + u'|' + country.replace(u'_', u' ') + u']]" -summary:"Adding [[Category:' + subjectByCountry.replace(u'_', u' ') + u']]"\n' 
    resultwiki = resultwiki.replace(u'_', u' ')
    #resultscript = resultscript.replace(u'_', u' ')
    page.put(resultwiki, comment)
    #f = file("/home/multichill/queries/bycountry.txt", 'w')
    #f.write(resultscript.encode('utf-8'))
    #f.close()
    #wikipedia.output(resultscript)

def main():
    conn = None
    cursor = None
    missingCatsTotal = []
    (conn, cursor) = connectDatabase()
    countries = getCountryList(cursor)
    
    byCountryList = getByCountryList(cursor, u'')

    for (subject, subjectByCountry) in byCountryList:
	missingCats = getMissingByCountry(cursor, subject, subjectByCountry, countries)
	if missingCats:
	    missingCatsTotal = missingCatsTotal + missingCats
    #for (a, b) in missingCatsTotal:
    #	print a + ' should be in ' + b

    outputResult(missingCatsTotal)
    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
