#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to convert Geograph images to SDoC (structured data on Commons).

https://commons.wikimedia.org/wiki/Category:Images_from_Geograph_Britain_and_Ireland contains about 1.85M files.
The source, author and license information should be converted to structured data format
(https://commons.wikimedia.org/wiki/Commons:Structured_data). Probably date and coordinates too.

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

class GeographSDOCBot:
    """
    Bot to add structured data to Geograph uploads
    """
    def __init__(self, gen):
        """
        Grab generator based on search to work on.

        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()

        self.generator = gen



    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            if not filepage.exists():
                continue
            # Probably want to get this all in a preloading generator to make it faster
            mediaid = u'M%s' % (filepage.pageid,)
            currentdata = self.getCurrentMediaInfo(mediaid)
            self.handleGeographFile(filepage, mediaid, currentdata)

    def getCurrentMediaInfo(self, mediaid):
        """
        Check if the media info exists. If that's the case, return that so we can check against it
        Otherwise return an empty dict
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :return: dict
        """
        request = self.site._simple_request(action='wbgetentities',ids=mediaid)
        data = request.submit()
        if data.get(u'entities').get(mediaid).get(u'pageid'):
            return data.get(u'entities').get(mediaid)
        return {}

    def handleGeographFile(self, filepage, mediaid, currentdata):
        """
        Handle a Geograph file.
        Extract the metadata, add the structured data

        :param filepage: The page of the file to work on.
        :param mediaid: The mediaid of the file (like M12345)
        :param currentdata: Dict with the current structured data
        :return: Nothing, edit in place
        """
        pywikibot.output(u'Working on %s' % (filepage.title(),))
        if not filepage.exists():
            return

        # Get the author
        authorInfo = self.getAuthor(filepage)
        if not authorInfo:
            pywikibot.output(u'Unable to extract author on %s, skipping' % (filepage.title(),))
            return
        (authorUrl, authorName) = authorInfo
        print (authorUrl)
        print (authorName)

        # Check if the file is from Geograph
        geographid = self.getGeographId(filepage, authorName)
        if not geographid:
            pywikibot.output(u'No Geograph ID found  on %s, skipping' % (filepage.title(),))
            return
        print (geographid)

        # Here we're collecting
        newclaims = {}

        # We got all the needed info, let's add it
        newclaims['source'] = self.addSourceGeograph(mediaid, currentdata, geographid)
        newclaims['author'] = self.addAuthor(mediaid, currentdata, authorUrl, authorName)
        newclaims['copyright'] = self.addCopyrightLicense(mediaid, currentdata)
        # Optional stuff, maybe split that up too
        newclaims['date'] = self.handleDate(mediaid, currentdata, filepage)
        newclaims['coordinates'] = self.handlePointOfViewCoordinates(mediaid, currentdata, filepage)
        newclaims['object coordinates'] = self.handleObjectCoordinates(mediaid, currentdata, filepage)

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

    def getAuthor(self, filepage):
        """
        Extract the author from the information template
        :param filepage: The page of the file to work on.
        :return: Tuple with a User and a string
        """

        # |author=[https://www.geograph.org.uk/profile/5 Helena Downton]
        authorRegex = u'^[aA]uthor\s*\=\s*\[\s*(https\:\/\/www\.geograph\.org\.uk\/profile\/\d+) ([^\]]+)\s*\]$'

        for template, parameters in filepage.templatesWithParams():
            if template.title()==u'Template:Information':
                for field in parameters:
                    if field.lower().startswith(u'author'):
                        match = re.match(authorRegex, field)
                        if match:
                            authorLink = match.group(1).strip()
                            authorName = match.group(2).strip()
                            return (authorLink, authorName)
                        else:
                            pywikibot.output(field)
                        break

        return False

    def getGeographId(self, filepage, authorName):
        """
        Extract the geograph ID from the filepage

        :param filepage: The page of the file to work on.
        :param authorName: The expected name of the author
        :return: The ID of the file (string)
        """
        templateFound = False
        for template in filepage.itertemplates():
            if template.title()==u'Template:Geograph':
                templateFound = True
        if not templateFound:
            return False

        regex = u'\{\{[gG]eograph\|(\d+)\|%s\}\}' % (authorName,)
        match = re.search(regex, filepage.text)
        if not match:
            return False
        return match.group(1)

    def addSourceGeograph(self, mediaid, currentdata, geographid):
        """
        Construct the structured source to add if it isn't in the currentdata
        :return: List of dicts
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P7482'):
            return False
        geographUrl = u'https://www.geograph.org.uk/photo/%s' % (geographid, )
        toclaim = {'mainsnak': { 'snaktype': 'value',
                                 'property': 'P7482',
                                 'datavalue': { 'value': { 'numeric-id': 74228490,
                                                           'id' : 'Q74228490',
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   'qualifiers' : {'P137' : [ {'snaktype': 'value',
                                               'property': 'P137',
                                               'datavalue': { 'value': { 'numeric-id': '1503119',
                                                                         'id' : 'Q1503119',
                                                                         },
                                                              'type' : 'wikibase-entityid',
                                                              },
                                               } ],
                                   'P7384' : [ {'snaktype': 'value',
                                               'property': 'P7384',
                                               'datavalue': { 'value': geographid,
                                                              'type' : 'string',
                                                              },
                                               } ],
                                   'P973' : [ {'snaktype': 'value',
                                               'property': 'P973',
                                               'datavalue': { 'value': geographUrl,
                                                              'type' : 'string',
                                                              },
                                               } ],
                                   },
                   }
        return [toclaim,]

    def addAuthor(self, mediaid, currentdata, authorUrl, authorName):
        """
        Construct the structured author to add if it isn't in the currentdata
        :param authorUrl: The url pointing to the author on Geograph
        :param authorName: The name of the author
        :return: List of dicts
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
                                   'P2699' : [ {'snaktype': 'value',
                                                'property': 'P2699',
                                                'datavalue': { 'value': authorUrl,
                                                               'type' : 'string',
                                                               },
                                                } ],
                                   },
                   }
        return [toclaim,]

    def addCopyrightLicense(self, mediaid, currentdata):
        """
        Construct the structured copyright license  to add if it isn't in the currentdata
        :return: List of dicts
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P6216'):
            return False
        if currentdata.get('statements') and currentdata.get('statements').get('P275'):
            return False
        result = []
        # Copyright status -> copyrighted
        toclaim = {'mainsnak': { 'snaktype': 'value',
                                 'property': 'P6216',
                                 'datavalue': { 'value': { 'numeric-id': 50423863,
                                                           'id' : 'Q50423863',
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        result.append(toclaim)
        # License -> cc-by-2.0
        toclaim = {'mainsnak': { 'snaktype': 'value',
                                 'property': 'P275',
                                 'datavalue': { 'value': { 'numeric-id': 19068220,
                                                           'id' : 'Q19068220',
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        result.append(toclaim)
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

        request = self.site._simple_request(action='wbparsevalue', datatype='time', values=dateString)
        data = request.submit()
        # Not sure if this works or that I get an exception.
        if data.get('error'):
            return False
        postvalue = data.get(u'results')[0].get('value')

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

    def handlePointOfViewCoordinates(self, mediaid, currentdata, filepage):
        """
        Handle the point of view coordinates on the file page
        :param filepage:
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P1259'):
            return False

        cameraregex = u'\{\{[lL]ocation(\s*dec)?\|(?P<lat>-?\d+\.?\d*)\|(?P<lon>-?\d+\.?\d*)(\|)?(_?source:geograph-osgb36\([^\)]+\))?(_?heading\:(?P<heading>\d+))?(\|prec\=\d+)?\}\}'
        cameramatch = re.search(cameraregex, filepage.text)

        if not cameramatch:
            return False

        if cameramatch:
            coordinateText = u'%s %s' % (cameramatch.group('lat'), cameramatch.group('lon'), )

            request = self.site._simple_request(action='wbparsevalue', datatype='globe-coordinate', values=coordinateText)
            data = request.submit()
            # Not sure if this works or that I get an exception.
            if data.get('error'):
                return False

            postvalue = data.get(u'results')[0].get('value')

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

    def handleObjectCoordinates(self, mediaid, currentdata, filepage):
        """
        Handle the object coordinates on the file page
        :param filepage:
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P625'):
            return False

        objectregex = u'\{\{[oO]bject location(\s*dec)?\|(?P<lat>-?\d+\.?\d*)\|(?P<lon>-?\d+\.?\d*)(\|)?(_?source:geograph-osgb36\([^\)]+\))?(_?heading\:(?P<heading>\d+))?(\|prec\=\d+)?\}\}'
        objectmatch = re.search(objectregex, filepage.text)

        if not objectmatch:
            return False

        if objectmatch:
            coordinateText = u'%s %s' % (objectmatch.group('lat'), objectmatch.group('lon'), )

            request = self.site._simple_request(action='wbparsevalue', datatype='globe-coordinate', values=coordinateText)
            data = request.submit()
            # Not sure if this works or that I get an exception.
            if data.get('error'):
                return False

            postvalue = data.get(u'results')[0].get('value')

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


def main(*args):
    gen = None
    genFactory = pagegenerators.GeneratorFactory()

    for arg in pywikibot.handle_args(args):
        if genFactory.handleArg(arg):
            continue
    gen = genFactory.getCombinedGenerator(gen, preload=True)

    geographSDOCBot = GeographSDOCBot(gen)
    geographSDOCBot.run()

if __name__ == "__main__":
    main()
