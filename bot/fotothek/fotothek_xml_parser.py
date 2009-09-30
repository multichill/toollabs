#!/usr/bin/python
# -*- coding: utf-8  -*-
import sys, os
import os.path
import xml.etree.ElementTree
sys.path.append("/home/multichill/pywikipedia")
#import wikipedia
import MySQLdb, config

xmlFile = "wiki-2.xml"
conn = None
cursor = None

tabels = dict()

tabels[u'dataset'] = [u'5000', u'5064', u'5130', u'5198', u'5200', u'5202', u'5204', u'520b', u'5220', u'5230', u'5240', u'5260', u'52df', u'52in', u'52ku', u'52se', u'5300', u'5358', u'5360', u'55df', u'8350', u'9920', u'99d3']
tabels[u'ob26'] = [u'2660', u'2661', u'2662', u'2664', u'2690', u'2700', u'2730']
tabels[u'ob28'] = [u'2864', u'2890', u'2900', u'2930']
tabels[u'ob30'] = [u'3100', u'310d', u'3470', u'3475', u'3496', u'3498']
tabels[u'ob35'] = [u'3600', u'3970', u'3975', u'3996']
tabels[u'ob40'] = [u'4100', u'410d', u'4475', u'4498']
tabels[u'ob45'] = [u'4600']
tabels[u'5060'] = [u'5062']
tabels[u'5108'] = [u'5110', u'5116', u'5117']
tabels[u'5109'] = [u'5116a', u'5117a']
tabels[u'5140'] = [u'5145']
tabels[u'5364'] = [u'5365']
tabels[u'5930'] = [u'5944']
tabels[u'599a'] = [u'599e', u'599n']
tabels[u'8450'] = [u'8460', u'8470', u'8479', u'8480', u'8481', u'8482', u'8490', u'8494', u'8510', u'8540', u'8555']


def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    global conn
    global cursor
    conn = MySQLdb.connect('daphne', db = 'u_multichill_fotothek2_p', user = config.db_username, passwd = config.db_password)
    cursor = conn.cursor()
    return (conn, cursor)


def parseDocument(xmlFile = u''):
    tree = xml.etree.ElementTree.parse(xmlFile)
    root = tree.getroot()

    for document in root.getchildren():
        for dataset in document.getchildren():
            parseDataset(dataset)

def parseDataset(dataset):
    elements = dict()
    
    for datasetElement in dataset.getchildren():
        elementType = datasetElement.get(u'Type')
        elementValue = datasetElement.get(u'Value')
                                          
        if datasetElement.get(u'Type') == '5000':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Datensatz-ID 
	elif datasetElement.get(u'Type') in tabels[u'dataset']:
	    elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value')
	elif tabels.get(datasetElement.get(u'Type')):
	     parseElement(elements['5000'], datasetElement, tabels[datasetElement.get(u'Type')])
        else:
            print datasetElement.get(u'Type') + "WHAT THE FUCK!!!!!!!!!!!!!!!!!"
    if(elements.get(u'5000')):
        #print "Het id is " + str(elements['5000'])
        if not findSet(u'dataset', elements):
            #print "Insert"
            insertElement(u'dataset', elements)
        #else:
            #print "Al gevonden"
        #for datasetSubElement in datasetElement.getchildren():
        #    print datasetSubElement.items()
    #for (t, v) in elements.items():
    #    print (t + " - " +  v).encode("UTF-8")
    return

