#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Quite a few files on Commons have an RKDimages template and link to Wikidata. Let's import that!

"""
import pywikibot
import re
import requests
from pywikibot import pagegenerators


class RKDImagesImporter:
    """
    A bot tto import RKDimages from Commons to Wikidata
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields Page objects.


        """
        self.generator = generator
        self.repo = pywikibot.Site().data_repository()


    def run(self):
        """
        Starts the robot.
        """
        wdregex = u'\s*\|\s*wikidata\s*=\s*(Q\d+)'
        rkdimagesregex = u'\{\{RKDimages\|(\d+)(\||\})'

        for filepage in self.generator:
            pywikibot.output(u'Working on %s' % (filepage.title(),))
            text = filepage.get()
            wdmatch = re.search(wdregex, text)
            if not wdmatch:
                pywikibot.output(u'Wikidata regex did not match, skipping')
                continue

            rkdimagesmatch = re.search(rkdimagesregex, text)
            if not rkdimagesmatch:
                pywikibot.output(u'RKDimage regex did not match, skipping')
                continue
            rkdid=rkdimagesmatch.group(1)

            paintingitem = pywikibot.ItemPage(self.repo, title=wdmatch.group(1))
            pywikibot.output(u'Working on the item %s' % (paintingitem.title(),))

            # Workaround for bug phab:T145971

            try:
                if not paintingitem.exists():
                    pywikibot.output(u'Item %s does not exist, skipping' % (paintingitem.title(),))
                    continue
                if paintingitem.isRedirectPage():
                    pywikibot.output(u'Item %s is a redirect, skipping' % (paintingitem.title(),))
                    continue
            except pywikibot.IsRedirectPage:
                pywikibot.output(u'Item %s is a redirect, skipping' % (paintingitem.title(),))
                continue

            data = paintingitem.get()
            claims = data.get('claims')

            if 'P350' in claims:
                rkdclaim = claims.get('P350')[0]
                rkdtarget = rkdclaim.getTarget()
                if rkdid == rkdtarget:
                    pywikibot.output(u'Item %s already has a link to same id %s, done' % (paintingitem.title(),rkdid,))
                else:
                    pywikibot.output(u'ERROR: I found a link to %s, but item %s already has a link to DIFFERENT id %s, skipping' % (rkdid,paintingitem.title(),rkdtarget,))
                continue

            print u'I would add it now'


            # Add RKDImages claim
            newclaim = pywikibot.Claim(self.repo, u'P350')
            newclaim.setTarget(rkdid)
            summary=u'Adding RKDimages id %s based on [[:Commons:%s]]' % (rkdid, filepage.title(),)
            pywikibot.output(summary)
            paintingitem.addClaim(newclaim, summary=summary)

            # P143 Q565
            commonsref = pywikibot.Claim(self.repo, u'P143')
            commonsitem = pywikibot.ItemPage(self.repo, u'Q565')
            commonsref.setTarget(commonsitem)
            newclaim.addSources([commonsref])


def main():
    commonssite = pywikibot.Site(u'commons', u'commons')
    templatepage = pywikibot.Page(commonssite, title=u'Template:RKDimages')
    gen = pagegenerators.PreloadingGenerator(pagegenerators.NamespaceFilterPageGenerator(pagegenerators.ReferringPageGenerator(templatepage, onlyTemplateInclusion=True), 6))

    rkdimagesImporter=RKDImagesImporter(gen)
    rkdimagesImporter.run()

    #for page in gen:
    #    print page.title()

    # for (paintingitem, rkdid) in toDeprecateGenerator():
    #     rkdDeprecate(paintingitem, rkdid)
    

if __name__ == "__main__":
    main()
