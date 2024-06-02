#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add the point in time (P585) qualifier to image (P18) statements.

"""
import sys
import pywikibot
from pywikibot import pagegenerators


class ImagePointInTimeBot:
    """
    A bot to add point in time (P585) qualifiers
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields ItemPage objects.
        """
        self.generator = generator
        self.commons = pywikibot.Site('commons', 'commons')
        self.repo = pywikibot.Site().data_repository()

    def run(self):
        """
        Starts the robot.
        """
        for item_page in self.generator:
            pywikibot.output('Working on %s' % (item_page.title(),))
            if not item_page.exists():
                pywikibot.output(u'Item does not exist, skipping')
                continue

            if item_page.isRedirectPage():
                item_page = item_page.getRedirectTarget()
                
            data = item_page.get()
            claims = data.get('claims')

            if 'P18' not in claims:
                pywikibot.output('Item does not have an image (P18), skipping')
                continue

            for image_claim in claims.get('P18'):
                if 'P585' in image_claim.qualifiers:
                    pywikibot.output('Image already has point in time (P585) qualifier, skipping')
                    continue

                file_page = image_claim.getTarget()
                if not file_page:
                    pywikibot.output('Image does not exist or novalue, skipping')
                    continue

                media_info = file_page.data_item()
                media_data = media_info.get()
                claims = media_data.get('statements')

                if 'P571' not in claims:
                    pywikibot.output('Image %s missing inception (P571), skipping' % (file_page.title(),))
                    continue
                if len(claims.get('P571')) > 1:
                    pywikibot.output('Image %s has multiple inception (P571) claims, skipping' % (file_page.title(),))
                    continue

                qualifier_target = claims.get('P571')[0].getTarget()
                new_qualifier = pywikibot.Claim(self.repo, 'P585')
                new_qualifier.setTarget(qualifier_target)
                summary = 'based on [[Property:P571]] on [[:Commons:%s]]' % (file_page.title(), )
                pywikibot.output('Adding point in time (P585) based in inception (P571) on %s' % (file_page.title(), ))
                image_claim.addQualifier(new_qualifier, summary=summary)


def main(*args):
    wikidata_property = None

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-wikidataproperty:'):
            if len(arg) == 18:
                wikidata_property = pywikibot.input(
                    'Please enter the property you want to work on:')
            else:
                wikidata_property = arg[18:]

    if not wikidata_property:
        pywikibot.output('Please provide -wikidataproperty:')
        sys.exit()

    query = """SELECT ?item WHERE {
  ?item wdt:%s ?id;
        p:P18 ?imagestatement.
  MINUS { ?imagestatement pq:P585 [] } .
  } LIMIT 10000""" % (wikidata_property, )

    repo = pywikibot.Site().data_repository()
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    image_point_in_time_bot = ImagePointInTimeBot(generator)
    image_point_in_time_bot.run()


if __name__ == "__main__":
    main()
