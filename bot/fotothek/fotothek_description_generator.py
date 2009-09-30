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
    
    fileId = getFileId(subject)

    #Start template
    output = output + u'{{Fotothek-Description\n'
    output = output + u'| description = <!-- To override the description field -->\n'
    output = output + u'| comment = <!-- To add a comment -->\n'
    output = output + u'| date = <!-- To override the date field -->\n'
    output = output + u'| author = <!-- To override the author field -->\n'
    #Get file info (t_8450)
    (setId, output) = getFileInfo(fileId, output, cursor)
    #Get set info (t_dataset)
    if setId:
        output = getSetInfo(setId, output, cursor)
        
        #End description template
        output = output + u'}}\n'    
    
    #Add licence header + template
    output = output + u'\n'
    output = output + u'== {{int:License}} ==\n'
    output = output + u'{{Fotothek-License}}\n'
    #Add uncategorized
    output = output + u'\n'
    output = output + u'{{Uncategorized-Fotothek|year={{subst:CURRENTYEAR}}|month={{subst:CURRENTMONTHNAME}}|day={{subst:CURRENTDAY}}}}\n'

    return output
    

def getFileId(subject):
    filename = os.path.basename(subject)
    fileId, extension = os.path.splitext(filename)
    return fileId

def getFileInfo(fileId, output, cursor):
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

def getSetInfo(setId, output, cursor):
    result = output
    query = u"SELECT e_5000, e_5064, e_5130, e_5198, e_5200, e_5202, e_5204, e_520b, e_5220, e_5230, e_5240, e_5260, e_52df, e_52in, e_52ku, e_52se, e_5300, e_5358, e_5360, e_55df, e_8350, e_9920, e_99d3 FROM t_dataset WHERE e_5000=%s LIMIT 1"
    #print query % setId
    cursor.execute(query, (setId,))

    #Some error checking would be nice
    e_5000, e_5064, e_5130, e_5198, e_5200, e_5202, e_5204, e_520b, e_5220, _e_5230, e_5240, e_5260, e_52df, e_52in, e_52ku, e_52se, e_5300, e_5358, e_5360, e_55df, e_8350, e_9920, e_99d3 = cursor.fetchone()

    if(e_5000):
        result = result + u'| 5000 = ' + e_5000 + u'\n'
    if(e_5064):
	result = result + u'| 5064 = ' + e_5064 + u'\n'
    if(e_5130):
        result = result + u'| 5130 = ' + e_5130 + u'\n'
    if(e_5198):
        result = result + u'| 5198 = ' + e_5198 + u'\n'
    if(e_5200):
        result = result + u'| 5200 = ' + e_5200 + u'\n'
    '''
    if(e_5260):
        result = result + u'| 5260 = ' + e_5260 + u'\n'
    if(e_5300):
        result = result + u'| 5300 = ' + e_5300 + u'\n'
    if(e_5360):
        result = result + u'| 5360 = ' + e_5360 + u'\n'
    if(e_55df):
        result = result + u'| 55df = ' + e_55df + u'\n'
    if(e_5730):
        result = result + u'| 5730 = ' + e_5730 + u'\n'
    if(e_5064):
        result = result + u'| 5064 = ' + e_5064 + u'\n'
    if(e_5202):
        result = result + u'| 5202 = ' + e_5202 + u'\n'
    if(e_520a):
        result = result + u'| 520a = ' + e_520a + u'\n'
    if(e_5230):
        result = result + u'| 5230 = ' + e_5230 + u'\n'
    if(e_52df):
        result = result + u'| 52df = ' + e_52df + u'\n'
    if(e_52in):
        result = result + u'| 52in = ' + e_52in + u'\n'
    if(e_52se):
        result = result + u'| 52se = ' + e_52se + u'\n'
    '''
    if(e_8350):
        result = result + u'| 8350 = ' + e_8350 + u'\n'
    if(e_9920):
        result = result + u'| 9920 = ' + e_9920 + u'\n'
    if(e_99d3):
	result = result + u'| 99d3 = ' + e_99d3 + u'\n'
    
    #Now get everything linked to this set
    for (base, elements) in tabels.items():
	if not base=='dataset':
	    result = result + getLinkedInfo(setId, base, elements, cursor)
    '''
    result = getob28Info(setId, result, cursor)
    result = getob30Info(setId, result, cursor)
    result = getob35Info(setId, result, cursor)
    result = getob40Info(setId, result, cursor)
    result = getob45Info(setId, result, cursor)
    result = get5007Info(setId, result, cursor)
    result = get5364Info(setId, result, cursor)
    result = get5060Info(setId, result, cursor)
    result = get5108Info(setId, result, cursor)        
    '''

    return result

