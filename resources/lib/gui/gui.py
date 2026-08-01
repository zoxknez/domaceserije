# -*- coding: utf-8 -*-
from resources.lib.handler.ParameterHandler import ParameterHandler

class cGui:
    current_items = []

    def __init__(self):
        pass

    def addFolder(self, element, params, is_folder=True, total=0):
        cGui.current_items.append({
            'element': element,
            'params': dict(ParameterHandler._params),
            'is_folder': is_folder
        })

    def setView(self, view_name):
        pass

    def setEndOfDirectory(self, *args):
        pass

    def showKeyBoard(self, sHeading=""):
        return "senke"

    def showInfo(self, *args):
        print("[cGui] Show info called")
