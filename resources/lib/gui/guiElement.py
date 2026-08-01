# -*- coding: utf-8 -*-

class cGuiElement:
    def __init__(self, title, site, function):
        self.title = title
        self.site = site
        self.function = function
        self.media_type = 'video'
        self.thumbnail = ''
        self.description = ''
        self.tvshow_title = ''
        self.season = 1
        self.episode = 1

    def setMediaType(self, media_type):
        self.media_type = media_type

    def setThumbnail(self, thumbnail):
        self.thumbnail = thumbnail

    def setDescription(self, description):
        self.description = description

    def setTVShowTitle(self, tvshow_title):
        self.tvshow_title = tvshow_title

    def setSeason(self, season):
        self.season = season

    def setEpisode(self, episode):
        self.episode = episode

    def __repr__(self):
        return f"<GuiElement title='{self.title}' function='{self.function}' thumb='{self.thumbnail}'>"
