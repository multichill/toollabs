#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
A bot to add and update creators on paintings.

"""
import pywikibot
from pywikibot import pagegenerators
import re

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
                         u'Unbekannter Künstler' : anonymous,
                         u'Indian' : anonymous,
                         u'Japanese' : anonymous,
                         u'Tibetan' : anonymous,
                         u'Mughal' : anonymous,
                         u'unknown artist' : anonymous,
                         u'American School, painter' : anonymous,
                         u'N/A' : anonymous,
                         u'English School' : anonymous,
                         u'Dutch School' : anonymous,
                         u'British School 18th century' : anonymous,
                         u'French School, painter' : anonymous,
                         u'Netherlandish School' : anonymous,
                         u'Unknown Anglo-Netherlandish artist' : anonymous,
                         u'Unknown English artist' : anonymous,
                         u'onbekend' : anonymous,
                         u'an unknown artist' : anonymous,
                         u'anonymous painter' : anonymous,
                         u'Unknown Italian artist' : anonymous,
                         u'Anonymous Artist' : anonymous,
                         u'Unknown German artist' : anonymous,
                         u'Islamic' : anonymous,
                         u'Unknown artist of the venetian school' : anonymous,
                         u'French painter' : anonymous,
                         u'Okänd' : anonymous,
                         u'unidentified artist' : anonymous,
                         #u'' : anonymous,
                        }
        self.replaceableCreators = { u'Q19595156' : True, # Not the right Gerhard Richter
                                   } 
                    
    def run(self):
        """
        Starts the robot.
        """
        regex = u'^painting by ([^\(]+)(\s\([^\)]+\))?$'
        attributed_regex = u'^painting [aA]ttributed to ([^\(]+)(\s\([^\)]+\))?$'
        #regex = u'^anonymous painting$'
        #regex = u'^peinture de (.+)$'
        for item in self.generator:
            pywikibot.output(u'Working on %s' % (item.title(),))
            
            if item.exists() and not item.isRedirectPage():
                data = item.get()

                # If we don't want to change this, we might as well bail out now
                if data.get('claims').get('P170') and not self.change:
                    pywikibot.output('Item already has creator (P170) claim and change is set to False')
                    continue

                # We need an English description
                if not (data.get('descriptions') and data.get('descriptions').get(u'en')):
                    pywikibot.output('No English description I can use')
                    continue

                if data.get('descriptions').get(u'en').lower()=='painting':
                    pywikibot.output('Unable to extract a name from the English description "painting"')
                    continue

                # And this description should match our regex
                match = re.match(regex, data.get('descriptions').get(u'en'))
                attributed_match = re.match(attributed_regex, data.get('descriptions').get(u'en'))
                if not match and not attributed_match:
                    pywikibot.output('Regexes didn\'t match on "%s"' % (data.get('descriptions').get(u'en'),))
                    continue

                # Let's see if we can find a victim
                if match:
                    creator = match.group(1).strip()
                    attributed = False
                elif attributed_match:
                    creator = attributed_match.group(1).strip()
                    attributed = True

                # The search generator in getCreator() sometimes times out
                try:
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
                except pywikibot.exceptions.TimeoutError:
                    pywikibot.output(u'Looks like the search timed out while looking for %s' % (creator,))
                    continue

                # No creator set yet
                if not data.get('claims').get('P170'):
                    newclaim = pywikibot.Claim(self.repo, u'P170')
                    newclaim.setTarget(creatorItem)
                    summary = 'Adding creator [[%s]] based on "%s"' % (creatorItem.title(), data.get('descriptions').get(u'en'))
                    pywikibot.output(summary)
                    item.addClaim(newclaim, summary=summary)
                    if attributed:
                        newqualifier = pywikibot.Claim(self.repo, 'P5102')
                        newqualifier.setTarget(pywikibot.ItemPage(self.repo, 'Q230768'))
                        newclaim.addQualifier(newqualifier)
                # We do have a creator, let's see if we can replace it
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
                            if attributed:
                                newqualifier = pywikibot.Claim(self.repo, 'P5102')
                                newqualifier.setTarget(pywikibot.ItemPage(self.repo, 'Q230768'))
                                creatorclaim.addQualifier(newqualifier)

    def getCreator(self, creator):
        """
        Find the painter with the name in creator

        First check if the name is already in the self.creators cache
        Second, do a search
        If a hit is found, update the cache in self.creators
        """

        # First use the cache
        if creator in self.creators:
            return self.creators[creator]

        # Search Wikidata for a suitable candidate, tell the search to only return humans
        searchstring = u'%s haswbstatement:P31=Q5' % (creator,)
        creategen = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikibaseItemGenerator(pagegenerators.SearchPageGenerator(searchstring, step=None, total=50, namespaces=[0], site=self.repo)))

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
        anonymousRegex = '^(Workshop of|Follower of|Circle of|Manner of|Forgery after|School of|After|Unidentified Artist|School of)\s.*$'
        anonymousMatch = re.match(anonymousRegex, creator, flags=re.I)
        if anonymousMatch:
            self.creators[creator] = self.creators.get('anonymous')
            return self.creators.get('anonymous')
                        
        # We don't want to do the same search over and over again
        self.creators[creator] = None
        return None

    def replaceableCreator(self, oldCreatorItem):
        """
        Figure out if we should replace this or not
        """

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

def main(*args):
    """
    Do a query and have the bot process the items
    :param args:
    :return:
    """

    # The queries for paintings without a creator, all or a specific collection
    query = u'SELECT ?item WHERE { ?item wdt:P31 wd:Q3305213 . MINUS { ?item wdt:P170 [] } }'
    querycollection = u"""SELECT ?item WHERE { ?item wdt:P31 wd:Q3305213 .
                                 ?item wdt:P195 wd:%s .
                                 MINUS { ?item wdt:P170 [] }
                           }"""

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-collectionid'):
            if len(arg) == 13:
                collectionid = pywikibot.input(
                        u'Please enter the collectionid you want to work on:')
            else:
                collectionid = arg[14:]
            query = querycollection % (collectionid,)

    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    paintingBot = PaintingBot(generator, change=False)
    paintingBot.run()

if __name__ == "__main__":
    main()
