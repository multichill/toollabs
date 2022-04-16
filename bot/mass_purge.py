#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to mass purge pages to clear out things.

Just pass a normal page generator and the bot will work on it.

The bot will purge the items in batches. The default batch size is 25 and you can adjust it with -batchsize
"""
import pywikibot
from pywikibot import pagegenerators


def main(*args):
    """
    Run the bot.
    """
    # Process global args and prepare generator args parser
    local_args = pywikibot.handle_args(args)
    gen_factory = pagegenerators.GeneratorFactory()

    batchsize = 25
    for arg in local_args:
        if gen_factory.handleArg(arg):
            continue
        elif arg.startswith('-batchsize'):
            if len(arg) == 10:
                batchsize = int(pywikibot.input('Please enter the batch size:'))
            else:
                batchsize = int(arg[11:])

    gen = gen_factory.getCombinedGenerator(preload=False)

    purgelist = []
    batch = 0
    for page in gen:
        purgelist.append(page)
        if len(purgelist) > batchsize:
            batch = batch + 1
            pywikibot.output('Purging %s page in batch %s ending at %s' % (batchsize, batch, page.title()))
            try:
                page.site.purgepages(purgelist, forcelinkupdate=1)
                purgelist = []
            except pywikibot.exceptions.APIError:
                pywikibot.output('Yah! Broke it again. Let\'s sleep for a minute')
                time.sleep(60)
    if purgelist:
        pywikibot.output('Purging last batch')
        purgelist[0].site.purgepages(purgelist, forcelinkupdate=1)

if __name__ == "__main__":
    main()