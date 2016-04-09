#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
A bot to add and update creators on paintings.

"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib
import re
import pywikibot.data.wikidataquery as wdquery
from pywikibot.data import api

class PaintingBot:
    """
    A bot to add streets on Wikidata
    """
    def __init__(self, generator, change=False):
        """
        Arguments:
            * generator    - A generator that yields itempage objects.

        """
        self.generator = generator
        self.repo = pywikibot.Site().data_repository()
        self.change = change
        anonymous = pywikibot.ItemPage(self.repo, u'Q4233718')
        self.creators = {u'unknown painter' : anonymous,
                         u'anonymous' : anonymous,
                         u'Unidentified' : anonymous,
                         u'tuntematon' : anonymous,
                         u'American 19th Century' : anonymous,
                         u'Unknown' : anonymous,
                         u'Unidentified artist' : anonymous,
                         u'Unidentified Artist' : anonymous,
                         u'Anonymous' : anonymous,
                         u'Anoniem' : anonymous,
                         u'Chinese' : anonymous,
                         u'French Painter' : anonymous,
                         u'Unidentified artist, American, mid-19th century' : anonymous,
                         u'American 18th Century' : anonymous,
                         u'Artist unknown' : anonymous,
                         u'Tibet' : anonymous,
                         u'Company school' : anonymous,
                         u'Russian Painter' : anonymous,
                         u'Unidentified Puerto Rican Artist' : anonymous,
                         u'India' : anonymous,
                         u'Unidentified artist, American, 19th century' : anonymous,
                         u'Netherlandish Painter' : anonymous,
                         u'American' : anonymous,
                         u'Antwerp' : anonymous,
                         u'Belgium' : anonymous,
                         u'British' : anonymous,
                         u'China' : anonymous,
                         u'Dutch' : anonymous,
                         u'England' : anonymous,
                         u'English' : anonymous,
                         u'Flanders' : anonymous,
                         u'France' : anonymous,
                         u'French' : anonymous,
                         u'German' : anonymous,
                         u'Iran' : anonymous,
                         u'Italy' : anonymous,
                         u'Japan' : anonymous,
                         u'Mongolia' : anonymous,
                         u'Nepal' : anonymous,
                         u'Persia' : anonymous,
                         u'Russia' : anonymous,
                         u'Southern Netherlands' : anonymous,
                         u'Spain' : anonymous,
                         u'Spanish' : anonymous,
                         u'Yao people' : anonymous,
                         u'Rajasthan, India' : anonymous,
                         u'pupil of Joseph Mallord William Turner' : anonymous,
                         u'Attributed to Corneille de Lyon' : anonymous,
                         u'Jaipur, Rajasthan, India' : anonymous,
                         u'Pierre Henri de Valenciennes or Circle' : anonymous,
                         u'French 19th Century' : anonymous,
                         u'Bikaner, Rajasthan, India' : anonymous,
                         u'Puri, Orissa, India' : anonymous,
                         u'North India, India' : anonymous,
                         u'German Painter' : anonymous,
                         u'French 18th Century' : anonymous,
                         u'Workshop of Peter Paul Rubens' : anonymous,
                         u'Unknown Designer' : anonymous,
                         u'British Painter' : anonymous,
                         u'Rembrandts skole' : anonymous,
                         u'Kalighat school' : anonymous,
                         u'Unknown artist' : anonymous,
                         u'Unknown Artist' : anonymous,
                         u'Unidentified artist, American, early 19th century' : anonymous,
                         u'American 20th Century' : anonymous,
                         u'Unidentified artist, French, 18th century' : anonymous,
                         u'Jurriaan toegeschreven aan aan Andriessen' : anonymous,
                         u'Unidentified artist, French, 19th century' : anonymous,
                         u'Central Tibet' : anonymous,
                         u'British 18th Century' : anonymous,
                         u'Italian (Florentine) Painter' : anonymous,
                         u'Anonymous Artist, Titian' : anonymous,
                         u'Northern French Painter' : anonymous,
                         u'Netherlandish' : anonymous,
                         u'Spanish (Catalan) Painter' : anonymous,
                         u'Italian' : anonymous,
                         u'North Netherlandish' : anonymous,
                         u'Central India, India' : anonymous,
                         u'Antwerp 16th Century' : anonymous,
                         u'Unidentified artist, American, 18th century' : anonymous,
                         u'Workshop of Rogier van der Weyden' : anonymous,
                         u'French 15th Century' : anonymous,
                         u'Workshop of Giovanni Battista Tiepolo' : anonymous,
                         u'Workshop of Simone Martini' : anonymous,
                         u'Northern Italy' : anonymous,
                         u'Paris, France' : anonymous,
                         u'Siena' : anonymous,
                         u'South German' : anonymous,
                         #u'' : anonymous,
                         #u'' : anonymous,
                         #u'' : anonymous,
                         #u'' : anonymous,
                        }
        self.replaceableCreators = { u'Q19595156' : True, # Not the right Gerhard Richter
                                   } 
                    
    def run(self):
        """
        Starts the robot.
        """
        regex = u'^painting by ([^\(]+)(\s\([^\)]+\))?$'
        #regex = u'^anonymous painting$'
        #regex = u'^peinture de (.+)$'
        for item in self.generator:
            pywikibot.output(u'Working on %s' % (item.title(),))
            canreplace = False
            
            if item.exists():
                data = item.get()
                # We need an English description
                if not (data.get('descriptions') and data.get('descriptions').get(u'en')):
                    pywikibot.output('No English description I can use')
                    continue

                # And this description should match our regex
                match = re.match(regex, data.get('descriptions').get(u'en'))
                if not match:
                    pywikibot.output('Regex didn\'t match on "%s"' % (data.get('descriptions').get(u'en'),))
                    continue

                # If we don't want to change this, we might as well bail out now
                if data.get('claims').get('P170') and not self.change:
                    pywikibot.output('Item already has creator (P170) claim and change is set to False')
                    continue

                # Let's see if we can find a victim
                creator = match.group(1)
                creatorItem = self.getCreator(creator)
                if not creatorItem:
                    pywikibot.output(u'No creator found for "%s"' % (creator,))
                    
                    # The name is maybe like "surname, firstname"
                    if u',' not in creator:
                        # Just continue
                        continue
                    else:
                        (surname, sep, firstname) = creator.partition(u',')
                        creator = u'%s %s' % (firstname.strip(), surname.strip(),)
                        creatorItem = self.getCreator(creator)
                        if not creatorItem:
                            pywikibot.output(u'No creator found for "%s" either' % (creator,))
                            continue
                    

                # No occupation set yet
                if not data.get('claims').get('P170'):
                    newclaim = pywikibot.Claim(self.repo, u'P170')
                    newclaim.setTarget(creatorItem)
                    summary = 'Adding creator [[%s]] based on "%s"' % (creatorItem.title(), data.get('descriptions').get(u'en'))
                    pywikibot.output(summary)
                    item.addClaim(newclaim, summary=summary)
                # We do have an occupation, let's see if we can replace it
                else:
                    creators = data.get('claims').get('P170')
                    if len(creators)>1:
                        pywikibot.output(u'More than one creator, I\'m not handling that!')
                        continue
                    else:
                        creatorclaim = creators[0]
                        if self.replaceableCreator(creatorclaim.getTarget()):
                            summary = 'Changing creator [[%s]] to the painter [[%s]]' % (creatorclaim.getTarget().title(), creatorItem.title())
                            pywikibot.output(summary)
                            creatorclaim.changeTarget(creatorItem, summary=summary)
                        

    def getCreator(self, creator):
        '''
        Find the painter with the name in creator

        First check if the name is already in the self.creators cache
        Second, do a search
        If a hit is found, update the cache in self.creators
        '''

        # First use the cache
        if creator in self.creators:
            return self.creators[creator]

        # Search Wikidata for a suitable candidate
        creategen = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataItemGenerator(pagegenerators.SearchPageGenerator(creator, step=None, total=50, namespaces=[0], site=self.repo)))

        for creatoritem in creategen:
            if creatoritem.isRedirectPage():
                creatoritem = creatoritem.getRedirectTarget()
            # See if the label or one of the aliases of the creatoritem matches the string we have. Only label is case insensitive.
            if (creatoritem.get().get('labels').get('en') and creatoritem.get().get('labels').get('en').lower() == creator.lower()) or (creatoritem.get().get('aliases').get('en') and creator in creatoritem.get().get('aliases').get('en')):
                if u'P106' in creatoritem.get().get('claims'):
                    existing_claims = creatoritem.get().get('claims').get('P106')
                    for existing_claim in existing_claims:
                        if existing_claim.target_equals(u'Q1028181'):
                            self.creators[creator] = creatoritem
                            return creatoritem

        # Regex that should match all the anonymous work stuff that isn't covered by the list
        anonymousRegex = u'^(Attributed to|Workshop of|Follower of|Circle of|Manner of|Forgery after|School of|After|Unidentified Artist|School of)\s.*$'
        anonymousMatch = re.match(anonymousRegex, creator, flags=re.I)
        if anonymousMatch:
            self.creators[creator] = self.creators.get('anonymous')
            return self.creators.get('anonymous')
                        
        # We don't want to do the same search over and over again
        self.creators[creator] = None
        return None

    def replaceableCreator(self, oldCreatorItem):
        '''
        Figure out if we should replace this or not
        '''

        # If I encounter these, I'm skipping it
        skiplist = [ u'Q1028181', # painter, doh!
                     u'Q15296811', # draughtsperson
                     u'Q644687', # illustrator
                     u'Q3391743', # visual artist
                     u'Q483501', # artist
                     u'Q329439', # engraver
                     u'Q10862983', # etcher
                     u'Q18074503', # installation artist
                     u'Q1281618', # sculptor
                     u'Q1925963', # graphic artist
                     ]
        
        
        data = oldCreatorItem.get()
        if oldCreatorItem.title() in self.replaceableCreators:
            pywikibot.output(u'Cache says %s' % (self.replaceableCreators[oldCreatorItem.title()],))
            return self.replaceableCreators[oldCreatorItem.title()]
        if data.get('claims').get('P245'):
            pywikibot.output(u'Not replaceable, ULAN found')
            self.replaceableCreators[oldCreatorItem.title()]= False
            return False
        elif data.get('claims').get('P650'):
            pywikibot.output(u'Not replaceable, RKDartists found')
            self.replaceableCreators[oldCreatorItem.title()]= False
            return False
        elif data.get('claims').get('P1367'):
            pywikibot.output(u'Not replaceable, BBC Your Paintings artist identifier found')
            self.replaceableCreators[oldCreatorItem.title()]= False
            return False
        elif data.get('claims').get('P106'):
            existing_claims = oldCreatorItem.get().get('claims').get('P106')
            for existing_claim in existing_claims:
                for toskip in skiplist: 
                    if existing_claim.target_equals(toskip):
                        # We found some occupation we want to skip
                        self.replaceableCreators[oldCreatorItem.title()]= False
                        return False
            # We didn't find an occupation we wanted to skip
            self.replaceableCreators[oldCreatorItem.title()]= True
            return True
        else:
            pywikibot.output(u'No authority control and no occupation, let\'s try to replace this!')
            #No occupation found, no authority control, let's try to replace it
            self.replaceableCreators[oldCreatorItem.title()]= True
            return True

        #unreachable?
        self.replaceableCreators[oldCreatorItem.title()]= False
        return False


