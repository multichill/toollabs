#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import POTD translations into the structured data captions.

This is just a proof of concept to show that this is possible. When we're actually going to import,
I should probably optimize it.

TODO: Fix authentication, currently editing as IP(v6)

"""

import pywikibot
import re
import pywikibot.data.sparql
import datetime
import requests
import json
from pywikibot import pagegenerators

class PotdCaptionBot:
    """
    A bot to enrich and create paintings on Wikidata
    """
    def __init__(self):
        """
        Just grab the category
        https://commons.wikimedia.org/wiki/Category:Potd_filename_templates
        and put the templates in a generator

        """
        self.site = pywikibot.Site(u'commons', u'commons')
        potdcat = pywikibot.Category(self.site, title=u'Category:Potd_filename_templates')
        self.generator = pagegenerators.CategorizedPageGenerator(potdcat, namespaces=10)

    def run(self):
        """
        Run on the POTD temlates
        """
        for potd in self.generator:
            #print potd.title()
            self.handlePotd(potd)

    def handlePotd(self, potd):
        """
        Handle one picture of the day
        :param potd: The POTD template of that day
        """
        regex = u'\{\{Potd filename\|([^\|]+)\|(\d\d\d\d)\|(\d{1,2})|(\d{1,2})\}\}'
        match = re.search(regex, potd.text)
        captions = {}
        if match:
            filename = match.group(1)
            for potdlang in pagegenerators.PrefixingPageGenerator(potd.title()+u'_(', site=self.site, includeredirects=False):
                print potdlang.title()
                potdinfo  = self.handlePotdLang(potdlang)
                if potdinfo:
                    (lang, caption) = potdinfo
                    captions[lang] = caption

        # Reshufle so I don't end up getting the captions all the time
        if captions:
            print captions
            filepage = pywikibot.FilePage(self.site, title=filename)
            if filepage.exists():
                # Might run into redirects
                mediaid = u'M%s' % (filepage.pageid,)
                print mediaid
                if not self.mediaInfoExists(mediaid):
                    self.addCaptions(mediaid, captions)

    def handlePotdLang(self, potdlang):
        """
        Extract the caption of a single POTD lang

        :param potdlang: Tuple with language and the caption
        :return:
        """
        regex = u'\{\{Potd (page|description)\|1\=(.+)\|2\=([^\|]{2,5})\|3\=(\d\d\d\d)\|4\=(\d\d)\|5\=(\d\d)\}\}'
        match = re.search(regex, potdlang.text)
        if match:
            print match.group(2)
            caption = self.sanitizeCaption(match.group(2))
            lang = match.group(3)
            return (lang, caption)
        return None

    def sanitizeCaption(self, caption):
        """
        Clean up a POTD caption. Remove links and bolded text

        :param caption: Text to clean up
        :return: Cleaned up text
        """
        regexes = [(u'\'\'\'([\']+)\'\'\'', u'\\1'),
                   (u'\[\[([^\|]+)\|([^\]]+)\]\]', u'\\2'),
                   (u'\[\[([^\]]+)\]\]', u'\\1'),
                   ]
        result = caption
        for (regex, replace) in regexes:
            result = re.sub(regex, replace, result)

        #pywikibot.showDiff(caption, result)
        return result

    def addCaptions(self, mediaid, captions):
        """
        Add the captions to the mediaid

        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :param captions: Dict of language and the caption in that language
        :return:
        """
        print u'ADDING CAPTIONS'
        labels = {}
        for lang in captions:
            labels[lang] = {u'language' : lang, 'value' : captions.get(lang)}

        # I hate tokens
        #tokenrequest = self.site._simple_request(action='query', meta='tokens', type='csrf')
        tokenrequest = requests.get(u'https://commons.wikimedia.org/w/api.php?action=query&meta=tokens&type=csrf&format=json')
        #tokendata = tokenrequest.submit()
        tokendata = tokenrequest.json()
        token = tokendata.get(u'query').get(u'tokens').get(u'csrftoken')

        postdata = {u'action' : u'wbeditentity',
                    u'format' : u'json',
                    u'id' : mediaid,
                    u'data' : json.dumps({ u'labels' : labels}),
                    u'token' : token }

        userinfo = tokendata.get(u'query').get(u'tokens').get(u'userinfo')
        #print tokendata

        print postdata

        #apipage = requests.post(u'https://commons.wikimedia.org/w/api.php?action=wbeditentity&format=json&data=, data=postdata)
        apipage = requests.post(u'https://commons.wikimedia.org/w/api.php', data=postdata)
        print apipage.text

        print labels
        #tokens = self.site.get_tokens('csrf')
        #print tokens
        #token = self.site.tokens['csrf']
        #request = self.site._simple_request(action='wbeditentity',data=json.dumps(labels), token=token)
        #data = request.submit()


        # First look if it already exists, if that's the case, just skip it.

    def mediaInfoExists(self, mediaid):
        """
        Check if the media info exists or not
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :return: True if it exists, otherwise False
        """
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M52611909
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M10038
        request = self.site._simple_request(action='wbgetentities',ids=mediaid)
        data = request.submit()
        if data.get(u'entities').get(mediaid).get(u'pageid'):
            return True
        return False


def main():
    potdCaptionBot = PotdCaptionBot()
    potdCaptionBot.run()

if __name__ == "__main__":
    main()
