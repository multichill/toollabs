#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
MSK creator bot


"""
import pywikibot
import creatorbot


def main():
    inputfilename = u'msk_artist_completed_2015-12_04.csv'
    outputfilename = u'msk_artist_completed.csv'
    outputpagename = u'User:Multichill/MSK Gent creators'
    museumName = u'MSK Gent'
    museumItemTitle = u'Q2365880'
    
        
    painterGen = creatorbot.getPainterGenerator(inputfilename)

    #for painter in painterGen:
    #    print painter
    
    creatorBot = creatorbot.CreatorBot(painterGen, outputfilename, outputpagename, museumName, museumItemTitle, create=True)
    creatorBot.run()
    
    

if __name__ == "__main__":
    main()
