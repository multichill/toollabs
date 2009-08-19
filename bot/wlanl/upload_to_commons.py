#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
http://wikipedia.ramselehof.de/flinfo.php
https://fisheye.toolserver.org/browse/Magnus/flickr2commons.php?r=HEAD
'''
#import sys
#sys.path.append("/home/multichill/pywikipedia")
#import wikipedia, MySQLdb, config

import flickrapi
import xml.etree.ElementTree
api_key = 'e3df7868503946355dae7a1c6a1bd8fd'

def getPhotosInGroup(flickr=None, group_id=''):
    '''
    Get a list of photo id's
    '''
    result = []
    #First get the total number of photo's in the group
    photos = flickr.groups_pools_getPhotos(group_id=group_id, per_page='100', page='1')
    pages = photos.find('photos').attrib['pages']
    
    for i in range(1, int(pages)):
        for photo in flickr.groups_pools_getPhotos(group_id=group_id, per_page='100', page=i).find('photos').getchildren():
            print photo.attrib['id']
            yield photo.attrib['id']

def getPhotos(flickr=None, photoIds=[]):
    result = []
    for photo_id in photoIds:
        result.append(getPhoto(flickr=flickr, photo_id=photo_id))
    return

def getPhoto(flickr=None, photo_id=''):
    photoInfo = flickr.photos_getInfo(photo_id=photo_id)
    xml.etree.ElementTree.dump(photoInfo)
    photoSizes = flickr.photos_getSizes(photo_id=photo_id)
    xml.etree.ElementTree.dump(photoSizes)
    return (photoInfo, photoSizes)
    
def prepareUpload(photoInfo=None, photoSizes=None):

    return 0

def getFlinfo(photoId=''):

    return ''

def getTagDescription(tags = []):

    return 0

def getTagCategories(tags = []):

    return 0

def cleanUpCategories(description =''):

    return ''

def expandTemplates(template='', parameter=''): # should be dict

    return 0


def main():
    flickr = flickrapi.FlickrAPI(api_key)
    groupId = '1044478@N20'
    #photos = flickr.flickr.groups_search(text='73509078@N00', per_page='10') = 1044478@N20
    for photoId in getPhotosInGroup(flickr=flickr, group_id=groupId):
        (photoInfo, photoSizes) = getPhoto(flickr=flickr, photo_id=photoId)
        #if photoCanUpload(photoInfo=photoInfo, photoSizes=photoSizes):
            #(photoUrl, filename, photoDescription) = prepareUpload(photoInfo=photoInfo, photoSizes=photoSizes)
            #Do the actual upload
        
    #photos = getPhotos(flickr=flickr, photoIds=photoIds)
    #photos = flickr.groups_pools_getPhotos(group_id=group_id, per_page='10', page='1')
    #xml.etree.ElementTree.dump(photos)

    print 
    
    for item in photos.getchildren():
        print item.attrib
        for photo in item.getchildren():
            print photo.attrib
    #print photos
    
if __name__ == "__main__":
    try:
        main()
    finally:
        print 'done'
        #wikipedia.stopme()