def WikidataQueryItemPageGenerator(query, site=None):
    """Generate pages that result from the given WikidataQuery.

    @param query: the WikidataQuery query string.

    """
    if site is None:
        site = pywikibot.Site()
    repo = site.data_repository()

    wd_queryset = wdquery.QuerySet(query)

    wd_query = wdquery.WikidataQuery(cacheMaxAge=0)
    data = wd_query.query(wd_queryset)

    pywikibot.output(u'retrieved %d items' % data[u'status'][u'items'])
    for item in data[u'items']:
        yield pywikibot.ItemPage(repo, u'Q' + unicode(item))
        


def testGenerator():
    '''
    Simple generator to test a single item
    '''
    site = pywikibot.Site()
    repo = site.data_repository()
    yield pywikibot.ItemPage(repo, u'Q20881436')
    
    


def main():

    # Paintings without a creator
    query = u'CLAIM[31:3305213] AND NOCLAIM[170]' # All paintings without creator
    #query = u'CLAIM[31:132137] AND NOCLAIM[170]' # Icons!
    # query = u'CLAIM[31:3305213] AND CLAIM[170] AND NOCLAIM[170:(CLAIM[106:1028181] )] AND NOCLAIM[170:4233718] AND NOCLAIM[170:4294967294]' # Creators to correct?
    #query = u'CLAIM[195:2983474] AND NOCLAIM[170]' # Finnish museum
    #query = u'CLAIM[31:3305213] AND NOCLAIM[170] AND CLAIM[195:1928672]' # Working on MuZEE
    #query = u'CLAIM[31:3305213] AND NOCLAIM[170] AND CLAIM[195:1641836))]' # Working on LACMA
    #query = u'CLAIM[31:3305213] AND NOCLAIM[170] AND CLAIM[195:1192305]' # Working on SAAM
    #query = u'CLAIM[31:3305213] AND NOCLAIM[170] AND CLAIM[195:132783]' # Working on Hermitage
    #query = u'CLAIM[31:3305213] AND NOCLAIM[170] AND CLAIM[195:1700481]' # Working on Minneapolis Institute of Art
    #query = u'CLAIM[31:3305213] AND CLAIM[195:705551] AND NOCLAIM[170] ' # Working on AGNSW
    #query = u'CLAIM[31:3305213] AND NOCLAIM[170] AND CLAIM[195:1416890]' # Working on San Fran
    #query = u'CLAIM[31:3305213] AND NOCLAIM[170] AND CLAIM[195:526170]' # Working on Biblioteca Museu Víctor Balaguer
    #query = u'CLAIM[31:3305213] AND NOCLAIM[170] AND CLAIM[195:1952033)]' # Working on Pennsylvania Academy of the Fine Arts
    #query = u'CLAIM[31:3305213] AND NOCLAIM[170] AND CLAIM[195:842858)]' # Working on Nationalmuseum Sweden
    #query = u'CLAIM[31:3305213] AND CLAIM[195:49133] AND NOCLAIM[170]' # Working on Boston
    pigenerator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataItemGenerator(WikidataQueryItemPageGenerator(query)))
    #pigenerator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataItemGenerator(testGenerator()))
    

    paintingBot = PaintingBot(pigenerator, change=False)
    paintingBot.run()
    
   

if __name__ == "__main__":
    main()
