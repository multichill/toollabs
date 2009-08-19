#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Tool to transfer all suitable files in the WLANL flickr pool to Commons.
'''
import sys, urllib
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, query, imagerecat, upload

import flickrapi
import xml.etree.ElementTree
api_key = 'e3df7868503946355dae7a1c6a1bd8fd'

allowed_tags =	[   u'gama',
		    u'vanmourik',
                    u'twentsewelle',
                    u'kunsthal',
                    u'nemo',
                    u'thermenmuseum',
                    u'gemeentemuseum',
                    u'vincent van gogh',
                    u'nbm',
                    u'textielmuseum',
                    u'naturalis',
                    u'sieboldhuis',
                    u'vanabbemuseum',
                    u'rmo',
                    u'openluchtmuseum',
                    u'visserijmuseum',
                    u'catharijneconvent',
                    u'aardewerkmuseum',
                    u'zeeuwsmuseum',
                    u'rmt',
                    u'nai',
                    u'admiraliteitshuis',
                    u'loevestein',
                    u'tropenmuseum',
                    u'historischetuin',
                    u'friesmuseum',
                    u'nimk',
                    u'boijmans',
                    u'glaspaleis',
                    u'maritiem',
                    u'princessehof',
                    u'friesmuseum',
                    u'franshals',
                    u'vermeerdelft',
		]

waiting_tags =	[   u'museumhilversum',
		    u'jhm',
		    u'allardpierson',
		    u'havenmuseum',
		    u'vrijthof',
		    u'verzetsmuseum',
		    u'volkenkunde',
		]

denied_tags =	[   u'ing',	    # Ing needs OTRS
		    u'gdm',	    # Derivative works, not free
		    u'nocommons',   # Dont upload to Commons
		    u'nowcommons',  # Is already uploaded
		]

def getPhotosInGroup(flickr=None, group_id=''):
    '''
    Get a list of photo id's
    '''
    result = []
    #First get the total number of photo's in the group
    photos = flickr.groups_pools_getPhotos(group_id=group_id, per_page='100', page='1')
    pages = photos.find('photos').attrib['pages']

    #Raise this to not start at the first page again
    for i in range(1, int(pages)):
        for photo in flickr.groups_pools_getPhotos(group_id=group_id, per_page='100', page=i).find('photos').getchildren():
            #print photo.attrib['id']
            yield photo.attrib['id']

def getPhoto(flickr=None, photo_id=''):
    '''
    Get the photo info and the photo sizes so we can use these later on
    '''
    photoInfo = flickr.photos_getInfo(photo_id=photo_id)
    #xml.etree.ElementTree.dump(photoInfo)
    photoSizes = flickr.photos_getSizes(photo_id=photo_id)
    #xml.etree.ElementTree.dump(photoSizes)
    return (photoInfo, photoSizes)

def isAllowedLicense(photoInfo=None):
    '''
    Check if the image contains the right license
    '''
    license = photoInfo.find('photo').attrib['license']
    if (license=='4' or license=='5'):
	#Is cc-by or cc-by-sa
	return True
    else:
	#We don't accept other licenses
	return False

def getTags(photoInfo=None):
    '''
    Get all the tags on a photo
    '''
    result = []
    for tag in photoInfo.find('photo').find('tags').findall('tag'):
	result.append(tag.text.lower())
    return result

def photoCanUpload(tags=[]):
    '''
    See if the photo contains an allowed tag and not a tag on the disallowed list
    '''
    foundAllowed = False
    #xml.etree.ElementTree.dump(photoInfo)
    for tag in tags:
	if tag in denied_tags:
	    return False
	elif tag in allowed_tags:
	    foundAllowed = True
	#print tag
    if foundAllowed:
	#print 'Foundallowed'
	return True
    else:
	#Didn't find an allowed tag
	return False

def getFlinfoDescription(photoId=0):
    '''
    Get the description from http://wikipedia.ramselehof.de/flinfo.php
    '''
    parameters = urllib.urlencode({'id' : photoId, 'raw' : 'on'})
    
    #print 'Flinfo gaat nu aan de slag'
    rawDescription = urllib.urlopen("http://wikipedia.ramselehof.de/flinfo.php?%s" % parameters).read()
    #print rawDescription.decode('utf-8')
    return rawDescription.decode('utf-8')

def getTagDescription(tags=[]):
    '''
    Get a descriptions based on tags.
    This uses http://commons.wikimedia.org/wiki/User:Multichill/WLANL/descriptions for the descriptions
    '''
    description = u''
    template = u'User:Multichill/WLANL/descriptions'
    for tag in tags:
	description = description + expandTemplates(template=template, parameter=tag)
    #print 'De tag based description is:'
    #print description.strip()
    return description.strip()

def getTagCategories(tags=[]):
    '''
    Get one or more categories based on tags
    This uses http://commons.wikimedia.org/wiki/User:Multichill/WLANL/museums
    ''' 
    categories = u''
    template = u'User:Multichill/WLANL/museums'
    for tag in tags:
	categories = categories + expandTemplates(template=template, parameter=tag)
    #print 'De tag categories zijn:'
    #print categories.strip()
    return categories.strip()

def getFilename(photoInfo=None):
    '''
    Build a good filename for the upload based on the username and the title
    '''
    username = photoInfo.find('photo').find('owner').attrib['username']
    title = photoInfo.find('photo').find('title').text

    return u'WLANL - %s - %s.jpg' % (username, title)

def getPhotoUrl(photoSizes=None):
    '''
    Get the url of the jpg file with the highest resolution
    '''
    url = ''
    # The assumption is that the largest image is last
    for size in photoSizes.find('sizes').findall('size'):
	url = size.attrib['source']
    return url

def buildDescription(flinfoDescription=u'', tagDescription=u'', tagCategories=u''):
    '''
    Build the final description for the image. The description is based on the info from flickrinfo and improved.
    '''
    description = u''
    # Add the tag based description if it's not empty
    if not(tagDescription==u''):
	description = flinfoDescription.replace(u'|Description=', u'|Description=' + tagDescription + u' ')
    else:
	description = flinfoDescription

    # Add the tag based categories
    description = description + tagCategories
    # Add WLANL template
    description = description.replace(u'{{flickrreview}}', u'{{WLANL}}\n{{flickrreview}}')
    # Mark as flickr reviewed
    description = description.replace(u'{{flickrreview}}', u'{{flickrreview|Multichill|{{subst:CURRENTYEAR}}-{{subst:CURRENTMONTH}}-{{subst:CURRENTDAY2}}}}')
    # Filter the categories
    description = cleanUpCategories(description=description)
    #print description
    return description
    
def cleanUpCategories(description =''):
    '''
    Filter the categories in the description using the functions in imagerecat
    '''
    #Get the list of current categories
    categoryPages = wikipedia.getCategoryLinks(description, wikipedia.getSite())

    #Make it a list of strings (not page objects)
    categories = []
    for cat in categoryPages:
	categories.append(cat.titleWithoutNamespace())

    #Strip the categories of the current description
    description = wikipedia.removeCategoryLinks(description, wikipedia.getSite())    

    #Filter the list of categories
    categories = imagerecat.applyAllFilters(categories)

    #Add the categories to the description again
    description = description + u'\n'
    for category in categories:
	#print u'Category : ' + category
	description = description + u'[[Category:' + category + u']]\n'
    return description

def expandTemplates(template='', parameter=''):
    '''
    Take a template and a parameter and return the resulting wikitext.
    TODO : Should take a dict with multiple parameters.
    '''
    text = u'{{' + template + u'|' + parameter + u'}}'

    params = {
	'action'    : 'expandtemplates',
	'text'	    : text
    }

    data = query.GetData(params, wikipedia.getSite(), useAPI = True, encodeTitle = False)
    # Beware, might be some encoding issues!
    return data['expandtemplates']['*']

def main():
    site = wikipedia.getSite(u'commons', u'commons')
    wikipedia.setSite(site)
    imagerecat.initLists()

    flickr = flickrapi.FlickrAPI(api_key)
    groupId = '1044478@N20'
    #photos = flickr.flickr.groups_search(text='73509078@N00', per_page='10') = 1044478@N20
    for photoId in getPhotosInGroup(flickr=flickr, group_id=groupId):
        (photoInfo, photoSizes) = getPhoto(flickr=flickr, photo_id=photoId)
	if isAllowedLicense(photoInfo=photoInfo):
	    tags=getTags(photoInfo=photoInfo)
	    if photoCanUpload(tags=tags):
		flinfoDescription = getFlinfoDescription(photoId=photoId)
		tagDescription = getTagDescription(tags=tags)
		tagCategories = getTagCategories(tags)
		filename = getFilename(photoInfo=photoInfo)
		#print filename
		photoUrl = getPhotoUrl(photoSizes=photoSizes)
		#print photoUrl
		photoDescription = buildDescription(flinfoDescription, tagDescription, tagCategories)
		if (wikipedia.Page(title=u'File:'+ filename, site=wikipedia.getSite()).exists()):
		    # I should probably check if the hash is the same and if not upload it under a different name
		    wikipedia.output(u'File:' + filename + u' already exists!')
		else:
		    #Do the actual upload
		    #Would be nice to check before I upload if the file is already at Commons
		    #Not that important for this program, but maybe for derived programs
		    bot = upload.UploadRobot(url=photoUrl, description=photoDescription, useFilename=filename, keepFilename=True, verifyDescription=False)
		    bot.run()

    wikipedia.output('All done')
    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
