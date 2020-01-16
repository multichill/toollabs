#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to upload onroerenderfgoed.be images.

"""

import pywikibot
import re
import pywikibot.data.sparql
from pywikibot.comms import http
import datetime
import hashlib
import io
import base64
import tempfile
import os
import time
import requests
import json
from html.parser import HTMLParser

class OnroerendUploaderBot:
    """
    A bot to upload images
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.generator = generator
        self.repo = pywikibot.Site().data_repository()
        self.site = pywikibot.Site(u'commons', u'commons')

    def run(self):
        """
        Starts the robot.
        """
        for metadata in self.generator:
            self.uploadPainting(metadata)

    def uploadPainting(self, metadata):
        """
        Process the metadata and if suitable, upload the painting
        """
        pywikibot.output(metadata)
        description = self.getDescription(metadata)
        title = self.cleanUpTitle(self.getTitle(metadata))
        if not description or not title:
            return
        pywikibot.output(title)
        pywikibot.output(description)
        try:
            response = requests.get(metadata.get(u'downloadurl'), verify=False) # Museums and valid SSL.....
        except requests.exceptions.ConnectionError:
            pywikibot.output(u'Got a connection error for Wikidata item [[:d:%(item)s]] with url %(downloadurl)s' % metadata)
            return False

        if response.status_code == 200:
            hashObject = hashlib.sha1()
            hashObject.update(response.content)
            sha1base64 = base64.b16encode(hashObject.digest())
            duplicates = list(self.site.allimages(sha1=sha1base64))
            if duplicates:
                pywikibot.output(u'Found a duplicate, trying to add it')
                imagefile = duplicates[0]
                self.addImageToWikidata(metadata, imagefile, summary = u'Adding already uploaded image')
                duplicate = { u'title' : title,
                              u'qid' : metadata.get(u'item'),
                              u'downloadurl' : metadata.get(u'downloadurl'),
                              u'sourceurl' : metadata.get(u'sourceurl'),
                              u'duplicate' : imagefile.title(withNamespace=False),
                              u'description' : description,
                              }
                self.duplicates.append(duplicate)
                return

            # This part is commented out because only sysop users can do this :-(
            ## self.site.filearchive does not exist, have to dig deeper
            ## deleted = list(self.site.filearchive(sha1=sha1base64))
            #deleted_url = u'https://commons.wikimedia.org/w/api.php?action=query&list=filearchive&faprop=sha1&fasha1=%s&format=json'
            #fa_response = http.fetch(deleted_url % (sha1base64,))
            #fa_data = json.loads(fa_response.text)
            #print (fa_data)
            #if fa_data.get(u'query').get(u'filearchive'):
            #    fa_title = fa_data.get(u'query').get(u'filearchive')[0].get(u'title')
            #    pywikibot.output(u'Found a deleted file %s with the same hash %s, skipping it' % (fa_title, sha1base64))
            #    return

            with tempfile.NamedTemporaryFile() as t:
                t.write(response.content)
                t.flush()

                imagefile = pywikibot.FilePage(self.site, title=title)
                imagefile.text=description

                comment = u'Uploading based on Wikidata item [[:d:%(item)s]] from %(downloadurl)s' % metadata
                try:
                    uploadsuccess = self.site.upload(imagefile, source_filename=t.name, ignore_warnings=True, comment=comment) # chunk_size=1000000)
                except pywikibot.data.api.APIError:
                    pywikibot.output(u'Failed to upload image for Wikidata item [[:d:%(item)s]] from %(downloadurl)s' % metadata)
                    uploadsuccess = False

            if uploadsuccess:
                pywikibot.output('Uploaded a file, sleeping a bit so I don\'t run into lagging databases')
                time.sleep(15)
                self.addImageToWikidata(metadata, imagefile, summary = u'Uploaded the image')
                mediaid = u'M%s' % (imagefile.pageid,)
                summary = u'this newly uploaded file depicts and is a digital representation of [[:d:%s]]' % (metadata.get(u'item'),)
                self.addClaim(mediaid, u'P180', metadata.get(u'item'), summary)
                self.addClaim(mediaid, u'P6243', metadata.get(u'item'), summary)
                self.addSource(mediaid, metadata)
                imagefile.touch()

    def addImageToWikidata(self, metadata, imagefile, summary=u'Added the image'):
        """
        Add the image to the Wikidata item. This might add an extra image if the item already has one
        """
        artworkItem = pywikibot.ItemPage(self.repo, title=metadata.get(u'item'))
        data = artworkItem.get()
        claims = data.get('claims')

        newclaim = pywikibot.Claim(self.repo, u'P18')
        newclaim.setTarget(imagefile)

        foundimage = False
        replacedimage = False
        if u'P18' in claims:
            for claim in claims.get(u'P18'):
                if claim.getTarget().title()==newclaim.getTarget().title():
                    pywikibot.output(u'The image is already on the item')
                    foundimage = True
            if not foundimage and len(claims.get(u'P18'))==1:
                claim = claims.get(u'P18')[0]
                newimagesize = imagefile.latest_file_info.size
                currentsize = claim.getTarget().latest_file_info.size
                # Only replace if new one is at least 4 times larger
                if currentsize * 4 < newimagesize:
                    summary = u'replacing with much larger image'
                    claim.changeTarget(imagefile, summary=summary)
                    replacedimage = True

        if not foundimage and not replacedimage:
            pywikibot.output('Adding %s --> %s' % (newclaim.getID(), newclaim.getTarget()))
            artworkItem.addClaim(newclaim, summary=summary)
        # Only remove if we had one suggestion. Might improve the logic in the future here
        if u'P4765' in claims and len(claims.get(u'P4765'))==1:
            artworkItem.removeClaims(claims.get(u'P4765')[0], summary=summary)

    def getDescription(self, metadata):
        """
        Construct the description for the file to be uploaded
        """
        artworkinfo = u'{{Artwork}}\n' # All structured data on Commons!
        licenseinfo = self.getLicenseTemplate(metadata)
        categoryinfo =  self.getCategories(metadata)
        if artworkinfo and licenseinfo and categoryinfo:
            description = u'== {{int:filedesc}} ==\n'
            description = description + artworkinfo
            description = description + u'\n=={{int:license-header}}==\n'
            description = description + licenseinfo + u'\n' + categoryinfo
            return description

    def getLicenseTemplate(self, metadata):
        """
        Construct the license template to be used
        """
        # FIXME: Add more or different implementation
        licenses = { u'Q6938433' : u'Cc-zero',
                     u'Q18199165' : u'cc-by-sa-4.0'}

        if metadata.get(u'license'):
            result = u'{{Licensed-PD-Art'
        else:
            result = u'{{PD-Art'

        if metadata.get(u'deathyear'):
            result += u'|PD-old-auto-expired'
        else:
            result += u'|PD-old-100-expired'

        if metadata.get(u'license'):
            if metadata.get(u'license') not in licenses:
                pywikibot.output(u'Found a license I do not understand: %(license)s' % metadata)
                return False
            licensetemplate = licenses.get(metadata.get(u'license'))
            result += u'|%s' % (licensetemplate,)

        if metadata.get(u'deathyear'):
            result += u'|deathyear=%s' % (metadata.get(u'deathyear'),)

        result += u'}}\n'
        return result

    def getCategories(self, metadata):
        """
        Add categories for the collection and creator if available.

        For the collection the fallback tree is:
        1. Category:Paintings in the <collectioncategory>
        2. Category:Paintings in <collectioncategory>
        3. Category:<collectioncategory>

        Only add a creatorcategory if it's available (not the case for anonymous works)
        """
        result = u'{{subst:#ifexist:Category:Paintings in the %(collectioncategory)s|[[Category:Paintings in the %(collectioncategory)s]]|{{subst:#ifexist:Category:Paintings in %(collectioncategory)s|[[Category:Paintings in %(collectioncategory)s]]|[[Category:%(collectioncategory)s]]}}}}\n' % metadata
        if metadata.get(u'creatorcategory'):
            result = result + u'{{subst:#ifexist:Category:Paintings by %(creatorcategory)s|[[Category:Paintings by %(creatorcategory)s]]|[[Category:%(creatorcategory)s]]}}' % metadata
        return result

    def getTitle(self, metadata):
        """
        Construct the title to be used for the upload
        """
        formats = { u'Q2195' : u'jpg',
                    #u'Q215106' : u'tiff',
                    }
        if not metadata.get(u'format') or metadata.get(u'format') not in formats:
            return u''

        metadata[u'ext'] = formats.get(metadata.get(u'format'))

        fmt = u'%(creatorname)s - %(title)s - %(inv)s - %(collectionLabel)s.%(ext)s'
        title = fmt % metadata
        if len(title) < 200:
            return title
        else:
            title = u'%(creatorname)s - ' % metadata
            title = title + metadata.get(u'title')[0:100].strip()
            title = title + u' - %(inv)s - %(collectionLabel)s.jpg' % metadata
            return title

    def cleanUpTitle(self, title):
        """
        Clean up the title of a potential mediawiki page. Otherwise the title of
        the page might not be allowed by the software.
        """
        title = title.strip()
        title = re.sub(u"[<{\\[]", u"(", title)
        title = re.sub(u"[>}\\]]", u")", title)
        title = re.sub(u"[ _]?\\(!\\)", u"", title)
        title = re.sub(u",:[ _]", u", ", title)
        title = re.sub(u"[;:][ _]", u", ", title)
        title = re.sub(u"[\t\n ]+", u" ", title)
        title = re.sub(u"[\r\n ]+", u" ", title)
        title = re.sub(u"[\n]+", u"", title)
        title = re.sub(u"[?!]([.\"]|$)", u"\\1", title)
        title = re.sub(u"[&#%?!]", u"^", title)
        title = re.sub(u"[;]", u",", title)
        title = re.sub(u"[/+\\\\:]", u"-", title)
        title = re.sub(u"--+", u"-", title)
        title = re.sub(u",,+", u",", title)
        title = re.sub(u"[-,^]([.]|$)", u"\\1", title)
        title = re.sub(u"^- ", u"", title)
        title = title.replace(u" ", u"_")
        return title

    def addClaim(self, mediaid, pid, qid, summary=''):
        """

        :param mediaid:
        :param pid:
        :param qid:
        :param summary:
        :return:
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

    def addSource(self, mediaid, metadata):
        """
        :return:
        """
        pid = u'P7482'
        qid =  u'Q74228490'

        summary = u'Adding source of file'
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

        # Add the described at URL (P973) where we got it from
        # FIXME: Don't think addQualifier returns the revision id
        revison = self.addQualifier(claim, u'P973', metadata.get('sourceurl'), u'string', revison, summary)

        if metadata.get('operator'):
            # Add the operator (P137) where we got it from if it's available
            revison = self.addQualifier(claim, u'P137', metadata.get('operator'), u'item', revison, summary)
        return

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

    def reportDuplicates(self):
        """
        We might have encountered some duplicates. Publish these so they can be sorted out

        https://commons.wikimedia.org/wiki/Commons:WikiProject_sum_of_all_paintings/To_upload/Duplicates

        :return:
        """
        print (u'Duplicates:')
        print (json.dumps(self.duplicates, indent=4, sort_keys=True))

        pageTitle = u'Commons:WikiProject sum of all paintings/To upload/Duplicates'
        page = pywikibot.Page(self.site, title=pageTitle)

        text = u'{{Commons:WikiProject sum of all paintings/To upload/Duplicates/header}}\n'
        text = text + u'{| class="wikitable sortable"\n'
        text = text + u'! Existing file !! Wikidata item !! Url !! Description\n'
        for duplicate in self.duplicates:
            text = text + u'|-\n'
            text = text + u'| [[File:%(duplicate)s|150px]]\n' % duplicate
            text = text + u'| [[:d:%(qid)s|%(qid)s]]\n' % duplicate
            text = text + u'| [%(sourceurl)s]\n' % duplicate
            text = text + u'|\n<small><nowiki>\n%(description)s\n</nowiki></small>\n' % duplicate
        text = text + u'|}\n'

        summary = u'Found %s duplicates in this bot run' % (len(self.duplicates), )
        pywikibot.output(summary)
        page.put(text, summary)

def getOnroerenderfgoedGenerator(startpage=1):
    htmlparser = HTMLParser()
    endpage = 19622
    for i in range(startpage, endpage):
        searchurl = 'https://beeldbank.onroerenderfgoed.be/images?license=https%%3A%%2F%%2Fcreativecommons.org%%2Flicenses%%2Fby%%2F4.0%%2F&page=%s' % (i,)
        searchpage = requests.get(searchurl)

        itemidregex = '\<img src\=\"[\s\t\r\n]*\/images\/(\d+)[\s\t\r\n]*\/content\/square\"\>'
        matches = re.finditer(itemidregex, searchpage.text)
        for match in matches:
            metadata = {}
            metadata['licence'] = 'Cc-by-4.0'
            metadata['licenseqid'] = 'Q20007257'

            imageid = match.group(1)
            url = 'https://beeldbank.onroerenderfgoed.be/images/%s' % (imageid,)

            pywikibot.output(url)
            metadata['imageid'] = imageid
            metadata['url'] = 'https://id.erfgoed.net/afbeeldingen/%s' % (imageid,)
            metadata['imageurl'] = 'https://beeldbank.onroerenderfgoed.be/images/%s/content/original' % (imageid,)

            itempage = requests.get(url)

            titleregex = '\<dl class\=\"caption-info\"\>[\s\t\r\n]*\\<dd\>Titel\<\/dd\>[\s\t\r\n]*\<dt\>([^\<]+)\<\/dt\>'

            titlematch = re.search(titleregex, itempage.text)
            metadata['title'] = htmlparser.unescape(titlematch.group(1)).strip()

            dateregex = '\<dd\>Datum opname\<\/dd\>[\s\t\r\n]*\<dt\>[\s\t\r\n]*(?P<day>\d\d)-(?P<month>\d\d)-(?P<year>\d\d\d\d)\s*(?P<hour>\d\d)\:(?P<minute>\d\d)[\s\t\r\n]*\<\/dt\>'
            datematch = re.search(dateregex, itempage.text)

            if datematch.group('minute')=='00' and datematch.group('hour')=='00' and datematch.group('day')=='01' and datematch.group('month')=='01':
                metadata['date'] = datematch.group('year')
            elif datematch.group('minute')=='00' and datematch.group('hour')=='00' and datematch.group('day')=='01':
                metadata['date'] = '%s-%s' % (datematch.group('year'), datematch.group('month'))
            else:
                metadata['date'] = '%s-%s-%s %s:%s' % (datematch.group('year'), datematch.group('month'), datematch.group('day'), datematch.group('hour'), datematch.group('minute'))

            authorregex = '\<dd\>Fotograaf\<\/dd\>[\s\t\r\n]*\<dt\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/dt\>'
            authormatch = re.search(authorregex, itempage.text)
            metadata['author'] = htmlparser.unescape(authormatch.group(1)).strip()

            addressregex = '\<dd\>Adres\<\/dd\>[\s\t\r\n]*\<dt\>[\s\t\r\n]*\<ul class\=\"nodisk\"\>[\s\t\r\n]*\<li\>[\s\t\r\n]*Provincie\:[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/li\>[\s\t\r\n]*\<li\>[\s\t\r\n]*Gemeente\:[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/li\>[\s\t\r\n]*\<li\>[\s\t\r\n]*Straat\:[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/li\>[\s\t\r\n]*\<li\>[\s\t\r\n]*Nummer\:[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/li\>[\s\t\r\n]*\<\/ul\>[\s\t\r\n]*\<\/dt\>'
            addressmatch = re.search(addressregex, itempage.text)
            if addressmatch:
                metadata['province'] = addressmatch.group(1).strip()
                metadata['municipality'] = addressmatch.group(2).strip()
                metadata['street'] = addressmatch.group(3).strip()
                #print (addressmatch.group(2).strip())
                #print (addressmatch.group(3).strip())
                if addressmatch.group(4).strip()!='/':
                    metadata['housenumber'] = addressmatch.group(4).strip()

            erfgoedobjectregex = '\{\"uri\"\:\s*\"https\:\/\/id\.erfgoed\.net\/erfgoedobjecten\/(\d+)\"\}'
            erfgoedobjectmatches = re.finditer(erfgoedobjectregex, itempage.text)

            metadata['erfgoedobject'] = []
            for erfgoedobjectmatch in erfgoedobjectmatches:
                metadata['erfgoedobject'].append(erfgoedobjectmatch.group(1))



                print (erfgoedobjectmatch.group(1))


            pointregex = 'var point\s*\=\s*JSON\.parse\(\'\{\"coordinates\"\:\s*\[(?P<x>\d+(\.\d+)?), (?P<y>\d+(\.\d+)?)\], \"crs\"\:\s*\{\"properties\"\: \{\"name\"\: \"urn\:ogc\:def\:crs\:EPSG\:\:31370\"\}, \"type\"\: \"name\"\}\, \"type\"\: \"Point\"\}\'\)'
            pointmatch = re.search(pointregex, itempage.text)
            if pointmatch:
                print ('%s %s' % (pointmatch.group('x'), pointmatch.group('y')))




            yield metadata


def main():
    generator = getOnroerenderfgoedGenerator()
    for page in generator:
        print (page)
    #onroerendUploaderBot = OnroerendUploaderBot()
    #onroerendUploaderBot.run()

if __name__ == "__main__":
    main()
