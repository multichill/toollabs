#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import M Leuven stuff. Is maar een bestand


"""
import artdatabot
import pywikibot
import os
import csv



def getMGenerator():
    '''
    Generator that combines 3 csv files and returns dicts
    

    artists = {}
    objectnames = {}
    
    # Open the artists and dump it in a dict id -> qid

    with open('SMAK-creators-completed-2016-01-23.csv', 'rb') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            artists[row.get('creatorId')] = row.get('creatorWikidataPid').replace('http://www.wikidata.org/entity/', '').replace('http://www.wikidata.org/wiki/', '')
    #print artists

    # Open the types
    with open('SMAK-objectnames-20160124.csv', 'rb') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            objectnames[row.get('objectNameId')] = row.get('Wikidata Q')
    #print objectnames
    '''
    foundit=False
    with open('M Leuven enkel notable items - nieuwe URLs.csv', 'rb') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            metadata = {}

            metadata['collectionqid'] = u'Q2362660'
            metadata['collectionshort'] = u'M Leuven'
            metadata['locationqid'] = u'Q2362660'
            
            metadata['id'] = unicode(row.get('object_number'), u'utf-8')
            metadata['idpid'] = u'P217'
            metadata['title'] = { u'nl' : unicode(row.get('title'), u'utf-8') } # Hier iets met Nederlands doen

            # Welcome in URL hell.
            # Data url in the reference
            metadata['refurl'] = unicode(row.get('DataPID'), u'utf-8')
            # The Pid url for described by url
            metadata['describedbyurl'] = unicode(row.get('WorkPID'), u'utf-8')
            # The Pid url for the inventory number reference
            metadata['idrefurl'] = unicode(row.get('WorkPID'), u'utf-8')
            # This shouldn't actually be used
            metadata['url'] = unicode(row.get('WorkPID'), u'utf-8')

            name = unicode(row.get('creator'), u'utf-8')
            # We need to normalize the name
            if u',' in name:
                (surname, sep, firstname) = name.partition(u',')
                name = u'%s %s' % (firstname.strip(), surname.strip(),)
            metadata['creatorname'] = name
            
            metadata['objectname'] = unicode(row.get('object_name'), u'utf-8')               

            if metadata['creatorname'] and metadata['objectname']:
                metadata['description'] = { u'nl' : u'%s van %s' % (metadata['objectname'], metadata['creatorname']) }
                if metadata['objectname']==u'schilderij': 
                    metadata['description']['en'] = u'painting by %s' % (metadata['creatorname'],)
                elif metadata['objectname']==u'beeldhouwwerk': 
                    metadata['description']['en'] = u'sculpture by %s' % (metadata['creatorname'],)
                elif metadata['objectname']==u'kunstwerk': 
                    metadata['description']['en'] = u'work of art by %s' % (metadata['creatorname'],)
                    

            metadata['creatorqid'] = unicode(row.get('creator Q'), u'utf-8')
            metadata['instanceofqid'] = unicode(row.get('objectname Q'), u'utf-8')



            #if row.get('dateIso8601'):
            #    metadata['inception'] = unicode(row.get('dateIso8601'), u'utf-8')

            ## Start with only paintings
            #workwork = [u'olieverfschildering',
            #            #u'beeldhouwwerk',
            #            #u'aquarel',
            #            ]
            #if metadata['objectname'] in workwork:
            #    yield metadata
            ##else:
            # De dubbele regels hebben geen id
            if row.get('Wikidata notability')==u'1':
                if metadata['id']==u'S/67/M':
                    foundit=True
                if foundit:
                    yield metadata
            
        

def main():
    dictGen = getMGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
