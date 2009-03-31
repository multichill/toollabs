#!/usr/bin/python
# -*- coding: utf-8  -*-
import sys, os
import os.path
import xml.etree.ElementTree
sys.path.append("/home/multichill/pywikipedia")
#import wikipedia
import MySQLdb, config

xmlFile = "wiki-kur.xml"
conn = None
cursor = None

tabels = dict()

tabels[u'dataset'] = [u'5000', u'2965', u'5130', u'5200', u'5260', u'5300', u'5360', u'55df', u'5730', u'5064', u'5202', u'520a', u'5230', u'52df', u'52in', u'52se', u'8350', u'9902']
tabels[u'ob28'] = [u'2864', u'2900', u'2950']
tabels[u'ob30'] = [u'3100', u'3475', u'3498']
tabels[u'ob35'] = [u'3600', u'3975', u'3998']
tabels[u'ob40'] = [u'4100', u'410d', u'4475', u'4485', u'4498']
tabels[u'ob45'] = [u'4600', u'4998']
tabels[u'5007'] = [u'5009', u'5010', u'5013', u'501a', u'501k', u'501m']
tabels[u'5364'] = [u'5365']
tabels[u'5060'] = [u'5062']
tabels[u'5108'] = [u'5110', u'5116', u'5117']
tabels[u'8450'] = [u'8460', u'8470', u'8482', u'8490', u'8494', u'8510', u'8491']


def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    global conn
    global cursor
    conn = MySQLdb.connect(config.db_hostname, db = 'u_multichill_fotothek_p', user = config.db_username, passwd = config.db_password)
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

        #print elementType
        #print elementValue.encode("UTF-8")
                                          
        if datasetElement.get(u'Type') == '5000':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Datensatz-ID 
        elif datasetElement.get(u'Type') == 'ob28':
            parseElement(elements['5000'], datasetElement, tabels[u'ob28']) # Beziehung zum Verwalter des abbg. Objekts / wiederholbare Feldgruppe
        elif datasetElement.get(u'Type') == '2965':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Folio-Nr. / Seite / Stelle 
        elif datasetElement.get(u'Type') == 'ob30':
            parseElement(elements['5000'], datasetElement, tabels[u'ob30']) # Beziehung zum Künstler / wiederholbare Feldgruppe 
        elif datasetElement.get(u'Type') == 'ob35':
            parseElement(elements['5000'], datasetElement, tabels[u'ob35']) # Beziehung zur künstl. Werkstatt / wiederholbare Feldgruppe 
        elif datasetElement.get(u'Type') == 'ob40':
            parseElement(elements['5000'], datasetElement, tabels[u'ob40']) # Beziehung zur Person / wiederholbare Feldgruppe 
        elif datasetElement.get(u'Type') == 'ob45':
            parseElement(elements['5000'], datasetElement, tabels[u'ob45']) # Beziehung zur Körperschaft / wiederholbare Feldgruppe 
        elif datasetElement.get(u'Type') == '5007':
            parseElement(elements['5000'], datasetElement, tabels[u'5007']) # Beziehung zu einem (anderen) Objekt / wiederholbare Feldgruppe 
        elif datasetElement.get(u'Type') == '5130':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Entstehungsort  
        elif datasetElement.get(u'Type') == '5200':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Titel 
        elif datasetElement.get(u'Type') == '5260':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Material   
        elif datasetElement.get(u'Type') == '5300':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Technik  
        elif datasetElement.get(u'Type') == '5360':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Maße (Höhe x Breite) 
        elif datasetElement.get(u'Type') == '5364':
            parseElement(elements['5000'], datasetElement, tabels[u'5364']) # Art der Maßangabe/ wiederholbare Feldgruppe 
        elif datasetElement.get(u'Type') == '55df':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Subject/Schlagwort 
        elif datasetElement.get(u'Type') == '5730':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Link zum digitalen Buch: http://digital.slub-dresden.de/[Feldinhalt] 
        elif datasetElement.get(u'Type') == '5064':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Datierung 
        elif datasetElement.get(u'Type') == '5060':
            parseElement(elements['5000'], datasetElement, tabels[u'5060']) # Art der Datierung / wiederholbare Feldgruppe 
        elif datasetElement.get(u'Type') == '5108':
            parseElement(elements['5000'], datasetElement, tabels[u'5108']) # abgeb. Ort / wiederholbare Feldgruppe 
        elif datasetElement.get(u'Type') == '5202':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Bauwerkname 
        elif datasetElement.get(u'Type') == '520a':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Kategorie/Schlagwort 
        elif datasetElement.get(u'Type') == '5230':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Sachbegriff/Kategorie 
        elif datasetElement.get(u'Type') == '52df':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Bildbeschreibung 
        elif datasetElement.get(u'Type') == '52in':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Originaltitel 
        elif datasetElement.get(u'Type') == '52se':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Serientitel 
        elif datasetElement.get(u'Type') == '8350':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Literatur 
        elif datasetElement.get(u'Type') == '8450':
            parseElement(elements['5000'], datasetElement, tabels[u'8450']) # Leit-Tag für wiederholbare Feldgruppe „Foto“ 
        elif datasetElement.get(u'Type') == '9902':
            elements[datasetElement.get(u'Type')] = datasetElement.get(u'Value') # Datensatzurheber 
        else:
            print datasetElement.get(u'Type') + "WHAT THE FUCK!!!!!!!!!!!!!!!!!"
    if(elements.get(u'5000')):
        #print "Het id is " + str(elements['5000'])
        if not findSet(u'dataset', elements):
            instertElement(u'dataset', elements)    
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
        instertElement(elementType, elements)
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

def instertElement(table, items):
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
        cursor.fetchone()
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
