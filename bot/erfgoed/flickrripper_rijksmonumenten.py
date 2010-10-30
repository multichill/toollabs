#!/usr/bin/python
# -*- coding: utf-8  -*-
'''

Bot to copy files from http://www.flickr.com/groups/rijksmonumenten/pool/ to Commons

'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, upload
import re, flickrripper, flickrapi

def processPhoto(flickr=None, photo_id=u'', flickrreview=False, reviewer=u'', addCategory=u'', removeCategories=False, autonomous=False):
    '''
    Process a single Flickr photo
    '''
    if photo_id:
        print photo_id
        (photoInfo, photoSizes) = flickrripper.getPhoto(flickr, photo_id)
    if  flickrripper.isAllowedLicense(photoInfo):
        #Get the url of the largest photo
        photoUrl = flickrripper.getPhotoUrl(photoSizes)
        #Should download the photo only once
        photo = flickrripper.downloadPhoto(photoUrl)

        #Don't upload duplicate images, should add override option
        duplicates = flickrripper.findDuplicateImages(photo)
        if duplicates:
            wikipedia.output(u'Found duplicate image at %s' % duplicates.pop())
        else:
            filename = flickrripper.getFilename(photoInfo, project=u'Rijksmonument')
            flinfoDescription = flickrripper.getFlinfoDescription(photo_id)

	    rijksmonumentid = getRijksmonumentid(photoInfo)

            photoDescription = buildDescription(flinfoDescription, flickrreview, reviewer, addCategory, removeCategories, rijksmonumentid)
            #wikipedia.output(photoDescription)
            if not autonomous:
                (newPhotoDescription, newFilename, skip)=Tkdialog(photoDescription, photo, filename).run()
            else:
                newPhotoDescription=photoDescription
                newFilename=filename
                skip=False

	    wikipedia.output(newPhotoDescription)
	    if not skip:
		bot = upload.UploadRobot(photoUrl, description=newPhotoDescription, useFilename=newFilename, keepFilename=True, verifyDescription=False)
		bot.upload_image(debug=False)
		return 1
    return 0

def buildDescription(flinfoDescription=u'', flickrreview=False, reviewer=u'', addCategory=u'', removeCategories=False, rijksmonumentid=1):
    '''
    Build the final description for the image. The description is based on the info from flickrinfo and improved.
    '''
    description = flinfoDescription

    description = description.replace(u'\n|Source=[http://www.flickr.com/', u'\n{{Rijksmonument|%s}}\n|Source=[http://www.flickr.com/' % (rijksmonumentid,))

    if removeCategories:
        description = wikipedia.removeCategoryLinks(description, wikipedia.getSite('commons', 'commons'))
    
    # Add template

    if flickrreview:
        if reviewer:
            description = description.replace(u'{{flickrreview}}', u'{{flickrreview|' + reviewer + '|{{subst:CURRENTYEAR}}-{{subst:CURRENTMONTH}}-{{subst:CURRENTDAY2}}}}')
    
    if addCategory:
	description = description.replace(u'{{subst:unc}}\n', u'')
        description = description + u'\n[[Category:' + addCategory + ']]\n'
    description = description.replace(u'\r\n', u'\n')
    return description

def getRijksmonumentid(photoInfo):
    '''
    Try to find the Rijksmonumenten id in the tags
    '''
    rijksmonumentid=-1
    tags = flickrripper.getTags(photoInfo)

    for tag in tags:
	if tag.startswith(u'rm'):
	    wikipedia.output(u'Try to extract id from: %s' % (tag,))
	    try:
		rijksmonumentid = int(tag[2:])
		break
	    except ValueError:
		wikipedia.output(u'That did not work')
	if tag.startswith(u'rijksmonument'):
	    wikipedia.output(u'Try to extract id from: %s' % (tag,))
	    try:
		rijksmonumentid = int(tag[len(u'rijksmonument'):])
		break
	    except ValueError:
		wikipedia.output(u'That did not work')

    return rijksmonumentid

def main():
    wikipedia.setSite(wikipedia.getSite(u'commons', u'commons'))

    #Get the api key
    if config.flickr['api_key']:
        flickr = flickrapi.FlickrAPI(config.flickr['api_key'])
    else:
        wikipedia.output('Flickr api key not found! Get yourself an api key')
        wikipedia.output('Any flickr user can get a key at http://www.flickr.com/services/api/keys/apply/')
        return

    group_id = u'1336898@N25'
    addCategory = u'Rijksmonumenten'
    removeCategories = True
    autonomous = True
    totalPhotos = 0
    uploadedPhotos = 0

    # Do we mark the images as reviewed right away?
    if config.flickr['review']:
        flickrreview = config.flickr['review']
    else:    
        flickrreview = False 

    # Set the Flickr reviewer
    if config.flickr['reviewer']:
        reviewer = config.flickr['reviewer']
    elif 'commons' in config.sysopnames['commons']:
        print config.sysopnames['commons']
        reviewer = config.sysopnames['commons']['commons']
    elif 'commons' in config.usernames['commons']:
        reviewer = config.usernames['commons']['commons']
    else:
        reviewer = u''

    for photo_id in flickrripper.getPhotos(flickr=flickr, group_id=group_id):
	uploadedPhotos += processPhoto(flickr, photo_id, flickrreview, reviewer, addCategory, removeCategories, autonomous)
	totalPhotos += 1

    wikipedia.output(u'Finished running')
    wikipedia.output(u'Total photos: ' + str(totalPhotos))
    wikipedia.output(u'Uploaded photos: ' + str(uploadedPhotos))

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
