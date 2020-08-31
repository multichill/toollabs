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
import json
from pywikibot import pagegenerators

class OwnWorkBot:
    """
    Bot to add structured data statements on Commons
    """
    def __init__(self, gen, loose, fileownwork, authorpage, authorname, authorqid, filelicenses):
        """
        Grab generator based on search to work on.
        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()

        self.informationTemplates = ['information',
                                     'photograph',
                                     'specimen']
        self.validLicenses = self.getLicenseTemplates()
        self.participantTemplates = self.getParticipantTemplates()
        self.sponsorTemplates = self.getSponsorTemplates()
        self.exifCameraMakeModel = self.getExifCameraMakeModel()
        self.generator = gen
        self.loose = loose
        self.fileownwork = fileownwork
        self.authorpage = authorpage
        self.authorname = authorname
        self.authorqid = authorqid
        self.filelicenses = filelicenses

    def getLicenseTemplates(self):
        """
        Get the template to qid mappings for license templates
        Everything all lowercase and spaces instead of underscores
        :return: dict()
        """
        # FIXME: Do query later
        result = { 'cc-zero' : 'Q6938433',
                   'cc0' : 'Q6938433',
                   'cc-0' : 'Q6938433',
                   'cc-by-1.0' : 'Q30942811',
                   'cc-by-2.0' : 'Q19125117',
                   'cc-by-2.0-de' : 'Q75466259',
                   'cc-by-2.0-fr' : 'Q75470422',
                   'cc-by-2.1-jp' : 'Q26116436',
                   'cc-by-2.5' : 'Q18810333',
                   'cc-by-2.5-ar' : 'Q75491630',
                   'cc-by-2.5-au' : 'Q75494411',
                   'cc-by-2.5-dk' : 'Q75665696',
                   'cc-by-2.5-hu' : 'Q75759387',
                   'cc-by 3.0' : 'Q14947546',
                   'cc-by-3.0' : 'Q14947546',
                   'cc-by-3.0-at' : 'Q75768706',
                   'cc-by-3.0-au' : 'Q52555753',
                   'cc-by-3.0-br' : 'Q75770766',
                   'cc-by-3.0-de' : 'Q62619894',
                   'cc-by-3.0-us' : 'Q18810143',
                   'cc-by-3.0,2.5,2.0,1.0' : ['Q14947546', 'Q18810333', 'Q19125117', 'Q30942811'],
                   'cc by 4.0' : 'Q20007257',
                   'cc-by 4.0' : 'Q20007257',
                   'cc-by-4.0' : 'Q20007257',
                   'cc-by-sa-1.0' : 'Q47001652',
                   'cc-by-sa-2.0' : 'Q19068220',
                   'cc-by-sa-2.0-de' : 'Q77143083',
                   'cc-by-sa-2.0-fr' : 'Q77355872',
                   'cc-by-sa-2.1-jp' : 'Q77367349',
                   'cc-by-sa-2.5' : 'Q19113751',
                   'cc-by-sa-2.5-ca' : 'Q24331618',
                   'cc-by-sa-2.5-hu' : 'Q98755330',
                   'cc-by-sa-2.5-nl' : 'Q18199175',
                   'cc-by-sa-2.5-pl' : 'Q98755337',
                   'cc-by-sa-2.5,2.0,1.0' : ['Q19113751', 'Q19068220', 'Q47001652'],
                   'cc-by-sa 3.0' : 'Q14946043',
                   'cc-by-sa-3.0' : 'Q14946043',
                   'cc-by-sa-3.0,2.5,2.0,1.0' : ['Q14946043', 'Q19113751', 'Q19068220', 'Q47001652'],
                   'cc-by-sa-3.0-migrated' : 'Q14946043', # Just cc-by-sa-3.0
                   'cc-by-sa-3.0-at' : 'Q80837139',
                   'cc-by-sa-3.0-au' : 'Q86239208',
                   'cc-by-sa-3.0-br' : 'Q98755369',
                   'cc-by-sa-3.0-cz' : 'Q98755321',
                   'cc-by-sa-3.0-de' : 'Q42716613',
                   'cc-by-sa-3.0-ee' : 'Q86239559',
                   'cc-by-sa-3.0-es' : 'Q86239991',
                   'cc-by-sa-3.0-fr' : 'Q86240326',
                   'cc-by-sa-3.0-igo' : 'Q56292840',
                   'cc-by-sa-3.0-it' : 'Q98755364',
                   'cc-by-sa-3.0-lu' : 'Q86240624',
                   'cc-by-sa-3.0-nl' : 'Q18195572',
                   'cc-by-sa-3.0-no' : 'Q63340742',
                   'cc-by-sa-3.0-pl' : 'Q80837607',
                   'cc-by-sa-3.0-ro' : 'Q86241082',
                   'cc-by-sa-3.0-rs' : 'Q98755344',
                   'cc-by-sa-3.0-us' : 'Q18810341',
                   'cc-by-sa 4.0' : 'Q18199165',
                   'cc-by-sa-4.0' : 'Q18199165',
                   'cc-by-sa-4.0,3.0,2.5,2.0,1.0' : ['Q18199165', 'Q14946043', 'Q19113751', 'Q19068220', 'Q47001652'],
                   'cc-by-sa-all' : ['Q18199165', 'Q14946043', 'Q19113751', 'Q19068220', 'Q47001652'],
                   'cecill' : 'Q1052189',
                   'fal' : 'Q152332',
                   'gfdl' : 'Q50829104',
                   'bild-gfdl-neu' : 'Q50829104',
                   'gfdl-1.2' : 'Q26921686',
                   'pd-author' : 'Q98592850',
                   'pd-self' : 'Q98592850', #  released into the public domain by the copyright holder (Q98592850)
                   'pd-user' : 'Q98592850',
                   }
        return result

    def getParticipantTemplates(self):
        """
        Get the template to qid mappings for participation templates
        Everything all lowercase and spaces instead of underscores
        :return: dict()
        """
        result = { 'wiki loves earth 2013' : 'Q98768417',
                   'wiki loves earth 2014' : 'Q15978259',
                   'wiki loves earth 2015' : 'Q23953679',
                   'wiki loves earth 2016' : 'Q23946940',
                   'wiki loves earth 2017' : 'Q98751859',
                   'wiki loves earth 2018' : 'Q98751978',
                   'wiki loves earth 2019' : 'Q98752118',
                   'wiki loves earth 2020' : 'Q97331615',
                   'wiki loves monuments 2010' : 'Q20890568',
                   'wiki loves monuments 2011' : 'Q8168264',
                   'wiki loves monuments 2012' : 'Q13390164',
                   'wiki loves monuments 2013' : 'Q14568386',
                   'wiki loves monuments 2014' : 'Q15975254',
                   'wiki loves monuments 2015' : 'Q19833396',
                   'wiki loves monuments 2016' : 'Q26792317',
                   'wiki loves monuments 2017' : 'Q30015204',
                   'wiki loves monuments 2018' : 'Q56165596',
                   'wiki loves monuments 2019' : 'Q56427997',
                   'wiki loves monuments 2020' : 'Q66975112',
                   }
        return result

    def getSponsorTemplates(self):
        """
        Get the template to qid mappings for participation templates
        Everything all lowercase and spaces instead of underscores
        :return: dict()
        """
        result = { 'supported by wikimedia argentina' : 'Q18559618',
                   'supported by wikimedia armenia' : 'Q20515521',
                   'supported by wikimedia ch' : 'Q15279140',
                   'supported by wikimedia deutschland' : 'Q8288',
                   'supported by wikimedia españa' : 'Q14866877',
                   'supported by wikimedia france' : 'Q8423370',
                   'supported by wikimedia israel' : 'Q16130851',
                   'supported by wikimedia österreich' : 'Q18559623',
                   'supported by wikimedia polska' : 'Q9346299',
                   'supported by wikimedia uk' : 'Q7999857',
                   }
        return result

    def getExifCameraMakeModel(self):
        """
        Do a SPARQL query to get the exif make and model lookup table
        :return: Dict with (make, model) as keys
        """
        query = """SELECT ?item ?make ?model WHERE {
  ?item wdt:P2010 ?make ;
        wdt:P2009 ?model ;
        }"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)
        result = {}

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[(resultitem.get('make'),resultitem.get('model'))] = qid
        return result

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

        if not filepage.has_permission():
            # Picture might be protected
            return

        # Check if the file is own work
        ownwork = self.isOwnWorkFile(filepage)
        if not ownwork and not self.loose:
            pywikibot.output(u'No own and self templates found on %s, skipping' % (filepage.title(),))
            return

        # Get the author
        authorInfo = self.getAuthor(filepage)
        if not authorInfo and not self.authorqid and not self.loose:
            pywikibot.output(u'Unable to extract author on %s, skipping' % (filepage.title(),))
            return

        # Get one or more licenses
        licenses = self.getSelfLicenses(filepage)
        if not licenses and not self.loose:
            pywikibot.output(u'Unable to extract licenses on %s, skipping' % (filepage.title(),))
            return

        # Need to have found something to continue in loose mode
        if self.loose and not ownwork and (not authorInfo or not self.authorqid) and not licenses:
            pywikibot.output(u'Loose mode, but did not find anything on %s, skipping' % (filepage.title(),))
            return

        # Here we're collecting
        newclaims = {}

        # We got all the needed info, let's add it
        if ownwork:
            newclaims['source'] = self.addSourceOwn(mediaid, currentdata)
        if self.authorqid:
            newclaims['author'] = self.addAuthorQid(mediaid, currentdata, self.authorqid)
        elif authorInfo:
            (authorPage, authorName) = authorInfo
            newclaims['author'] = self.addAuthor(mediaid, currentdata, authorPage, authorName)
        if licenses:
            newclaims['copyright'] = self.addLicenses(mediaid, currentdata, licenses)
        # Optional stuff, maybe split that up too
        newclaims['date'] = self.handleDate(mediaid, currentdata, filepage)
        # TODO: Consider adding date from exif DateTimeOriginal if nothing is found
        newclaims['coordinates'] = self.handlePointOfViewCoordinates(mediaid, currentdata, filepage)
        newclaims['object coordinates'] = self.handleObjectCoordinates(mediaid, currentdata, filepage)
        newclaims['camera'] = self.handleCameraMakeModel(mediaid, currentdata, filepage)
        newclaims['participant'] = self.handleParticipant(mediaid, currentdata, filepage)
        newclaims['sponsor'] = self.handleSponsor(mediaid, currentdata, filepage)

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
                    if license.lower() in self.validLicenses:
                        licenseqid = self.validLicenses.get(license.lower())
                        if isinstance(licenseqid, list):
                            result.extend(licenseqid)
                        else:
                            result.append(licenseqid)
                    elif license=='':
                        continue
                    elif license.lower().strip().startswith('author='):
                        continue
                    elif license.lower().strip().startswith('attribution='):
                        continue
                    elif license.lower().strip().startswith('migration='):
                        continue
                    else:
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
                                                'datavalue': { 'value': u'https://commons.wikimedia.org/wiki/user:%s' % (authorPage.title(underscore=True, with_ns=False, as_url=True), ),
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
                # Crude check for cc-zero or released into the public domain by the copyright holder
                if 'Q6938433' in currentlicenses or 'Q6938433' in licenses \
                        or 'Q98592850' in currentlicenses or 'Q98592850' in licenses:
                    # Add copyrighted, dedicated to the public domain by copyright holder
                    result.extend(self.addClaimJson(mediaid, u'P6216', u'Q88088423'))
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
        takenRegex = u'^\s*date\s*\=\s*\{\{taken on\s*(\|\s*location\s*\=\s*[^\|]*)?\s*\|\s*(?P<date>\d\d\d\d-\d\d-\d\d)(\s*\d\d\:\d\d(\:\d\d(\.\d\d)?)?)?\s*(\|\s*location\s*\=\s*[^\|]*)?\s*\}\}\s*$'
        dateString = None

        for template, parameters in filepage.templatesWithParams():
            lowertemplate = template.title(underscore=False, with_ns=False).lower()
            if lowertemplate in self.informationTemplates:
                for field in parameters:
                    if field.lower().startswith(u'date'):
                        datematch = re.match(dateRegex, field, flags=re.IGNORECASE)
                        takenmatch = re.match(takenRegex, field, flags=re.IGNORECASE)
                        if datematch:
                            dateString = datematch.group('date').strip()
                        elif takenmatch:
                            dateString = takenmatch.group('date').strip()
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

        cameraregex = u'\{\{[lL]ocation(\s*dec)?\|(?P<lat>-?\d+\.?\d*)\|(?P<lon>-?\d+\.?\d*)(\|)?(_?source:[^_]+)?(_?heading\:(?P<heading>\d+(\.\d+)?))?(\|prec\=\d+)?\}\}'
        cameramatch = re.search(cameraregex, filepage.text)

        if not cameramatch:
            return False

        if cameramatch:
            coordinateText = u'%s %s' % (cameramatch.group('lat'), cameramatch.group('lon'), )

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

        objectregex = u'\{\{[oO]bject location(\s*dec)?\|(?P<lat>-?\d+\.?\d*)\|(?P<lon>-?\d+\.?\d*)(\|)?(_?source:[^_]+)?(_?heading\:(?P<heading>\d+(\.\d+)?))?(\|prec\=\d+)?\}\}'
        objectmatch = re.search(objectregex, filepage.text)

        if not objectmatch:
            return False

        if objectmatch:
            coordinateText = u'%s %s' % (objectmatch.group('lat'), objectmatch.group('lon'), )

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
                                     'property': 'P625',
                                     'datavalue': { 'value': postvalue,
                                                    'type' : 'globecoordinate',
                                                    }

                                     },
                       'type': 'statement',
                       'rank': 'normal',
                       }
            return [toclaim,]

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

        if not filepage.latest_file_info.metadata:
            return False
        metadata = filepage.latest_file_info.metadata

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
    gen = None
    genFactory = pagegenerators.GeneratorFactory()
    loose = False
    fileownwork = None
    authorpage = None
    authorname = None
    authorqid = None
    filelicenses = []

    for arg in pywikibot.handle_args(args):
        if arg == '-loose':
            loose = True
        elif arg == '-fileownwork':
            fileownwork = True
        elif arg.startswith('-authorpage'):
            authorpage = arg[12:]
        elif arg.startswith('-authorname'):
            authorname = arg[12:]
        elif arg.startswith('-authorqid'):
            authorqid = arg[11:]
        elif arg.startswith('-filelicense'):
            filelicenses.append(arg[13:])
        elif genFactory.handleArg(arg):
            continue
    gen = pagegenerators.PageClassGenerator(genFactory.getCombinedGenerator(gen, preload=True))

    ownWorkBot = OwnWorkBot(gen, loose, fileownwork, authorpage, authorname, authorqid, filelicenses)
    ownWorkBot.run()

if __name__ == "__main__":
    main()
