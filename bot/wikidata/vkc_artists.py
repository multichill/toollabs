#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Vlaamse Kunstcollectie creator bot. Zo een superset moeten zijn dus meeste matches


"""
import pywikibot
import creatorbot


def main():
    inputfilename = u'VKC-artists-anonymous-completed.csv'
    outputfilename = u'vkc_artist_completed.csv'
    outputpagename = u'User:Multichill/Vlaamse Kunstcollectie creators'
    museumName = u'Vlaamse Kunstcollectiet'
    museumItemTitle = u'Q2542010'
    
        
    painterGen = creatorbot.getPainterGenerator(inputfilename)

    #for painter in painterGen:
    #    print painter
    
    creatorBot = creatorbot.CreatorBot(painterGen, outputfilename, outputpagename, museumName, museumItemTitle, create=False)
    creatorBot.run()
    
    

if __name__ == "__main__":
    main()
