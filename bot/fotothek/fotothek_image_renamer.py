#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
This program tries to rename all images in a batch to a more sensible name.
Images like df_n-04_0000013.jpg get renamed to Fotothek_df_n-04_0000013_<description>.jpg
The program tries to pull the description from the following fields:
52df - Image description
55df - Subject/subject heading
52in - Original title
(ob45_1_4600 - Corporate body)

The descriptions are stripped of nasty characters.

'''
import sys, os.path, glob, re
import MySQLdb
sys.path.append("/home/multichill/pywikipedia")
import config

maxTitleLength = 80

def connectDatabase():
    conn = MySQLdb.connect(config.db_hostname, db='u_multichill_fotothek_p', user = config.db_username, passwd = config.db_password, charset='utf8')
    cursor = conn.cursor()
    return (conn, cursor)

def renameFile(f, batch, cursor):
    '''
    '''
    dirname = os.path.dirname(f)
    filename = os.path.basename(f)
    baseFilename, extension = os.path.splitext(filename)
    fileId = re.sub("Fotothek_", "", baseFilename)

    description = getDescription(fileId, cursor)
    description = cleanUpDescription(description)
    if (description==u''):
        newname = u'Fotothek_' + fileId
    else:    
        newname = u'Fotothek_' + fileId + u'_' + description
    

    updateFileTable(fileId, newname + u'.jpg', batch, cursor)

    oldnameJpg = filename
    oldnameTxt = baseFilename + u'.txt'
    
    newnameJpg = newname + u'.jpg'
    newnameTxt = newname + u'.txt'

    print oldnameJpg.encode("UTF-8")
    print newnameJpg.encode("UTF-8")
    print oldnameTxt.encode("UTF-8")
    print newnameTxt.encode("UTF-8")
    
    os.rename(os.path.join(dirname, oldnameJpg), os.path.join(dirname, newnameJpg))
    os.rename(os.path.join(dirname, oldnameTxt), os.path.join(dirname, newnameTxt))
    
    #Renamefile .jpg and .txt oldname, u'Fotothek_' + fileId + u'_' + description + u'.jpg'

def getFileId(subject):
    filename = os.path.basename(subject)
    fileId, extension = os.path.splitext(filename)
    return re.sub("Fotothek_", "", fileId)

def getDescription(fileId, cursor):
    query = u"SELECT e_52df, e_55df, e_52in FROM t_8450 LEFT JOIN 8450_links ON t_8450.id=8450_links.id LEFT JOIN t_dataset ON 8450_links.e_5000=t_dataset.e_5000 WHERE e_8470=%s LIMIT 1"
   
    cursor.execute(query, (fileId,))

    #Some error checking would be nice
    try:
        e_52df, e_55df, e_52in = cursor.fetchone()
    except TypeError:
        return u''

    if(e_52df):
        return e_52df
    elif(e_55df):
        return e_55df
    elif(e_52in):
        return e_52in
    else:
        return u''

def cleanUpDescription(description):
   
    description = description.strip()	
    	
    description = re.sub("[<{\\[]", "(", description)
    description = re.sub("[>}\\]]", ")", description)
    description = re.sub("[ _]?\\(!\\)", "", description)
    description = re.sub(",:[ _]", ", ", description)
    description = re.sub("[;:][ _]", ", ", description)
    description = re.sub("[\t\n ]+", " ", description)
    description = re.sub("[\r\n ]+", " ", description)
    description = re.sub("[\n]+", "", description)
    description = re.sub("[?!]([.\"]|$)", "\\1", description)
    description = re.sub("[&#%?!]", "^", description)
    description = re.sub("[;]", ",", description)
    description = re.sub("[/+\\\\:]", "-", description)
    description = re.sub("--+", "-", description)
    description = re.sub(",,+", ",", description)
    description = re.sub("[-,^]([.]|$)", "\\1", description)
    description = description.replace(" ", "_")
    
    if len(description)>maxTitleLength: description = description[0 : maxTitleLength]
    return description

def updateFileTable(fileId, name, batch, cursor):

    query = u"REPLACE INTO file (e_8470, name, batch) VALUES (%s, %s, %s)"

    cursor.execute(query, (fileId, name, batch) )
    return

def main(args):
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()

    if(args[0] and args[1]):
        subject = args[0]
        batch = args[1]
        if os.path.isdir(subject):
            for f in glob.glob(subject + "/*.jpg"):
                renameFile(f, batch, cursor)
        else:
            renameFile(f, batch, cursor)
    else:
        print u'Use fotothek_image_renamer.py <folder> <batch>'
    
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print "All done!"
