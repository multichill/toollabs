#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from https://www.webumenia.sk
* This will loop over a bunch of collections and for each collection
* Old system: Loop over https://www.webumenia.sk/en/katalog?work_type=maliarstvo&gallery=Slovensk%C3%A1+n%C3%A1rodn%C3%A1+gal%C3%A9ria%2C+SNG
* New system: Ask the api at http://api.webumenia.sk ( https://github.com/SlovakNationalGallery/web-umenia-2/wiki/ElasticSearch-Public-API )
* Grab individual paintings like https://www.webumenia.sk/en/dielo/SVK:SNG.O_184 as items in the API
Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re
import csv
import datetime
import time

class ArtcenterArtistsImporterBot:
    """
    A bot to enrich humans on Wikidata
    """
    def __init__(self, create=False):
        """
        Arguments:
            * generator    - A generator that yields ItemPage objects.

        """
        self.generator = self.getArtcenterGenerator()
        self.artcenterArtists = self.israelArtcenterArtistsOnWikidata()
        # Do something with artwork list on Wikipedia and the xls I got?
        self.repo = pywikibot.Site().data_repository()
        self.create = create

    def getArtcenterGenerator(self):
        """
        Generator to return Web Umenia painters

        yields the json as returned by the Elasticsearch API
        """

        with open('/home/mdammers/temp/israel_artists.csv', 'rb') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                result = {}
                result[u'itemnum'] = unicode(row.get('itemnum'), u'utf-8')
                result[u'synopsis_heb'] = unicode(row.get('synopsis_heb'), u'utf-8')
                result[u'synopsis_eng'] = unicode(row.get('synopsis_eng'), u'utf-8')
                # Could try to exctract stuff here
                #pywikibot.output (result)
                if int(result[u'itemnum']) > 0:
                    yield result

    def israelArtcenterArtistsOnWikidata(self):
        '''
        Just return all the Information Center for Israeli Art people (and other) as a dict
        :return: Dict
        '''
        result = {}
        query = u'SELECT ?item ?id WHERE { ?item wdt:P1736 ?id }'
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[resultitem.get('id')] = qid
        print result
        return result

    def run(self):
        """
        Starts the robot.
        """
        for artistinfo in self.generator:
            self.processArtist(artistinfo)

    def processArtist(self, artistinfo):
        """
        """

        artistid = artistinfo.get(u'itemnum')
        artistItem = None
        if artistid in self.artcenterArtists:
            artistTitle = self.artcenterArtists.get(artistid)
            artistItem = pywikibot.ItemPage(self.repo, title=artistTitle)
        elif self.create:
            pywikibot.output(u'Trying to establish notability for http://www.imj.org.il/artcenter/newsite/en/?artist=%s' % (artistid,))
            notability = self.getNotability(artistinfo)
            if notability:
                artistItem = self.createArtist(artistinfo, notability)

        if artistItem:
            pywikibot.output(u'Working on %s based on http://www.imj.org.il/artcenter/newsite/en/?artist=%s' % (artistItem.title(),
                                                                                            artistid))
            self.expandArtist(artistItem, artistinfo)

    def getNotability(self, artistinfo):
        """
        See if this artist is notable enough to create
        * If it's notable, return a reason that can be used as summary
        ** It's linked from https://en.wikipedia.org/wiki/List_of_public_art_in_Israel
        ** It has artwork links
        * If it's not notable, return None
        :param artistinfo:
        :return:
        """
        artistid = artistinfo.get(u'itemnum')
        artisturl = u'http://www.imj.org.il/artcenter/newsite/en/?artist=%s' % (artistid,)
        site = pywikibot.Site(u'en', u'wikipedia')
        page = pywikibot.Page(site, title=u'List of public art in Israel')

        if artisturl in page.text:
            return u'Link found on [[:en:List of public art in Israel]]'

        regex = u'\<h5\>\<a href\=\'\/artcenter\/newsite\/en\/gallery\/\?artist\=[^\']+\'\>View artwork'
        aristpage = requests.get(artisturl)
        # Ok, this explains some content encoding issues!!!!!!
        aristpage.encoding = u'utf-8'
        match = re.search(regex, aristpage.text)

        if match:
            return u'Links found to artworks gallery'
        return None


    def createArtist(self, artistinfo, notability):
        """

        :param itemjson:
        :return:
        """
        langs =  [u'ca', u'da', u'de', u'en', u'es', u'fr', u'it', u'nl', u'pt', u'sv']

        data = {'labels': {},
                'aliases': {},
                }

        (enlabel, helabel) = self.getLabels(artistinfo)

        if enlabel:
            for lang in langs:
                data['labels'][lang] = {'language': lang, 'value': enlabel}

        if helabel:
            data['labels'][u'he'] = {'language': u'he', 'value': helabel}

        print (data)

        summary = u'Creating item based on http://www.imj.org.il/artcenter/newsite/en/?artist=%s . %s' % (artistinfo.get(u'itemnum'),
                                                                                                          notability)

        identification = {}
        pywikibot.output(summary)

        # No need for duplicate checking
        result = self.repo.editEntity(identification, data, summary=summary)
        artistTitle = result.get(u'entity').get('id')

        # Wikidata is sometimes lagging. Wait for 10 seconds before trying to actually use the item
        time.sleep(10)

        artistItem = pywikibot.ItemPage(self.repo, title=artistTitle)

        # Add to self.artworkIds so that we don't create dupes
        self.artcenterArtists[artistinfo.get(u'itemnum')]=artistTitle

        # Add human
        humanitem = pywikibot.ItemPage(self.repo,u'Q5')
        instanceclaim = pywikibot.Claim(self.repo, u'P31')
        instanceclaim.setTarget(humanitem)
        artistItem.addClaim(instanceclaim)

        # Add the id to the item so we can get back to it later
        newclaim = pywikibot.Claim(self.repo, u'P1736')
        newclaim.setTarget(artistinfo.get(u'itemnum'))
        pywikibot.output('Adding new Information Center for Israeli Art artist ID claim to %s' % artistItem)
        artistItem.addClaim(newclaim)

        # Force an update so everything is available for the next step
        artistItem.get(force=True)

        return artistItem

    def getLabels(self, artistinfo):
        """
        Get the labels: Prefered one and the aliases
        :param itemjson:
        :return:
        """
        artistid = artistinfo.get(u'itemnum')

        regex = u'\<h2\>\<strong\>([^\<]+)(\n\<br\>)?\<\/strong\>\<\/h2\>'

        enpage = requests.get(u'http://www.imj.org.il/artcenter/newsite/en/?artist=%s' % (artistid,))
        hepage = requests.get(u'http://www.imj.org.il/artcenter/newsite/he/?artist=%s' % (artistid,))

        # Ok, this explains some content encoding issues!!!!!!
        enpage.encoding = u'utf-8'
        hepage.encoding = u'utf-8'

        enmatch = re.search(regex, enpage.text)
        hematch = re.search(regex, hepage.text)

        enlabel = u''
        helabel = u''

        if enmatch:
            enlabel = enmatch.group(1)

        if hematch:
            helabel = hematch.group(1)

        pywikibot.output(enlabel)
        pywikibot.output(helabel)

        return (enlabel, helabel)

    def expandArtist(self, artistItem, artistinfo):
        """

        :param itemjson:
        :return:
        """

        # getLabels hits the website so we only want to do that if something is actually missing
        langs = [u'he', u'ca', u'da', u'de', u'en', u'es', u'fr', u'it', u'nl', u'pt', u'sv']

        data = artistItem.get()
        wdlabels = data.get('labels')

        missinglang = False

        for lang in langs:
            if not wdlabels.get(lang):
                missinglang = True
                break

        if missinglang:
            (enlabel, helabel) = self.getLabels(artistinfo)
            self.updateLabels(artistItem, artistinfo, enlabel, helabel)
        return


        # Reference needed later
        refurl = u'https://www.webumenia.sk/autor/%s' % (itemjson.get(u'identifier'))

        # Add painter claim
        newclaim = self.addItemStatement(artistItem, u'P106', u'Q1028181')
        if newclaim:
            self.addReference(artistItem, newclaim, refurl)

        if itemjson.get(u'sex'):
            if itemjson.get(u'sex')==u'male':
                newclaim = self.addItemStatement(artistItem, u'P21', u'Q6581097')
                if newclaim:
                    self.addReference(artistItem, newclaim, refurl)
            elif itemjson.get(u'sex')==u'female':
                newclaim = self.addItemStatement(artistItem, u'P21', u'Q6581072')
                if newclaim:
                    self.addReference(artistItem, newclaim, refurl)

        data = artistItem.get()
        claims = data.get('claims')
        if (u'P569' not in claims) and (u'P570' not in claims):
            self.addDateOfBirthDeath(artistItem, refurl)

    def updateLabels(self, item, artistinfo, enlabel, helabel):
        """
        Update the Wikidata labels on the item based on prefLabel
        """
        artistid = artistinfo.get(u'itemnum')
        data = item.get()
        wdlabels = data.get('labels')
        # The item doesn't have a label in my languages. Let's fix that!
        mylangs = [u'ca', u'da', u'de', u'en', u'es', u'fr', u'it', u'nl', u'pt', u'sv']

        labelschanged = 0
        for mylang in mylangs:
            if enlabel and not wdlabels.get(mylang):
                wdlabels[mylang] = enlabel
                labelschanged = labelschanged + 1

        if helabel and not wdlabels.get(u'he'):
            wdlabels[u'he'] = helabel
            labelschanged = labelschanged + 1

        if labelschanged:
            summary = u'Added missing labels in %s languages based on Information Center for Israeli Art artist ID %s' % (labelschanged, artistid)
            pywikibot.output(summary)
            try:
                item.editLabels(wdlabels, summary=summary)
            except pywikibot.data.api.APIError:
                pywikibot.output(u'Couldn\'t update the labels, conflicts with another item')
            except pywikibot.exceptions.OtherPageSaveError:
                pywikibot.output(u'Couldn\'t update the labels, conflicts with another item')

    def addDateOfBirthDeath(self, artistItem, refurl):
        '''

        :return:
        '''
        pywikibot.output(u'Getting the page at %s for the date of birth and date of death' % (refurl,))
        page = requests.get(refurl)

        fulldobregex = u'\<span itemprop\=\"birthDate\"\>(\d\d)\.(\d\d)\.(\d\d\d\d)\<\/span\>'
        partdobregex = u'\<span itemprop\=\"birthDate\"\>(\d\d\d\d)\<\/span\>'
        fulldobmatch = re.search(fulldobregex, page.text)
        partdobmatch = re.search(partdobregex, page.text)

        newdob = None
        if fulldobmatch:
            newdob = pywikibot.WbTime( year=int(fulldobmatch.group(3)),
                                       month=int(fulldobmatch.group(2)),
                                       day=int(fulldobmatch.group(1)))
        elif partdobmatch:
            newdob = pywikibot.WbTime( year=int(partdobmatch.group(1)))

        if newdob:
            newclaim = pywikibot.Claim(self.repo, u'P569')
            newclaim.setTarget(newdob)
            artistItem.addClaim(newclaim)
            self.addReference(artistItem, newclaim, refurl)

        fulldodregex = u'\<span itemprop\=\"deathDate\"\>(\d\d)\.(\d\d)\.(\d\d\d\d)\<\/span\>'
        partdodregex = u'\<span itemprop\=\"deathDate\"\>(\d\d\d\d)\<\/span\>'
        fulldodmatch = re.search(fulldodregex, page.text)
        partdodmatch = re.search(partdodregex, page.text)

        newdod = None
        if fulldodmatch:
            newdod = pywikibot.WbTime( year=int(fulldodmatch.group(3)),
                                       month=int(fulldodmatch.group(2)),
                                       day=int(fulldodmatch.group(1)))
        elif partdodmatch:
            newdod = pywikibot.WbTime( year=int(partdodmatch.group(1)))

        if newdod:
            newclaim = pywikibot.Claim(self.repo, u'P570')
            newclaim.setTarget(newdod)
            artistItem.addClaim(newclaim)
            self.addReference(artistItem, newclaim, refurl)

    def addItemStatement(self, item, pid, qid):
        '''
        Helper function to add a statement
        '''
        if not qid:
            return False

        claims = item.get().get('claims')
        if pid in claims:
            return

        newclaim = pywikibot.Claim(self.repo, pid)
        destitem = pywikibot.ItemPage(self.repo, qid)
        newclaim.setTarget(destitem)
        pywikibot.output(u'Adding %s->%s to %s' % (pid, qid, item))
        item.addClaim(newclaim)
        return newclaim

    def addReference(self, item, newclaim, url):
        """
        Add a reference with a retrieval url and todays date
        """
        pywikibot.output('Adding new reference claim to %s' % item)
        statedin = pywikibot.Claim(self.repo, u'P248')
        webumeniaitem = pywikibot.ItemPage(self.repo,u'Q50828580')
        statedin.setTarget(webumeniaitem)
        refurl = pywikibot.Claim(self.repo, u'P854')
        refurl.setTarget(url)
        refdate = pywikibot.Claim(self.repo, u'P813')
        today = datetime.datetime.today()
        date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
        refdate.setTarget(date)
        newclaim.addSources([statedin, refurl, refdate])

def main(*args):
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-create'):
            create = True

    artistsBot = ArtcenterArtistsImporterBot(create=create)
    artistsBot.run()


if __name__ == "__main__":
    main()
