#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to tag old RCE uploads for which a higher resolution file should be available.

The bot works on https://commons.wikimedia.org/wiki/Category:Images_from_the_Rijksdienst_voor_het_Cultureel_Erfgoed
* If the file has one edge that is 1200 or smaller
* and has only one uploader BotMultichill or BotMultichillT
* and doesn't already have the tag
* tag it with {{RCE-license}}

"""

import pywikibot
import re
from pywikibot import pagegenerators

class TagRceHigherBot:
    """
    Bot to add structured data statements on Commons
    """
    def __init__(self):
        """
        Grab generator based on search to work on.
        """
        self.site = pywikibot.Site(u'commons', u'commons')
        category = pywikibot.Category(self.site, 'Category:Images from the Rijksdienst voor het Cultureel Erfgoed')
        self.generator = pagegenerators.PreloadingGenerator(pagegenerators.CategorizedPageGenerator(category,
                                                                                                    recurse=False,
                                                                                                    namespaces=[6]))

    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            self.treat(filepage)


    def treat(self, page: pywikibot.page.FilePage) -> None:
        """
        Work on a single file
        :param page:
        :return:
        """
        pywikibot.output('Working on %s' % (page.title(),))
        if '{{RCE-higher-resolution}}' in page.text:
            # Already tagged
            return
        if not '{{RCE-license' in page.text:
            # No RCE-license so no idea where to put it
            return
        file_history = page.get_file_history()
        timestamps = list(file_history.keys())

        if len(timestamps) != 1:
            # Already has multiple uploads
            return
        fileinfo = file_history.get(timestamps[0])

        if fileinfo.user not in ['BotMultichill', 'BotMultichillT']:
            # Not uploaded by me
            return
        if fileinfo.width > 1200 and fileinfo.height > 1200:
            # Already higher resolution than 1200x1200
            return

        rce_license_regex = '(\{\{RCE-license[\}\|])'
        newtext = re.sub(rce_license_regex, '{{RCE-higher-resolution}}\n\\1', page.text)
        if newtext == page.text:
            return
        pywikibot.showDiff(page.text, newtext)
        summary = 'Higher resolution available on RCE website for this %sx%s file of %s bytes' % (fileinfo.width,
                                                                                                  fileinfo.height,
                                                                                                  fileinfo.size)
        page.put(newtext, summary, asynchronous=True)
        pywikibot.output(summary)


def main(*args):
    tagRceHigherBot = TagRceHigherBot()
    tagRceHigherBot.run()

if __name__ == "__main__":
    main()
