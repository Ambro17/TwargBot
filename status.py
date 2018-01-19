# -*- coding: utf-8 -*-
import logging

import requests


class MinimalStatus(object):
    """ Wrapper class of tweepy Status class for easier handling. """

    def __init__(self, status_obj):
        self._status = status_obj
        self.id_str = status_obj.id_str
        self.author = status_obj.author
        self.text = status_obj.full_text
        self.entities = status_obj.entities
        self.extended_entities = status_obj.extended_entities if hasattr(status_obj, "extended_entities") else None
        self.created_at = status_obj.created_at
        self.favorited = status_obj.favorite_count
        self.retweets = status_obj.retweet_count
        # para posts self.ups, self.downs, self.upvote_ratio

    def has_media(self):
        return "media" in self._status._json["entities"].keys()

    def has_extended_media(self):
        return "extended_entities" in self._status._json.keys()

    def get_entities(self):
        return self.user_mentions(), self.urls()

    def hashtags(self):
        return ['#'+_hashtag["text"] for _hashtag in self.entities["hashtags"]]

    def user_mentions(self):
        alist = []
        for mention in self.entities["user_mentions"]:
            (full_name, screen_name) = mention["name"], mention["screen_name"]
            alist.append((full_name, screen_name))
        return alist

    def urls(self, unshorten = True):
        urls = [url_descriptor['url'] for url_descriptor in self.entities["urls"]]
        if unshorten:
            urls = list(map(self.unshorten_url, urls))
        return urls

    def _get_url_from(self, media_desc):
        type = media_desc["type"]

        if   type == "photo":
            return media_desc["media_url_https"]
        elif type == "video":
            return media_desc["video_info"]["variants"][0]["url"]
        elif type == "animated_gif":
            return media_desc["video_info"]["variants"][0]["url"]
        else:
            raise KeyError

    def get_all_media(self):
        return self.images(), self.videos(), self.gifs()

    def get_media(self, type_):
        media_list = [] # resolves to false with __bool__ method
        if self.has_media():
            for media_descriptor in self.extended_entities["media"]:
                if media_descriptor["type"] == type_:
                    url = self._get_url_from(media_descriptor)
                    media_list.append(url)
        return media_list

    def images(self):
        return self.get_media("photo")

    def videos(self):
        return self.get_media("video")

    def gifs(self):
        return self.get_media("animated_gif")

    def author_tuple(self):
        return (self.author.name, self.author.screen_name )

    def author_profile_link(self):
        return f'https://twitter.com/{self.author.screen_name}'

    def unshorten_url(self, a_url):
        return requests.head(a_url, allow_redirects=True).url

    def tweet_link(self):
        return f"https://twitter.com/statuses/{self.id_str}"