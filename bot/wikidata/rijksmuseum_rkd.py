#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
C:\pywikibot\core>add_category.py -lang:wikidata -family:wikidata -file:categories_not_category.txt -namespace:0


"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib
import re
import pywikibot.data.wikidataquery as wdquery
import csv
from collections import OrderedDict

class RkdBot:
    """
    
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        
        self.repo = pywikibot.Site().data_repository()

        self.progressPage = pywikibot.Page(self.repo, title=u'User:Multichill/Rijksmuseum creators RKD')
        #self.progressPage.get()

        self.creators = self.getCreators()
        self.rkditems = self.getRKD()

        #self.creators = self.fillCache()
        #self.missingCreators = self.getMissingCreators()
        
        #self.paintingIdProperty = paintingIdProperty
        #self.paintingIds = self.fillCache(self.paintingIdProperty)

    def getCreators(self, cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = []
        query = u'CLAIM[195:190804] AND CLAIM[170]'
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset, props=[str(170),])

        if data.get('status').get('error')=='OK':
            expectedItems = data.get('status').get('items')
            props = data.get('props').get(str(170))
            for prop in props:                
                # FIXME: This will overwrite id's that are used more than once.
                # Use with care and clean up your dataset first
                result.append(prop[2])

            if expectedItems==len(result):
                pywikibot.output('I now processed %s items for creators' % expectedItems)

        return set(result)

    def getRKD(self, cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        query = u'CLAIM[650]'
        
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset, props=[str(650),])

        if data.get('status').get('error')=='OK':
            expectedItems = data.get('status').get('items')
            props = data.get('props').get(str(650))
            for prop in props:
                # FIXME: This will overwrite id's that are used more than once.
                # Use with care and clean up your dataset first
                result[u'Q%s' % (prop[0],)] = prop[2]

            if expectedItems==len(result):
                pywikibot.output('I now have %s items with RKD in cache' % expectedItems)

        return result
    
    
    def run(self):
        '''
        Bla die bla
        '''
        text = self.progressPage.get()
        newtext = u''

        totalCreators = 0
        totalWithRKD = 0
        totalWithoutRKD = 0

        for itemId in sorted(self.creators):
            itemTitle = u'Q%s' % (itemId, )
            totalCreators = totalCreators + 1
            if itemTitle in self.rkditems:
                newtext = newtext + '* [[%s]] - [//rkd.nl/explore/artists/%s %s]\n'% (itemTitle, self.rkditems[itemTitle], self.rkditems[itemTitle])
                totalWithRKD = totalWithRKD + 1
            else:
                # Do something with getting the label and make an automatic link like https://rkd.nl/nl/explore/artists/record?query=
                newtext = newtext + '* [[%s]] - https://rkd.nl/nl/explore/artists/record?query={{urlencode:{{Label|%s}}}}' % (itemTitle, itemTitle)
                newtext = newtext + ' - Dob: {{#invoke:Wikidata|formatStatementsE|item=%s|property=P569}}' % (itemTitle, )
                newtext = newtext + ' - Dod: {{#invoke:Wikidata|formatStatementsE|item=%s|property=P570}}' % (itemTitle, )
                newtext = newtext + ' - Country: {{#invoke:Wikidata|formatStatementsE|item=%s|property=P27}}' % (itemTitle, )
                newtext = newtext + '\n'
                totalWithoutRKD = totalWithoutRKD + 1

        newtext = newtext + u'\n\nSome statistics:\n'
        newtext = newtext + u'* Total creators: %s\n' % (totalCreators,)
        newtext = newtext + u'* Total match with RKD: %s\n' % (totalWithRKD,)
        newtext = newtext + u'* Total without RKD match: %s\n' % (totalWithoutRKD,)

        summary = u'Updating list of %s Rijksmuseum creators matched with RKD: %s hits, %s misses' % (totalCreators, totalWithRKD, totalWithoutRKD,)

        pywikibot.output(newtext)
        pywikibot.output(summary)

        self.progressPage.put(newtext, summary)

        
        
            
        
    def fillCache(self):
        '''
        Fill the cache based on the progress page
        '''

        #Moet een normale dict zijn
        result = {}
        
        text = self.progressPage.get()
        regex = u'^\*\s(.+)\s->\s\[\[(Q\d+)\]\]$'
        for match in re.finditer(regex, text, flags=re.M):
            result[match.group(1)] = match.group(2)

        return result

    def getMissingCreators(self):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        query = u'CLAIM[195:190804] AND NOCLAIM[170]'

        paintingGen = pagegenerators.PreloadingEntityGenerator(WikidataQueryPageGenerator(query))

        for paintingItem in paintingGen:
            creator = paintingItem.get().get('descriptions').get('en').replace(u'painting by ', u'')
            
            if not creator in result:
                result[creator] = [paintingItem.title(),]
            else:
                result[creator].append(paintingItem.title())

        print result
        return result
                
                
        
    def flushCreators(self):
        '''
        Flush contents
        '''
        text = self.progressPage.get()
        newtext = u''

        # hier moet ik iets met sorted doen
        for name in sorted(self.creators):
            if self.creators[name].startswith(u'Q'):
                newtext = newtext + u'* %s -> [[%s]]\n' % (name, self.creators[name])
            else:
                newtext = newtext + u'* %s -> ??? %s\n' % (name, self.creators[name])

        pywikibot.showDiff(text,newtext)

        summary = u'Updating list of matched creators'

        self.progressPage.put(newtext, summary)
                

        #print newtext
        
        
        
    
                        
    def run2(self):
        """
        Starts the robot.
        """

        totalCreators = 0
        totalMatched = 0
        totalMissed = 0
        totalMissedAllInfo = 0
        totalMissedBasicInfo = 0
        totatlMissedCreators = 0
        
        for painter in self.generator:
            totalCreators = totalCreators + 1
            #print u'start painter loop'
            #print painter.get('name')

            (familyname, sep, givenname) = unicode(painter.get('name'), "utf-8").partition(u',')
            if givenname:
                name = '%s %s'.strip() % (givenname.strip(), familyname.strip(),)
            else:
                name = familyname
            pywikibot.output(name)

            if name in self.creators.keys():
                pywikibot.output(u'Found a creator in the cache.')
                totalMatched = totalMatched + 1

            else:
                

            
                creatergen = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataItemGenerator(pagegenerators.SearchPageGenerator(name, step=None, total=50, namespaces=[0], site=self.repo)))
                            
                newcreator = None

                for creatoritem in creatergen:
                    
                    #print creatoritem.title()
                    if creatoritem.get().get('labels').get('en') == name or creatoritem.get().get('labels').get('nl') == name:
                        #print creatoritem.get().get('labels').get('en')
                        #print creatoritem.get().get('labels').get('nl')
                        # Check occupation and country of citizinship
                        if u'P106' in creatoritem.get().get('claims') and (u'P21' in creatoritem.get().get('claims') or u'P800' in creatoritem.get().get('claims')):
                            newcreator = creatoritem
                            continue
                    elif (creatoritem.get().get('aliases').get('en') and name in creatoritem.get().get('aliases').get('en')) or (creatoritem.get().get('aliases').get('nl') and name in creatoritem.get().get('aliases').get('nl')):
                        if u'P106' in creatoritem.get().get('claims') and (u'P21' in creatoritem.get().get('claims') or u'P800' in creatoritem.get().get('claims')):
                            newcreator = creatoritem
                            continue

                if newcreator:
                    pywikibot.output(u'Found a new creator!!!')
                    pywikibot.output(newcreator.title())
                    totalMatched = totalMatched + 1
                    self.creators[name] = newcreator.title()
                else:
                    pywikibot.output(u'Did not find a creator.')
                    totalMissed = totalMissed + 1
                    infostring = u''

                    foundDob = False
                    foundPob = False
                    foundDod = False
                    foundPod = False
                    foundGender = False
                    foundNationality = False
                    
                    if painter.get('birth_on') and painter.get('birth.date.end'):
                        if painter.get('birth_on')==painter.get('birth.date.end'):
                            infostring = infostring + u'- dob: %s ' % (unicode(painter.get('birth_on'), "utf-8"),)
                            foundDob = True
                        else:
                            infostring = infostring + u'- dob: %s/%s ' % (unicode(painter.get('birth_on', "utf-8")), unicode(painter.get('birth.date.end'), "utf-8"))
                    if painter.get('born_at'):
                        infostring = infostring + u'- birth location: %s ' % (unicode(painter.get('born_at'), "utf-8"),)
                        foundPob = True

                    if painter.get('died_on') and painter.get('death.date.end'):
                        if painter.get('died_on')==painter.get('death.date.end'):
                            infostring = infostring + u'- dod: %s ' % (unicode(painter.get('died_on'), "utf-8"),)
                            foundDod = True
                        else:
                            infostring = infostring + u'- dod: %s/%s ' % (unicode(painter.get('died_on'), "utf-8"), unicode(painter.get('death.date.end'), "utf-8"))
                    if painter.get('died_at'):
                        infostring = infostring + u'- death location: %s ' % (unicode(painter.get('died_at'), "utf-8"),)
                        foundPod = True

                    if painter.get('gender'):
                        foundGender = True
                        if painter.get('gender')==u'man':
                            infostring = infostring + u'- gender: male '
                        elif painter.get('gender')==u'vrouw':
                            infostring = infostring + u'- gender: female '

                    if painter.get('nationality'):
                        infostring = infostring + u'- nationality: %s ' % (unicode(painter.get('nationality'), "utf-8"),)
                        foundNationality = True

                    if painter.get('source') and painter.get('source.id'):
                        if painter.get('source')==u'RKD':
                            infostring = infostring + u'- RKDartists: %s ' % (unicode(painter.get('source.id'), "utf-8"),)
      
                    

                    if foundDob and foundPob and foundDod and foundPod and foundGender and foundNationality:
                        totalMissedAllInfo = totalMissedAllInfo + 1
                        self.creators[name] = self.makePainterItem(name, painter)
                    elif foundDob and foundDod and foundGender:
                        totalMissedBasicInfo = totalMissedBasicInfo + 1
                        self.creators[name] = self.makePainterItem(name, painter)
                    elif name in self.missingCreators:
                        totatlMissedCreators = totatlMissedCreators + 1
                        self.creators[name] = self.makePainterItem(name, painter)
                        
                        
                    

                    self.creators[name] = infostring
                        
            pywikibot.output(u'Current score after %s creators: %s hits - %s missed (%s complete, %s basic, %s needed creators)' % (totalCreators, totalMatched, totalMissed, totalMissedAllInfo, totalMissedBasicInfo, totatlMissedCreators))


        self.flushCreators()


    def makePainterItem(self, name, metadata):
        '''
        Function to create a new painter, fill it and return the id
        '''
        print metadata

        data = {'labels': {},
                'descriptions': {},
                }

        for lang in (u'de', u'en', u'fr', u'nl'):
            data['labels'][lang] = {'language': lang, 'value': name}

        countryId = u''

        if metadata.get('nationality'):
            if metadata.get('nationality') in (u'Noord-Nederlands', u'Nederlands'):
                data['descriptions']['en'] = {'language': u'en', 'value' : u'Dutch painter'}
                data['descriptions']['nl'] = {'language': u'nl', 'value' : u'Nederlands schilder'}
                countryId = u'Q55'
            elif metadata.get('nationality') in (u'Zuid-Nederlands', u'Belgisch'):
                data['descriptions']['en'] = {'language': u'en', 'value' : u'Belgian painter'}
                data['descriptions']['nl'] = {'language': u'nl', 'value' : u'Belgisch schilder'}
                countryId = u'Q31'
            elif metadata.get('nationality')==u'Italiaans':
                data['descriptions']['en'] = {'language': u'en', 'value' : u'Italian painter'}
                data['descriptions']['nl'] = {'language': u'nl', 'value' : u'Italiaans schilder'}
                countryId = u'Q38'
            elif metadata.get('nationality')==u'Duits':
                data['descriptions']['en'] = {'language': u'en', 'value' : u'German painter'}
                data['descriptions']['nl'] = {'language': u'nl', 'value' : u'Duits schilder'}
                countryId = u'Q183'
            elif metadata.get('nationality')==u'Frans':
                data['descriptions']['en'] = {'language': u'en', 'value' : u'French painter'}
                data['descriptions']['nl'] = {'language': u'nl', 'value' : u'Frans schilder'}
                countryId = u'Q142'
            
        print data

        identification = {}
        summary = u'Creating new painter item with data from the Rijksmuseum'
        pywikibot.output(summary)

        #return u'Q-1'

        

        result = self.repo.editEntity(identification, data, summary=summary)
        print result
        painterItemTitle = result.get(u'entity').get('id')
        painterItem = pywikibot.ItemPage(self.repo, title=painterItemTitle)
                         

        # It's a human
        humanItem = pywikibot.ItemPage(self.repo, title=u'Q5')
        newclaim = pywikibot.Claim(self.repo, u'P31')
        newclaim.setTarget(humanItem)
        painterItem.addClaim(newclaim)
        
        # Occupation is painter
        occupationItem = pywikibot.ItemPage(self.repo, title=u'Q1028181')
        newclaim = pywikibot.Claim(self.repo, u'P106')
        newclaim.setTarget(occupationItem)
        painterItem.addClaim(newclaim)
        
        # Gender
        genderItem = None
        if metadata.get('gender'):
            if metadata.get('gender')==u'man':
                genderItem = pywikibot.ItemPage(self.repo, title=u'Q6581097')
            elif metadata.get('gender')==u'vrouw':
                genderItem = pywikibot.ItemPage(self.repo, title=u'Q6581072')

            if genderItem:
                newclaim = pywikibot.Claim(self.repo, u'P21')
                newclaim.setTarget(genderItem)
                painterItem.addClaim(newclaim)               
        
        # Nationality
        if countryId:
            countryItem = pywikibot.ItemPage(self.repo, title=countryId)
            newclaim = pywikibot.Claim(self.repo, u'P27')
            newclaim.setTarget(countryItem)
            painterItem.addClaim(newclaim)                 
        
        # Date of birth
        if metadata.get('birth_on') and metadata.get('birth.date.end'):
            if metadata.get('birth_on')==metadata.get('birth.date.end'):
                newdate = self.getDate(metadata.get('birth_on'))
                newclaim = pywikibot.Claim(self.repo, u'P569') 
                newclaim.setTarget(newdate)
                painterItem.addClaim(newclaim)
            elif metadata.get('birth_on')[0:4]==metadata.get('birth.date.end')[0:4]:
                newdate = self.getDate(metadata.get('birth_on')[0:4])
                newclaim = pywikibot.Claim(self.repo, u'P569') 
                newclaim.setTarget(newdate)
                painterItem.addClaim(newclaim)

        # Date of death
        if metadata.get('died_on') and metadata.get('death.date.end'):
            if metadata.get('died_on')==metadata.get('death.date.end'):
                newdate = self.getDate(metadata.get('died_on'))
                newclaim = pywikibot.Claim(self.repo, u'P570') 
                newclaim.setTarget(newdate)
                painterItem.addClaim(newclaim)
            elif metadata.get('died_on')[0:4]==metadata.get('death.date.end')[0:4]:
                newdate = self.getDate(metadata.get('died_on')[0:4])
                newclaim = pywikibot.Claim(self.repo, u'P570') 
                newclaim.setTarget(newdate)
                painterItem.addClaim(newclaim)

        # Notable works
        if name in self.missingCreators:
            for workItemTitle in self.missingCreators[name]:
                workItemage = pywikibot.ItemPage(self.repo, workItemTitle)
                newclaim = pywikibot.Claim(self.repo, u'P800')
                newclaim.setTarget(workItemage)
                painterItem.addClaim(newclaim)
                

        return painterItem.title()


    def getDate (self, datestring):
        if len(datestring)==4:
            newdate = pywikibot.WbTime(year=int(datestring))
            return newdate

        dateList = datestring.split(u'-')

        if len(dateList)==2:
            newdate = pywikibot.WbTime(year=int(dateList[0]), month=int(dateList[1]))
            return newdate
        elif len(dateList)==3:
            newdate = pywikibot.WbTime(year=int(dateList[0]), month=int(dateList[1]), day=int(dateList[2]))
            return newdate
            
            


        """  
                    
            newclaim = pywikibot.Claim(self.repo, u'P170')
            newclaim.setTarget(newcreator)
            pywikibot.output('Adding creator claim to %s' % paintingItem)
            paintingItem.addClaim(newclaim)

                            newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                            newreference.setTarget(europeanaUrl)
                            pywikibot.output('Adding new reference claim to %s' % paintingItem)
                            newclaim.addSource(newreference)
                            
                            #creatoritem = pywikibot.ItemPage(self.repo, creatorpage)
                            print creatoritem.title()
                            print creatoritem.get()
            
            
            # Make sure it's the Frans Hals Museum
            if painting['object']['proxies'][0]['about'].startswith(u'/proxy/provider/92034/GVNRC_FHM01'):
                paintingId = painting['object']['proxies'][0]['dcIdentifier']['def'][0].strip()
                uri = painting['object']['proxies'][0]['dcIdentifier']['def'][1].strip()
                europeanaUrl = u'http://europeana.eu/portal/record/%s.html' % (painting['object']['about'],)

                print paintingId
                print uri

                if painting['object']['proxies'][0].get('dcCreator'):
                    dcCreator = painting['object']['proxies'][0]['dcCreator']['def'][0].strip()
                else:
                    dcCreator = u'anoniem'
                #print dcCreator

                paintingItem = None
                newclaims = []
                if paintingId in self.paintingIds:
                    paintingItemTitle = u'Q%s' % (self.paintingIds.get(paintingId),)
                    print paintingItemTitle
                    paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

                else:
                    
                    #print 'bla'
                    #monumentItem = pywikibot.ItemPage(self.repo, title=u'')

                    
                            #print dcCreatorName


                    data = {'labels': {},
                            'descriptions': {},
                            }

                    data['labels'][u'nl'] = {'language': u'nl', 'value': painting['object']['title'][0]}
                    

                    if dcCreator:
                        data['descriptions']['en'] = {'language': u'en', 'value' : u'painting by %s' % (dcCreator,)}
                        data['descriptions']['nl'] = {'language': u'nl', 'value' : u'schilderij van %s' % (dcCreator,)}
                        

                    print data

                    identification = {}
                    summary = u'Creating new item with data from %s ' % (europeanaUrl,)
                    pywikibot.output(summary)
                    #monumentItem.editEntity(data, summary=summary)
                    result = self.repo.editEntity(identification, data, summary=summary)
                    #print result
                    paintingItemTitle = result.get(u'entity').get('id')
                    paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

                    newclaim = pywikibot.Claim(self.repo, u'P%s' % (self.paintingIdProperty,))
                    newclaim.setTarget(paintingId)
                    pywikibot.output('Adding new id claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)

                    newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                    newreference.setTarget(uri)
                    pywikibot.output('Adding new reference claim to %s' % paintingItem)
                    newclaim.addSource(newreference)
                    
                    newqualifier = pywikibot.Claim(self.repo, u'P195') #Add collection, isQualifier=True
                    newqualifier.setTarget(fhmuseum)
                    pywikibot.output('Adding new qualifier claim to %s' % paintingItem)
                    newclaim.addQualifier(newqualifier)

                    collectionclaim = pywikibot.Claim(self.repo, u'P195')
                    collectionclaim.setTarget(fhmuseum)
                    pywikibot.output('Adding collection claim to %s' % paintingItem)
                    paintingItem.addClaim(collectionclaim)

                    newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                    newreference.setTarget(europeanaUrl)
                    pywikibot.output('Adding new reference claim to %s' % paintingItem)
                    collectionclaim.addSource(newreference)
                    
                    

                if paintingItem and paintingItem.exists():
                    
                    data = paintingItem.get()
                    claims = data.get('claims')
                    #print claims

                    # located in
                    if u'P276' not in claims:
                        newclaim = pywikibot.Claim(self.repo, u'P276')
                        newclaim.setTarget(fhmuseum)
                        pywikibot.output('Adding located in claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                        newreference.setTarget(europeanaUrl)
                        pywikibot.output('Adding new reference claim to %s' % paintingItem)
                        newclaim.addSource(newreference)
                        

                    # instance of always painting while working on the painting collection
                    if u'P31' not in claims:
                        
                        dcformatItem = pywikibot.ItemPage(self.repo, title='Q3305213')

                        newclaim = pywikibot.Claim(self.repo, u'P31')
                        newclaim.setTarget(dcformatItem)
                        pywikibot.output('Adding instance claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                        newreference.setTarget(europeanaUrl)
                        pywikibot.output('Adding new reference claim to %s' % paintingItem)
                        newclaim.addSource(newreference) 

                    # creator        
                    if u'P170' not in claims and dcCreator:
                        creategen = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataItemGenerator(pagegenerators.SearchPageGenerator(dcCreator, step=None, total=10, namespaces=[0], site=self.repo)))
                        
                        newcreator = None


                        for creatoritem in creategen:
                            print creatoritem.title()
                            if creatoritem.get().get('labels').get('en') == dcCreator or creatoritem.get().get('labels').get('nl') == dcCreator:
                                print creatoritem.get().get('labels').get('en')
                                print creatoritem.get().get('labels').get('nl')
                                # Check occupation and country of citizinship
                                if u'P106' in creatoritem.get().get('claims') and u'P27' in creatoritem.get().get('claims'):
                                    newcreator = creatoritem
                                    continue
                            elif (creatoritem.get().get('aliases').get('en') and dcCreator in creatoritem.get().get('aliases').get('en')) or (creatoritem.get().get('aliases').get('nl') and dcCreator in creatoritem.get().get('aliases').get('nl')):
                                if u'P106' in creatoritem.get().get('claims') and u'P27' in creatoritem.get().get('claims'):
                                    newcreator = creatoritem
                                    continue

                        if newcreator:
                            pywikibot.output(newcreator.title())

                            newclaim = pywikibot.Claim(self.repo, u'P170')
                            newclaim.setTarget(newcreator)
                            pywikibot.output('Adding creator claim to %s' % paintingItem)
                            paintingItem.addClaim(newclaim)

                            newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                            newreference.setTarget(europeanaUrl)
                            pywikibot.output('Adding new reference claim to %s' % paintingItem)
                            newclaim.addSource(newreference)
                            
                            #creatoritem = pywikibot.ItemPage(self.repo, creatorpage)
                            print creatoritem.title()
                            print creatoritem.get()
                                
                                

                            

                        else:
                            pywikibot.output('No item found for %s' % (dcCreator, ))
                        
                    # date of creation
                    if u'P571' not in claims:
                        if painting['object']['proxies'][0].get('dctermsCreated'):
                            dccreated = painting['object']['proxies'][0]['dctermsCreated']['def'][0].strip()
                            if len(dccreated)==4: # It's a year
                                newdate = pywikibot.WbTime(year=dccreated)
                                newclaim = pywikibot.Claim(self.repo, u'P571')
                                newclaim.setTarget(newdate)
                                pywikibot.output('Adding date of creation claim to %s' % paintingItem)
                                paintingItem.addClaim(newclaim)

                                newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                                newreference.setTarget(europeanaUrl)
                                pywikibot.output('Adding new reference claim to %s' % paintingItem)
                                newclaim.addSource(newreference)
                    '''
                    # material used
                    if u'P186' not in claims:
                        dcFormats = { u'http://vocab.getty.edu/aat/300014078' : u'Q4259259', # Canvas
                                      u'http://vocab.getty.edu/aat/300015050' : u'Q296955', # Oil paint
                                      }
                        if painting['object']['proxies'][0].get('dcFormat') and painting['object']['proxies'][0]['dcFormat'].get('def'):
                            for dcFormat in painting['object']['proxies'][0]['dcFormat']['def']:
                                if dcFormat in dcFormats:
                                    dcformatItem = pywikibot.ItemPage(self.repo, title=dcFormats[dcFormat])

                                    newclaim = pywikibot.Claim(self.repo, u'P186')
                                    newclaim.setTarget(dcformatItem)
                                    pywikibot.output('Adding material used claim to %s' % paintingItem)
                                    paintingItem.addClaim(newclaim)

                                    newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                                    newreference.setTarget(europeanaUrl)
                                    pywikibot.output('Adding new reference claim to %s' % paintingItem)
                                    newclaim.addSource(newreference)
                    
                    # Handle 
                    if u'P1184' not in claims:
                        handleUrl = painting['object']['proxies'][0]['dcIdentifier']['def'][0]
                        handle = handleUrl.replace(u'http://hdl.handle.net/', u'')
                        
                        newclaim = pywikibot.Claim(self.repo, u'P1184')
                        newclaim.setTarget(handle)
                        pywikibot.output('Adding handle claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                        newreference.setTarget(europeanaUrl)
                        pywikibot.output('Adding new reference claim to %s' % paintingItem)
                        newclaim.addSource(newreference)
                    '''
                    # Europeana ID
                    if u'P727' not in claims:
                        europeanaID = painting['object']['about'].lstrip('/')

                        newclaim = pywikibot.Claim(self.repo, u'P727')
                        newclaim.setTarget(europeanaID)
                        pywikibot.output('Adding Europeana ID claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                        newreference.setTarget(europeanaUrl)
                        pywikibot.output('Adding new reference claim to %s' % paintingItem)
                        newclaim.addSource(newreference)

        """

def WikidataQueryPageGenerator(query, site=None):
    """Generate pages that result from the given WikidataQuery.

    @param query: the WikidataQuery query string.
    @param site: Site for generator results.
    @type site: L{pywikibot.site.BaseSite}

    """
    if site is None:
        site = pywikibot.Site()
    repo = site.data_repository()

    wd_queryset = wdquery.QuerySet(query)

    wd_query = wdquery.WikidataQuery(cacheMaxAge=0)
    data = wd_query.query(wd_queryset)

    pywikibot.output(u'retrieved %d items' % data[u'status'][u'items'])
    for item in data[u'items']:
        itempage = pywikibot.ItemPage(repo, u'Q' + unicode(item))
        yield itempage       

def getPainterGenerator():
    with open('csv VV SK Maarten Dammers.csv', 'rb') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            yield row
    


def main():
    
        
    #painterGen = getPainterGenerator()
    



    rkdBot = RkdBot()
    rkdBot.run()
    
    

if __name__ == "__main__":
    main()
