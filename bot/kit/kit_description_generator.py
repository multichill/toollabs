#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
A program do generate descriptions for KIT (Tropenmuseum) images and to upload them right away.

'''
import sys, os.path, glob, re, hashlib, base64
import pyodbc
#sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, query, upload

def connectDatabase():
    '''
    Connect to the ODBC database
    '''
    #conn = pyodbc.connect('DSN=KIT suriname')
    conn = pyodbc.connect('DSN=KIT_objecten')
    cursor = conn.cursor()
    return (conn, cursor)

def generateDescriptionFromFile(f, cursor):
    '''
    Generate a description for a file
    '''
    dirname = os.path.dirname(f)
    filename = os.path.basename(f)
    baseFilename, extension = os.path.splitext(filename)

    #objectNumber = re.sub("Tropenmuseum_Royal Tropical Institute_Objectnum[bm]er ([^_]*)_.*\.jpg", "\\1", filename)
    #objectNumber = re.sub("COLLECTIE_TROPENMUSEUM.*\_TMnr_(d+)\.jpg", "\\1", filename)
    objectNumber = re.sub(u"COLLECTIE_TROPENMUSEUM.*\_TMnr_(.+)\.jpg", u"\\1", filename)
    #print filename
    #print objectNumber

    (objectId, objectName, dated, dimensions, creditLine, objectDescription) = getOjectdata(objectNumber, cursor)
    constituents  = getConstituents(objectNumber, cursor)
    thesauri = getThesauri(objectNumber, cursor)
    titels = getTitels(objectNumber, cursor)

    # First we need to generate the description

    informationDescription=u''
        
    description = {}
    description['en'] = u''
    description['nl'] = u''
    description['inheems'] = u''
    #print objectNumber
    #print constituents
    #print thesauri
    if objectName:
        description['nl'] = description['nl'] + objectName + u'. '
        #print objectName
        #wikipedia.output(objectName)
    if objectDescription:
        description['nl'] = description['nl'] + objectDescription + u'. '
        #print description
        #wikipedia.output(description)
    for titleType, title in titels:
        if (titleType=='Display title'):
            description['en'] = description['en'] + title + u' '
        if (titleType=='Inheemse naam'):
            description['inheems'] = description['inheems'] + title + u' '
        if (titleType=='Presentatietitel'):
            description['nl'] = description['nl'] + title + u' '
    
    if description['en']:
        informationDescription = informationDescription + u'{{en|1=' + description['en'].strip() + u'}}\n'
    #For adding the Indonesian translations later
    informationDescription = informationDescription + u'<!--{{id|1=To be translated}}-->\n'
    if description['nl']:
        informationDescription = informationDescription + u'{{nl|1=' + description['nl'].strip() + u'}}\n'
    if description['inheems']:
        informationDescription = informationDescription + u'{{Unknown language|1=' + description['inheems'].strip() + u'}}\n'
    #wikipedia.output(u'bla ' + objectNumber + u' - ' + informationDescription)

    informationDate=u'{{Unknown}}'

    if dated:            
        informationDate=dated

    #print informationDate

    informationSource=u'{{KIT-source|ObjectNumber=' + objectNumber + u'}}'

    #print informationSource

    informationAuthor=u''
    validAuthorRoles = [u'Fotograaf/photographer',
             u'Fotostudio',
             u'Graveur',
             u'Lithograaf',
             u'Maker',
             u'Schilder',
             u'Tekenaar',
             u'Uitgever',
             ]
                 
    for (role, displayName) in constituents:
        if role in validAuthorRoles:
            informationAuthor = informationAuthor + displayName + u' (' + role + u'). '
    if not informationAuthor:
        #informationAuthor = u'{{Unknown}}'
        informationAuthor = u'[[Commons:Tropenmuseum|Tropenmuseum]]'
        
    #wikipedia.output(objectNumber + u' - ' + informationAuthor)


    finalDescription = u''
    finalDescription = finalDescription + u'== {{int:filedesc}} ==\n'
    finalDescription = finalDescription + u'{{Information\n'
    finalDescription = finalDescription + u'|description=' + informationDescription.strip() + u'\n'
    finalDescription = finalDescription + u'|date=' + informationDate.strip() + u'\n'
    finalDescription = finalDescription + u'|source=' + informationSource.strip() + u'\n'
    finalDescription = finalDescription + u'|author=' + informationAuthor.strip() + u'\n'
    finalDescription = finalDescription + u'|permission=\n'
    finalDescription = finalDescription + u'|other_versions=\n'
    finalDescription = finalDescription + u'|other_fields=\n'
    finalDescription = finalDescription + u'}}\n'
    finalDescription = finalDescription + u'\n'
    finalDescription = finalDescription + u'== {{int:license}} ==\n'
    finalDescription = finalDescription + u'{{KIT-license}}\n'
    finalDescription = finalDescription + u'\n'
    
    validCategoryRoles = [u'Afgebeelde instelling',
                          u'Gerelateerde instelling/groep',                         
                          ]

    for (role, displayName) in constituents:
        if role in validCategoryRoles:
            #finalDescription = finalDescription + u'{{Subst:User:Multichill/KIT/constituent|' + role + u'|' + displayName + u'}}\n'
            finalDescription = finalDescription + u'[[Category:Images from KIT, ' + role + u' - ' + displayName + u']]\n'
    objectSkips = [u'litho',
                   ]
    #finalDescription = finalDescription + u'{{Subst:User:Multichill/KIT/object|' + objectName + u'}}\n'
    if not objectName.lower() in objectSkips:
        finalDescription = finalDescription + u'[[Category:Images from KIT, objectnaam ' + objectName + u']]\n'
    
    for (expr1, term) in thesauri:
        #finalDescription = finalDescription + u'{{Subst:User:Multichill/KIT/thesauri|' + expr1 + u'|' + term + u'}}\n'
        finalDescription = finalDescription + u'[[Category:Images from KIT, objecten ' + expr1 + u' - ' + term + u']]\n'
    #wikipedia.output(finalDescription)
    return finalDescription


def getOjectdata(objectNumber, cursor):
    '''
    Get the object data from Objectdatatabel for a single object
    '''
    query = "select ObjectId, ObjectName, Dated, Dimensions, CreditLine, Description from \"Objectdata\" WHERE ObjectNumber ='" + objectNumber + "'"
    
    cursor.execute(query)

    (objectId, objectName, dated, dimensions, creditLine, description)= cursor.fetchone()
   
    return (objectId, objectName, dated, dimensions, creditLine, description)


def getConstituents(objectNumber, cursor):
    '''
    Get the related conctituents records FROM Constituentstabel based on objectNumber
    '''
   
    query = "select Role, DisplayName from \"Constituents\" WHERE ObjectNumber ='" + objectNumber + "'"
    cursor.execute(query) 
    result= cursor.fetchall()
   
    return result

def getThesauri(objectNumber, cursor):
    '''
    Get the related thesauri records FROM Thesauri based on objectNumber
    '''
    skips = [u'Materiaal - hoofd',
             u'Materiaal - overig',
             u'Objecttrefwoord',
             u'Techniek',
             u'Voorstelling Cultuur',
             u'Voorstelling Materiaal',
            ]
    
    query = u"select ThesXrefType, Term from Thesauri WHERE ObjectNumber ='" + objectNumber + u"'"
    
    for skip in skips:
        query = query + u" AND not ThesXrefType='" + skip + "'"
    
    cursor.execute(query) 
    result= cursor.fetchall()
   
    return result

def getTitels(objectNumber, cursor):
    '''
    Get the different titels from \"Titel\" based on objectNumber
    '''
   
    query = "select TitleType, Title FROM  \"Titel\" WHERE ObjectNumber ='" + objectNumber + "'"
    cursor.execute(query) 
    result= cursor.fetchall()
   
    return result

    return

def findDuplicateImages(filename):
    '''
    Takes the photo, calculates the SHA1 hash and asks the mediawiki api for a list of duplicates.

    TODO: Add exception handling, fix site thing
    '''
    f = open(filename, 'rb')
    
    result = []
    hashObject = hashlib.sha1()
    hashObject.update(f.read(-1)) 
    #f.close()
    sha1Hash = base64.b16encode(hashObject.digest())
    
    params = {
    'action'    : 'query',
        'list'      : 'allimages',
        'aisha1'    : sha1Hash,
        'aiprop'    : '',
    }
    data = query.GetData(params, site=wikipedia.getSite(), useAPI = True, encodeTitle = False)

    for image in data['query']['allimages']:
        result.append(image['name'])
    return result

def main(args):
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()
    
    if(args[0]):
        subject = args[0]
        if os.path.isdir(subject):
            for filename in glob.glob(subject + "/*.jpg"):
                duplicates = findDuplicateImages(filename)
                if duplicates:
		    wikipedia.output(u'Found duplicate image at %s' % duplicates.pop())
		else:
                #print f
                    description = generateDescriptionFromFile(filename, cursor)
                    #wikipedia.output(description)
                    #wikipedia.output(description)
                    #wikipedia.output(u'Reading file %s' % filename.decode(sys.getfilesystemencoding()))
                    bot = upload.UploadRobot(url=filename.decode(sys.getfilesystemencoding()), description=description, keepFilename=True, verifyDescription=False)
                    bot.run()
        #else:
        #    generateDescriptionFromFile(f, cursor)
    else:
        print u'Use kit_description_generator.py <folder> '
    
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print "All done!"
