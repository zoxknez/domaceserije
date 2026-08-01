# -*- coding: utf-8 -*-
import re

class Logger:
    def info(self, msg):
        print(f"[INFO] {msg}")

    def error(self, msg):
        print(f"[ERROR] {msg}")

logger = Logger()

class cParser:
    @staticmethod
    def parseSingleResult(html, pattern):
        m = re.search(pattern, html, re.DOTALL)
        if m:
            return True, m.group(1)
        return False, ""

    @staticmethod
    def parse(html, pattern):
        res = re.findall(pattern, html, re.DOTALL)
        if res:
            return True, res
        return False, []

    @staticmethod
    def search(pattern, string):
        return bool(re.search(pattern, string, re.IGNORECASE))

class cUtil:
    pass
