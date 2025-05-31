#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add genre is still life to paintings based on the label

TODO: Configure what to look for at https://www.wikidata.org/wiki/User:BotMultichillT/still_life_paintings.js

"""
import json
import pywikibot
from pywikibot import pagegenerators

class StillLifePaintingsBot:
    """
    A bot to add genre to paintings on Wikidata
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields Wikidata items objects.

        """
        self.repo = pywikibot.Site().data_repository()
        self.lang_label_pairs = self.get_configuration()
        self.generator = self.get_generator_search()
        self.not_matched = []

    def get_configuration(self):
        """
        Grab the configuration of tuples to work on
        :return: List of tuples
        """
        result = [('en', 'Still Life'),
                  ('en', 'Stilllife'),
                  ('en', 'Nature morte'),
                  ('fr', 'Nature morte'),
                  ('nl', 'Stilleven'),
                  ('nl', 'Bloemstilleven'),
                  ('de', 'Stillleben'),
                  ('de', 'Stilleben'),
                  ('de', 'Blumenstillleben'),
                  ('de', 'Früchtestillleben'),
                  ('de', 'Blumenstilleben'),
                  ('de', 'Früchtestilleben'),
                  ('de', 'Jagdstillleben'),
                  ('de', 'Fischstillleben'),
                  ('sv', 'Stilleben'),
                  ('sv', 'Nature morte'),
                  ('ca', 'Natura morta'),
                  ('da', 'Stilleben'),
                  ('da', 'Nature morte'),
                  ('nn', 'Stilleben'),
                  ('en', 'Still-life'),
                  ('en', 'Stilllife'),
                  ('en', 'Flower Still Life'),
                  ('en', 'Kitchen Still Life'),
                  ('en', 'Untitled (Still Life)'),
                  ('en', 'Hunting Still Life'),
                  ('nl', 'Atelierstilleven'),
                  ('nl', 'Bloemstilleven'),
                  ('nl', 'Bloemenstilleven'),
                  ('nl', 'Fruitstilleven'),
                  ('nl', 'Jachtstilleven'),
                  ('nl', 'Keukenstilleven'),
                  ('nl', 'Pronkstilleven'),
                  ('nl', 'Vruchtenstilleven'),
                  ('nl', 'Visstilleven'),
                  ('nl', 'Nature morte'),
                  ('pt', 'Natureza Morta'),
                  ('es', 'Bodegón'),
                  ('es', 'Naturaleza muerta'),
                  ('en', 'Vanitas'),
                  ('fr', 'Vanitas'),
                  ('de', 'Vanitas'),
                  ('nl', 'Vanitas'),
                  ]
        return result
        result = []
        configpage = pywikibot.Page(self.repo, title=u'User:BotMultichillT/still_life_paintings.js')
        (comments, sep, jsondata) = configpage.get().partition(u'[')
        jsondata = u'[' + jsondata
        configjson = json.loads(jsondata)
        for workitem in configjson:
            langlabelpair = (workitem.get('lang'), workitem.get('labelstart'))
            result.append(langlabelpair)
        return result

    def get_generator_search(self):
        """
        Do searches and return the results
        :return: A generator that yields items
        """
        for (lang, labelstart) in self.lang_label_pairs:
            search = f'inlabel:"{labelstart}" haswbstatement:P31=Q3305213 -haswbstatement:P136'
            gen = pagegenerators.PreloadingEntityGenerator(pagegenerators.SearchPageGenerator(search, site=self.repo))
            for item in gen:
                yield item

    def run(self):
        """
        Starts the robot.
        """
        for item in self.generator:
            self.process_painting(item)

        self.report_no_automatic_match()

    def process_painting(self, item):
        """
        Work on a individual painting. Add the genre if a label is found
        """
        data = item.get()
        claims = data.get('claims')

        if 'P136' in claims:
            # Already done
            return

        got_match = self.find_label_match(item)

        if not got_match:
            self.not_matched.append(item.title())
            return

        summary = 'based on (%s)"%s" ' % got_match

        genre_claim = pywikibot.Claim(self.repo, 'P136')
        genre_claim.setTarget(pywikibot.ItemPage(self.repo, title='Q170571'))
        pywikibot.output('Adding genre claim to %s %s' % (item.title(), summary))
        item.addClaim(genre_claim, summary=summary)

    def find_label_match(self, item):
        """
        Try to find a match in the item.
        :param item: The painting ItemPage
        :return: Tuple (lang, labelstart) if match is found
        """
        labels = item.get().get('labels')
        for (item_lang, item_label) in labels.items():
            for (lang, label_start) in self.lang_label_pairs:
                if item_lang==lang:
                    if item_label.lower().startswith(label_start.lower()):
                        got_match = (lang, label_start)
                        return got_match
        return None

    def report_no_automatic_match(self):
        """
        Report the list of items that could not be matched
        :return:
        """
        page = pywikibot.Page(self.repo,
                              title='Wikidata:WikiProject sum of all paintings/Possible still life no automatic match')
        text = 'For this list of paintings, a bot was unable to add {{P|P136}}. It might be {{Q|Q170571}}\n'

        item_list = sorted(list(set(self.not_matched)))
        for item_title in item_list:
            text += '* {{Q+|%s}}\n' % (item_title,)
        text += '\n[[Category:WikiProject sum of all paintings genres|Possible still life no automatic match]]'

        summary = f'Found {len(item_list)} possible still life without automatic match'
        pywikibot.output(summary)
        page.put(text, summary)


def main():
    """
    Just a main function to start the robot
    """
    still_life_paintingsBot = StillLifePaintingsBot()
    still_life_paintingsBot.run()

if __name__ == "__main__":
    main()
