#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Lazy script to check the ports at https://meta.wikimedia.org/wiki/Wikimania_Handbook#Hackathon_requirements

It first lookups the public ip and after that works it way down the list of hostnames and ports.

"""
import socket
import requests

tocheck = [(u'ftp.surfnet.nl', 21), # FTP (21)
           (u'tools-dev.wmflabs.org', 22), # SSH (22)
           (u'mx1001.wikimedia.org', 25), # SMTP (25)
           (u'google-public-dns-a.google.com', 53), # DNS (53)
           (u'www.wikipedia.org', 80), # HTTP (80)
           (u'www.wikipedia.org', 443), # HTTPS (443)
           (u'chat.freenode.org', 6666), # IRC (6666)
           (u'gerrit.wikimedia.org', 29418), # Gerrit 29418
           ]

def getMyPublicIP():
    '''
    Get my public ipaddress and print it
    '''
    page = requests.get(u'https://api.ipify.org')
    print (u'[OK] My public ipaddress is %s (according to api.ipify.org)' % page.text)

def checkConnection(check):
    '''

    :param check:
    :return:
    '''
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    (hostname, port) = check
    try:
        s.connect(check)
        s.send('Wikimedia Hackathon connectivity testing script. It worked\n\n')
        data = s.recv(1024)
        s.close()
        print (u'[OK] The check of %s on port %s was successful' % check)
        return True
    except socket.timeout:
        print (u'[FAILED] The check of %s on port %s failed' % check)
        return False


def main(*args):
    """
    Main function. Grab a generator and pass it to the bot to work on
    """
    getMyPublicIP()
    allchecks = 0
    successchecks = 0
    for check in tocheck:
        allchecks +=1
        checkstatus = checkConnection(check)
        if checkstatus:
            successchecks += 1
    if allchecks==successchecks:
        print (u'All %s checks were successful. Have a good hackathon!' % (allchecks,))
    else:
        print (u'Only %s checks out of %s were successful. Please fix!' % (successchecks, allchecks,))

if __name__ == "__main__":
    main()
