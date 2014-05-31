#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
A program do generate descriptions for KIT (Tropenmuseum) images and to upload them right away.

'''
import sys, os.path, glob, re, hashlib, base64

import wikipedia, config, MySQLdb
import sys, time, warnings, traceback
import wikipedia, config, pagegenerators

conn = None
cursor = None

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    global conn
    global cursor
    conn = MySQLdb.connect('sql.toolserver.org', db='p_erfgoed_nrhp_p', user = config.db_username, passwd = config.db_password, use_unicode=True, charset='utf8')

    cursor = conn.cursor()
    return (conn, cursor)

def addRefnums(page):

    wikipedia.output(u'Working on %s' % page.title())
    
    text = page.get()
    
    pattern = u'\{\{NRHP row[\s\r\n]+\|pos=(?P<pos>.*[\s\r\n]+)\|refnum=(?P<refnum>.*[\s\r\n]+)\|type=(?P<type>.*[\s\r\n]+)\|article=(?P<article>.*[\s\r\n]+)\|name=(?P<name>.*[\s\r\n]+)\|address=(?P<address>.*[\s\r\n]+)\|city=(?P<city>.*[\s\r\n]+)\|county=(?P<county>.*[\s\r\n]+)\|date=(?P<date>.*[\s\r\n]+)\|image=(?P<image>.*[\s\r\n]+)\|lat=(?P<lat>.*[\s\r\n]+)\|lon=(?P<lon>.*[\s\r\n]+)\|description=(?P<description>.*[\s\r\n]+)\}\}'

    newtext = re.sub(pattern, addRefnum, text)    

    if not text==newtext:
        wikipedia.showDiff(text, newtext)

        comment = u'Adding reference numbers based on NRHP database'

        #choice = wikipedia.inputChoice(u'Do you want to accept these changes?', ['Yes', 'No'], ['y', 'n'], 'n')
        choice = 'y'

        if choice == 'y':
            #DEBUG
            page.put(newtext, comment)
            return u'Success'
            #wikipedia.output(newtext)

def addRefnum(match):
    if match.group(u'refnum').strip():
        # Already has a refnum
        return match.group(0)

    #dbName
    #dbAddress
    dbCity = getCity(match.group(u'city'))
    (dbCounty, dbState) = getCounty(match.group(u'county'))
    dbDate = match.group(u'date').replace(u'-', u'').strip()
    if not(dbCounty and dbState and dbDate):
        # We don't have all info, just return
        return match.group(0)
    
    rows = getMonuments(dbCounty, dbState, dbDate)
    if not rows:
	# Nothing found, just return, try Virginia
	# Do a trick for independent cities
	# FIXME: Should not be reached anymore
	if dbCity==dbCounty:
	    dbCity = dbCity + u' (Independent city)'
	    #Try again
	    rows = getMonuments(dbCounty, dbState, dbDate)
	    if not rows:
		# Nothing found in Virginia
		return match.group(0)
	else:
	    # Not in Virginia
	    return match.group(0)

    name = match.group(u'name').strip()
    article = match.group(u'article').strip()
    address = match.group(u'address').replace(u'[', u'').replace(u']', u'').strip()

    for row in rows:
	dbName = row[1]
	dbAddress = row[2]
	nameParts = row[1].split(u', ', 2)
	if len(nameParts)==2:
	    dbNameGlued = nameParts[1].strip() + u' ' + nameParts[0].strip()
	elif len(nameParts)==3:
	    # NRHP adds extra spaces in initials, we remove them
	    nameParts[1] = nameParts[1].replace(u'. ', u'.')
	    dbNameGlued = nameParts[1].strip() + u' ' + nameParts[0].strip() + u' ' + nameParts[2].strip()
	elif len(nameParts)==4:
	    dbNameGlued = nameParts[1].strip() + u' ' + nameParts[2].strip() + u' ' + nameParts[0].strip() + u' ' + nameParts[3].strip()
	else:
	    dbNameGlued = False

	dbNameDashes = dbName.replace(u'--', u'-')
	dbNameDashes = dbNameDashes.replace(u' #', u' No. ')

	if dbNameGlued:
	    dbNameGlued = dbNameGlued.replace(u'--', u'-')
	    dbNameGlued = dbNameGlued.replace(u' #', u' No. ')
	#print u'-----------'
	#print dbName
	#print name
	#print dbName
	#print article
	#print dbAddress
	#print address
	#print u'-----------'
	if dbName==name or dbName==article or dbNameGlued==name or dbNameGlued==article or dbNameDashes==name or dbNameDashes==article or (dbAddress==address and not address==u'Address Restricted'):
	    #print u'WE HAVE A MATCH'
	    refnum = row[0]
	    newtext = match.group(0).replace(u'|refnum=', u'|refnum=' + refnum)
	    return newtext


    return match.group(0)
    


def getCity(line):
    patternDifferent = u'\[\[(?P<article>.+)\|(?P<name>.+)\]\]'
    patternSimple = u'\[\[(?P<name>.+)\]\]'

    matchDifferent = re.search(patternDifferent, line)
    matchSimple = re.search(patternSimple, line)

    if matchDifferent:
        return matchDifferent.group('name').strip()
    
    if matchSimple:
        return matchSimple.group('name').strip()

    return False

def getCounty(line):
    patternc = u'\[\[(?P<county>.+)(County|Parish|Borough|Census Area), (?P<state>.+)\]\]'
    patterni = u'\[\[(?P<county>.+), (?P<state>.+)\]\]'

    matchc = re.search(patternc, line)

    if matchc:
        dbCounty = matchc.group('county').strip()
        dbState = matchc.group('state').strip().upper()
	if dbCounty==u'DeKalb':
	    dbCounty=u'De Kalb'
	elif dbCounty==u'DuPage':
	    dbCounty=u'Du Page'
	elif dbCounty==u'LaPorte':
	    dbCounty=u'La Porte'
	elif dbCounty==u'DeSoto':
	    dbCounty=u'De Soto'
	elif dbCounty==u'LaCrosse':
	    dbCounty=u'La Crosse'
        return (dbCounty, dbState)

    matchi = re.search(patterni, line)

    if matchi:
	dbCounty = matchi.group('county').strip()
	dbState = matchi.group('state').strip().upper()
	return (dbCounty, dbState)

    return (False, False)
    

def getMonuments(dbCounty, dbState, dbDate):
    '''
    Get the different titels from \"Titel\" based on objectNumber
    '''
    global cursor
    query = u"""SELECT REFNUM, RESNAME, ADDRESS, CITY, COUNTY, STATE, CERTDATE FROM main WHERE COUNTY=%s AND STATE=%s AND CERTDATE=%s LIMIT 100"""

    cursor.execute(query, (dbCounty, dbState, dbDate)) 
    result= cursor.fetchall()

    return result


def main():
    #conn = None
    #cursor = None
    (conn, cursor) = connectDatabase()
    
    # First find out what to work on
    successList = []
    failedList = []

    # Load a lot of default generators
    genFactory = pagegenerators.GeneratorFactory()

    for arg in wikipedia.handleArgs():
        genFactory.handleArg(arg)

    generator = genFactory.getCombinedGenerator()
    if not generator:
        raise add_text.NoEnoughData('You have to specify the generator you want to use for the script!')
    else:
        pregenerator = pagegenerators.PreloadingGenerator(generator)

        for page in pregenerator:
            if page.exists() and (page.namespace() == 0) and not page.isRedirectPage():
                status = addRefnums(page)
                if status==u'Success':
                    successList.append(page.title())
                elif status==u'Failed':
                    failedList.append(page.title())

    wikipedia.output(u'Number of pages changed: %s' % (len(successList),))
    for title in successList:
        wikipedia.output(title)

    wikipedia.output(u'Number of pages that failed: %s' % (len(failedList),))
    for title in failedList:
        wikipedia.output(title)  
    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
