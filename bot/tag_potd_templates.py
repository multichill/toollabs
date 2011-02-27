#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Tag potd templates at Wikimedia Commons.
'''
import sys
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
               AND NOT page_title LIKE '%preload%' LIMIT 30"""
    
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

    filenameRegex = u'^(<?P<type>[MP]otd)/(?P<year>\d\d\d\d)-(?P<month>\d\d)-(?P<day>\d\d)$'
    descriptionRegex = u'^(<?P<type>[MP]otd)/(?P<year>\d\d\d\d)-(?P<month>\d\d)-(?P<day>\d\d)_\(?P<language>.+\)$'
    thumbtimeRegex = u'^(<?P<type>[MP]otd)/(?P<year>\d\d\d\d)-(?P<month>\d\d)-(?P<day>\d\d)_\(?P<language>.+\)$'

    filenameMatch= re.match(filenameRegex, templateTitle)
    descriptionMatch= re.match(filenameRegex, templateTitle)
    thumbtimeMatch= re.match(filenameRegex, templateTitle)

    if filenameMatch:
        text = tagFilename(page, filenameMatch)
    elif descriptionMatch:
        text = tagDescription(page, descriptionMatch)
    elif thumbtimeMatch:
        text = tagThumbtime(page, thumbtimeMatch)
        
    '''
    if templateTitle.startsWith(u'Motd'):
        if re.match(u'^Motd/\d\d\d\d-\d\d-\d\d$', templateTitle):        
            text = tagMOTDFilename(page)
        elif re.match(u'^Motd/\d\d\d\d-\d\d-\d\d_\(.+\)$', templateTitle):   
            text = tagMOTDdescription(page)
        elif re.match(u'^Motd/\d\d\d\d-\d\d-\d\d_thumbtime$', templateTitle):
            text = tagMOTDthumbtime(page)
    elif templateTitle.startsWith(u'Potd'):
        if re.match(u'^Potd/\d\d\d\d-\d\d-\d\d$', templateTitle):        
            text = tagPOTDFilename(page)
        elif re.match(u'^Potd/\d\d\d\d-\d\d-\d\d_\(.+\)$', templateTitle):
            text = tagPOTDdescription(page)
    '''
    if oldtext == text:
        return
    
    wikipedia.showDiff(oldtext, text)
    comment = u'bla'
    
    try:
        print u'Put'
	#page.put(text, comment, maxTries=1)
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
    else:
        text = u'{{%s(type)s filename|1=%s(oldtext)s|2=%s(year)s|3=%s(month)s|4=%s(day)s}}' % {
            u'type' : match.group('type'),
            u'oldtext' : page.get(),
            u'year' : match.group('year'),
            u'month' : match.group('month'),
            u'day' : match.group('day'),
            }
        
    return text

def tagDescription(page, match):
    if re.search(u'%s description' % (match.group('type'),), page.get()):
        #Already contains the template. We have to fix it
        text = page.get()
    else:
        text = u'{{%s(type)s description|1=%s(oldtext)s|2=%s(year)s|3=%s(month)s|4=%s(day)s|5=%s(languageoldtext)s}}' % {
            u'type' : match.group('type'),
            u'oldtext' : page.get(),
            u'year' : match.group('year'),
            u'month' : match.group('month'),
            u'day' : match.group('day'),
            u'language' : match.group('language'),
            }    
        
    return text

def tagThumbtime(page):
    print 'Fix MOTD thumbtime'
    return page.get()

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
