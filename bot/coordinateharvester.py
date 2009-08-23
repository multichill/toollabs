#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
Harvest coördinates from the nl wikipedia.

"""
import sys, copy, re
import time
import codecs
import socket

try:
    set # introduced in Python 2.4: faster and future
except NameError:
    from sets import Set as set

try: sorted ## Introduced in 2.4
except NameError:
    def sorted(seq, cmp=None, key=None, reverse=False):
        """Copy seq and sort and return it.
        >>> sorted([3, 1, 2])
        [1, 2, 3]
        """
        seq2 = copy.copy(seq)
        if key:
            if cmp == None:
                cmp = __builtins__.cmp
            seq2.sort(lambda x,y: cmp(key(x), key(y)))
        else:
            if cmp == None:
                seq2.sort()
            else:
                seq2.sort(cmp)
        if reverse:
            seq2.reverse()
        return seq2

import wikipedia, config, pagegenerators, catlib
import titletranslate, add_text

def scaleToZoom(scale):
    """
    This functions converts scales (like 1:1000000) to zoom (10 in this case)
    The function expects an integer and returns an integer
    
    List is from http://nl.wikipedia.org/wiki/Help:Externe_kaarten#type:
    """
    zoom = 0
    if scale >= 10000000:
        zoom=7
    elif scale >= 5000000:
        zoom=8
    elif scale >= 3000000:
        zoom=9
    elif scale >= 1000000:
        zoom=10
    elif scale >= 300000:
        zoom=11
    elif scale >= 200000:
        zoom=12
    elif scale >= 100000:
        zoom=13
    elif scale >= 30000:
        zoom=14
    elif scale >= 10000:
        zoom=15
    elif scale >= 5000:
        zoom=16
    elif scale >= 3000:
        zoom=17
    elif scale >= 1:
        zoom=18
    #print 'scaleToZoom: ' + str(scale) + ' to ' + str(zoom)  
    return zoom

def typeToZoom(type):
    """
    This function uses the type to figure out a zoomlevel.
    This function expects a valid type, i took the list from :
    http://en.wikipedia.org/wiki/Wikipedia:WikiProject_Geographical_coordinates#type:T
    
    If the funcion found a valid type it will return a zoomlevel greater than 0, otherwise 0.
    """
    zoom = 0
    if type.lower()=="country":
        zoom = scaleToZoom(10000000)
    elif type.lower()=="state":
        zoom = scaleToZoom(3000000)
    elif type.lower()=="adm1st":
        zoom = scaleToZoom(1000000)
    elif type.lower()=="adm2nd":
        zoom = scaleToZoom(300000)
    elif type.lower()=="city":
        zoom = scaleToZoom(100000)
    elif type.lower()=="airport":
        zoom = scaleToZoom(30000)
    elif type.lower()=="mountain":
        zoom = scaleToZoom(100000)
    elif type.lower()=="isle":
        zoom = scaleToZoom(100000)
    elif type.lower()=="island":
        zoom = scaleToZoom(100000)
    elif type.lower()=="lake":
        zoom = scaleToZoom(100000)
    elif type.lower()=="waterbody":
        zoom = scaleToZoom(100000)
    elif type.lower()=="landmark":
        zoom = scaleToZoom(10000)
    elif type.lower()=="forest":
        zoom = scaleToZoom(100000)
    elif type.lower()=="building":
        zoom = scaleToZoom(3000)

    #print 'typeToZoom: ' + str(type) + ' gaf ' + str(zoom) 
    return zoom

def populationToZoom(pop):
    """
    This function will retun a zoomlevel based on the population
    """
    print 'populationToZoom: ' + str(pop)
    return 1

def parseCoordinates (coordinates):
    """
    This function expects a string with the parameters of the template coördinaten
    (see http://nl.wikipedia.org/wiki/Sjabloon:Co%C3%B6rdinaten for the template)

    It will try to parse the template. It will return:
    *latitude
    *longitude
    *zoom (will try to figure this out if it isnt set)
    *region
    """
    success = False
    latitude = 0.0 # breedtegraad -90 tot 90 S / N
    longitude = 0.0 # lengtegraad -180 tot 180 W / E
    zoom = 0
    type = "NULL"
    region = "NULL"


    #First extract the coördinates
    p = re.compile('(?P<lat_deg>(\d|\.)+)_(?P<lat_min>(\d|\.)*)_*(?P<lat_sec>(\d|\.)*)_*(?P<lat_dir>N|S|Z)_(?P<lon_deg>(\d|\.)+)_(?P<lon_min>(\d|\.)*)_*(?P<lon_sec>(\d|\.)*)_*(?P<lon_dir>O|E|W)') 

    m = p.match(coordinates)
    
    if m:
        latitude = latitude + float(m.group('lat_deg'))
        if m.group('lat_min'):
            latitude = latitude + float(m.group('lat_min')) / 60
        if m.group('lat_sec'):
            latitude = latitude + float(m.group('lat_sec')) / 3600
        if m.group('lat_dir').upper()=="S" or m.group('lat_dir').upper()=="Z":
            latitude = latitude * -1
        longitude = longitude + float(m.group('lon_deg'))
        if m.group('lon_min'):
            longitude = longitude + float(m.group('lon_min')) / 60
        if m.group('lon_sec'):
            longitude = longitude + float(m.group('lon_sec')) / 3600
        if m.group('lon_dir').upper()=="W":
            longitude = longitude * -1
        #We got the most important part
        success = True

    #Check if zoom is set and get it
    p = re.compile('(.*)zoom:(?P<zoom>\d+)')
    m = p.match(coordinates)
    if m:
        zoom = int(m.group('zoom'))

    #If zoom isnt set, maybe scale is set
    p = re.compile('(.*)scale:(?P<scale>\d+)')
    m = p.match(coordinates)
    if m:
        if zoom==0:
            zoom = scaleToZoom(int(m.group('scale')));

    #Get the type and if zoom isnt set, set it too
    p = re.compile('(.*)type:(?P<type>country|state|adm1st|adm2nd|city|city\((?P<pop>pop)\)|airport|mountain|isle|island|lake|waterbody|landmark|building|forest)')
    m = p.match(coordinates)
    if m:
        type =  m.group('type')
        if m.group('pop'):
            type="city" # Cleanup, otherwise it would be something like city(123)
        if zoom==0:
            if m.group('pop'):
                zoom = popToZoom (int(m.group('pop')))
            else:
                zoom = typeToZoom (m.group('type'))

    #Extract the region
    p = re.compile('(.*)region:(?P<region>[a-zA-Z]+)')
    m = p.match(coordinates)
    if m:
        region = m.group('region')

    wikipedia.output(" " + str(latitude) + " " + str(longitude) + " " + str(zoom) + " " + type + " " + region)
    return (success, latitude, longitude, zoom, type, region)

def updateDatabase(page_title, latitude, longitude, zoom, type, region, image, text):
    import MySQLdb as mysqldb
    conn = mysqldb.connect(config.db_hostname, db = "u_multichill", user = config.db_username, passwd = config.db_password)
    conn.set_character_set("utf8")
    cursor = conn.cursor()
    #query = "REPLACE INTO kmltest(page_title, latitude, longitude, zoom, type, region, image, text) VALUES('" + str(page_title) + "','" + str(latitude)  + "','" + str(longitude)  + "','" + str(zoom)  + "','" + str(type) + "','" + str(region)  + "','" + str(image) + "','" + str(text) + "')"
    cursor.execute("""REPLACE INTO kmltest(page_title, latitude, longitude, zoom, type, region, image, text) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""", (page_title, latitude, longitude, zoom, type, region, image, text))
    #cursor.execute("""REPLACE INTO kmltest(page_title, latitude, longitude) VALUES(%s,%s,%s)""", (page_title, latitude, longitude))
    #print query
    #cursor.execute(query)

def workOnPage(page):
    success = False
    latitude = 0.0
    longitude = 0.0
    zoom = 0
    type = "NULL"
    region = "NULL"
    image = "NULL"
    text = "NULL"
    wikipedia.output(page.title())
    for template in  page.templatesWithParams():
        (templatename, templateparams) = template
	if (templatename == u'Co\u00f6rdinaten'):
	    (success, latitude, longitude, zoom, type, region) =  parseCoordinates(templateparams[0])
            if not success:
               return False

    #getPageText(Page)
    #getPagePicture(Page)
    
    #updateDatabase(Page, ... ... ...)
    updateDatabase(page.title(), latitude, longitude, zoom, type, region, image, text);
    return True

def main():
    summary = None; generator = None; always = False
    i = 0
    amount = 50
    query = "SELECT page_namespace, page_title FROM page JOIN templatelinks ON page_id=tl_from WHERE page_namespace=0 AND page_is_redirect=0 AND tl_title LIKE 'Co%rdinaten'"
    while True:
        thisquery = query + " LIMIT " + str(i) + " , " + str(amount)
        generator = pagegenerators.MySQLPageGenerator(thisquery )
        i = i + amount

        for page in generator:
            workOnPage(page)
                         

    #singlePageTitle = "Categorie:Tenerife"    
    #page = wikipedia.Page(wikipedia.getSite(), singlePageTitle);
    #addCommonscat (page);
    # Main Loop
    #for page in generator:
    #    (status, always) = addCommonscat(page, summary, always)        

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
