#!/usr/bin/python
# -*- coding: utf-8  -*-
'''

'''
import sys, os.path, glob
import MySQLdb
sys.path.append("/home/multichill/pywikipedia")
import config

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
    conn = MySQLdb.connect('daphne', db='u_multichill_fotothek2_p', user = config.db_username, passwd = config.db_password, charset='utf8')
    cursor = conn.cursor()
    return (conn, cursor)

def makeDescription(subject, cursor):

    output = u''
    fileInfoOutput = u''
    setInfoOutput = u''
    
    fileId = getFileId(subject)

    #Get file info (t_8450)
    (setId, fileInfoOutput) = getFileInfo(fileId, cursor)
    #Get set info (t_dataset)
    if setId:
	setInfoOutput = getSetInfo(setId, cursor)

    #Start template
    output = output + u'{{Fotothek-Description\n'
    output = output + u'| description = <!-- To override the description field -->\n'
    output = output + u'| comment = <!-- To add a comment -->\n'
    output = output + u'| date = <!-- To override the date field -->\n'
    output = output + u'| author = <!-- To override the author field -->\n'

    output = output + fileInfoOutput
    output = output + setInfoOutput
        
    #End description template
    output = output + u'}}\n'    
    
    #Add licence header + template
    output = output + u'\n'
    output = output + u'== {{int:License}} ==\n'
    output = output + u'{{Fotothek-License}}\n'
    #Add category or uncategorized
    output = output + u'\n'
    output = output + u'{{subst:Fotothek-Category|subst=subst:\n'
    output = output + fileInfoOutput
    output = output + setInfoOutput
    output = output + u'}}\n'
    
    #output = output + u'{{Uncategorized-Fotothek|year={{subst:CURRENTYEAR}}|month={{subst:CURRENTMONTHNAME}}|day={{subst:CURRENTDAY}}}}\n'

    return output
    

def getFileId(subject):
    filename = os.path.basename(subject)
    fileId, extension = os.path.splitext(filename)
    return fileId

def getFileInfo(fileId, cursor):
    result = u''
    query = u"SELECT e_5000 FROM t_8450 JOIN 8450_links ON t_8450.id=8450_links.id WHERE e_8470=%s LIMIT 1"

    #print query % fileId
    
    cursor.execute(query, (fileId,))

    #Some error checking would be nice
    try:
        (e_5000,) = cursor.fetchone()
    except TypeError:
        #Empty? Wtf?
        result = u'{{Fotothek-Metadata missing}}\n'
        return None, result
    result = getLinkedInfo(e_5000, u'8450', tabels[u'8450'], cursor)
    
    return (e_5000, result)

def getSetInfo(setId, cursor):
    result = u''

    query = u""
    isFirst = True

    for element in tabels[u'dataset']:
	if isFirst:
	    query = u"SELECT e_" + element
	    isFirst = False
	else:
	    query = query + ", e_" + element
    
    query = query + u" FROM t_dataset WHERE e_5000='" + setId + "' LIMIT 1"
    cursor.execute(query)
    
    row = cursor.fetchone()
    e = 0

    for item in row:
	if item:
	    result = result + u'| ' + tabels[u'dataset'][e] + ' = ' + item + u'\n'
	e = e +1
    
    #Now get everything linked to this set
    for (base, elements) in tabels.items():
	if not (base=='dataset' or base=='8450'):
	    result = result + getLinkedInfo(setId, base, elements, cursor)

    return result

def getLinkedInfo(setId, base, elements, cursor):
    result = u''
    query = u"SELECT value"
    for element in elements:
	query = query + ", e_" + element
    query = query + " FROM t_" + base + " JOIN " + base + "_links ON t_" + base + ".id=" + base + "_links.id WHERE  e_5000='" + setId + "'"
    #print query
    #print len(elements)

    cursor.execute(query)

    n = 1
    while True:
	e = 0
	#try:
	row = cursor.fetchone()
	if not row:
	    return result
	else:
	    for item in row:
		if item:
		    if e==0:
			result = result + u'| ' + base + '_' + str(n) + u' = ' + item + u'\n'
		    else:
			result = result + u'| ' + base + '_' + str(n) + u'_' + elements[(e-1)] + ' = ' + item + u'\n'
		e = e +1
	n = n + 1

def outputDescription(subject, description):
    basename, extension = os.path.splitext(subject)
    txtfilename = basename + '.txt'
    f = open(txtfilename, "w")
    f.write(description.encode("UTF-8"))
    f.close()
    return
    
def main(args):
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()
    
    subject = args[0]
    if os.path.isdir(subject):
        for f in glob.glob(subject + "/*.jpg"):
            description = makeDescription(f, cursor)
	    print description
            #outputDescription(f, description)
    else:
        description = makeDescription(subject, cursor)
	print description
        #outputDescription(subject, description)    
    
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print "All done!"