def getLinkedInfo(setId, base, elements, cursor):
    result = u''
    query = u"SELECT value"
    for element in elements:
	query = query + ", e_" + element
    query = query + " FROM t_" + base + " JOIN " + base + "_links ON t_" + base + ".id=" + base + "_links.id WHERE  e_5000='" + setId + "'"
    print query
    print len(elements)

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

def getob28Info(setId, output, cursor):
    result = output
    query = u"SELECT value, e_2864, e_2900, e_2950 FROM t_ob28 JOIN ob28_links ON t_ob28.id=ob28_links.id WHERE e_5000=%s"

    #print query % setId
    
    cursor.execute(query, (setId,))

    n = 1
    while True:
        try:
            e_ob28, e_2864, e_2900, e_2950 = cursor.fetchone()
        except TypeError:
            return result
        if(e_ob28):
            result = result + u'| ob28_' + str(n) + u' = ' + e_ob28 + u'\n'
        if(e_2864):
            result = result + u'| ob28_' + str(n) + u'_2864 = ' + e_2864 + u'\n'
        if(e_2900):
            result = result + u'| ob28_' + str(n) + u'_2900 = ' + e_2900 + u'\n'
        if(e_2950):
            result = result + u'| ob28_' + str(n) + u'_2950 = ' + e_2950 + u'\n'
        n = n + 1

def getob30Info(setId, output, cursor):
    result = output
    query = u"SELECT value, e_3100, e_3475, e_3498 FROM t_ob30 JOIN ob30_links ON t_ob30.id=ob30_links.id WHERE e_5000=%s"

    #print query % setId
    
    cursor.execute(query, (setId,))

    n = 1
    while True:
        try:
            e_ob30, e_3100, e_3475, e_3498 = cursor.fetchone()
        except TypeError:
            return result
        if(e_ob30):
            result = result + u'| ob30_' + str(n) + u' = ' + e_ob30 + u'\n'
        if(e_3100):
            result = result + u'| ob30_' + str(n) + u'_3100 = ' + e_3100 + u'\n'
        if(e_3475):
            result = result + u'| ob30_' + str(n) + u'_3475 = ' + e_3475 + u'\n'
        if(e_3498):
            result = result + u'| ob30_' + str(n) + u'_3498 = ' + e_3498 + u'\n'
        n = n + 1

def getob35Info(setId, output, cursor):
    result = output
    query = u"SELECT value, e_3600, e_3975, e_3998 FROM t_ob35 JOIN ob35_links ON t_ob35.id=ob35_links.id WHERE e_5000=%s"

    #print query % setId
    
    cursor.execute(query, (setId,))

    n = 1
    while True:
        try:
            e_ob35, e_3600, e_3975, e_3998 = cursor.fetchone()
        except TypeError:
            return result
        if(e_ob35):
            result = result + u'| ob35_' + str(n) + u' = ' + e_ob35 + u'\n'
        if(e_3600):
            result = result + u'| ob35_' + str(n) + u'_3600 = ' + e_3600 + u'\n'
        if(e_3975):
            result = result + u'| ob35_' + str(n) + u'_3975 = ' + e_3975 + u'\n'
        if(e_3998):
            result = result + u'| ob35_' + str(n) + u'_3998 = ' + e_3998 + u'\n'
        n = n + 1

def getob40Info(setId, output, cursor):
    result = output
    query = u"SELECT value, e_4100, e_410d, e_4475, e_4485, e_4498 FROM t_ob40 JOIN ob40_links ON t_ob40.id=ob40_links.id WHERE e_5000=%s"

    #print query % setId
    
    cursor.execute(query, (setId,))

    n = 1
    while True:
        try:
            e_ob40, e_4100, e_410d, e_4475, e_4485, e_4498 = cursor.fetchone()
        except TypeError:
            return result
        if(e_ob40):
            result = result + u'| ob40_' + str(n) + u' = ' + e_ob40 + u'\n'
        if(e_4100):
            result = result + u'| ob40_' + str(n) + u'_4100 = ' + e_4100 + u'\n'
        if(e_410d):
            result = result + u'| ob40_' + str(n) + u'_410d = ' + e_410d + u'\n'
        if(e_4475):
            result = result + u'| ob40_' + str(n) + u'_4475 = ' + e_4475 + u'\n'
        if(e_4485):
            result = result + u'| ob40_' + str(n) + u'_4485 = ' + e_4485 + u'\n'
        if(e_4498):
            result = result + u'| ob40_' + str(n) + u'_4498 = ' + e_4498 + u'\n'
        n = n + 1


