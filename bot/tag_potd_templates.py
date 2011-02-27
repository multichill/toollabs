#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Tag potd templates at Wikimedia Commons.
'''
import sys, re
sys.path.append("../pywikipedia")
import wikipedia, MySQLdb, config

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
    Get all uncategorized MOTD and POTD templates. Skip templates with "preload" in the name. We probably don't want to tag these templates.
    '''

    query =u"""SELECT page_namespace, page_title FROM page
               LEFT JOIN categorylinks ON page_id=cl_from
               WHERE page_namespace=10 AND page_is_redirect=0
               AND (
               page_title LIKE 'Motd/2___-__-__' OR
               page_title LIKE 'Motd/2___-__-__\_(%)' OR
               page_title LIKE 'Motd/2___-__-__\_thumbtime' OR
               page_title LIKE 'Potd/2___-__-__' OR
               page_title LIKE 'Potd/2___-__-__\_(%)')
               AND cl_from IS NULL
               AND NOT page_title LIKE '%preload%'"""
    
    cursor.execute(query)
    result = cursor.fetchall()
    if result:
        for (page_namespace, page_title) in result:
	    yield unicode(page_title, 'utf-8')
	    

def tagUncategorized(templateTitle):
    page = wikipedia.Page(wikipedia.getSite(), u'Template:%s' % (templateTitle,))

    if not page.exists() or page.isRedirectPage():
	return False

    wikipedia.output(u'Working on %s' % (page.title(),))
    oldtext = page.get()
    text = oldtext

    filenameRegex = u'^(?P<type>[MP]otd)/(?P<year>\d\d\d\d)-(?P<month>\d\d)-(?P<day>\d\d)$'
    descriptionRegex = u'^(?P<type>[MP]otd)/(?P<year>\d\d\d\d)-(?P<month>\d\d)-(?P<day>\d\d) \((?P<language>.+)\)$'
    thumbtimeRegex = u'^(?P<type>[MP]otd)/(?P<year>\d\d\d\d)-(?P<month>\d\d)-(?P<day>\d\d)_\(?P<language>.+\)$'

    filenameMatch= re.match(filenameRegex, page.titleWithoutNamespace())
    descriptionMatch= re.match(descriptionRegex, page.titleWithoutNamespace())
    thumbtimeMatch= re.match(thumbtimeRegex, page.titleWithoutNamespace())

    if filenameMatch:
	print u'Found filename match'
        (text, comment) = tagFilename(page, filenameMatch)
    elif descriptionMatch:
	print u'Found description match'
        (text, comment) = tagDescription(page, descriptionMatch)
    elif thumbtimeMatch:
        (text,comment) = tagThumbtime(page, thumbtimeMatch)
        
    if oldtext == text:
        return
    
    wikipedia.showDiff(oldtext, text)
    
    try:
	page.put(text, comment, maxTries=1)
    except wikipedia.LockedPage:
	return
    except wikipedia.MaxTriesExceededError:
	return
    except wikipedia.EditConflict:
	return

def tagFilename(page, match):
    if re.search(u'%s filename' % (match.group('type'),), page.get()):
        #Already contains the template. We have to fix it
        text = page.get()
	comment = u'Correcting {{%(type)s filename}}' % {u'type' : match.group('type')}
    else:
        text = u'{{%(type)s filename|1=%(oldtext)s|2=%(year)s|3=%(month)s|4=%(day)s}}' % {
            u'type' : match.group('type'),
            u'oldtext' : page.get().strip(),
            u'year' : match.group('year'),
            u'month' : match.group('month'),
            u'day' : match.group('day'),
            }
	comment = u'Adding {{%(type)s filename}}' % {u'type' : match.group('type')}
        
    return (text, comment)

def tagDescription(page, match):
    if re.search(u'%s description' % (match.group('type'),), page.get()):
        #Already contains the template. We have to fix it
        text = page.get()
	comment = u'Correcting {{%(type)s description}}' % {u'type' : match.group('type')}
    else:
        text = u'{{%(type)s description|1=%(oldtext)s|2=%(language)s|3=%(year)s|4=%(month)s|5=%(day)s}}' % {
            u'type' : match.group('type'),
            u'oldtext' : page.get().strip(),
	    u'language' : match.group('language'),
            u'year' : match.group('year'),
            u'month' : match.group('month'),
            u'day' : match.group('day'),
            }
	comment = u'Adding {{%(type)s description}}' % {u'type' : match.group('type')}
        
    return (text, comment)

def tagThumbtime(page):
    print 'Fix MOTD thumbtime'
    return (page.get(), u'bla')

def main():
    '''
    The main loop
    '''
    wikipedia.setSite(wikipedia.getSite(u'commons', u'commons'))
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
