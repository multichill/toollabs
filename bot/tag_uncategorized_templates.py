#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Tag uncategorized templates at Wikimedia Commons.
Could later be expanded to work on other sites too
'''
import sys
sys.path.append("../pywikipedia")
import wikipedia, MySQLdb, config

uncategorizedTemplate ={
    'commons' : {
        'commons' : u'{{Subst:Unc}}',
        },
    'wikipedia' : {
        'en' : u'{{subst:dated|uncategorized}}',
        'nl' : u'{{Nocat||{{subst:CURRENTYEAR}}|{{subst:CURRENTMONTH}}|{{subst:CURRENTDAY2}}}}',
        },
    }

editComment ={
    'commons' : {
        'commons' : u'Tagging this template as uncategorized.',
        },
    'wikipedia' : {
        'en' : u'Tagging this template as uncategorized.',
        'nl' : u'Dit sjabloon bevat geen categorie.',
        },
    }

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames.
    This will connect to the database of the site we want to work on.
    '''
    site = wikipedia.getSite()
    language = site.language()
    family = site.family.name
    conn_start = MySQLdb.connect('sql.toolserver.org', db='toolserver', user = config.db_username, passwd = config.db_password, use_unicode=True)
    cursor_start = conn_start.cursor()
    
    query_start = u"""SELECT dbname, server FROM wiki WHERE family='%s' AND (lang='%s' OR (lang='en' AND is_multilang=1)) LIMIT 1"""
    cursor_start.execute(query_start % (family, language))
    (dbname, server) = cursor_start.fetchone() 
    conn_start.close()

    conn = MySQLdb.connect('sql-s' + str(server) + '.toolserver.org', db=dbname, user = config.db_username, passwd = config.db_password, use_unicode=True)
    cursor = conn.cursor()
    return (conn, cursor)

def getUncategorizedTemplates(cursor):
    '''
    Get all uncategorized templates. Skip templates with "preload" in the name. We probably don't want to tag these templates.
    '''

    query =u"""SELECT page_namespace, page_title FROM page
               LEFT JOIN categorylinks ON page_id=cl_from
               WHERE page_namespace=10 AND page_is_redirect=0
               AND cl_from IS NULL
               AND NOT page_title LIKE '%preload%'"""
    
    cursor.execute(query)
    result = cursor.fetchall()
    if result:
        for (page_namespace, page_title) in result:
	    yield unicode(page_title, 'utf-8')
	    

def tagUncategorized(templateTitle):
    site = wikipedia.getSite()
    language = site.language()
    family = site.family.name

    page = wikipedia.Page(wikipedia.getSite(), u'Template:%s' % (templateTitle,))

    if not page.exists() or page.isRedirectPage():
	return False

    text = page.get()
    oldtext = text

    text = text + u'<noinclude>\n\n%s\n</noinclude>' % (uncategorizedTemplate.get(family).get(language), )

    wikipedia.showDiff(oldtext, text)
    try:
        wikipedia.output(page.title())
	page.put(text, editComment.get(family).get(language), maxTries=1)
    except wikipedia.LockedPage:
	return
    except wikipedia.MaxTriesExceededError:
	return
    except wikipedia.EditConflict:
	return

def main():
    '''
    The main loop
    '''
    wikipedia.handleArgs()
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()
    for templateTitle in getUncategorizedTemplates(cursor):
        tagUncategorized(templateTitle)
    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
