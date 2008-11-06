#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Create a list of users who uploaded a lot of uncategorized files
'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, MySQLdb, config

def connectDatabase():
    conn = MySQLdb.connect(config.db_hostname, db='commonswiki_p', user = config.db_username, passwd = config.db_password)
    cursor = conn.cursor()
    return (conn, cursor)

def getUncategorizedUsers(cursor):
    query = u"SELECT user_name, COUNT(user_name) AS count FROM image JOIN user ON img_user=user_id JOIN page ON img_name=page_title JOIN categorylinks ON page.page_id=cl_from WHERE page_namespace=6 AND page_is_redirect=0 AND cl_to LIKE 'Media_needing_categories_as_of_%' GROUP BY(user_name) HAVING COUNT(user_name) > 20";

    cursor.execute(query)
    result = []
    while True:
	try:
	    user_name, count, = cursor.fetchone()
	    result.append((unicode(user_name, 'utf-8'), unicode(str(count), 'utf-8')))
	except TypeError:
	    # Limit reached or no more results
	    break
    return result

def outputResult(suggestions):
    resultwiki = u'{{User:Multichill/My_uncategorized/header}}\n'
    page = wikipedia.Page(wikipedia.getSite(u'commons', u'commons'), u'User:Multichill/My_uncategorized')
    comment = u'Updated the list of users'
    for (user_name, count) in suggestions:
	resultwiki = resultwiki + u'|-\n'
	resultwiki = resultwiki + u'| [[:User:' + user_name.replace(u'_', u' ') + u'|' + user_name.replace(u'_', u' ') +  u']] || ' + count + u' || [http://toolserver.org/~multichill/my_uncategorized.php?user_name={{urlencode:' + user_name + u'}} list]\n'
    resultwiki = resultwiki + u'|}\n'
    page.put(resultwiki, comment)

def main():
    conn = None
    cursor = None
    suggestions = []
    (conn, cursor) = connectDatabase()
    suggestions = getUncategorizedUsers(cursor)
    outputResult(suggestions)
    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
