#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add valued image claim to SDC.

Loop over https://commons.wikimedia.org/w/api.php?action=query&list=categorymembers&cmtitle=Category:Valued_images_sorted_by_promotion_date&cmprop=ids|sortkey|sortkeyprefix|timestamp|title|type&cmtype=file&cmlimit=100&format=json

Pageid with M is the entity id, the sortkeyprefix is a unix time stamp needed for the start time.
"""

import pywikibot
import time
import json
import datetime

class ValuedImageBot:
    """
    Bot to add structured data statements on Commons
    """
    def __init__(self):
        """
        Grab generator based on search to work on.
        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()

        self.generator = self.getGenerator()

    def getGenerator(self):
        """
        Get the generator to work on. Yields dict with these fields:
        * page
        * mediaid
        * starttime
        """
        continuemore = True
        cmcontinue = None
        while continuemore:
            postdata = {'action' : 'query',
                        'format' : 'json',
                        'list' : 'categorymembers',
                        'cmtitle' : 'Category:Valued_images_sorted_by_promotion_date',
                        'cmprop' : 'ids|sortkey|sortkeyprefix|timestamp|title|type',
                        'cmtype' : 'file',
                        'cmlimit' : 100,
                        'cmcontinue' : cmcontinue
                        }

            if cmcontinue:
                postdata['postdata'] = postdata
            request = self.site._simple_request(**postdata)
            data = request.submit()
            if data.get('query-continue') and data.get('query-continue').get('categorymembers') \
                    and data.get('query-continue').get('categorymembers').get('cmcontinue'):
                cmcontinue = data.get('query-continue').get('categorymembers').get('cmcontinue')
            else:
                cmcontinue = None
                continuemore = False
            for categorymember in data.get('query').get('categorymembers'):
                try:
                    yield { 'page' : pywikibot.FilePage(self.site, title=categorymember.get('title')),
                            'mediaid' : 'M%s' % (categorymember.get('pageid')),
                            'starttime' : datetime.datetime.utcfromtimestamp(int(categorymember.get('sortkeyprefix'))).strftime('%Y-%m-%d'),
                            }
                except ValueError:
                    # Some dates are not correctly formatted
                    continue

    def run(self):
        """
        Run on the items
        """
        alreadydonecounter = 0

        for pagedict in self.generator:
            filepage = pagedict.get('page')
            mediaid = pagedict.get('mediaid')
            starttime = pagedict.get('starttime')

            if not filepage.exists():
                continue

            currentdata = self.getCurrentMediaInfo(mediaid)
            alreadydone = self.handleValuedImage(filepage, mediaid, currentdata, starttime)
            #if alreadydone:
            #    alreadydonecounter +=1
            # Later I can change to reverse sorting and use this in a cronjob
            #if alreadydonecounter > 250:
            #    return


    def getCurrentMediaInfo(self, mediaid):
        """
        Check if the media info exists. If that's the case, return that so we can expand it.
        Otherwise return an empty structure with just <s>claims</>statements in it to start
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :return: json
            """
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M52611909
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M10038
        request = self.site._simple_request(action='wbgetentities',ids=mediaid)
        data = request.submit()
        if data.get(u'entities').get(mediaid).get(u'pageid'):
            return data.get(u'entities').get(mediaid)
        return {}

    def handleValuedImage(self, filepage, mediaid, currentdata, starttime):
        """
        Handle a single file.

        :return: Nothing, edit in place
        """
        pywikibot.output(u'Working on %s' % (filepage.title(),))
        if not filepage.exists():
            return

        if currentdata.get('statements') and currentdata.get('statements').get('P6731'):
            for statement in currentdata.get('statements').get('P6731'):
                if statement.get('mainsnak').get('datavalue').get('value').get('id')=='Q63348040':
                    # Already on it. I'm not checking for the start time qualifier
                    return True

        # Use the API to format the date
        request = self.site._simple_request(action='wbparsevalue', datatype='time', values=starttime)
        try:
            data = request.submit()
        except AssertionError:
            # This will break at some point in the future
            return False
        datevalue = data.get(u'results')[0].get('value')

        toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': 'P6731',
                                 'datavalue': { 'value': { 'numeric-id': 63348040,
                                                           'id' : 'Q63348040',
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   'qualifiers' : {'P580' : [ { 'snaktype':'value',
                                                'property': 'P580',
                                                'datavalue': { 'value': datevalue,
                                                               'type' : 'time',
                                                               }

                                                }, ],
                                   },
                   }

        itemdata = {u'claims' : [toclaim,] }
        summary = 'Valued image since %s added to structured data' % (starttime,)

        pywikibot.output(summary)

        token = self.site.tokens['csrf']

        postdata = {u'action' : u'wbeditentity',
                    u'format' : u'json',
                    u'id' : mediaid,
                    u'data' : json.dumps(itemdata),
                    u'token' : token,
                    u'summary' : summary,
                    u'bot' : True,
                    }

        request = self.site._simple_request(**postdata)
        try:
            data = request.submit()
            filepage.touch()
        except pywikibot.data.api.APIError:
            pywikibot.output('Got an API error while saving page. Sleeping and skipping')
            time.sleep(120)
            # Reload the tokens to be sure
            self.site.get_tokens('csrf')
        return


def main(*args):
    valuedImageBot = ValuedImageBot()
    valuedImageBot.run()

if __name__ == "__main__":
    main()
