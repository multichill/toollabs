#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
A bot to add and update creators on paintings.

"""
import pywikibot
from pywikibot import pagegenerators
import re

class PaintingCreatorBot:
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
        anonymous = pywikibot.ItemPage(self.repo, 'Q4233718')
        self.creators = {'unknown painter' : anonymous,
                         'anonymous' : anonymous,
                         'Unidentified' : anonymous,
                         'tuntematon' : anonymous,
                         'American 19th Century' : anonymous,
                         'Unknown' : anonymous,
                         'Unidentified artist' : anonymous,
                         'Unidentified Artist' : anonymous,
                         'Anonymous' : anonymous,
                         'Anoniem' : anonymous,
                         'Chinese' : anonymous,
                         'French Painter' : anonymous,
                         'Unidentified artist, American, mid-19th century' : anonymous,
                         'American 18th Century' : anonymous,
                         'Artist unknown' : anonymous,
                         'Tibet' : anonymous,
                         'Company school' : anonymous,
                         'Russian Painter' : anonymous,
                         'Unidentified Puerto Rican Artist' : anonymous,
                         'India' : anonymous,
                         'Unidentified artist, American, 19th century' : anonymous,
                         'Netherlandish Painter' : anonymous,
                         'American' : anonymous,
                         'Antwerp' : anonymous,
                         'Belgium' : anonymous,
                         'British' : anonymous,
                         'China' : anonymous,
                         'Dutch' : anonymous,
                         'England' : anonymous,
                         'English' : anonymous,
                         'Flanders' : anonymous,
                         'France' : anonymous,
                         'French' : anonymous,
                         'German' : anonymous,
                         'Iran' : anonymous,
                         'Italy' : anonymous,
                         'Japan' : anonymous,
                         'Mongolia' : anonymous,
                         'Nepal' : anonymous,
                         'Persia' : anonymous,
                         'Russia' : anonymous,
                         'Southern Netherlands' : anonymous,
                         'Spain' : anonymous,
                         'Spanish' : anonymous,
                         'Yao people' : anonymous,
                         'Rajasthan, India' : anonymous,
                         'Jaipur, Rajasthan, India' : anonymous,
                         'French 19th Century' : anonymous,
                         'Bikaner, Rajasthan, India' : anonymous,
                         'Puri, Orissa, India' : anonymous,
                         'North India, India' : anonymous,
                         'German Painter' : anonymous,
                         'French 18th Century' : anonymous,
                         'Unknown Designer' : anonymous,
                         'British Painter' : anonymous,
                         'Kalighat school' : anonymous,
                         'Unknown artist' : anonymous,
                         'Unknown Artist' : anonymous,
                         'Unidentified artist, American, early 19th century' : anonymous,
                         'American 20th Century' : anonymous,
                         'Unidentified artist, French, 18th century' : anonymous,
                         'Unidentified artist, French, 19th century' : anonymous,
                         'Central Tibet' : anonymous,
                         'British 18th Century' : anonymous,
                         'Italian (Florentine) Painter' : anonymous,
                         'Northern French Painter' : anonymous,
                         'Netherlandish' : anonymous,
                         'Spanish (Catalan) Painter' : anonymous,
                         'Italian' : anonymous,
                         'North Netherlandish' : anonymous,
                         'Central India, India' : anonymous,
                         'Antwerp 16th Century' : anonymous,
                         'Unidentified artist, American, 18th century' : anonymous,
                         'French 15th Century' : anonymous,
                         'Northern Italy' : anonymous,
                         'Paris, France' : anonymous,
                         'Siena' : anonymous,
                         'South German' : anonymous,
                         'Unbekannter Künstler' : anonymous,
                         'Indian' : anonymous,
                         'Japanese' : anonymous,
                         'Tibetan' : anonymous,
                         'Mughal' : anonymous,
                         'unknown artist' : anonymous,
                         'American School, painter' : anonymous,
                         'N/A' : anonymous,
                         'English School' : anonymous,
                         'Dutch School' : anonymous,
                         'British School 18th century' : anonymous,
                         'French School, painter' : anonymous,
                         'Netherlandish School' : anonymous,
                         'Unknown Anglo-Netherlandish artist' : anonymous,
                         'Unknown English artist' : anonymous,
                         'onbekend' : anonymous,
                         'an unknown artist' : anonymous,
                         'anonymous painter' : anonymous,
                         'Unknown Italian artist' : anonymous,
                         'Anonymous Artist' : anonymous,
                         'Unknown German artist' : anonymous,
                         'Islamic' : anonymous,
                         'Unknown artist of the venetian school' : anonymous,
                         'French painter' : anonymous,
                         'Okänd' : anonymous,
                         'unidentified artist' : anonymous,
                         'Anonyme' : anonymous,
                         #u'' : anonymous,
                        }
        self.replaceableCreators = { u'Q19595156' : True, # Not the right Gerhard Richter
                                   } 
                    
    def run(self):
        """
        Starts the robot.
        """

        for item in self.generator:
            if item.exists() and not item.isRedirectPage():
                pywikibot.output(u'Working on %s' % (item.title(),))
                self.process_painting_item(item)

    def process_painting_item(self, item):
        """
        Process a single painting item
        :param item:
        :return:
        """
        regex = '^painting by ([^\(]+)(\s\([^\)]+\))?$'
        attributed_regex = '^painting [aA]ttributed to ([^\(]+)(\s\([^\)]+\))?$'
        data = item.get()

        # If we don't want to change this, we might as well bail out now
        if data.get('claims').get('P170') and not self.change:
            pywikibot.output('Item already has creator (P170) claim and change is set to False')
            return

        # We need an English description
        if not (data.get('descriptions') and data.get('descriptions').get('en')):
            pywikibot.output('No English description I can use')
            return

        # Just painting is just not enough
        if data.get('descriptions').get('en').lower()=='painting':
            pywikibot.output('Unable to extract a name from the English description "painting"')
            return

        # And this description should match our regex
        match = re.match(regex, data.get('descriptions').get('en'))
        attributed_match = re.match(attributed_regex, data.get('descriptions').get('en'))
        if not match and not attributed_match:
            pywikibot.output('Regexes didn\'t match on "%s"' % (data.get('descriptions').get('en'),))
            return

        # Let's see if we can find a victim
        if match:
            creator = match.group(1).strip()
            attributed = False
        elif attributed_match:
            creator = attributed_match.group(1).strip()
            attributed = True
        else:
            return

        # Try to extract the year of creation
        if data.get('claims').get('P571'):
            inception_claim = data.get('claims').get('P571')[0]
            inception = inception_claim.getTarget().year
        else:
            inception = None

        # The search generator in get_creator() sometimes times out
        try:
            creator_item = self.get_creator(creator, inception=inception)

            if not creator_item:
                pywikibot.output('No creator found for "%s"' % (creator,))

                # The name is maybe like "surname, firstname"
                if ',' not in creator:
                    # Just continue to the next painting
                    return
                else:
                    (surname, sep, firstname) = creator.partition(',')
                    creator = '%s %s' % (firstname.strip(), surname.strip(),)
                    creator_item = self.get_creator(creator)
                    if not creator_item:
                        pywikibot.output('No creator found for "%s" either' % (creator,))
                        return
        except pywikibot.exceptions.TimeoutError:
            pywikibot.output('Looks like the search timed out while looking for %s' % (creator,))
            return

        # We found a creator and no creator set yet
        if not data.get('claims').get('P170'):
            new_claim = pywikibot.Claim(self.repo, u'P170')
            new_claim.setTarget(creator_item)
            summary = 'Adding creator [[%s]] based on "%s"' % (creator_item.title(), data.get('descriptions').get('en'))
            pywikibot.output(summary)
            item.addClaim(new_claim, summary=summary)
            if attributed:
                new_qualifier = pywikibot.Claim(self.repo, 'P5102')
                new_qualifier.setTarget(pywikibot.ItemPage(self.repo, 'Q230768'))
                new_claim.addQualifier(new_qualifier)
        # We do have a creator, let's see if we can replace it
        else:
            creators = data.get('claims').get('P170')
            if len(creators)>1:
                pywikibot.output('More than one creator, I\'m not handling that!')
                return
            else:
                creator_claim = creators[0]
                if self.replaceableCreator(creator_claim.getTarget()):
                    summary = 'Changing creator [[%s]] to the painter [[%s]]' % (creator_claim.getTarget().title(), creator_item.title())
                    pywikibot.output(summary)
                    creator_claim.changeTarget(creator_item, summary=summary)
                    if attributed:
                        new_qualifier = pywikibot.Claim(self.repo, 'P5102')
                        new_qualifier.setTarget(pywikibot.ItemPage(self.repo, 'Q230768'))
                        creator_claim.addQualifier(new_qualifier)

    def get_creator(self, creator, inception=None):
        """
        Find the painter with the name in creator

        First check if the name is already in the self.creators cache
        Second, do a search
        If a hit is found, update the cache in self.creators
        """

        # First use the cache
        if creator in self.creators:
            return self.creators.get(creator)

        # Search Wikidata for a suitable candidate, tell the search to only return humans that are painters
        searchstring = 'inlabel:"%s" haswbstatement:P31=Q5 haswbstatement:P106=Q1028181' % (creator,)
        creator_gen = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikibaseItemGenerator(pagegenerators.SearchPageGenerator(searchstring, total=50, namespaces=[0], site=self.repo)))

        found_creators = []

        for creator_item in creator_gen:
            if creator_item.isRedirectPage():
                creator_item = creator_item.getRedirectTarget()
            # See if the label or one of the aliases of the creatoritem matches the string we have. Only label is case insensitive.
            if (creator_item.get().get('labels').get('en') and creator_item.get().get('labels').get('en').lower() == creator.lower()) or (creator_item.get().get('aliases').get('en') and creator in creator_item.get().get('aliases').get('en')):
                if 'P106' in creator_item.get().get('claims'):
                    existing_claims = creator_item.get().get('claims').get('P106')
                    for existing_claim in existing_claims:
                        if existing_claim.target_equals('Q1028181'):
                            self.creators[creator] = creator_item
                            found_creators.append(creator_item)

        if not found_creators:
            return None
        if not inception and len(found_creators) == 1:
            return found_creators[0]
        if not inception and len(found_creators) > 1:
            return None
        if inception:
            for found_creator in found_creators:
                creator_data = found_creator.get()

                if not creator_data.get('claims').get('P569'):
                    pywikibot.output('Date of birth missing for %s / %s' % (creator, found_creator,))
                    return None
                elif len(creator_data.get('claims').get('P569')) == 1:
                    if creator_data.get('claims').get('P569')[0].getTarget():
                        dob = creator_data.get('claims').get('P569')[0].getTarget().year
                    else:
                        return
                else:
                    if creator_data.get('claims').get('P569')[0].getTarget():
                        dob = creator_data.get('claims').get('P569')[0].getTarget().year
                    else:
                        return
                    for dob_claim in creator_data.get('claims').get('P569'):
                        if dob != dob_claim.getTarget().year and dob_claim.rank != 'deprecated':
                            pywikibot.output('Different date of birth years found for %s / %s' % (creator, found_creator,))
                            return None

                if creator_data.get('claims').get('P570') and len(creator_data.get('claims').get('P570')) == 1:
                    dod = creator_data.get('claims').get('P570')[0].getTarget().year
                else:
                    dod = dob + 100
                # And check if the inception makes sense
                if dob < inception <= dod:
                    return found_creator

        ## Regex that should match all the anonymous work stuff that isn't covered by the list
        #anonymousRegex = '^(Workshop of|Follower of|Circle of|Manner of|Forgery after|School of|After|Unidentified Artist|School of)\s.*$'
        #anonymousMatch = re.match(anonymousRegex, creator, flags=re.I)
        #if anonymousMatch:
        #    self.creators[creator] = self.creators.get('anonymous')
        #    return self.creators.get('anonymous')
                        
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
    query = 'SELECT ?item WHERE { ?item wdt:P31 wd:Q3305213 . MINUS { ?item wdt:P170 [] } }'
    query_collection = """SELECT ?item WHERE { ?item wdt:P31 wd:Q3305213 .
                                 ?item wdt:P195 wd:%s .
                                 MINUS { ?item wdt:P170 [] }
                           }"""

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-collectionid'):
            if len(arg) == 13:
                collection_id = pywikibot.input(
                        u'Please enter the collectionid you want to work on:')
            else:
                collection_id = arg[14:]
            query = query_collection % (collection_id,)

    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    painting_creator_bot = PaintingCreatorBot(generator, change=False)
    painting_creator_bot.run()

if __name__ == "__main__":
    main()
