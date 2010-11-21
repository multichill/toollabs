#!/usr/bin/python
# -*- coding: utf-8  -*-
'''

'''
import sys, os.path, hashlib, base64,  glob, re, urllib, time, StringIO
sys.path.append("/home/multichill/pyoai-2.4.4/src/")
from oaipmh.client import Client
from oaipmh.metadata import MetadataRegistry, MetadataReader
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, query, socket, upload

def getLicenseTemplate(metadata):
    '''
    Return the right license template. If it's not a free license, return False
    '''
    if metadata.getField('license'):
        if metadata.getField('license')[0]==u'http://creativecommons.org/licenses/by-sa/3.0/nl/':
            return u'Cc-by-sa-3.0-nl'
    return False

def getAttribution(metadata):

    if not (metadata.getField('attributionURL') and metadata.getField('attributionURL')[0]):
        return False
    if not (metadata.getField('attributionName') and metadata.getField('attributionName')[0]):
        return False

    return u'[%s %s]' % (metadata.getField('attributionURL')[0], metadata.getField('attributionName')[0])  
     

def getRightMovie(metadata):
    '''
    Extract the right movie (biggest ogv file) from the list of files.
    '''
    ogv_url = u''
    ogv_size = 0

    for medium in metadata.getField('medium'):
        if medium.endswith(u'.ogv'):
            movieFile=urllib.urlopen(medium)
            #print movieFile.info()
            #print movieFile.info().get('Content-Length')
            if int(movieFile.info().get('Content-Length')) > ogv_size:
                ogv_url = medium.replace(u' ', u'%20')
                ogv_size = int(movieFile.info().get('Content-Length'))
            
            #print movieFile.info()

    if not (ogv_url and  ogv_size):
        return False

    return ogv_url
    
def downloadPhoto(photoUrl = ''):
    '''
    Download the photo and store it in a StrinIO.StringIO object.

    TODO: Add exception handling
    '''
    imageFile=urllib.urlopen(photoUrl).read()
    return StringIO.StringIO(imageFile)

def findDuplicateImages(photo = None, site = wikipedia.getSite(u'commons', u'commons')):
    '''
    Takes the photo, calculates the SHA1 hash and asks the mediawiki api for a list of duplicates.

    TODO: Add exception handling, fix site thing
    '''
    hashObject = hashlib.sha1()
    hashObject.update(photo.getvalue())
    return site.getFilesFromAnHash(base64.b16encode(hashObject.digest()))

def getTitle(metadata, identifier):
    '''
    Build a valid title for the file to be uploaded to.
    '''
    #metadata.getField('alternative')[0] +
    if metadata.getField('alternative') and metadata.getField('alternative')[0]:
        title = metadata.getField('title')[0] + u' ' + metadata.getField('alternative')[0] +  u' - Open Beelden - ' + str(identifier) + u'.ogv'
    else:
        title = metadata.getField('title')[0] +  u' - Open Beelden - ' + str(identifier) + u'.ogv'

    title = re.sub(u"[<{\\[]", u"(", title)
    title = re.sub(u"[>}\\]]", u")", title)
    title = re.sub(u"[ _]?\\(!\\)", u"", title)
    title = re.sub(u",:[ _]", u", ", title)
    title = re.sub(u"[;:][ _]", u", ", title)
    title = re.sub(u"[\t\n ]+", u" ", title)
    title = re.sub(u"[\r\n ]+", u" ", title)
    title = re.sub(u"[\n]+", u"", title)
    title = re.sub(u"[?!]([.\"]|$)", u"\\1", title)
    title = re.sub(u"[&]", u"and", title)
    title = re.sub(u"[#%?!]", u"^", title)
    title = re.sub(u"[;]", u",", title)
    title = re.sub(u"[/+\\\\:]", u"-", title)
    title = re.sub(u"--+", u"-", title)
    title = re.sub(u",,+", u",", title)
    title = re.sub(u"[-,^]([.]|$)", u"\\1", title)
    title = title.replace(u" ", u"_")   
    
    return title

def getDescription(metadata, identifier):
    '''
    Create the description of the file based on the metadata
    '''
    description = u''

    description = description + u'== {{int:filedesc}} ==\n'
    description = description + u'{{Information\n'

    if metadata.getField('language') and metadata.getField('language')[0]:
        language = metadata.getField('language')[0]
    else:
        language = u'nl'
    
    description = description + u'|description={{%s|1=' % language
    for mdescription in metadata.getField('description'):
        description = description + u'%s\n' % mdescription
    for abstract in metadata.getField('abstract'):
        description = description + u'%s\n' % abstract
    description = description + u'}}\n'
    description = description + u'|date=%s\n' % metadata.getField('date')[0]
    description = description + u'|source=%s\n' % getSource(metadata, identifier)
    description = description + u'|author=%s\n' % getAuthor(metadata)
    description = description + u'|permission=\n'
    description = description + u'|other_versions=\n'
    description = description + u'}}\n'
    description = description + u'\n'

    licenseTemplate = getLicenseTemplate(metadata)
    attribution = getAttribution(metadata)

    description = description + u'== {{int:license}} ==\n'
    description = description + u'{{Open Beelden}}\n'
    if attribution:
        description = description + u'{{%s|1=%s}}'% (licenseTemplate, attribution)
    else:
        description = description + u'{{%s}}'% licenseTemplate
    description = description + u'\n' 
    description = description + u'[[Category:Media from Open Beelden needing categories]]\n'
    
    return description

