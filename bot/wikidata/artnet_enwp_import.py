#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Pull artnet links from http://www.artnet.com/artists/ from the English Wikipedia and import to Wikidata
Do some checking to prevent junk.
"""
import pywikibot
import requests
import urllib
import re
from pywikibot import pagegenerators, WikidataBot


class ArtnetRobot(WikidataBot):

    """A bot to import artnet ids from Wikipedia"""

    def __init__(self, generator):
        """
        Constructor.

        @param generator: A generator that yields Page objects.
        @type generator: iterator
        """
        super(ArtnetRobot, self).__init__(use_from_page=None)
        self.generator = generator
        self.cacheSources()

    def treat(self, page, item):
        """Treat each page."""
        #self.current_page = page
        regex = u'http\:\/\/www\.artnet\.com\/artists\/([^\/\s]+)'
        baseurl = u'http://www.artnet.com/artists/%s/'
        text = page.get()
        match = re.search(regex, text)
        if not match:
            pywikibot.output(u'No match found on %s ' % (page.title(),))
            return
        artnetid_encoded = match.group(1).lower()
        artnetid = urllib.unquote(artnetid_encoded.encode('utf8')).decode('utf8')
        pywikibot.output(u'Found id %s (%s) on %s ' % (artnetid, artnetid_encoded, page.title(),))
        if not page.title()[:3].lower()==artnetid[:3].lower():
            pywikibot.output(u'First letters do not match, skipping')
            return
        url = baseurl % (artnetid_encoded,)
        artnetpage = requests.get(url)
        if artnetpage.status_code==404:
            pywikibot.output(u'Got a 404 (not found) for %s, skipping' % (url,))
            return
        if not artnetpage.url.startswith(url):
            pywikibot.output(u'The url %s redirected to the incorrect url %s, skipping' % (url,artnetpage.url))
            return
        if 'P3782' in item.claims:
            pywikibot.output(u'The item already has P3782, skipping')
            return
        claim = pywikibot.Claim(self.repo, u'P3782')
        claim.setTarget(artnetid)
        self.user_add_claim(item, claim, page.site)


def main():
    site = pywikibot.Site('en', 'wikipedia')
    generator = pagegenerators.PreloadingGenerator(pagegenerators.LinksearchPageGenerator(u'www.artnet.com/artists/', namespaces=[0], site=site))

    bot = ArtnetRobot(generator)
    bot.run()

if __name__ == "__main__":
    main()
