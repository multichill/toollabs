#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Staatliche Museen zu Berlin to Wikidata based on some CSV files we got


"""
import artdatabot
import pywikibot
import requests
import json
import pywikibot.data.sparql
import re
import csv
import random
from pathlib import Path

def getWorksFromCsv():
    """
    Get the works from the CSV files.
    :param filter: Dict for some simple filtering
    :return: Yield the csv entries
    """
    dir = str(Path.home()) + '/SMB/'
    files = [ 'obj_ifg__teil1.csv', 'obj_ifg__teil2.csv', 'obj_ifg__teil3.csv']

    for filename in files:
        fullfilename = dir + filename
        with open(fullfilename) as crapcsvfile:
            # Yes, I'm really using a regex to parse an csv file. The file is complete crap
            regex = '^"(?P<id>\d+),""(?P<identnr>[^\"]*)"",""(?P<titel>[^\"]*)"",""(?P<beteiligte>[^\"]*)"",""(?P<bereich>[^\"]*)"",""(?P<matTech>[^\"]*)"",""(?P<objekttyp>[^\"]*)"",""(?P<datierung>[^\"]*)"""(?P<junk>[^\"]*)$'
            for match in re.finditer(regex, crapcsvfile.read(), flags=re.M):
                yield match.groupdict()
            #reader = csv.DictReader(csvfile)
            #for row in reader:
            #    yield row


def getSMBGenerator(collectioninfo):
    """
    Generator to return SMB paintings for a specific collection
    """
    #mediumstats = {} # Temp

    painting_types = ['Gemälde', 'Malerei', 'Malerei/Gemälde']
    for workinfo in getWorksFromCsv():
        metadata = {}
        #print (workinfo)
        # Check if it's a painting
        if workinfo.get('objekttyp') not in painting_types:
            continue
        metadata['instanceofqid'] = 'Q3305213'
        # And check if we're working on the right collection
        if workinfo.get('bereich') != collectioninfo.get('collectioncode'):
            continue
        metadata['collectionqid'] = collectioninfo['collectionqid']
        metadata['collectionshort'] = collectioninfo['collectionshort']
        metadata['locationqid'] = collectioninfo['locationqid']
        # Only use this if I create new items.
        metadata['idrefurl'] = 'https://fragdenstaat.de/anfrage/inventar-der-staatlichen-museen-zu-berlin/#nachricht-607708'

        title = workinfo.get('titel').strip()

        if len(title) > 220:
            title = title[0:200]
        metadata['title'] = { 'de' : title,
                              }

        # Get the SMB-digital ID (P8923)
        metadata['artworkid'] = '%s' % (workinfo.get('id'),)
        metadata['artworkidpid'] = 'P8923'
        metadata['url'] = 'http://www.smb-digital.de/eMuseumPlus?service=ExternalInterface&objectId=%s' % (workinfo.get('id'),)

        # I had one item with missing identifier, wonder if it shows up here too
        metadata['idpid'] = 'P217'
        if not workinfo.get('identnr'):
            # Few rare items without an inventory number, just skip them
            print (workinfo)
            print('The inventory number (identnr) is missing on %s' % (metadata.get('url'),))
            continue
        metadata['id'] = workinfo.get('identnr')

        name = workinfo.get('beteiligte')

        if u',' in name:
            (surname, sep, firstname) = name.partition(u',')
            name = '%s %s' % (firstname.strip(), surname.strip(),)
        metadata['creatorname'] = name

        print (workinfo.get('bereich'))

        if workinfo.get('bereich') == 'GGVerlust':
            metadata['description'] = { 'en' : '%s by %s' % ('lost painting', metadata.get('creatorname'),),
                                        }
        else:
            metadata['description'] = { u'de' : u'%s von %s' % (u'Gemälde', metadata.get('creatorname'),),
                                        u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }

        # Try to extract the date
        # Let's see if we can extract some dates. Json-ld is provided, but doesn't have circa and the likes
        datestring = workinfo.get('datierung').strip().lower()
        if datestring:
            dateregex = '^(\d\d\d\d)$'
            datecircaregex = '^um\s*(\d\d\d\d)$'
            periodregex = '^(\d\d\d\d)\s*[\/-]\s*(\d\d\d\d)$'
            circaperiodregex = '^um\s*(\d\d\d\d)\s*[\/-]\s*(\d\d\d\d)$'
            shortperiodregex = '^(\d\d)(\d\d)\s*[\/-]\s*(\d\d)$'
            circashortperiodregex = '^um\s*(\d\d)(\d\d)\s*[\/-]\s*(\d\d)$'

            datematch = re.match(dateregex, datestring)
            datecircamatch = re.search(datecircaregex, datestring)
            periodmatch = re.search(periodregex, datestring)
            circaperiodmatch = re.search(circaperiodregex, datestring)
            shortperiodmatch = re.search(shortperiodregex, datestring)
            circashortperiodmatch = re.search(circashortperiodregex, datestring)

            if datematch:
                metadata['inception'] = int(datematch.group(1).strip())
            elif datecircamatch:
                metadata['inception'] = int(datecircamatch.group(1).strip())
                metadata['inceptioncirca'] = True
            elif periodmatch:
                metadata['inceptionstart'] = int(periodmatch.group(1))
                metadata['inceptionend'] = int(periodmatch.group(2))
            elif circaperiodmatch:
                metadata['inceptionstart'] = int(circaperiodmatch.group(1))
                metadata['inceptionend'] = int(circaperiodmatch.group(2))
                metadata['inceptioncirca'] = True
            elif shortperiodmatch:
                metadata['inceptionstart'] = int('%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(2),))
                metadata['inceptionend'] = int('%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(3),))
            elif circashortperiodmatch:
                metadata['inceptionstart'] = int('%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(2),))
                metadata['inceptionend'] = int('%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(3),))
                metadata['inceptioncirca'] = True
            else:
                print ('Could not parse date: "%s"' % (datestring,))

        mediumstring = workinfo.get('matTech').strip().lower()
        if mediumstring:

            mediums = { 'öl auf leinwand' : 'oil on canvas',
                        'öl auf leinwand, ölhaltiges bindemittel auf textilem bildträger' : 'oil on canvas',
                        'öl auf holz' : 'oil on wood panel',
                        #'öl auf pappe' : 'oil on cardboard',
                        'öl auf leinwand, oil on canvas' : 'oil on canvas',
                        'öl auf leinwand, ölhaltiges bindemittel auf textilem bildträger, oil on canvas' : 'oil on canvas',
                        'öl auf eichenholz' : 'oil on oak panel',
                        'eichenholz, eichenholz' : 'paint on wood panel',
                        'leinwand, leinwand' : 'paint on canvas',
                        'pappelholz, pappelholz' : 'paint on poplar panel',
                        'leinwand, leinwand, ölfarbe' : 'oil on canvas',
                        'lindenholz, lindenholz' : 'paint on lime panel',
                        'kupfer, kupfer' : 'paint on copper',
                        'öl auf leinwand, leinwand, ölfarbe' : 'oil on canvas',
                        'leinwand, öl auf leinwand' : 'oil on canvas',
                        'nadelholz, nadelholz' : 'paint on wood panel',
                        'holz, holz' : 'paint on wood panel',
                        'tannenholz, tannenholz' : 'paint on fir panel',
                        'rotbuchenholz, rotbuchenholz' : 'paint on wood panel',
                        'leinwand, ölfarbe, leinwand' : 'oil on canvas',
                        'fichtenholz, fichtenholz' : 'paint on wood panel',
                        'nußbaumholz, nußbaumholz' : 'paint on walnut panel',
                        }
            if mediumstring in mediums:
                metadata['medium'] = mediums.get(mediumstring)
            else:
                print('Unable to match %s to a medium' % (mediumstring,))
                #if mediumstring not in mediumstats:
                #    mediumstats[mediumstring] = 0
                #mediumstats[mediumstring] +=1
        yield metadata
    #for mediumstring in sorted(mediumstats, key=mediumstats.get, reverse=True)[0:100]:
    #    print ('%s - %s' % (mediumstring, mediumstats.get(mediumstring)))

def processCollection(collectioninfo, dryrun=False, create=False):

    dictGen = getSMBGenerator(collectioninfo)

    if dryrun:
        for painting in dictGen:
            print (painting)
    else:
        artDataBot = artdatabot.ArtDataBot(dictGen, create=create)
        artDataBot.run()
    
def main(*args):
    collectioncode = None
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-collectioncode:'):
            if len(arg) == 16:
                collectioncode = pywikibot.input(
                    'Please enter the collectioncode you want to work on:')
            else:
                collectioncode = arg[16:]
        elif arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True

    painting_types = ['Gemälde', 'Malerei', 'Malerei/Gemälde']
    collections = {
        'GGFremdbesitz' : { 'name' : 'Gemäldegalerie - owned my someone else',
                        'collectioncode' : 'GGFremdbesitz',
                        'collectionqid' : 'Q165631',
                        'collectionshort' : 'GG',
                        'locationqid' : 'Q165631',
                        }, # 129, not owned by Gemäldegalerie
        'GGLeihnahmen' : { 'name' : 'Gemäldegalerie - loans',
                        'collectioncode' : 'GGLeihnahmen',
                        'collectionqid' : 'Q165631',
                        'collectionshort' : 'GG',
                        'locationqid' : 'Q165631',
                        }, # 67, loans at the Gemäldegalerie
        'GGMalerei' : { 'name' : 'Gemäldegalerie - main collection',
                        'collectioncode' : 'GGMalerei',
                        'collectionqid' : 'Q165631',
                        'collectionshort' : 'GG',
                        'locationqid' : 'Q165631',
                        }, # 2737, main collection Gemäldegalerie
        'GGVerlust' : { 'name' : 'Gemäldegalerie - lost works',
                        'collectioncode' : 'GGVerlust',
                        'collectionqid' : 'Q165631',
                        'collectionshort' : 'GG',
                        'locationqid' : 'Q165631',
                        },# 561, works lost by Gemäldegalerie mostly in 1945
        'NGAlteNationalgalerie' : { 'name' : 'Alte Nationalgalerie - main collection',
                                    'collectioncode' : 'NGAlteNationalgalerie',
                                    'collectionqid' : 'Q162111',
                                    'collectionshort' : 'NG',
                                    'locationqid' : 'Q162111',
                                    }, # 1900, main collection Alte Nationalgalerie
        'NGHamburgerBahnhofMuseumfurGegenwart' : { 'name' : 'Hamburger Bahnhof - main collection',
                                    'collectioncode' : 'NGHamburgerBahnhofMuseumfurGegenwart',
                                    'collectionqid' : 'Q584756',
                                    'collectionshort' : 'NGHB',
                                    'locationqid' : 'Q584756',
                                    }, # 155, only small part of the collection?
        'NGMuseumBerggruen' : { 'name' : 'Berggruen Museum',
                                'collectioncode' : 'NGMuseumBerggruen',
                                'collectionqid' : 'Q641630',
                                'collectionshort' : 'Berggruen',
                                'locationqid' : 'Q641630',
                                }, # 45, Berggruen Museum
        'NGNeueNationalgalerie' : { 'name' : 'Neue Nationalgalerie - main collection',
                                    'collectioncode' : 'NGNeueNationalgalerie',
                                    'collectionqid' : 'Q32659772',
                                    'collectionshort' : 'NNG',
                                    'locationqid' : 'Q32659772',
                                    }, # 1795, main collection Neue Nationalgalerie
        'NGSammlungScharfGerstenberg' : { 'name' : 'Scharf-Gerstenberg Collection',
                                    'collectioncode' : 'NGSammlungScharfGerstenberg',
                                    'collectionqid' : 'Q322010',
                                    'collectionshort' : 'NGSG',
                                    'locationqid' : 'Q322010',
                                    }, # NGSammlungScharfGerstenberg # 26,
        # NGehemSammlung # 1201, former collection (Alte) Nationalgalerie? It's a mess and missing inventory numbers
    }

    if dryrun and not collectioncode:
        i = 0
        bereich = {}
        objekttyp = {}
        for work in getWorksFromCsv():
            if work.get('objekttyp'):
                if work.get('objekttyp') not in objekttyp:
                    objekttyp[work.get('objekttyp')] = 0
                objekttyp[work.get('objekttyp')] += 1

            if work.get('objekttyp') in painting_types:
                i +=1
                if work.get('bereich'):
                    if work.get('bereich') not in bereich:
                        bereich[work.get('bereich')] = 0
                    bereich[work.get('bereich')] += 1
                if work.get('bereich')=='NGAlteNationalgalerie':


                    for field in work:
                        print ('* %s - %s' % (field, work.get(field)))
                    #print (work)
            #time.sleep(1)
        print(i)

        for objekttypname in sorted(objekttyp):
            print ('* %s - %s' % (objekttypname, objekttyp.get(objekttypname) ))

        for beriechname in sorted(bereich):
            print ('* %s - %s' % (beriechname, bereich.get(beriechname) ))

        #print (bereich)
        return

    if collectioncode:
        if collectioncode not in collections.keys():
            pywikibot.output('%s is not a valid collectioncode!' % (collectioncode,))
            return
        processCollection(collections[collectioncode], dryrun=dryrun, create=create)
    else:
        collectionlist = list(collections.keys())
        random.shuffle(collectionlist) # Different order every time we run
        for collectioncode in collectionlist:
            processCollection(collections[collectioncode], dryrun=dryrun, create=create)


if __name__ == "__main__":
    main()
