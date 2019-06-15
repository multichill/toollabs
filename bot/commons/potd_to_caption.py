#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import POTD translations into the structured data captions.

This is just a proof of concept to show that this is possible. When we're actually going to import,
I should probably optimize it.

"""

import pywikibot
import re
import pywikibot.data.sparql
import datetime
from pywikibot.comms import http
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
            self.handlePotd(potd)

    def handlePotd(self, potd):
        """
        Handle one picture of the day
        :param potd: The POTD template of that day
        """
        regex = u'\{\{Potd filename\|([^\|]+)\|(\d\d\d\d)\|(\d{1,2})|(\d{1,2})\}\}'
        match = re.search(regex, potd.text)
        captions = {}
        filename = None
        if match:
            filename = match.group(1)
            for potdlang in pagegenerators.PrefixingPageGenerator(potd.title()+u'_(', site=self.site, includeredirects=False):
                potdinfo  = self.handlePotdLang(potdlang)
                if potdinfo:
                    (lang, caption) = potdinfo
                    captions[lang] = caption

        # Reshufle so I don't end up getting the captions all the time
        if captions and filename:
            filepage = pywikibot.FilePage(self.site, title=filename)
            if filepage.exists():
                # Might run into redirects
                mediaid = u'M%s' % (filepage.pageid,)
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
        labels = {}
        for lang in captions:
            labels[lang] = {u'language' : lang, 'value' : captions.get(lang)}

        tokenrequest = http.fetch(u'https://commons.wikimedia.org/w/api.php?action=query&meta=tokens&type=csrf&format=json')
        tokendata = json.loads(tokenrequest.text)
        token = tokendata.get(u'query').get(u'tokens').get(u'csrftoken')

        summary = u'adding captions for %s languages based on POTD template' % (len(captions),)
        pywikibot.output(mediaid + u' ' + summary)

        postdata = {u'action' : u'wbeditentity',
                    u'format' : u'json',
                    u'id' : mediaid,
                    u'data' : json.dumps({ u'labels' : labels}),
                    u'token' : token,
                    u'summary' : summary,
                    u'bot' : True,
                    }
        apipage = http.fetch(u'https://commons.wikimedia.org/w/api.php', method='POST', data=postdata)

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
