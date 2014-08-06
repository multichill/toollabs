#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import images from Commons and add them as claims to Wikidata.
Todo:
* Make more flexible
* Move to pywikibot

"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib
import re
import pywikibot.data.wikidataquery as wdquery

class ImageBot:
    """
    A bot to find images and add them to Wikidata
    """
    def __init__(self, institution, invId=217):
        """
        Arguments:
            * institution    - Name of the institution to work on
            * invId          - Property id of the inventory id

        """
        self.site = pywikibot.Site('commons', 'commons')
        self.repo = pywikibot.Site().data_repository()
        
        self.institution = institution
        self.invId = invId
        self.institutionPage = pywikibot.Page(self.site, title=institution, ns=106)
        self.institutionItem = self.getInstitutionItem(self.institutionPage)
                 
        self.generator = pagegenerators.ImageGenerator(pagegenerators.PreloadingGenerator(self.institutionPage.getReferences(onlyTemplateInclusion=True, namespaces=[6])))

        self.withoutImage = self.withoutImage(self.institutionItem)
        self.withImage = self.withImage(self.institutionItem)

        #print self.withoutImage
        #print self.withImage
        
        #self.paintingIdProperty = paintingIdProperty
        #self.paintingIds = self.fillCache(self.paintingIdProperty)

    def getInstitutionItem(self, institutionPage):
        '''
        Parse the contents of institutionPage looking for a Wikidata id
        '''
        text = institutionPage.get()
        regex = '\s*\|\s*wikidata\s*=\s*(Q\d+)\s*'
        match = re.search(regex, text)
        if match:
            itemTitle = match.group(1)
            print itemTitle
            itemPage = pywikibot.ItemPage(self.repo, title=itemTitle)
            return itemPage
            
    def withoutImage(self, institutionItem, invId=217, imageId=18, cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        collectionId = institutionItem.title().replace(u'Q', u'')
        query = u'CLAIM[195:%s] AND CLAIM[%s] AND NOCLAIM[%s]'% (collectionId, invId, imageId)

        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset, props=[str(invId),])

        if data.get('status').get('error')=='OK':
            expectedItems = data.get('status').get('items')
            props = data.get('props').get(str(invId))
            for prop in props:
                # FIXME: This will overwrite id's that are used more than once.
                # Use with care and clean up your dataset first
                result[prop[2]] = prop[0]

            if expectedItems==len(result):
                pywikibot.output('I now have %s items without an image in cache' % expectedItems)
            else:
                pywikibot.output('I now have %s items without an image in cache, but I expected %s' % (len(result), expectedItems))

        return result
    
    def withImage(self, institutionItem, invId=217, imageId=18, cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        collectionId = institutionItem.title().replace(u'Q', u'')
        query = u'CLAIM[195:%s] AND CLAIM[%s] AND CLAIM[%s]'% (collectionId, invId, imageId)

        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset, props=[str(imageId),])

        if data.get('status').get('error')=='OK':
            expectedItems = data.get('status').get('items')
            props = data.get('props').get(str(imageId))
            for prop in props:
                # FIXME: This will overwrite id's that are used more than once.
                # Use with care and clean up your dataset first
                result[prop[2]] = prop[0]

            if expectedItems==len(result):
                pywikibot.output('I now have %s items with an image in cache' % expectedItems)
            else:
                pywikibot.output('I now have %s items with an image in cache, but I expected %s' % (len(result), expectedItems))

        return result
                        
    def run(self):
        """
        Starts the robot.
        """

        for imagePage in self.generator:
            pywikibot.output(u'Working on %s' % (imagePage.title(),))
            if imagePage.title(withNamespace=False) in self.withImage:
                pywikibot.output(u'Image is already in use in item %s' % (self.withImage.get(imagePage.title(withNamespace=False),)))
                continue

            text = imagePage.get()
            regex = '\s*\|\s*accession number\s*=\s*([^\s]+)\s*'
            match = re.search(regex, text)
            if match:
                paintingId = match.group(1).strip()
                pywikibot.output(u'Found ID %s on the image' % (paintingId,))

                if paintingId in self.withoutImage:
                    pywikibot.output(u'Found an item to add it to!')

                    paintingItemTitle = u'Q%s' % (self.withoutImage.get(paintingId),)
                    paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)
                    paintingItem.get()

                    if u'P18' not in paintingItem.claims:
                        newclaim = pywikibot.Claim(self.repo, u'P18')
                        newclaim.setTarget(imagePage)
                        pywikibot.output('Adding image claim to %s' % paintingItem)
                        summary = u'Adding image based on %s' % (paintingId,)
                        paintingItem.addClaim(newclaim, summary=summary)



def main():
    institution = 'Rijksmuseum' 

    imageBot = ImageBot(institution)
    imageBot.run()


if __name__ == "__main__":
    main()
