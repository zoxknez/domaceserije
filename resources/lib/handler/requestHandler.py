# -*- coding: utf-8 -*-
import urllib.request
import ssl

class cRequestHandler:
    def __init__(self, url, caching=True, ignoreErrors=False, *args, **kwargs):
        self.url = url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def addHeaderEntry(self, key, value):
        self.headers[key] = value

    def request(self):
        try:
            context = ssl._create_unverified_context()
            req = urllib.request.Request(self.url, headers=self.headers)
            with urllib.request.urlopen(req, context=context, timeout=15) as response:
                return response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            return ""
