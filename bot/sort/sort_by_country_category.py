#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
test
'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, pagegenerators, catlib, MySQLdb
import config

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect(config.db_hostname, db='commonswiki_p', user = config.db_username, passwd = config.db_password)
    cursor = conn.cursor()
    return (conn, cursor)

def getSubjects(cursor):
    '''
    Get a list of my country subjects to work on
    '''
    query=u"SELECT parent.page_title AS subject FROM page AS bycountry JOIN categorylinks ON bycountry.page_id=cl_from JOIN page AS parent ON cl_to=parent.page_title WHERE bycountry.page_namespace=14 AND bycountry.page_is_redirect=0 AND bycountry.page_title LIKE '%_by_country' AND parent.page_namespace=14 AND parent.page_is_redirect=0 AND CONCAT(parent.page_title, '_by_country')=bycountry.page_title LIMIT 5000"
    cursor.execute(query)
    result = []
    while True:
        try:
            subject, = cursor.fetchone()
            result.append(unicode(subject, 'utf-8'))
        except TypeError:
            # Limit reached or no more results
            break
    return result
    
def sort_by_country_category(cursor, subject):
    query=u"SELECT subcat.page_title, cl1.cl_sortkey FROM page AS subcat JOIN categorylinks AS cl1 ON subcat.page_id=cl1.cl_from JOIN page AS cat ON cl1.cl_to=cat.page_title JOIN categorylinks AS cl2 ON cat.page_id=cl2.cl_from WHERE subcat.page_namespace=14 AND subcat.page_is_redirect=0 AND cat.page_namespace=14 AND cat.page_is_redirect=0 AND cl2.cl_to=%s AND cat.page_title=CONCAT(cl2.cl_to,'_by_country') AND subcat.page_title LIKE CONCAT(cl2.cl_to, '%%') AND REPLACE(subcat.page_title, '_', ' ')=cl1.cl_sortkey"
    cursor.execute(query, (subject,))

    while True:
        try:
            subcat, sortkey = cursor.fetchone()
            #result.append(unicode(subject, 'utf-8'))
	    sort_by_country_subcat(subcat, subject)
        except TypeError:
            # Limit reached or no more results
            break
    #return result


def sort_by_country_subcat(subcat, subject):
    print subcat
    subcat = subcat.replace('_', ' ')
    subject = subject.replace('_', ' ')
    if subcat.startswith(subject):
	temp1 = subcat[len(subject):].lstrip()
	if temp1.startswith('from'):
	    temp2 = temp1[len('from'):].lstrip()
	elif temp1.startswith('of'):
            temp2 = temp1[len('of'):].lstrip()
        elif temp1.startswith('in'):
            temp2 = temp1[len('in'):].lstrip()
	else:
	    temp2 = ''
	if temp2:
	    if temp2.startswith('the'):
		country = temp2[len('the'):].lstrip() 
	    else:
		country = temp2
	    page = wikipedia.Page(wikipedia.getSite(), 'Category:' + subcat)
	    old = u'\[\[[cC]ategory:' + subject + u' by country[^\]]*\]\]'
	    new = u'[[Category:' + subject + u' by country|' + country + u']]'
	    comment = u'Sorting [[:Category:' + subject + u' by country]]'
	    newtext = wikipedia.replaceExcept(page.get(), old, new, [])
	    wikipedia.showDiff(page.get(), newtext)
	    page.put(newtext, comment)

def main():
    site = wikipedia.getSite(u'commons', u'commons')
    wikipedia.setSite(site)
    
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()

    subjects = getSubjects(cursor)
    #subjects = [u'Engineers']

    for subject in subjects:
	sort_by_country_category(cursor, subject)

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
