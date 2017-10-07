#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add https://commons.wikimedia.org/wiki/Template:Interwiki_from_wikidata to categories on Commons

1. Run the query at https://tools.wmflabs.org/multichill/queries/commons/commons_need_wikidata_sitelinks.sql
2. Download the result at https://tools.wmflabs.org/multichill/queries/commons/commons_need_wikidata_sitelinks.txt
3. Run the bot on the file with -file:/tmp/commons_need_wikidata_sitelinks.txt

The bot will just loop over all categories and if none of the skip templates are found, at {{Interwiki from wikidata}}
"""

import pywikibot
from pywikibot import pagegenerators
import re
import datetime
import requests

def main(*args):
    '''
    Main and only loop
    '''

    # Process global args and prepare generator args parser
    local_args = pywikibot.handle_args(args)
    genFactory = pagegenerators.GeneratorFactory()

    for arg in local_args:
        genFactory.handleArg(arg)
    gen = genFactory.getCombinedGenerator(preload=True)
    if gen:
        generator = pagegenerators.NamespaceFilterPageGenerator(gen, 14)
        skiptemplates = [u'Interwiki from wikidata',
                         u'On Wikidata',
                         u'Countries of Europe',
                         u'VN'
                         ]

        for page in generator:
            pywikibot.output(u'Working on %s' % (page.title(),))
            if not page.exists():
                pywikibot.output(u'Page does not exist')
                continue
            text = page.get()
            foundtemplate = False
            for skiptemplate in skiptemplates:
                if u'{{%s' % (skiptemplate.lower(),) in text.lower():
                    foundtemplate = True
            if foundtemplate:
                pywikibot.output(u'Already has the template')
                continue
            newtext = u'{{Interwiki from wikidata}}\n' + text
            summary = u'Adding {{Interwiki from wikidata}} to get links to Wikipedia articles'
            pywikibot.showDiff(text, newtext)
            page.put(newtext, summary=summary)

    else:
        pywikibot.bot.suggest_help(missing_generator=True)
        return False


if __name__ == "__main__":
    main()
