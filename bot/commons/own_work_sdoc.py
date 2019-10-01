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
import datetime
from pywikibot.comms import http
import json
from pywikibot import pagegenerators

class OwnWorkBot:
    """
    Bot to add depicts statements on Commons
    """
    def __init__(self, gen):
        """
        Grab generator based on search to work on.

        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.repo = self.site.data_repository()

        # Probably get licenses
        self.validLicenses = self.getLicenseTemplates()

        self.generator = gen

    def getLicenseTemplates(self):
        """
        Get the monuments currently on Wikidata. Keep the id as a string.
        :return:
        """
        # FIXME: Do query later
        result = { u'cc-zero' : u'Q6938433',
                   u'cc-by-2.0' : u'Q19125117',
                   u'cc-by-sa-2.0' : u'Q19068220',
                   u'cc-by-3.0' : u'Q14947546',
                   u'cc-by-sa-3.0' : u'Q14946043',
                   u'cc-by-sa-3.0-nl' : u'Q18195572',
                   u'cc-by-sa-4.0' : u'Q18199165',
                   }
        return result

        if designation:
            query = u'''SELECT ?item ?id WHERE {
  ?item wdt:P1435 wd:%s .
  ?item wdt:%s ?id .
  } ORDER BY ?id''' % (designation, property, )
        else:
            query = u'''SELECT ?item ?id WHERE {
  ?item wdt:%s ?id .
  } ORDER BY ?id''' % (property, )
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[resultitem.get('id')] = qid
        return result

    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            self.handleOwnWork(filepage)

    def handleOwnWork(self, filepage):
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
        print (authorPage)
        print (authorName)

        # Get one or more licenses
        licenses = self.getSelfLicenses(filepage)
        if not licenses:
            pywikibot.output(u'Unable to extract licenses on %s, skipping' % (filepage.title(),))
            return
        print (licenses)

        mediaid = u'M%s' % (filepage.pageid,)



        # We got all the needed info, let's add it
        self.addSourceOwn(mediaid)
        self.addAuthor(mediaid, authorPage, authorName)
        self.addLicenses(mediaid, licenses)
        return


        matches = list(re.finditer(self.templateregex, filepage.text))

        if not matches:
            pywikibot.output(u'No matches found on %s, skipping' % (filepage.title(),))
            return

        toadd = []

        # First collect the matches to add
        for match in matches:
            monumentid = match.group(u'id')
            if monumentid not in self.monuments:
                pywikibot.output(u'Found unknown monument id %s on %s, skipping' % (monumentid, filepage.title(),))
                return
            qid = self.monuments.get(monumentid)
            # Some cases the template is in the file text multiple times
            if (monumentid, qid) not in toadd:
                toadd.append((monumentid, qid))

        mediaid = u'M%s' % (filepage.pageid,)
        if self.mediaInfoHasStatement(mediaid, u'P180'):
            return
        i = 1
        for (monumentid, qid) in toadd:
            if len(toadd)==1:
                summary = u'based on [[Template:%s]] with id %s, which is the same id as [[:d:Property:%s|%s (%s)]] on [[:d:%s]]' % (self.template,
                                                                                                                                     monumentid,
                                                                                                                                     self.property,
                                                                                                                                     self.propertyname,
                                                                                                                                     self.property,
                                                                                                                                     qid, )
            else:
                summary = u'based on [[Template:%s]] with id %s, which is the same id as [[:d:Property:%s|%s (%s)]] on [[:d:%s]] (%s/%s)' % (self.template,
                                                                                                                                             monumentid,
                                                                                                                                             self.property,
                                                                                                                                             self.propertyname,
                                                                                                                                             self.property,
                                                                                                                                             qid,
                                                                                                                                             i,
                                                                                                                                             len(toadd))
            self.addClaim(mediaid, u'P180', qid, summary)
            i +=1

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
            print (u'Own work found!')
            return True
        return False

    def getAuthor(self, filepage):
        """
        Extract the author form the information template
        :param filepage: The page of the file to work on.
        :return: Tuple with a User and a string
        """

        authorRegex = u'^Author\s*\=\s*\[\[User\:([^\|^\]]+)\|([^\|^\]]+)\]\](\s*\(\s*\[\[User talk\:[^\|^\]]+\|[^\|^\]]+\]\]\s*\)\s*)?$'

        for template, parameters in filepage.templatesWithParams():
            if template.title()==u'Template:Information':
                for field in parameters:
                    if field.startswith(u'Author'):
                        match = re.match(authorRegex, field)
                        if match:
                            authorPage = pywikibot.User(self.site, match.group(1))
                            authorName = match.group(2)
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

    def addSourceOwn(self, mediaid):
        """
        Dummy method for now
        :return:
        """
        return

    def addAuthor(self, mediaid, authorPage, authorName):
        """
        Add the author info to filepage
        :param authorPage:
        :param authorName:
        :return:
        """
        if self.mediaInfoHasStatement(mediaid, u'P170'):
            return

        # Do the adding of somevalue here

        summary = u'Extracted [[Commons:Structured data/Modeling/Author|author]] from [[Template:Information|Information]] in the wikitext '

        tokenrequest = http.fetch(u'https://commons.wikimedia.org/w/api.php?action=query&meta=tokens&type=csrf&format=json')

        tokendata = json.loads(tokenrequest.text)
        token = tokendata.get(u'query').get(u'tokens').get(u'csrftoken')

        postdata = {u'action' : u'wbcreateclaim',
                    u'format' : u'json',
                    u'entity' : mediaid,
                    u'property' : u'P170',
                    u'snaktype' : u'somevalue',
                    u'token' : token,
                    u'summary' : summary,
                    u'bot' : True,
                    }
        apipage = http.fetch(u'https://commons.wikimedia.org/w/api.php', method='POST', data=postdata)

        revison = json.loads(apipage.text).get(u'pageinfo').get(u'lastrevid')
        claim = json.loads(apipage.text).get(u'claim').get(u'id')

        # Object has role (P3831) ->  photographer (Q33231)
        apipage = self.addQualifier(claim, u'P3831', u'Q33231', u'item', revison, summary)
        revison = json.loads(apipage.text).get(u'pageinfo').get(u'lastrevid')

        # author name string (P2093) ->  authorName
        apipage = self.addQualifier(claim, u'P2093', authorName, u'string', revison, summary)
        revison = json.loads(apipage.text).get(u'pageinfo').get(u'lastrevid')

        #  Wikimedia username (P4174) ->  authorPage.username
        apipage = self.addQualifier(claim, u'P4174', authorPage.username, u'string', revison, summary)
        revison = json.loads(apipage.text).get(u'pageinfo').get(u'lastrevid')

        #   URL (P2699) ->  authorPage.title
        authorUrl = u'https://commons.wikimedia.org/wiki/%s' % (authorPage.title(underscore=True), )
        apipage = self.addQualifier(claim, u'P2699', authorUrl, u'string', revison, summary)
        print (apipage)

    def addLicenses(self, mediaid, licenses):
        """
        Add the author info to filepage
        :param authorPage:
        :param authorName:
        :return:
        """
        if self.mediaInfoHasStatement(mediaid, u'P6216'):
            return
        if self.mediaInfoHasStatement(mediaid, u'P275'):
            return

        # Add the fact that the file is copyrighted
        self.addClaim(mediaid, u'P6216', u'Q50423863', u'Extracted [[Commons:Structured data/Modeling/Copyright|copyright]] status from wikitext' )

        # Add the different licenses
        for license in licenses:
            self.addClaim(mediaid, u'P275', license, u'Extracted [[Commons:Structured data/Modeling/Licensing|license]] from [[Template:Self|Self]] in the wikitext' )


    def addClaim(self, mediaid, pid, qid, summary=u''):
        """
        Add a claim to a mediaid

        :param mediaid: The mediaid to add it to
        :param pid: The property P id (including the P)
        :param qid: The item Q id (including the Q)
        :param summary: The summary to add in the edit
        :return: Nothing, edit in place
        """
        pywikibot.output(u'Adding %s->%s to %s. %s' % (pid, qid, mediaid, summary))

        tokenrequest = http.fetch(u'https://commons.wikimedia.org/w/api.php?action=query&meta=tokens&type=csrf&format=json')

        tokendata = json.loads(tokenrequest.text)
        token = tokendata.get(u'query').get(u'tokens').get(u'csrftoken')

        postvalue = {"entity-type":"item","numeric-id": qid.replace(u'Q', u'')}

        postdata = {u'action' : u'wbcreateclaim',
                    u'format' : u'json',
                    u'entity' : mediaid,
                    u'property' : pid,
                    u'snaktype' : u'value',
                    u'value' : json.dumps(postvalue),
                    u'token' : token,
                    u'summary' : summary,
                    u'bot' : True,
                    }
        apipage = http.fetch(u'https://commons.wikimedia.org/w/api.php', method='POST', data=postdata)
        return apipage

    def addQualifier(self, claim, pid, value, entityType, baserevid, summary=u''):
        """

        :param claim:
        :param pid:
        :param value:
        :param entityType:
        :param baserevid:
        :return:
        """
        pywikibot.output(u'Adding %s->%s to %s. %s' % (pid, value, claim, summary))

        tokenrequest = http.fetch(u'https://commons.wikimedia.org/w/api.php?action=query&meta=tokens&type=csrf&format=json')

        tokendata = json.loads(tokenrequest.text)
        token = tokendata.get(u'query').get(u'tokens').get(u'csrftoken')

        if entityType==u'item':
            postvalue = {"entity-type":"item","numeric-id": value.replace(u'Q', u'')}
        else:
            postvalue = value

        postdata = {u'action' : u'wbsetqualifier',
                    u'format' : u'json',
                    u'claim' : claim,
                    u'property' : pid,
                    u'snaktype' : u'value',
                    u'value' : json.dumps(postvalue),
                    u'token' : token,
                    u'summary' : summary,
                    u'baserevid' : baserevid,
                    u'bot' : True,
                    }
        apipage = http.fetch(u'https://commons.wikimedia.org/w/api.php', method='POST', data=postdata)
        return apipage


    def mediaInfoExists(self, mediaid):
        """
        Check if the media info exists or not
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :return: True if it exists, otherwise False
        """
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M72643194
        request = self.site._simple_request(action='wbgetentities',ids=mediaid)
        data = request.submit()
        if data.get(u'entities').get(mediaid).get(u'pageid'):
            return True
        return False

    def mediaInfoHasStatement(self, mediaid, property):
        """
        Check if the media info exists or not
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :param property: The property ID to check for (like P180)
        :return: True if it exists, otherwise False
        """
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M72643194
        request = self.site._simple_request(action='wbgetentities',ids=mediaid)
        data = request.submit()
        # No structured data at all is no pageid
        if not data.get(u'entities').get(mediaid).get(u'pageid'):
            return False
        # Has structured data, but the list of statements is empty
        if not data.get(u'entities').get(mediaid).get(u'statements'):
            return False
        if property in data.get(u'entities').get(mediaid).get(u'statements'):
            return True
        return False


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
