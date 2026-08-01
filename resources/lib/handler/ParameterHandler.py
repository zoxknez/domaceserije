# -*- coding: utf-8 -*-

class ParameterHandler:
    _params = {}

    def __init__(self):
        # We start with existing parameters if any set
        pass

    def setParam(self, key, value):
        ParameterHandler._params[key] = value

    def getValue(self, key):
        return ParameterHandler._params.get(key, False)
