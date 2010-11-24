#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
A program do generate descriptions for KIT (Tropenmuseum) images and to upload them right away.

'''
import sys, os.path, glob, re, hashlib, base64
import pyodbc
#sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, query, upload, csv
import flickrripper


def generateDescription(basename, batchinfo, maininfo):
    '''
    Generate a description for a file
    '''

    batchrecord=batchinfo.get(basename)
    bestandsnaam_image=unicode(batchrecord[0], 'utf-8')
    bestanddeelnummer_negatief=unicode(batchrecord[1], 'utf-8')
    link_naar_record_in_NA_Beeldbank=unicode(batchrecord[2], 'utf-8')
    record_ID=unicode(batchrecord[3], 'utf-8')
    naar_Wiki=unicode(batchrecord[4], 'utf-8')
    Credits=unicode(batchrecord[5], 'utf-8')

    mainrecord=maininfo.get(bestanddeelnummer_negatief)

    main_record_ID=unicode(mainrecord[0], 'utf-8')
    fotonummer=unicode(mainrecord[1], 'utf-8')
    UUID=unicode(mainrecord[2], 'utf-8')
    handle=unicode(mainrecord[3], 'utf-8')
    bestandeelnr=unicode(mainrecord[4], 'utf-8')
    fotocollectie=unicode(mainrecord[5], 'utf-8')
    reportage_serie=unicode(mainrecord[6], 'utf-8')
    beschrijving=unicode(mainrecord[7], 'utf-8')
    datum=unicode(mainrecord[8], 'utf-8')
    onderwerpstrefwoorden=unicode(mainrecord[9], 'utf-8')
    geografische_trefwoorden=unicode(mainrecord[10], 'utf-8')
    trefwoorden_persoonsnamen=unicode(mainrecord[11], 'utf-8')
    trefwoorden_instellingsnaam=unicode(mainrecord[12], 'utf-8')
    fotograaf=unicode(mainrecord[13], 'utf-8')
    auteursrechten=unicode(mainrecord[14], 'utf-8')

    #print batchrecord
    #print mainrecord
    #print Credits
    #print auteursrechten + u'/' + fotograaf
    #if not (record_ID==fotonummer):
    #    print record_ID
    #    print fotonummer
    #description = u''
    
    
    description = u'{{subst:User:Multichill/Nationaal Archief|subst=subst:\n'
    #description = description + u'|bestandsnaam_image=%s\n' % (bestandsnaam_image,)
    #description = description + u'|bestanddeelnummer_negatief=%s\n' % (bestanddeelnummer_negatief,)
    #description = description + u'|link_naar_record_in_NA_Beeldbank=%s\n' % (link_naar_record_in_NA_Beeldbank,)
    description = description + u'|photo_id=%s\n' % (record_ID,)
    description = description + u'|Credits=%s\n' % (Credits,)
    #description = description + u'|fotonummer=%s\n' % (fotonummer,)
    description = description + u'|UUID=%s\n' % (UUID,)
    #description = description + u'|handle=%s\n' % (handle,)
    #description = description + u'|bestandeelnr=%s\n' % (bestandeelnr,)
    #description = description + u'|fotocollectie=%s\n' % (fotocollectie,)
    description = description + u'|reportage_serie=%s\n' % (reportage_serie,)
    description = description + u'|beschrijving=%s\n' % (beschrijving,)
    description = description + u'|datum=%s\n' % (datum,)
    description = description + u'|fotograaf=%s\n' % (fotograaf,)
    #description = description + u'|auteursrechten=%s\n' % (auteursrechten,)

    description = description + u'}}\n'

    #onderwerpstrefwoorden
    if onderwerpstrefwoorden:
        for onderwerpstrefwoord in onderwerpstrefwoorden.split(u'|'):
            description = description + u'[[Category:Images from Nationaal Archief, onderwerp %s]]\n' % (onderwerpstrefwoord,)
    #geografische_trefwoorden
    if geografische_trefwoorden:
        for geografische_trefwoord in geografische_trefwoorden.split(u'|'):
            description = description + u'[[Category:Images from Nationaal Archief, locatie %s]]\n' % (geografische_trefwoord,)
            
    #trefwoorden_persoonsnamen
    if trefwoorden_persoonsnamen:
        for trefwoord_persoonsnaam in trefwoorden_persoonsnamen.split(u'|'):
            description = description + u'[[Category:Images from Nationaal Archief, politicus %s]]\n' % (trefwoord_persoonsnaam,)

    #trefwoorden_instellingsnaam
    if trefwoorden_instellingsnaam:
        for trefwoord_instellingsnaam in trefwoorden_instellingsnaam.split(u'|'):
            description = description + u'[[Category:Images from Nationaal Archief, locatie %s]]\n' % (trefwoord_instellingsnaam,)
    '''
    politici = unicode(record[1], 'utf-8').strip()
    if politici:
        for politicus in politici.split(u'|'):
            description = description + u'[[Category:Images from Nationaal Archief, politicus %s]]\n' % (politicus,)
    
    locaties = unicode(record[4], 'utf-8').strip()
    if locaties:
        for locatie in locaties.split(u'|'):
            description = description + u'[[Category:Images from Nationaal Archief, locatie %s]]\n' % (locatie,)
    ''' 
    return description
    
    
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

def getTitle(baseFilename, beschrijving):
    title = u''
    
    if len(beschrijving)>120:
        beschrijving = beschrijving[0 : 120]

    title = u'%s - %s.jpg' % (beschrijving, baseFilename)

    return flickrripper.cleanUpTitle(title)


def main(args):


    directory = u'D:/Wikipedia/nationaal archief/WeTransfer-M18YYg8e/Nationaal Archief fotoselectie WM batch 20100906/Nationaal Archief fotoselectie WM batch 20100906/'
    batchCsvFile = u'D:/Wikipedia/nationaal archief/WeTransfer-M18YYg8e/Nationaal Archief_fotoselectie WM_batch20100906.csv'
    maincCsvFile = u'D:/Wikipedia/nationaal archief/Nationaal archief_memorixexp_metadata tbv Wikimediaselectie.csv'

    batchinfo = {}

    reader1 = csv.reader(open(batchCsvFile, "rb"))
    for row in reader1:
        batchinfo[row[0]] = row
        #print row
        #        wikipedia.output(row)

    maininfo = {}
    
    reader2 = csv.reader(open(maincCsvFile, "rb"))
    for row in reader2:
        maininfo[row[4]] = row
        #print row
        #        wikipedia.output(row)
        
    if os.path.isdir(directory):
        for filename in glob.glob(directory + "/*.jpg"):
            #print filename
            #duplicates = findDuplicateImages(filename)
            duplicates = False
            if duplicates:
                wikipedia.output(u'Found duplicate image at %s' % duplicates.pop())
            else:
                dirname = os.path.dirname(filename)
                basename = os.path.basename(filename)

                description = generateDescription(basename, batchinfo, maininfo)

                batchrecord=batchinfo.get(basename)               
                bestanddeelnummer_negatief=unicode(batchrecord[1], 'utf-8')
                mainrecord=maininfo.get(bestanddeelnummer_negatief)
                beschrijving=unicode(mainrecord[7], 'utf-8')
                
                baseFilename, extension = os.path.splitext(basename)

                title = getTitle(baseFilename, beschrijving)

                wikipedia.output(title)
                wikipedia.output(description)
                
                bot = upload.UploadRobot(url=filename.decode(sys.getfilesystemencoding()), description=description, useFilename=title, keepFilename=True, verifyDescription=False)
                bot.run()
                #time.sleep(30)

    
    
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print "All done!"