def getSource(metadata, identifier):

    # Worst case Open Beelden
    templateSource = u'Open Beelden'

    # Source is already better
    if metadata.getField('source') and metadata.getField('source')[0]:
        templateSource = metadata.getField('source')[0]

    # Identifier is best, don't confuse it with the other identifier
    if metadata.getField('identifier') and metadata.getField('identifier')[0]:
        templateSource = metadata.getField('identifier')[0]

    return u'{{Open beelden-source|id=%s|source=%s}}' % (identifier, templateSource)

def getAuthor(metadata):
    '''
    Get contents for the author field.
    Remember : The creator field is the same as the attributionName field
    '''
    creator = u''
    publisherName = u''
    publisherURL = u''

    if metadata.getField('creator') and metadata.getField('creator')[0]:
        creator = metadata.getField('creator')[0]

    if metadata.getField('publisher'):
        for publisher in metadata.getField('publisher'):
            if publisher.startswith(u'http://www.openbeelden.nl/users/'):
                publisherURL = publisher
            else:
                publisherName = publisher

    if creator:
        if creator == publisherName:
            return u'[%s %s]' % (publisherURL, publisherName)
        else:
            return creator

    # Creator is empty
    else:
        if publisherName and publisherURL:
            return u'[%s %s]' % (publisherURL, publisherName)

    # Worst case, shouldn't hit this one
    return u'Open Beelden'


def processItem(record):
    (header, metadata, about) = record

    identifier = header.identifier().replace(u'oai:openimages.eu:', u'')

    if not getLicenseTemplate(metadata):
        wikipedia.output(u'File doesn\'t contain a valid license')
        return False

    movieurl = getRightMovie(metadata)

    if not movieurl:
        wikipedia.output(u'No .ogv file found')
        return False

    photo = downloadPhoto(movieurl)

    duplicates = findDuplicateImages(photo)
    # We don't want to upload dupes
    if duplicates:
        wikipedia.output(u'Found duplicate file at %s' % duplicates.pop())
        # The file is at Commons so return True
        return True

    title = getTitle(metadata, identifier)
    description = getDescription(metadata, identifier)

    wikipedia.output(title)
    #wikipedia.output(description)
    
    bot = upload.UploadRobot(movieurl, description=description, useFilename=title, keepFilename=True, verifyDescription=False, ignoreWarning=True, targetSite = wikipedia.getSite('commons', 'commons'))
    bot.upload_image(debug=False)

    return True
        
def processItems():
    oai_oi_reader = MetadataReader(
        fields={
        'title':       ('textList', 'oai_oi:oi/oi:title/text()'),
        'alternative': ('textList', 'oai_oi:oi/oi:alternative/text()'),
        'creator':     ('textList', 'oai_oi:oi/oi:creator/text()'),
        'subject':     ('textList', 'oai_oi:oi/oi:subject/text()'),
        'description': ('textList', 'oai_oi:oi/oi:description/text()'),
        'abstract':       ('textList', 'oai_oi:oi/oi:abstract/text()'),
        'publisher':   ('textList', 'oai_oi:oi/oi:publisher/text()'),
        'contributor': ('textList', 'oai_oi:oi/oi:contributor/text()'),
        'date':        ('textList', 'oai_oi:oi/oi:date/text()'),
        'type':        ('textList', 'oai_oi:oi/oi:type/text()'),
        'extent':      ('textList', 'oai_oi:oi/oi:extend/text()'),
        'medium':       ('textList', 'oai_oi:oi/oi:medium/text()'),
        'identifier':  ('textList', 'oai_oi:oi/oi:identifier/text()'),
        'source':      ('textList', 'oai_oi:oi/oi:source/text()'),
        'language':    ('textList', 'oai_oi:oi/oi:language/text()'),
        'references':  ('textList', 'oai_oi:oi/oi:references/text()'),
        'spatial':  ('textList', 'oai_oi:oi/oi:spatial/text()'),
        'attributionName':       ('textList', 'oai_oi:oi/oi:attributionName/text()'),
        'attributionURL':       ('textList', 'oai_oi:oi/oi:attributionURL/text()'),
        'license':       ('textList', 'oai_oi:oi/oi:license/text()'),
        #Zitten er niet in
        #'rights':      ('textList', 'oai_oi:oi/oi:rights/text()'),
        #'relation':    ('textList', 'oai_oi:oi/oi:relation/text()'),
        #'coverage':    ('textList', 'oai_oi:oi/oi:coverage/text()'),
        #'format':      ('textList', 'oai_oi:oi/oi:format/text()'),        
        },
        namespaces={
            'oi' : 'http://www.openbeelden.nl/oai/',
            'oai_oi' : 'http://www.openarchives.org/OAI/2.0/oai_dc/',
            'dc' : 'http://purl.org/dc/elements/1.1/',
            'dcterms' : 'http://purl.org/dc/terms',
        }
    )
    url = u'http://www.openbeelden.nl/feeds/oai/'

    registry = MetadataRegistry()
    registry.registerReader('oai_oi', oai_oi_reader)
    client = Client(url, registry)
    
    for record in client.listRecords(metadataPrefix='oai_oi'):
        processItem(record)

def main(args):
    '''
    Main loop.
    '''

    processItems() # Start and end? 

if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