def parseElement(datasetId, element, allowedTypes):
    '''
    Parse an element and put it in a table
    '''
    elementType = element.get(u'Type')
    elementValue = element.get(u'Value')
    
    elements = dict()
   
    for subElement in element.getchildren():
        if(subElement.get(u'Type') in allowedTypes):
            elements[subElement.get(u'Type')] = subElement.get(u'Value')
        else:
            print "Ooooh shit, found " + subElement.get(u'Type') + " in " + elementType

    #Add the info to table "type"
    #for (t, v) in elements.items():
        #print (elementType + " - " + elementValue + " - " + t + " - " +  v).encode("UTF-8")
    #if elements:
        #First do a query if the element already exists
        #print "Do element query"
    elementId = findElement(elementType, elements)
    if not (elementId):
            #print "Didn't find it, inserting it"
            #If not insert it
        insertElement(elementType, elements)
            #And do the query again to get the id
            #print "Getting it again"
        elementId = findElement(elementType, elements)
    if not elementId:
        print "Seriously borked"

    linkElement(elementType, datasetId, elementValue, elementId)
    #Use the return value to make a link in "type"links

    return

def findElement(table, items):
    '''
    Find element in table where items and rest NULL
    '''
    global cursor
    resultlist = []
    query = u"SELECT id FROM t_" + table + " WHERE "
    firstKey = True
    for key in tabels[table]:
        if firstKey:
            firstKey = False
        else:
            query = query + " AND "
        if items.get(key):
            query = query + "e_" + key + "=%s"
            resultlist.append(items.get(key))
        else:
            query = query + "e_" + key + " IS NULL"
    query = query + u" LIMIT 1"
    #print (query % tuple(resultlist)).encode("UTF-8")
    cursor.execute(query, tuple(resultlist))

    try:
        elementId,  = cursor.fetchone()
        #print "ElementId is " + str(elementId)
        return elementId
    except TypeError:
        #print "Noneeeeeeeeeeeeeeeeeeeeeee"
        return None 

def insertElement(table, items):
    global cursor

    # First do a query to see if element exists
    
    query = u"INSERT INTO t_" + table + u"("
    firstKey = True
    for key in items.keys():
        if firstKey:
            query = query + u"e_" + key
            firstKey = False
        else:
            query = query + u", e_" + key
    query = query + u") VALUES ("
    firstKey = True
    for key in items.keys():
        if firstKey:
            query = query + u"%s"
            firstKey = False
        else:
            query = query + u", %s"
    query = query + u")"

    #print (query % tuple(items.values())).encode("UTF-8")
    cursor.execute(query, tuple(items.values()))  
    return

def linkElement(table, datasetId, elementValue, elementId):
    global cursor
    temp = None
    # First do a query to see if element exists

    queryFind = u"SELECT e_5000 FROM " + table + u"_links WHERE e_5000=%s AND value=%s AND id=%s LIMIT 1"
    queryInsert = u"INSERT INTO " + table + u"_links (e_5000, value, id) VALUES (%s, %s, %s)"

    #print (queryFind % (datasetId, elementValue, elementId)).encode("UTF-8")
    cursor.execute(queryFind, (datasetId, elementValue, elementId) ) 

    try:
        temp, = cursor.fetchone()
        return
    except TypeError:
        #print (queryInsert % (datasetId, elementValue, elementId)).encode("UTF-8")
        cursor.execute(queryInsert, (datasetId, elementValue, elementId) )  
        return

def findSet(table, items):
    '''
    Find element in table where items and rest NULL
    '''
    global cursor
    resultlist = []
    query = u"SELECT * FROM t_" + table + " WHERE "
    firstKey = True
    for key in tabels[table]:
        if firstKey:
            firstKey = False
        else:
            query = query + " AND "
        if items.get(key):
            query = query + "e_" + key + "=%s"
            resultlist.append(items.get(key))
        else:
            query = query + "e_" + key + " IS NULL"
    query = query + u" LIMIT 1"
    #print (query % tuple(resultlist)).encode("UTF-8")
    cursor.execute(query, tuple(resultlist))

    try:
        elementId, = cursor.fetchone()
        #print "ElementId is " + str(elementId)
        return True
    except TypeError:
        #print "Noneeeeeeeeeeeeeeeeeeeeeee"
        return False 


def main(args):
    '''
    Main loop.
    '''
    connectDatabase()

    parseDocument(xmlFile)
        
            
         
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
