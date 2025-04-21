#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This bot adds the missing digital representation and/or main subject link on files that are in use.

It uses https://multichill.toolforge.org/queries2/commons/paintings_without_wikidata_simple.txt as input.
"""
import pywikibot
import requests
import re
import pywikibot.data.sparql
from pywikibot import pagegenerators

class PaintingsMatchBot:
    """
    A bot to add missing links to Wikidata on Commons
    """
    def __init__(self):
        """
        Build all the lookup tables to work on
        """
        self.commons = pywikibot.Site(u'commons', u'commons')
        self.commons.login()
        self.commons.get_tokens('csrf')
        self.repo = self.commons.data_repository()

        self.items_incoming_commons = self.get_commons_without_wikidata()
        self.generator = pagegenerators.PreloadingEntityGenerator(self.get_items_to_check_generator())

    def run(self):
        """
        Get the intersection of painting items with images and painting images without an item and add the links
        """
        for item in self.generator:
            item_title = item.title()
            for filename in self.items_incoming_commons.get(item_title):
                self.check_item_for_image(item, filename)

    def get_commons_without_wikidata(self):
        """
        Get the list of painting images on Commons that don't have a Wikidata identifier.

        This returns a dict with the items to check and per item the list (usually 1) of images to check
        """
        result = {}
        url = 'https://multichill.toolforge.org/queries2/commons/paintings_without_wikidata_simple.txt'
        regex = '^\* \[\[:File:(?P<image>[^\]]+)\]\] - \[\[(?P<item>Q\d+)\]\]$'
        query_page = requests.get(url)
        for match in re.finditer(regex, query_page.text, flags=re.M):
            image = match.group("image")
            item = match.group("item")
            if item not in result:
                result[item] = []
            result[item].append(image)
        return result

    def get_items_to_check_generator(self):
        """
        Generator of all items to check
        :return: ItemPages
        """
        for item_title in self.items_incoming_commons:
            item = pywikibot.ItemPage(self.repo, item_title)
            yield item

    def check_item_for_image(self, item, filename):
        """

        :param item:
        :param filename:
        :return:
        """
        image_file = pywikibot.FilePage(self.commons, title=filename)

        data = item.get()
        claims = data.get('claims')

        pywikibot.output('Working on %s and %s' % (item.title(),filename))

        if 'P31' not in claims:
            pywikibot.output('No instance of, skipping')
            return

        if not claims.get('P31')[0].target_equals('Q3305213'):
            pywikibot.output('Not a painting, skipping')
            return

        if 'P18' not in claims and 'P7420' not in claims:
            pywikibot.output('No image (P18) and image with frame (P7420) found, skipping')
            return

        # First check image with frame (P7420)
        if 'P7420' in claims:
            for image_claim in claims.get('P7420'):
                if image_claim.getTarget() == image_file:
                    pywikibot.output('Match for P7420 on %s and %s' % (item.title(),filename))
                    self.add_wikidata_to_file(image_file, item, 'P7420')
                    return

        # Second check image (P18)
        if 'P18' in claims:
            for image_claim in claims.get('P18'):
                if image_claim.getTarget() == image_file:
                    pywikibot.output('Match for P18 on %s and %s' % (item.title(),filename))
                    self.add_wikidata_to_file(image_file, item, 'P18')
                    return

    def add_wikidata_to_file(self, image_file, item, source_property):
        """
        Add the Wikidata links to a file
        :param image_file: The file to work on
        :param item: Item to add
        :param source_property: What property used as source
        :return:
        """
        mediainfo = image_file.data_item()
        data = mediainfo.get()
        claims = data.get('statements')

        summary = f'based on [[d:Special:EntityPage/{source_property}]]'

        # Only add digital representation of (P6243) if it's based on image (P18)
        if 'P6243' not in claims:
            new_claim = pywikibot.Claim(self.commons, 'P6243')
            if source_property == 'P18':
                new_claim.setTarget(item)
            elif source_property == 'P7420':
                new_claim.setSnakType('novalue')
            pywikibot.output('Adding digital representation of (P6243) to %s %s' % (image_file.title(), summary))
            mediainfo.addClaim(new_claim, summary=summary)

        # Add main subject (P921)
        if 'P921' not in claims:
            new_claim = pywikibot.Claim(self.commons, 'P921')
            new_claim.setTarget(item)
            pywikibot.output('Adding main subject (P921) to %s %s' % (image_file.title(), summary))
            mediainfo.addClaim(new_claim, summary=summary)

        # Add depicts (P180)
        if 'P180' not in claims:
            new_claim = pywikibot.Claim(self.commons, 'P180')
            new_claim.setTarget(item)
            pywikibot.output('Adding depicts (P180) to %s %s' % (image_file.title(), summary))
            mediainfo.addClaim(new_claim, summary=summary)

        # Always to a null edit at the end to trigger page update
        image_file.touch()


def main():
    paintings_match_bot = PaintingsMatchBot()
    paintings_match_bot.run()

if __name__ == "__main__":
    main()
