# -*- coding: utf-8 -*-

class cConfig:
    def __init__(self):
        pass

    def getSetting(self, sName, default=""):
        if 'domain' in sName:
            return "domaceserije.net"
        return default

    def isBlockedHoster(self, sHosterName):
        return [False, sHosterName]
