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
import json
import datetime
import time

class WebUmeniaArtistsImporterBot:
    """
    A bot to enrich humans on Wikidata
    """
    def __init__(self, create=False):
        """
        Arguments:
            * generator    - A generator that yields ItemPage objects.

        """
        self.generator = self.getWebUmeniaGenerator()
        self.webumeniaArtists = self.webumeniaArtistsOnWikidata()
        self.repo = pywikibot.Site().data_repository()
        self.create = create

    def getWebUmeniaGenerator(self):
        """
        Generator to return Web Umenia painters

        yields the json as returned by the Elasticsearch API
        """

        baseSearchUrl = 'https://www.webumenia.sk/api/authorities_sk/_search?q=role:maliar&from=%s&size=%s'
        size = 100
        i = 0
        session = requests.Session()
        #session.auth = ('', '') set in your .netrc file, see https://www.labkey.org/Documentation/wiki-page.view?name=netrc

        while True:
            searchUrl = baseSearchUrl % (i, size)
            page = session.get(searchUrl)
            if not page.json().get(u'hits').get(u'hits'):
                # We're at the end, return
                return
            for bigitem in page.json().get(u'hits').get(u'hits'):
                item = bigitem.get(u'_source')
                yield item
            i = i + size

    def webumeniaArtistsOnWikidata(self):
        '''
        Just return all the Web Umenia people as a dict
        :return: Dict
        '''
        result = {}
        query = u'SELECT ?item ?id WHERE { ?item wdt:P4887 ?id . ?item wdt:P31 wd:Q5 }'
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[resultitem.get('id')] = qid
        return result

    def run(self):
        """
        Starts the robot.
        """
        for itemjson in self.generator:
            self.processArtist(itemjson)

    def processArtist(self, itemjson):
        """

        :param itemjson:
        :return:
        """
        #print (json.dumps(itemjson, sort_keys=True, indent=4, separators=(',', ': ')))
        artistid = itemjson.get(u'identifier')
        artistItem = None
        if artistid in self.webumeniaArtists:
            artistTitle = self.webumeniaArtists.get(artistid)
            artistItem = pywikibot.ItemPage(self.repo, title=artistTitle)
        elif self.create and itemjson.get(u'items_count') > 0:
            artistItem = self.createArtist(itemjson)

        if artistItem:
            pywikibot.output(u'Working on %s based on https://www.webumenia.sk/autor/%s' % (artistItem.title(),
                                                                                            artistid))
            self.expandArtist(artistItem, itemjson)

    def createArtist(self, itemjson):
        """

        :param itemjson:
        :return:
        """
        langs = [u'cs', u'de', u'en', u'es', u'fr', u'nl', u'sk']

        data = {'labels': {},
                'aliases': {},
                }

        (label, aliases) = self.getLabels(itemjson)

        for lang in langs:
            data['labels'][lang] = {'language': lang, 'value': label}

        if aliases:
            for lang in langs:
                data['aliases'][lang]=[]
                for alias in aliases:
                    data['aliases'][lang].append({'language': lang, 'value': alias})

        print (data)

        webumeniaid = '%s' % (itemjson.get('identifier'),)

        summary = 'Creating item based on https://www.webumenia.sk/autor/%s' % (webumeniaid,)

        identification = {}
        pywikibot.output(summary)

        # No need for duplicate checking
        result = self.repo.editEntity(identification, data, summary=summary)
        artistTitle = result.get('entity').get('id')

        # Wikidata is sometimes lagging. Wait for 10 seconds before trying to actually use the item
        time.sleep(10)

        artistItem = pywikibot.ItemPage(self.repo, title=artistTitle)

        # Add to self.artworkIds so that we don't create dupes
        self.webumeniaArtists[webumeniaid]=artistTitle

        # Add human
        humanitem = pywikibot.ItemPage(self.repo,u'Q5')
        instanceclaim = pywikibot.Claim(self.repo, u'P31')
        instanceclaim.setTarget(humanitem)
        artistItem.addClaim(instanceclaim)

        # Add the id to the item so we can get back to it later
        newclaim = pywikibot.Claim(self.repo, u'P4887')
        newclaim.setTarget(webumeniaid)
        pywikibot.output('Adding new Webumenia creator ID claim to %s' % artistItem)
        artistItem.addClaim(newclaim)

        # Force an update so everything is available for the next step
        artistItem.get(force=True)

        return artistItem

    def getLabels(self, itemjson):
        """
        Get the labels: Prefered one and the aliases
        :param itemjson:
        :return:
        """
        label = itemjson.get('name')
        if u',' in label:
            (surname, sep, firstname) = label.partition(u',')
            label = u'%s %s' % (firstname.strip(), surname.strip(),)

        aliases = []
        for alternative_name in itemjson.get(u'alternative_name'):
            name = alternative_name
            if u',' in name:
                (surname, sep, firstname) = name.partition(u',')
                name = u'%s %s' % (firstname.strip(), surname.strip(),)
            aliases.append(name)
        return (label, aliases)

    def expandArtist(self, artistItem, itemjson):
        """

        :param itemjson:
        :return:
        """
        (label, aliases) = self.getLabels(itemjson)
        self.updateLabels(artistItem, label, itemjson.get(u'identifier'))

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

    def updateLabels(self, item, prefLabel, webumeniaid):
        """
        Update the Wikidata labels on the item based on prefLabel
        """
        data = item.get()
        wdlabels = data.get('labels')
        # The item doesn't have a label in my languages. Let's fix that!
        mylangs = [u'cs', u'de', u'en', u'es', u'fr', u'nl', u'sk']

        labelschanged = 0
        for mylang in mylangs:
            if not wdlabels.get(mylang):
                wdlabels[mylang] = prefLabel
                labelschanged = labelschanged + 1

        if labelschanged:
            summary = u'Added missing labels in %s languages based on Webumenia creator ID %s' % (labelschanged, webumeniaid)
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
        page = requests.get(refurl, verify=False) # Getting an incorrect certificate here

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
        """
        Helper function to add a statement
        """
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

    artistsBot = WebUmeniaArtistsImporterBot(create=create)
    artistsBot.run()


if __name__ == "__main__":
    main()
