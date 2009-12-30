#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Notify users of uncategorized files they uploaded.
'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, MySQLdb, config, imagerecat, pagegenerators
from datetime import datetime
from datetime import timedelta

message_marker = u'<!-- Uncategorized notification -->'

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect('commonswiki-p.db.toolserver.org', db='commonswiki_p', user = config.db_username, passwd = config.db_password)
    cursor = conn.cursor()
    return (conn, cursor)

def getYesterday():
    yesterday = datetime.utcnow() + timedelta(days=-1)
    day = str(int(yesterday.strftime('%d')))
    month = yesterday.strftime('%B')
    year = yesterday.strftime('%Y')
    return day + u'_' + month + u'_' + year

def getUsersToNotify(cursor, uncat):
    '''
    Get a list of images + uploader which are in the uncat category
    '''
    query=u"SELECT img_user_text, img_name  FROM page JOIN categorylinks ON page_id=cl_from JOIN image ON img_name=page_title WHERE page_namespace=6 AND page_is_redirect=0 AND cl_to=%s AND NOT EXISTS(SELECT * FROM page AS tp JOIN pagelinks ON tp.page_id=pl_from WHERE tp.page_title=REPLACE(img_user_text, ' ', '_') AND tp.page_namespace=3 AND tp.page_is_redirect=0 AND pl_namespace=6 AND pl_title=img_name) ORDER BY img_user_text"
    
    result = []
    lastuser = ''
    images = []

    cursor.execute(query, (uncat.replace(' ', '_'),))
    while True:
	try:
	    user, image = cursor.fetchone()
	    #The start
	    if(lastuser==''):
		lastuser = user
		images.append((unicode(image, 'utf-8')))
	    elif(lastuser==user):
		images.append((unicode(image, 'utf-8')))
	    else:
		#Add the previous image and do some cleanup
		result.append((unicode(lastuser, 'utf-8'), list(set(images))))
		lastuser= ''
		images = []
		# Start over
                lastuser = user
                images.append((unicode(image, 'utf-8')))
	except TypeError:
	    # Limit reached or no more results
	    if(lastuser!=''):
		result.append((unicode(lastuser, 'utf-8'), list(set(images))))
	    break
    return result

def notifyUser(user, images, uncat):
    '''
    Replace uncategorized with a category
    '''
    page = wikipedia.Page(wikipedia.getSite(), u'User_talk:' + user)
    if not page.exists():
	wikipedia.output(u'Welcoming ' + user)
	newtext= u'{{subst:Welcome}} ~~~~\n'
    else:
	try:
	    newtext = page.get()
	except wikipedia.IsRedirectPage:
	    wikipedia.output(u'Talk page is a redirect')
	    return

    for image in images:
	if newtext.find(message_marker)==-1:
	    wikipedia.output(u'No marker found. Adding template and marker')
	    newtext = newtext + u'\n{{subst:Please link images}} ~~~~\n'
	    newtext = newtext + message_marker
	message = u'*[[:Image:' + image.replace(u'_', u' ') + u']] was uncategorized on ' + uncat.replace(u'Media_needing_categories_as_of_', '').replace(u'_', u' ') + u', ~~~~\n'
	newtext = newtext.replace(message_marker, message + message_marker)

    comment = u'Notifying user of ' + str(len(images)) + u' [[Category:' + uncat + u'|uncategorized]] image(s)'
    #Gaat nog fout bij niet bestaande pagina
    #wikipedia.showDiff(page.get(), newtext)
    wikipedia.output(comment)
    try:
	page.put(newtext = newtext, comment = comment, minorEdit=False)
    except wikipedia.LockedPage:
	wikipedia.output(u'Page is locked. Not saved')

def main():
    '''
    The main loop
    '''
    wikipedia.setSite(wikipedia.getSite(u'commons', u'commons'))
    conn = None
    cursor = None
    uncat = u''
    (conn, cursor) = connectDatabase()

    for arg in wikipedia.handleArgs():
        if arg.startswith('-date'):
            if len(arg) == 5:
                uncat = u'Media_needing_categories_as_of_' + wikipedia.input(u'What page do you want to use?')
            else:
                uncat = u'Media_needing_categories_as_of_' + arg[6:]
	elif arg.startswith('-yesterday'):
	    uncat = u'Media_needing_categories_as_of_' + getYesterday()
    if uncat:
	uncat = uncat.replace(' ', '_')
	for (user, images) in getUsersToNotify(cursor, uncat):
	    notifyUser(user, images, uncat)
    else:
	wikipedia.output(u'Please specify date to work with "-date:' + getYesterday() + u'" or "-yesterday"')
    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
