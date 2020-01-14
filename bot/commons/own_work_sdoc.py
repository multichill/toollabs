#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to convert own work images to SDoC (structured data on Commons).

https://commons.wikimedia.org/wiki/Category:Self-published_work contains about 25M files. The source, author and license
information should be converted to structured data format (https://commons.wikimedia.org/wiki/Commons:Structured_data).

Relevant modeling pages:
* https://commons.wikimedia.org/wiki/Commons:Structured_data/Modeling/Source
* https://commons.wikimedia.org/wiki/Commons:Structured_data/Modeling/Author
* https://commons.wikimedia.org/wiki/Commons:Structured_data/Modeling/Licensing

Should be switched to a more general Pywikibot implementation.

"""

import pywikibot
import re
import pywikibot.data.sparql
import time
from pywikibot.comms import http
import json
from pywikibot import pagegenerators

class OwnWorkBot:
    """
    Bot to add structured data statements on Commons
    """
    def __init__(self, gen):
        """
        Grab generator based on search to work on.
        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()

        self.validLicenses = self.getLicenseTemplates()
        self.generator = gen

    def getLicenseTemplates(self):
        """
        Get the monuments currently on Wikidata. Keep the id as a string.
        :return:
        """
        # FIXME: Do query later
        # cc-by-sa-3.0-au,-ee,-es,-fr,-lu,-ro all have 10.000+ files in it
        result = { u'cc-zero' : u'Q6938433',
                   u'cc-by-2.0' : u'Q19125117',
                   u'cc-by-3.0' : u'Q14947546',
                   u'cc-by-4.0' : u'Q20007257',
                   u'cc-by-sa-2.0' : u'Q19068220',
                   u'cc-by-sa-3.0' : u'Q14946043',
                   u'cc-by-sa-3.0-at' : u'Q80837139',
                   u'cc-by-sa-3.0-de' : u'Q42716613',
                   u'cc-by-sa-3.0-nl' : u'Q18195572',
                   u'cc-by-sa-3.0-pl' : u'Q80837607',
                   u'cc-by-sa-4.0' : u'Q18199165',
                   }
        return result

    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            # Probably want to get this all in a preloading generator to make it faster
            mediaid = u'M%s' % (filepage.pageid,)
            currentdata = self.getCurrentMediaInfo(mediaid)
            self.handleOwnWork(filepage, mediaid, currentdata)

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

    def handleOwnWork(self, filepage, mediaid, currentdata):
        """
        Handle a single own work file.
        Try to extract the template, look up the id and add the Q if no mediainfo is present.

        :param filepage: The page of the file to work on.
        :return: Nothing, edit in place
        """
        pywikibot.output(u'Working on %s' % (filepage.title(),))
        if not filepage.exists():
            return

        # Check if the file is own work
        if not self.isOwnWorkFile(filepage):
            pywikibot.output(u'No own and self templates found on %s, skipping' % (filepage.title(),))
            return

        # Get the author
        authorInfo = self.getAuthor(filepage)
        if not authorInfo:
            pywikibot.output(u'Unable to extract author on %s, skipping' % (filepage.title(),))
            return
        (authorPage, authorName) = authorInfo

        # Get one or more licenses
        licenses = self.getSelfLicenses(filepage)
        if not licenses:
            pywikibot.output(u'Unable to extract licenses on %s, skipping' % (filepage.title(),))
            return

        # Here we're collecting
        newclaims = {}

        # We got all the needed info, let's add it
        newclaims['source'] = self.addSourceOwn(mediaid, currentdata)
        newclaims['author'] = self.addAuthor(mediaid, currentdata, authorPage, authorName)
        newclaims['copyright'] = self.addLicenses(mediaid, currentdata, licenses)
        # Optional stuff, maybe split that up too
        newclaims['date'] = self.handleDate(mediaid, currentdata, filepage)
        newclaims['coordinates'] = self.handleCoordinates(mediaid, currentdata, filepage)

        addedclaims = []

        itemdata = {u'claims' : [] }

        for newclaim in newclaims:
            if newclaims.get(newclaim):
                itemdata['claims'].extend(newclaims.get(newclaim))
                addedclaims.append(newclaim)

        if len(addedclaims) > 0:
            summary = u'Adding structured data: %s' % (addedclaims[0],)
            if len(addedclaims) > 2:
                for i in range(1, len(addedclaims)-1):
                    summary = summary + u', %s' % (addedclaims[i],)
            if len(addedclaims) > 1:
                summary = summary + u' & %s' % (addedclaims[-1],)

            # Flush it
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
            data = request.submit()
            return

    def isOwnWorkFile(self, filepage):
        """
        Check if the file is own work. We do that by looking for both the "own" and the "self" template.
        :param filepage: The page of the file to work on.
        :return:
        """
        ownfound = False
        selfFound = False

        for template in filepage.itertemplates():
            if template.title()==u'Template:Own':
                ownfound = True
            elif template.title()==u'Template:Self':
                selfFound = True

        if ownfound and selfFound:
            pywikibot.output(u'Own work found!')
            return True
        return False

    def getAuthor(self, filepage):
        """
        Extract the author form the information template
        :param filepage: The page of the file to work on.
        :return: Tuple with a User and a string
        """

        authorRegex = u'^\s*[aA]uthor\s*\=\s*\[\[User\:([^\|^\]]+)\|([^\|^\]]+)\]\](\s*\(\s*\[\[User talk\:[^\|^\]]+\|[^\|^\]]+\]\]\s*\)\s*)?\s*$'

        for template, parameters in filepage.templatesWithParams():
            if template.title()==u'Template:Information':
                for field in parameters:
                    if field.lower().startswith(u'author'):
                        match = re.match(authorRegex, field)
                        if match:
                            authorPage = pywikibot.User(self.site, match.group(1))
                            authorName = match.group(2).strip()
                            return (authorPage, authorName)
                        else:
                            pywikibot.output(field)
                        break

        return False

    def getSelfLicenses(self, filepage):
        """
        Extract one or more licenses from the Self template
        :param filepage: The page of the file to work on.
        :return: List of Q ids of licenses
        """
        result = []

        for template, parameters in filepage.templatesWithParams():
            if template.title()==u'Template:Self':
                for license in parameters:
                    if license.lower() in self.validLicenses:
                        result.append(self.validLicenses.get(license.lower()))
                    else:
                        return False
                break
        return result

    def addSourceOwn(self, mediaid, currentdata):
        """
        Dummy method for now
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P7482'):
            return False
        return self.addClaimJson(mediaid, u'P7482', u'Q66458942')


    def addAuthor(self, mediaid, currentdata, authorPage, authorName):
        """
        Add the author info to filepage
        :param authorPage:
        :param authorName:
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P170'):
            return False

        toclaim = {'mainsnak': { 'snaktype':'somevalue',
                                 'property': 'P170',
                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   'qualifiers' : {'P3831' : [ {'snaktype': 'value',
                                                'property': 'P3831',
                                                'datavalue': { 'value': { 'numeric-id': '33231',
                                                                          'id' : 'Q33231',
                                                                          },
                                                               'type' : 'wikibase-entityid',
                                                               },
                                                } ],
                                   'P2093' : [ {'snaktype': 'value',
                                                'property': 'P2093',
                                                'datavalue': { 'value': authorName,
                                                               'type' : 'string',
                                                               },
                                                } ],
                                   'P4174' : [ {'snaktype': 'value',
                                                'property': 'P4174',
                                                'datavalue': { 'value': authorPage.username,
                                                               'type' : 'string',
                                                               },
                                                } ],
                                   'P2699' : [ {'snaktype': 'value',
                                                'property': 'P2699',
                                                'datavalue': { 'value': u'https://commons.wikimedia.org/wiki/%s' % (authorPage.title(underscore=True), ),
                                                               'type' : 'string',
                                                               },
                                                } ],
                                   },
                   }
        return [toclaim,]

    def addLicenses(self, mediaid, currentdata, licenses):
        """
        Add the author info to filepage
        :param authorPage:
        :param authorName:
        :return:
        """
        if currentdata.get('statements'):
            if currentdata.get('statements').get('P6216'):
                return False
            if currentdata.get('statements').get('P275'):
                return False

        # Add the fact that the file is copyrighted
        result = self.addClaimJson(mediaid, u'P6216', u'Q50423863')

        # Add the different licenses
        for license in licenses:
            result.extend(self.addClaimJson(mediaid, u'P275', license))
        return result

    def handleDate(self, mediaid, currentdata, filepage):
        """
        Handle the date on the filepage. If it matches an ISO date (YYYY-MM-DD) (with or without time), add a date claim
        :param filepage:
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P571'):
            return False

        dateRegex = u'^\s*[dD]ate\s*\=\s*(\d\d\d\d-\d\d-\d\d)(\s*\d\d\:\d\d(\:\d\d(\.\d\d)?)?)?\s*$'
        dateString = None

        for template, parameters in filepage.templatesWithParams():
            if template.title()==u'Template:Information':
                for field in parameters:
                    if field.lower().startswith(u'date'):
                        match = re.match(dateRegex, field)
                        if match:
                            dateString = match.group(1).strip()
                        break
        if not dateString:
            return False

        # FIXME: Switch to a site request
        parserequest = http.fetch(u'https://commons.wikimedia.org/w/api.php?format=json&action=wbparsevalue&datatype=time&values=%s' % (dateString,))
        parsedata = json.loads(parserequest.text)
        postvalue = parsedata.get(u'results')[0].get('value')

        toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': 'P571',
                                 'datavalue': { 'value': postvalue,
                                                'type' : 'time',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        return [toclaim,]

    def handleCoordinates(self, mediaid, currentdata, filepage):
        """
        Handle the date on the filepage. If it matches an ISO date (YYYY-MM-DD) (with or without time), add a date claim
        :param filepage:
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P1259'):
            return False

        cameraregex = u'\{\{[lL]ocation(\s*dec)?\|(?P<lat>-?\d+\.?\d*)\|(?P<lon>-?\d+\.?\d*)(\|heading\:(?P<heading>\d+))?\}\}'
        objectregex = u'\{\{[oO]bject location(\s*dec)?\|(?P<lat>-?\d+\.?\d*)\|(?P<lon>-?\d+\.?\d*)\}\}'

        cameramatch = re.search(cameraregex, filepage.text)
        objectmatch = re.search(objectregex, filepage.text)

        if not cameramatch and not objectmatch:
            return False

        if cameramatch and not cameramatch.group('heading'):
            coordinateText = u'%s %s' % (cameramatch.group('lat'), cameramatch.group('lon'), )
            # FIXME: Switch to a site request
            parserequest = http.fetch(u'https://commons.wikimedia.org/w/api.php?format=json&action=wbparsevalue&datatype=globe-coordinate&values=%s' % (coordinateText,))
            parsedata = json.loads(parserequest.text)
            if parsedata.get('error'):
                return False

            postvalue = parsedata.get(u'results')[0].get('value')

            toclaim = {'mainsnak': { 'snaktype':'value',
                                     'property': 'P1259',
                                     'datavalue': { 'value': postvalue,
                                                    'type' : 'globecoordinate',
                                                    }

                                     },
                       'type': 'statement',
                       'rank': 'normal',
                       }
            if cameramatch.group('heading'):
                toclaim['qualifiers'] = {'P7787' : [ {'snaktype': 'value',
                                                      'property': 'P7787',
                                                      'datavalue': { 'value': { 'amount': '+%s' % (cameramatch.group('heading'),),
                                                                                #'unit' : '1',
                                                                                'unit' : 'http://www.wikidata.org/entity/Q28390',
                                                                                },
                                                                     'type' : 'quantity',
                                                                     },
                                                      },
                                                     ],
                                         }
            return [toclaim,]

        elif objectmatch:
            if currentdata.get('statements') and currentdata.get('statements').get('P625'):
                return False

            coordinateText = u'%s %s' % (objectmatch.group('lat'), objectmatch.group('lon'), )
            # FIXME: Switch to a site request
            parserequest = http.fetch(u'https://commons.wikimedia.org/w/api.php?format=json&action=wbparsevalue&datatype=globe-coordinate&values=%s' % (coordinateText,))
            parsedata = json.loads(parserequest.text)

            postvalue = parsedata.get(u'results')[0].get('value')

            toclaim = {'mainsnak': { 'snaktype':'value',
                                     'property': 'P625',
                                     'datavalue': { 'value': postvalue,
                                                    'type' : 'globecoordinate',
                                                    }

                                     },
                       'type': 'statement',
                       'rank': 'normal',
                       }
            return [toclaim,]


    def addClaimJson(self, mediaid, pid, qid):
        """
        Add a claim to a mediaid

        :param mediaid: The mediaid to add it to
        :param pid: The property P id (including the P)
        :param qid: The item Q id (including the Q)
        :param summary: The summary to add in the edit
        :return: Nothing, edit in place
        """
        toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': pid,
                                 'datavalue': { 'value': { 'numeric-id': qid.replace(u'Q', u''),
                                                           'id' : qid,
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        return [toclaim,]


def main(*args):
    gen = None
    genFactory = pagegenerators.GeneratorFactory()

    for arg in pywikibot.handle_args(args):
        if genFactory.handleArg(arg):
            continue
    gen = genFactory.getCombinedGenerator(gen, preload=True)

    ownWorkBot = OwnWorkBot(gen)
    ownWorkBot.run()

if __name__ == "__main__":
    main()
