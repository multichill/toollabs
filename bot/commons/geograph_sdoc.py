#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to convert Geograph images to SDoC (structured data on Commons).

https://commons.wikimedia.org/wiki/Category:Images_from_Geograph_Britain_and_Ireland contains about 1.85M files.
The source, author and license information should be converted to structured data format
(https://commons.wikimedia.org/wiki/Commons:Structured_data).

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
    Bot to add depicts statements on Commons
    """
    def __init__(self, gen):
        """
        Grab generator based on search to work on.

        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.repo = self.site.data_repository()

        self.generator = gen



    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            self.handleGeographFile(filepage)

    def handleGeographFile(self, filepage):
        """
        Handle a Geograph file.
        Try to extract the template, look up the id and add the Q if no mediainfo is present.

        :param filepage: The page of the file to work on.
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
        licenses = [u'Q19068220',] # All Geograph images are cc-by-sa-2.0

        mediaid = u'M%s' % (filepage.pageid,)

        # We got all the needed info, let's add it
        self.addSourceGeograph(mediaid, geographid)
        self.addAuthor(mediaid, authorUrl, authorName)
        self.addLicenses(mediaid, licenses)
        # Optional stuff
        self.handleDate(filepage)
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

    def getAuthor(self, filepage):
        """
        Extract the author form the information template
        :param filepage: The page of the file to work on.
        :return: Tuple with a User and a string
        """

        # |author=[https://www.geograph.org.uk/profile/5 Helena Downton]
        authorRegex = u'^[aA]uthor\s*\=\s*\[\s*(https\:\/\/www\.geograph\.org\.uk\/profile\/\d+) ([^\]]+)\s*\]$'
        #authorRegex = u'^[aA]uthor\s*\=\s*\[\[User\:([^\|^\]]+)\|([^\|^\]]+)\]\](\s*\(\s*\[\[User talk\:[^\|^\]]+\|[^\|^\]]+\]\]\s*\)\s*)?$'

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
        Check if the file is own work. We do that by looking for both the "own" and the "self" template.
        :param filepage: The page of the file to work on.
        :return:
        """
        templateFound = False
        for template in filepage.itertemplates():
            if template.title()==u'Template:Geograph':
                templateFound = True
        if not templateFound:
            return False

        regex = u'\{\{Geograph\|(\d+)\|%s\}\}' % (authorName,)
        match = re.search(regex, filepage.text)
        if not match:
            return False
        return match.group(1)

    def addSourceGeograph(self, mediaid, geographid):
        """
        :return:
        """
        pid = u'P7482'
        qid =  u'Q74228490'
        if self.mediaInfoHasStatement(mediaid, pid):
            return
        #self.addClaim(mediaid, u'P7482', u'Q74228490', u'Extracted [[Commons:Structured data/Modeling/Source|source]] own work status from wikitext' )
        summary = u'Extracted [[Commons:Structured data/Modeling/Source|source]] Geograph from wikitext'
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

        revison = json.loads(apipage.text).get(u'pageinfo').get(u'lastrevid')
        claim = json.loads(apipage.text).get(u'claim').get(u'id')

        # operator (P137) -> Geograph Britain and Ireland (Q1503119)
        revison = self.addQualifier(claim, u'P137', u'Q1503119', u'item', revison, summary)

        #  geograph.org.uk image ID (P7384) -> the id
        revison = self.addQualifier(claim, u'P7384', geographid, u'string', revison, summary)

        #  described at URL (P973) ->  The Geograph page
        geographUrl = u'https://www.geograph.org.uk/photo/%s' % (geographid, )
        revison = self.addQualifier(claim, u'P973', geographUrl, u'string', revison, summary)

        return

    def addAuthor(self, mediaid, authorUrl, authorName):
        """
        Add the author info to filepage
        :param authorPage:
        :param authorName:
        :return:
        """
        if self.mediaInfoHasStatement(mediaid, u'P170'):
            return

        # Do the adding of somevalue here

        summary = u'Extracted [[Commons:Structured data/Modeling/Author|author]] from [[Template:Information|Information]] in the wikitext'

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
        revison = self.addQualifier(claim, u'P3831', u'Q33231', u'item', revison, summary)

        # author name string (P2093) ->  authorName
        revison = self.addQualifier(claim, u'P2093', authorName, u'string', revison, summary)

        # URL (P2699) ->  authorLink
        revison = self.addQualifier(claim, u'P2699', authorUrl, u'string', revison, summary)

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
        self.addClaim(mediaid, u'P6216', u'Q50423863', u'Added [[Commons:Structured data/Modeling/Copyright|copyright]] status based on [[Template:Geograph]]' )

        # Add the different licenses
        for license in licenses:
            self.addClaim(mediaid, u'P275', license, u'Added [[Commons:Structured data/Modeling/Copyright|copyright]] status based on [[Template:Geograph]]' )

    def handleDate(self, filepage):
        """
        Handle the date on the filepage. If it matches an ISO date (YYYY-MM-DD), add a date claim
        :param filepage:
        :return:
        """
        mediaid = u'M%s' % (filepage.pageid,)
        pid = u'P571'
        if self.mediaInfoHasStatement(mediaid, pid):
            return
        dateRegex = u'^[dD]ate\s*\=\s*(\d\d\d\d-\d\d-\d\d)\s*$'
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
            return

        parserequest = http.fetch(u'https://commons.wikimedia.org/w/api.php?format=json&action=wbparsevalue&datatype=time&values=%s' % (dateString,))
        parsedata = json.loads(parserequest.text)

        postvalue = parsedata.get(u'results')[0].get('value')

        summary = u'Extracted [[Commons:Structured data/Modeling/Date|date]] from [[Template:Information|Information]] in the wikitext'

        pywikibot.output(u'Adding %s->%s to %s. %s' % (pid, dateString, mediaid, summary))

        tokenrequest = http.fetch(u'https://commons.wikimedia.org/w/api.php?action=query&meta=tokens&type=csrf&format=json')

        tokendata = json.loads(tokenrequest.text)
        token = tokendata.get(u'query').get(u'tokens').get(u'csrftoken')

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
        try:
            revison = json.loads(apipage.text).get(u'pageinfo').get(u'lastrevid')
        except AttributeError:
            print (apipage.text)
            time.sleep(300)
            tokenrequest = http.fetch(u'https://commons.wikimedia.org/w/api.php?action=query&meta=tokens&type=csrf&format=json')

            tokendata = json.loads(tokenrequest.text)
            token = tokendata.get(u'query').get(u'tokens').get(u'csrftoken')
            postdata[u'token'] = token
            apipage = http.fetch(u'https://commons.wikimedia.org/w/api.php', method='POST', data=postdata)
            # Burn if it fails again
            revison = json.loads(apipage.text).get(u'pageinfo').get(u'lastrevid')

        return revison

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

    geographSDOCBot = GeographSDOCBot(gen)
    geographSDOCBot.run()

if __name__ == "__main__":
    main()
