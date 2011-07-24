#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot to upload NARA images to Commons.

The bot expects a directory containing the images on the commandline and a text file containing the mappings.

The bot uses http://toolserver.org/~slakr/archives.php to get the description


'''
import sys, os.path, hashlib, base64, glob, re, urllib, time
sys.path.append("..\..\pywikipedia")
import wikipedia, config, query, upload
import shutil, socket

def getRecords(textfile):
    result = {}
    f = open(textfile, "r")

    for line in f.readlines():
        (filename, sep, arc) = line.partition(u' ')
        result[filename] = int(arc.strip())

    return result


def findDuplicateImages(filename, site = wikipedia.getSite(u'commons', u'commons')):
    '''
    Takes the photo, calculates the SHA1 hash and asks the mediawiki api for a list of duplicates.

    TODO: Add exception handling, fix site thing
    '''
    f = open(filename, 'rb')

    hashObject = hashlib.sha1()
    hashObject.update(f.read(-1))
    return site.getFilesFromAnHash(base64.b16encode(hashObject.digest()))

def getDescription(fileId):
    url = u'http://toolserver.org/~slakr/archives.php?archiveHint=%s' % (fileId,)


    textareaRe = re.compile('^<textarea rows="\d+" cols="\d+">(.+)</textarea>$', re.MULTILINE + re.DOTALL)

    gotInfo = False
    matches = None
    maxtries = 10
    tries = 0
    while(not gotInfo):
        try:
            if ( tries < maxtries ):
                tries = tries + 1
                archivesPage = urllib.urlopen(url)
                matches = textareaRe.search(archivesPage.read().decode('utf-8'))
                gotInfo = True
            else:
                break
        except IOError:
            wikipedia.output(u'Got an IOError, let\'s try again')
        except socket.timeout:
            wikipedia.output(u'Got a timeout, let\'s try again')

    if (matches and gotInfo):
        return matches.group(1)
    return u''

def getTitle(fileId, description):
    titleRe = re.compile('^\|Title=(.+)$', re.MULTILINE)
    titleMatch = titleRe.search(description)
    titleText = titleMatch.group(1)
    if len(titleText)>120:
        titleText = titleText[0 : 120]

    title = u'%s - NARA - %s.tif' % (titleText, fileId)
    return cleanUpTitle(title)

def cleanUpTitle(title):
    '''
    Clean up the title of a potential mediawiki page. Otherwise the title of
    the page might not be allowed by the software.

    '''
    title = title.strip()
    title = re.sub(u"[<{\\[]", u"(", title)
    title = re.sub(u"[>}\\]]", u")", title)
    title = re.sub(u"[ _]?\\(!\\)", u"", title)
    title = re.sub(u",:[ _]", u", ", title)
    title = re.sub(u"[;:][ _]", u", ", title)
    title = re.sub(u"[\t\n ]+", u" ", title)
    title = re.sub(u"[\r\n ]+", u" ", title)
    title = re.sub(u"[\n]+", u"", title)
    title = re.sub(u"[?!]([.\"]|$)", u"\\1", title)
    title = re.sub(u"[&#%?!]", u"^", title)
    title = re.sub(u"[;]", u",", title)
    title = re.sub(u"[/+\\\\:]", u"-", title)
    title = re.sub(u"--+", u"-", title)
    title = re.sub(u",,+", u",", title)
    title = re.sub(u"[-,^]([.]|$)", u"\\1", title)
    title = title.replace(u" ", u"_")
    return title

def main(args):
    '''
    Main loop.
    '''
    workdir = u''
    textfile = u''
    records = {}
    
    site = wikipedia.getSite(u'commons', u'commons')
    wikipedia.setSite(site)

    if not (len(args)==2):
        wikipedia.output(u'Too few arguments. Usage: NARA_uploader.py <directory> <textfile>')
        sys.exit()
    
    if os.path.isdir(args[0]):
        workdir = args[0]
    else:
        wikipedia.output(u'%s doesn\'t appear to be a directory. Exiting' % (args[0],))
        sys.exit()
        
    textfile = args[1]
    records = getRecords(textfile)
    #print records

    sourcefilenames = glob.glob(workdir + u"/*.TIF")

    for sourcefilename in sourcefilenames:
        filename = os.path.basename(sourcefilename)
        # This will give an ugly error if the id is unknown
        if not records.get(filename):
             wikipedia.output(u'Can\'t find %s in %s. Skipping this file.' % (filename, textfile))

        else:
            fileId = records.get(filename)
        
            duplicates = findDuplicateImages(sourcefilename)
            if duplicates:
                wikipedia.output(u'Found duplicate image at %s' % duplicates.pop())
            else:
                # No metadata handling. We use a webtool
                description = getDescription(fileId)
                categories = u'{{Uncategorized-NARA|year={{subst:CURRENTYEAR}}|month={{subst:CURRENTMONTHNAME}}|day={{subst:CURRENTDAY}}}}\n'
                description = description + categories

                title = getTitle(fileId, description)
                
                wikipedia.output(title)
                wikipedia.output(description)
                    
                bot = upload.UploadRobot(url=sourcefilename.decode(sys.getfilesystemencoding()), description=description, useFilename=title, keepFilename=True, verifyDescription=False)
                bot.run()
 
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