def getob45Info(setId, output, cursor):
    result = output
    query = u"SELECT value, e_4600, e_4998 FROM t_ob45 JOIN ob45_links ON t_ob45.id=ob45_links.id WHERE e_5000=%s"

    #print query % setId
    
    cursor.execute(query, (setId,))

    n = 1
    while True:
        try:
            e_ob45, e_4600, e_4998 = cursor.fetchone()
        except TypeError:
            return result
        if(e_ob45):
            result = result + u'| ob45_' + str(n) + u' = ' + e_ob45 + u'\n'
        if(e_4600):
            result = result + u'| ob45_' + str(n) + u'_4600 = ' + e_4600 + u'\n'
        if(e_4998):
            result = result + u'| ob45_' + str(n) + u'_4998 = ' + e_4998 + u'\n'
        n = n + 1
        
def get5007Info(setId, output, cursor):
    result = output
    query = u"SELECT value, e_5009, e_5010, e_5013, e_501a, e_501k, e_501m FROM t_5007 JOIN 5007_links ON t_5007.id=5007_links.id WHERE e_5000=%s"

    #print query % setId
    
    cursor.execute(query, (setId,))

    n = 1
    while True:
        try:
            e_5007, e_5009, e_5010, e_5013, e_501a, e_501k, e_501m = cursor.fetchone()
        except TypeError:
            return result
        if(e_5007):
            result = result + u'| 5007_' + str(n) + u' = ' + e_5007 + u'\n'
        if(e_5009):
            result = result + u'| 5007_' + str(n) + u'_5009 = ' + e_5009 + u'\n'
        if(e_5010):
            result = result + u'| 5007_' + str(n) + u'_5010 = ' + e_5010 + u'\n'
        if(e_5013):
            result = result + u'| 5007_' + str(n) + u'_5013 = ' + e_5013 + u'\n'
        if(e_501a):
            result = result + u'| 5007_' + str(n) + u'_501a = ' + e_501a + u'\n'
        if(e_501k):
            result = result + u'| 5007_' + str(n) + u'_501k = ' + e_501k + u'\n'
        if(e_501m):
            result = result + u'| 5007_' + str(n) + u'_501m = ' + e_501m + u'\n'
        n = n + 1    

def get5364Info(setId, output, cursor):
    result = output
    query = u"SELECT value, e_5365 FROM t_5364 JOIN 5364_links ON t_5364.id=5364_links.id WHERE e_5000=%s"

    #print query % setId
    
    cursor.execute(query, (setId,))

    n = 1
    while True:
        try:
            e_5364, e_5365 = cursor.fetchone()
        except TypeError:
            return result
        if(e_5364):
            result = result + u'| 5364_' + str(n) + u' = ' + e_5364 + u'\n'
        if(e_5365):
            result = result + u'| 5364_' + str(n) + u'_5365 = ' + e_5365 + u'\n'
        n = n + 1

def get5060Info(setId, output, cursor):
    result = output
    query = u"SELECT value, e_5062 FROM t_5060 JOIN 5060_links ON t_5060.id=5060_links.id WHERE e_5000=%s"

    #print query % setId
    
    cursor.execute(query, (setId,))

    n = 1
    while True:
        try:
            e_5060, e_5062 = cursor.fetchone()
        except TypeError:
            return result
        if(e_5060):
            result = result + u'| 5060_' + str(n) + u' = ' + e_5060 + u'\n'
        if(e_5062):
            result = result + u'| 5060_' + str(n) + u'_5062 = ' + e_5062 + u'\n'
        n = n + 1

def get5108Info(setId, output, cursor):
    result = output
    query = u"SELECT value, e_5110, e_5116, e_5117 FROM t_5108 JOIN 5108_links ON t_5108.id=5108_links.id WHERE e_5000=%s"

    #print query % setId
    
    cursor.execute(query, (setId,))

    n = 1
    while True:
        try:
            e_5108, e_5110, e_5116, e_5117 = cursor.fetchone()
        except TypeError:
            return result
        if(e_5108):
            result = result + u'| 5108_' + str(n) + u' = ' + e_5108 + u'\n'
        if(e_5110):
            result = result + u'| 5108_' + str(n) + u'_5110 = ' + e_5110 + u'\n'
        if(e_5116):
            result = result + u'| 5108_' + str(n) + u'_5116 = ' + e_5116 + u'\n'
        if(e_5117):
            result = result + u'| 5108_' + str(n) + u'_5117 = ' + e_5117 + u'\n'
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
