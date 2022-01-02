#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to clean up files which have digital representation of (P6243).

These files should also have the same depicts (P180) and  main subject (P921).

Should be switched to a more general Pywikibot implementation.

"""

import pywikibot
import re
import pywikibot.data.sparql
import time
import json
from pywikibot import pagegenerators

class DigitalRepresentationCleaanupBot:
    """
    Bot to add structured data statements on Commons
    """
    def __init__(self, gen, alwaystouch, remove3d):
        """
        Grab generator based on search to work on.
        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()
        self.generator = gen
        self.alwaystouch = alwaystouch
        self.remove3d = remove3d
        (self.works_2d, self.works_3d, self.works_both) = self.loadWorktypes()

    def loadWorkTypes(self):
        """
        Load the different kinds of works. For now just static lists. Can do it later on the wiki
        :return:
        """
        works_2d = [ 'Q93184', # drawing
                     'Q11835431', # engraving
                     'Q18218093', # etching print
                     'Q3305213', # painting
                     'Q125191', # photograph
                     'Q11060274', # print
                     ]
        works_3d = [ 'Q860861', # sculpture
                     'Q179700', # statue
                     ]
        works_both = [ 'Q1278452', # polyptych
                       'Q79218', # triptych
                       ]

        return (works_2d, works_3d, works_both)

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

            pywikibot.output(u'Working on %s' % (filepage.title(),))

            if not filepage.exists():
                continue

            if not filepage.has_permission():
                # Picture might be protected
                continue

            self.addMissingStatementsToFile(filepage, mediaid, currentdata)
            if self.remove3d:
                self.removeDigitalRepresentation3d(filepage, mediaid, currentdata)

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

    def addMissingStatementsToFile(self, filepage, mediaid, currentdata):
        """
        Add missing depicts (P180) and main subject (P921) if these are missing

        :param filepage: The page of the file to work on.
        :return: Nothing, edit in place
        """

        # Retrieve the target
        if currentdata.get('statements') and currentdata.get('statements').get('P6243'):
            artworkqid = currentdata.get('statements').get('P6243')[0].get('mainsnak').get('datavalue').get('value').get('id')
        else:
            return

        # Here we're collecting
        newclaims = {}

        # Add depicts (P180) if it's missing
        if not currentdata.get('statements').get('P180'):
            newclaims['depicts'] = self.addClaimJson(mediaid, 'P180', artworkqid)

        # Add main subject (P921) if it's missing
        if not currentdata.get('statements').get('P921'):
            newclaims['main subject'] = self.addClaimJson(mediaid, 'P921', artworkqid)

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
            postdata = {'action' : u'wbeditentity',
                        'format' : u'json',
                        'id' : mediaid,
                        'data' : json.dumps(itemdata),
                        'token' : token,
                        'summary' : summary,
                        'bot' : True,
                        }
            if currentdata:
                # This only works when the entity has been created
                postdata['baserevid'] = currentdata.get('lastrevid')

            request = self.site._simple_request(**postdata)
            try:
                data = request.submit()
                # Always touch the page to flush it
                filepage.touch()
            except (pywikibot.data.api.APIError, pywikibot.exceptions.OtherPageSaveError):
                pywikibot.output('Got an API error while saving page. Sleeping, getting a new token and skipping')
                # Print the offending token
                print (token)
                time.sleep(30)
                # FIXME: T261050 Trying to reload tokens here, but that doesn't seem to work
                self. site.tokens.load_tokens(['csrf'])
                # This should be a new token
                print (self.site.tokens['csrf'])
        elif self.alwaystouch:
            try:
                filepage.touch()
            except:
                pywikibot.output('Got an API error while touching page. Sleeping, getting a new token and skipping')
                self. site.tokens.load_tokens(['csrf'])

    def removeDigitalRepresentation3d(self, filepage, mediaid, currentdata):
        """
        Remove the digital representation statement from 3d works

        We assume the P180 & P921 have been added
        """
        # Retrieve the target
        if currentdata.get('statements') and currentdata.get('statements').get('P6243'):
            artworkqid = currentdata.get('statements').get('P6243')[0].get('mainsnak').get('datavalue').get('value').get('id')
            claimid = currentdata.get('statements').get('P6243')[0].get('id')
        else:
            return

        artworkitem = pywikibot.ItemPage(self.repo, artworkqid)
        claims = artworkitem.get().get('claims')

        if 'P31' in claims:
            found_2d = 0
            found_3d = 0
            found_both = 0
            found_unknown = 0
            found_3d_example = None
            for claim in claims.get('P31'):
                instanceof = claim.getTarget()
                if instanceof in self.works_2d:
                    found_2d += 1
                elif instanceof in self.works_3d:
                    found_3d += 1
                    found_3d_example = instanceof
                elif instanceof in self.works_both:
                    found_both += 1
                else:
                    found_unknown += 1

            if found_3d and not found_2d and not found_both:
                summary = 'removing because [[d:Special:EntityPage/%s]] is an instance of [[d:Special:EntityPage/%s]]' % (artworkqid, found_3d_example)

                token = self.site.tokens['csrf']
                postdata = {'action' : 'wbremoveclaims',
                            'format' : 'json',
                            'claim' : claimid,
                            'token' : token,
                            'summary' : summary,
                            'bot' : True,
                            }
                #if currentdata:
                #    # This only works when the entity has been created
                #    postdata['baserevid'] = currentdata.get('lastrevid')

                request = self.site._simple_request(**postdata)
                try:
                    data = request.submit()
                    # Always touch the page to flush it
                    filepage.touch()
                except (pywikibot.data.api.APIError, pywikibot.exceptions.OtherPageSaveError):
                    pywikibot.output('Got an API error while saving page. Sleeping, getting a new token and skipping')
                    # Print the offending token
                    print (token)
                    time.sleep(30)
                    # FIXME: T261050 Trying to reload tokens here, but that doesn't seem to work
                    self. site.tokens.load_tokens(['csrf'])
                    # This should be a new token
                    print (self.site.tokens['csrf'])

    def isOwnWorkFile(self, filepage):
        """
        Check if the file is own work. We do that by looking for both the "own" and the "self" template.
        :param filepage: The page of the file to work on.
        :return:
        """
        if self.fileownwork:
            pywikibot.output(u'Own work forced!')
            return True
        ownfound = False
        selfFound = False

        ownTemplates = ['Template:Own',
                        'Template:Own photograph',
                        'Template:Own work by original uploader',
                        'Template:Self-photographed',
                        ]
        selfTemplates = ['Template:Self',
                         'Template:PD-self',
                         ]

        for template in filepage.itertemplates():
            if template.title() in ownTemplates:
                ownfound = True
            elif template.title() in selfTemplates:
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
        if self.authorpage and self.authorname:
            return (pywikibot.User(self.site, self.authorpage), self.authorname)
        elif self.authorpage:
            return (pywikibot.User(self.site, self.authorpage), self.authorpage)
        elif self.authorname:
            return (pywikibot.User(self.site, self.authorname), self.authorname)

        authorRegex = u'^\s*[aA]uthor\s*\=\s*\[\[[uU]ser\:([^\|^\]]+)\|([^\|^\]]+)\]\](\s*\(\s*\[\[[uU]ser talk\:[^\|^\]]+\|[^\|^\]]+\]\]\s*\)\s*)?\s*$'

        for template, parameters in filepage.templatesWithParams():
            lowertemplate = template.title(underscore=False, with_ns=False).lower()
            if lowertemplate in self.informationTemplates:
                for field in parameters:
                    if field.lower().startswith(u'author'):
                        match = re.match(authorRegex, field)
                        if match:
                            authorPage = pywikibot.User(self.site, match.group(1))
                            authorName = match.group(2).strip()
                            return (authorPage, authorName)
                        # The author regex didn't match. Let's get the uploader in the log to compare
                        # Todo, do a bit of trickery to detect a customer user template like {{User:<user>/<something}}
                        else:
                            pywikibot.output(field)
                        break

        return False

    def getOtherSource(self, mediaid, currentdata, filepage):
        """
        The file is not some standard own work file. Try to extract other sources like Flickr
        :return: Tuple with (type of source, list of statements)
        """
        operators = { 'flickr' : 'Q103204', }
        authordpids = { 'flickr' : 'P3267',  }
        sourceregexes = { 'flickr' : '^\s*source\s*\=(\s*originally posted to\s*\'\'\'\[\[Flickr\|Flickr\]\]\'\'\'\s* as)?\s*\[(?P<url>https?\:\/\/(www\.)?flickr\.com\/photos\/[^\s]+\/[^\s]+\/?)\s+(?P<title>[^\]]+)\]\s*$'}
        authorregexes = { 'flickr' : '^\s*author\s*\=\s*\[(?P<url>https?:\/\/(www\.)?flickr\.com\/(people|photos)\/(?P<id>\d{5,11}@N\d{2}))\/?\s+(?P<authorname>[^\]]+)\].*$'}
        sourcefound = {}
        authorfound = {}
        for template, parameters in filepage.templatesWithParams():
            lowertemplate = template.title(underscore=False, with_ns=False).lower()
            if lowertemplate in self.informationTemplates:
                for field in parameters:
                    if field.lower().startswith('source'):
                        for operator in sourceregexes:
                            match = re.match(sourceregexes.get(operator), field, flags=re.IGNORECASE)
                            if match:
                                sourcefound[operator] = match.groupdict()
                    elif field.lower().startswith('author'):
                        for operator in authorregexes:
                            match = re.match(authorregexes.get(operator), field, flags=re.IGNORECASE)
                            if match:
                                authorfound[operator] = match.groupdict()
        # Check if we got one match for both
        if sourcefound and authorfound and len(sourcefound)==1 and sourcefound.keys()==authorfound.keys():
            result = []
            operator = next(iter(sourcefound))
            operatorqid = operators.get(operator)
            operatornumid = operatorqid.replace('Q', '')
            if not currentdata.get('statements') or not currentdata.get('statements').get('P7482'):
                sourceurl = sourcefound.get(operator).get('url')
                sourceclaim = {'mainsnak': { 'snaktype': 'value',
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
                                                           'datavalue': { 'value': { 'numeric-id': operatornumid,
                                                                                     'id' : operatorqid,
                                                                                     },
                                                                          'type' : 'wikibase-entityid',
                                                                          },
                                                       } ],
                                               'P973' : [ {'snaktype': 'value',
                                                           'property': 'P973',
                                                           'datavalue': { 'value': sourceurl,
                                                                          'type' : 'string',
                                                                          },
                                                           } ],
                                               },
                               }
                result.append(sourceclaim)
            if not currentdata.get('statements') or not currentdata.get('statements').get('P170'):
                authordpid = authordpids.get(operator)
                authorid = authorfound.get(operator).get('id')
                authorname = authorfound.get(operator).get('authorname').strip()
                authorurl = authorfound.get(operator).get('url')
                authorclaim = {'mainsnak': { 'snaktype':'somevalue',
                                             'property': 'P170',
                                             },
                               'type': 'statement',
                               'rank': 'normal',
                               'qualifiers' : {'P2093' : [ {'snaktype': 'value',
                                                            'property': 'P2093',
                                                            'datavalue': { 'value': authorname,
                                                                           'type' : 'string',
                                                                           },
                                                            } ],
                                               'P2699' : [ {'snaktype': 'value',
                                                            'property': 'P2699',
                                                            'datavalue': { 'value': authorurl,
                                                                           'type' : 'string',
                                                                           },
                                                            } ],
                                               },
                               }
                if authordpid and authorid:
                    authorclaim['qualifiers'][authordpid] = [ {'snaktype': 'value',
                                                               'property': authordpid,
                                                               'datavalue': { 'value': authorid,
                                                                              'type' : 'string',
                                                                              },
                                                               } ]
                result.append(authorclaim)
            if result:
                return (operator, result)
        return False

    def getSelfLicenses(self, filepage):
        """
        Extract one or more licenses from the Self template
        :param filepage: The page of the file to work on.
        :return: List of Q ids of licenses
        """
        result = []

        if self.filelicenses:
            for license in self.filelicenses:
                if license.lower() in self.validLicenses:
                    licenseqid = self.validLicenses.get(license.lower())
                    if isinstance(licenseqid, list):
                        result.extend(licenseqid)
                    else:
                        result.append(self.validLicenses.get(license.lower()))
                else:
                    return False

        for template, parameters in filepage.templatesWithParams():
            if template.title()==u'Template:Self':
                for license in parameters:
                    cleanlicense = license.lower().strip().replace(' =', '=')
                    if cleanlicense in self.validLicenses:
                        licenseqid = self.validLicenses.get(cleanlicense)
                        if isinstance(licenseqid, list):
                            result.extend(licenseqid)
                        else:
                            result.append(licenseqid)
                    elif license=='':
                        continue
                    elif cleanlicense.startswith('author='):
                        continue
                    elif cleanlicense.startswith('attribution='):
                        continue
                    elif cleanlicense.startswith('migration='):
                        continue
                    elif cleanlicense.startswith('user:'):
                        # Funky user templates
                        continue
                    else:
                        pywikibot.output('Unable to parse self field: "%s"' % (cleanlicense,))
                        return False
                break
        # When we reach this point it means we didn't find an invalid self template or no self at all
        for template in filepage.templates():
            lowertemplate = template.title(underscore=False, with_ns=False).lower()
            if lowertemplate in self.validLicenses:
                licenseqid = self.validLicenses.get(lowertemplate)
                if isinstance(licenseqid, list):
                    result.extend(licenseqid)
                else:
                    result.append(licenseqid)
        return list(set(result))

    def addSourceOwn(self, mediaid, currentdata):
        """
        Dummy method for now
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P7482'):
            return False
        return self.addClaimJson(mediaid, 'P7482', 'Q66458942')

    def addAuthorQid(self, mediaid, currentdata, authorqid):
        """
        Add an author that has a qid
        :param mediaid:
        :param currentdata:
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P170'):
            return False
        return self.addClaimJson(mediaid, 'P170', authorqid)

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
                   'qualifiers' : {#'P3831' : [ {'snaktype': 'value',
                                   #             'property': 'P3831',
                                   #             'datavalue': { 'value': { 'numeric-id': '33231',
                                   #                                       'id' : 'Q33231',
                                   #                                       },
                                   #                            'type' : 'wikibase-entityid',
                                   #                            },
                                   #             } ],
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
                                                'datavalue': { 'value': u'https://commons.wikimedia.org/wiki/User:%s' % (authorPage.title(underscore=True, with_ns=False, as_url=True), ),
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
        result = []

        currentlicenses = []
        if currentdata.get('statements') and currentdata.get('statements').get('P275'):
            for licensestatement in currentdata.get('statements').get('P275'):
                if licensestatement.get('mainsnak').get('datavalue'):
                    currentlicenses.append(licensestatement.get('mainsnak').get('datavalue').get('value').get('id'))

        # Add the different licenses
        for license in licenses:
            if license not in currentlicenses:
                result.extend(self.addClaimJson(mediaid, u'P275', license))

        if not currentdata.get('statements') or not currentdata.get('statements').get('P6216'):
            # Add the fact that the file is copyrighted only if a license has been found
            if currentlicenses or licenses:
                # Check if current or new licenses are a public domain dedication license like CC0
                if (set(currentlicenses) | set(licenses) ) & set(self.pubDedication):
                    result.extend(self.addClaimJson(mediaid, u'P6216', u'Q88088423'))
                elif 'Q99263261' in (set(currentlicenses) | set(licenses) ):
                    # Flickr no known copyright restrictions junk
                    result.extend(self.addClaimJson(mediaid, u'P6216', u'Q99263261'))
                else:
                    # Add copyrighted, won't be reached is a file is both cc-zero and some other license
                    result.extend(self.addClaimJson(mediaid, u'P6216', u'Q50423863'))
        return result

    def handleDate(self, mediaid, currentdata, filepage):
        """
        Handle the date on the filepage. If it matches an ISO date (YYYY-MM-DD) (with or without time), add a date claim
        :param filepage:
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P571'):
            return False

        dateRegex = u'^\s*[dD]ate\s*\=\s*(?P<date>\d\d\d\d-\d\d-\d\d)(\s*\d\d\:\d\d(\:\d\d(\.\d\d)?)?)?\s*$'
        takenRegex = u'^\s*date\s*\=\s*\{\{taken on\s*(\|\s*location\s*\=\s*[^\|]*)?\s*\|\s*(?P<date>\d\d\d\d-\d\d-\d\d)(\s*\d\d\:\d\d(\:\d\d(\.\d\d)?)?)?\s*(\|\s*location\s*\=\s*[^\|]*)?\s*\}\}(\s*\d\d\:\d\d(\:\d\d(\.\d\d)?)?)?\s*$'
        exifRegex = u'^\s*date\s*\=\s*\{\{According to Exif(\s*data)?\s*(\|\s*location\s*\=\s*[^\|]*)?\s*\|\s*(?P<date>\d\d\d\d-\d\d-\d\d)(\s*\d\d\:\d\d(\:\d\d(\.\d\d)?)?)?\s*(\|\s*location\s*\=\s*[^\|]*)?\s*\}\}\s*$'

        dateString = None

        for template, parameters in filepage.templatesWithParams():
            lowertemplate = template.title(underscore=False, with_ns=False).lower()
            if lowertemplate in self.informationTemplates:
                for field in parameters:
                    if field.lower().startswith(u'date'):
                        datematch = re.match(dateRegex, field, flags=re.IGNORECASE)
                        takenmatch = re.match(takenRegex, field, flags=re.IGNORECASE)
                        exifmatch = re.match(exifRegex, field, flags=re.IGNORECASE)
                        if datematch:
                            dateString = datematch.group('date').strip()
                        elif takenmatch:
                            dateString = takenmatch.group('date').strip()
                        elif exifmatch:
                            dateString = exifmatch.group('date').strip()
                        break
        if not dateString:
            return False

        request = self.site._simple_request(action='wbparsevalue', datatype='time', values=dateString)
        try:
            data = request.submit()
        except AssertionError:
            # This will break at some point in the future
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

        cameraregex = '\{\{[lL]ocation(\s*dec)?\|(1\=)?(?P<lat>-?\d+\.?\d*)\|(2\=)?(?P<lon>-?\d+\.?\d*)(\|)?(_?source:[^_]+)?(_?heading\:(?P<heading>\d+(\.\d+)?))?(\|prec\=\d+)?\}\}'
        exifcameregex = '\{\{[lL]ocation\|(\d+)\|(\d+\.?\d*)\|(\d+\.?\d*)\|(N|S)\|(\d+)\|(\d+\.?\d*)\|(\d+\.?\d*)\|(E|W)\|alt\:(\d+\.?\d*|\?)_source:exif_heading:(\d+\.?\d*|\?)}}'
        cameramatch = re.search(cameraregex, filepage.text)
        exifcameramatch = re.search(exifcameregex, filepage.text)
        heading = None
        # altitude is in the spec, but doesn't seem to be in use

        if not cameramatch and not exifcameramatch:
            return False
        elif cameramatch:
            coordinateText = '%s %s' % (cameramatch.group('lat'), cameramatch.group('lon'), )
            if cameramatch.group('heading') and not cameramatch.group('heading') == '?':
                heading = cameramatch.group('heading')
        elif exifcameramatch:
            lat_dec = round((float(exifcameramatch.group(1)) * 3600.0 + float(exifcameramatch.group(2)) * 60.0 + float(exifcameramatch.group(3)) ) / 3600.0 , 6)
            lon_dec = round((float(exifcameramatch.group(5)) * 3600.0 + float(exifcameramatch.group(6)) * 60.0 + float(exifcameramatch.group(7)) ) / 3600.0 , 6)
            if exifcameramatch.group(4)=='S':
                lat_dec = -lat_dec
            if exifcameramatch.group(8)=='W':
                lon_dec = -lon_dec
            coordinateText = '%s %s' % (lat_dec, lon_dec, )
            if exifcameramatch.group(10) and not exifcameramatch.group(10) == '?':
                heading = exifcameramatch.group(10)

        if coordinateText:
            request = self.site._simple_request(action='wbparsevalue', datatype='globe-coordinate', values=coordinateText)
            try:
                data = request.submit()
            except AssertionError:
                # This will break at some point in the future
                return False
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
            if heading:
                try:
                    toclaim['qualifiers'] = {'P7787' : [ {'snaktype': 'value',
                                                          'property': 'P7787',
                                                          'datavalue': { 'value': { 'amount': '+%s' % (float(heading),),
                                                                                    #'unit' : '1',
                                                                                    'unit' : 'http://www.wikidata.org/entity/Q28390',
                                                                                    },
                                                                         'type' : 'quantity',
                                                                         },
                                                          },
                                                         ],
                                             }
                except ValueError:
                    # Weird heading
                    pass
            return [toclaim,]

    def handleObjectCoordinates(self, mediaid, currentdata, filepage):
        """
        Handle the object coordinates on the file page
        :param filepage:
        :return: #
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P9149'):
            return False
        elif currentdata.get('statements') and currentdata.get('statements').get('P625'):
            return self.replaceObjectCoordinates(mediaid, currentdata, filepage)

        objectregex = u'\{\{[oO]bject location(\s*dec)?\|(?P<lat>-?\d+\.?\d*)\|(?P<lon>-?\d+\.?\d*)(\|)?(_?source:[^_]+)?(_?heading\:(?P<heading>\d+(\.\d+)?))?(\|prec\=\d+)?\}\}'
        # I'm afraid this is not going to work if it's not decimal.
        #objectregex = u'\{\{[oO]bject location(\s*dec)?\|(?P<lat>-?\d+\.?\d*)\|(?P<lon>-?\d+\.?\d*)(?P<moreparameters>\|[^\}]+)?\}\}'
        objectmatch = re.search(objectregex, filepage.text)

        if not objectmatch:
            return False

        if objectmatch:
            coordinateText = '%s %s' % (objectmatch.group('lat'), objectmatch.group('lon'), )

            heading = None
            if 'moreparameters' in objectmatch.groupdict():
                headingregex = 'heading\:(?P<heading>\d+(\.\d+)?)'
                headingmatch = re.search(headingregex, objectmatch.group('moreparameters'))
                if headingmatch:
                    heading = headingmatch.group('heading')

            request = self.site._simple_request(action='wbparsevalue', datatype='globe-coordinate', values=coordinateText)
            try:
                data = request.submit()
            except AssertionError:
                # This will break at some point in the future
                return False
            # Not sure if this works or that I get an exception.
            if data.get('error'):
                return False

            postvalue = data.get(u'results')[0].get('value')

            toclaim = {'mainsnak': { 'snaktype':'value',
                                     'property': 'P9149',
                                     'datavalue': { 'value': postvalue,
                                                    'type' : 'globecoordinate',
                                                    }

                                     },
                       'type': 'statement',
                       'rank': 'normal',
                       }
            if heading:
                try:
                    toclaim['qualifiers'] = {'P7787' : [ {'snaktype': 'value',
                                                          'property': 'P7787',
                                                          'datavalue': { 'value': { 'amount': '+%s' % (float(heading),),
                                                                                    #'unit' : '1',
                                                                                    'unit' : 'http://www.wikidata.org/entity/Q28390',
                                                                                    },
                                                                         'type' : 'quantity',
                                                                         },
                                                          },
                                                         ],
                                             }
                except ValueError:
                    # Weird heading
                    pass
            return [toclaim,]

    def replaceObjectCoordinates(self, mediaid, currentdata, filepage):
        """
        We started off this party with coordinate location (P625), but switched to coordinates of depicted place (P9149)
        Replace it
        :param mediaid:
        :param currentdata:
        :param filepage:
        :return:
        """
        if len(currentdata.get('statements').get('P625'))!=1:
            return False

        toclaim = currentdata.get('statements').get('P625')[0]
        idtoremove = toclaim.pop('id')
        toclaim['mainsnak']['property'] = 'P9149'
        oldhash = toclaim['mainsnak'].pop('hash')
        return [{'id' : idtoremove, 'remove':''}, toclaim ]

    def handleCameraMakeModel(self, mediaid, currentdata, filepage):
        """
        Get the exif metadata and see if we can add a camera model
        :param mediaid:
        :param currentdata:
        :param filepage:
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P4082'):
            return False

        try:
            if not filepage.latest_file_info.metadata:
                return False
            metadata = filepage.latest_file_info.metadata
        except (pywikibot.exceptions.PageRelatedError, AttributeError):
            pywikibot.output('No file on %s, skipping' % (filepage.title(),))
            return False

        cameramake = None
        cameramodel = None

        for namevalue in metadata:
            if namevalue.get('name')=='Make':
                cameramake = namevalue.get('value').strip()
            elif namevalue.get('name')=='Model':
                cameramodel = namevalue.get('value').strip()

        if not cameramake or not cameramodel:
            return False

        cameraqid = self.exifCameraMakeModel.get((cameramake, cameramodel))
        if not cameraqid:
            return False
        return self.addClaimJson(mediaid, 'P4082', cameraqid)

    def handleParticipant(self, mediaid, currentdata, filepage):
        """
        Add the participant in based on template usage
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P1344'):
            return False
        for template in filepage.templates():
            lowertemplate = template.title(underscore=False, with_ns=False).lower()
            if lowertemplate in self.participantTemplates:
                qid = self.participantTemplates.get(lowertemplate)
                return self.addClaimJson(mediaid, 'P1344', qid)
        return False

    def handleSponsor(self, mediaid, currentdata, filepage):
        """
        Add the sponsor based on template usage
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P859'):
            return False
        for template in filepage.templates():
            lowertemplate = template.title(underscore=False, with_ns=False).lower()
            if lowertemplate in self.sponsorTemplates:
                qid = self.sponsorTemplates.get(lowertemplate)
                return self.addClaimJson(mediaid, 'P859', qid)
        return False

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
    fullrun = False
    alwaystouch = False
    remove3d = False
    gen = None
    genFactory = pagegenerators.GeneratorFactory()

    for arg in pywikibot.handle_args(args):
        if arg == '-fullrun':
            fullrun = True
        elif arg == '-alwaystouch':
            alwaystouch = True
        elif arg == '-remove3d':
            remove3d = True
        elif genFactory.handle_arg(arg):
            continue
    gen = pagegenerators.PageClassGenerator(genFactory.getCombinedGenerator(gen, preload=True))

    digitalRepresentationCleaanupBot = DigitalRepresentationCleaanupBot(gen, alwaystouch, remove3d)
    digitalRepresentationCleaanupBot.run()

if __name__ == "__main__":
    main()
