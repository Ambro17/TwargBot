# -*- coding: utf-8 -*-
import re
import sqlite3
import datetime
import logging
from datetime import datetime as d

import tweepy
import praw

import config
from formatter import RedditFormatter
from status import MinimalStatus


logger = logging.basicConfig(
    filename="twoop-15-enero.log", level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


class TwargBot(object):

    # Tweepy authentication
    auth = tweepy.OAuthHandler(config.API_KEY, config.API_SECRET)
    auth.set_access_token(config.TOKEN, config.TOKEN_SECRET)
    twitterAPI = tweepy.API(auth)

    #  Praw Initialization
    twargbot = praw.Reddit("TwArgINI")

    #  Establish DB connection
    db_connection = sqlite3.connect('posts.db',
                                    detect_types=sqlite3.PARSE_DECLTYPES |
                                    sqlite3.PARSE_COLNAMES)

    # REGEX
    TW_REGEX_URL = re.compile(
        r'https?://twitter.com/[a-zA-Z0-9]+/status/([0-9]+)/*')

    def __init__(self, subreddit="twargbot"):
        self.subreddit = self.twargbot.subreddit(subreddit)
        self.db_cursor = self.db_connection.cursor()
        """"
        self.db_cursor.execute('''CREATE TABLE posts
                               (post_id text, title text, author text,
                               link text,
                               is_tweet integer, date timestamp, subreddit text)''')
        """
        self.db_connection.commit()

    def _get_status_from_twitter_post(self, post):
        status_id = self.get_status_id(post.url)
        status_obj = self.twitterAPI.get_status(
            status_id, tweet_mode="extended")
        return MinimalStatus(status_obj)

    def filter_tweet_posts(self):
        return list(filter(self.new_twitter_post, self.subreddit.new(limit=100)))

    def new_twitter_post(self, post):
        # Determines if a post is a not visited tw post
        return self._is_tweet(post) and not self.visited_db(post)

    def r_edit_tweet(self, status):
        rformatter = RedditFormatter()
        r_edited_tweet = rformatter.format(status)
        return r_edited_tweet

    def comment_post(self, post):
        status = self._get_status_from_twitter_post(post)
        redited_tweet = self.r_edit_tweet(status)
        post.reply(redited_tweet)

    def comment_tweet_posts(self, cant=30):
        for post in self.subreddit.new(limit=cant):
            logger.info(f"Visiting post https://reddit.com/{post.id}")
            if not self.visited_db(post):
                if self._is_tweet(post):
                    self.comment_post(post)
                    self.add_to_db(post, is_tweet=1)
                    logger.info(f"Replied on https://reddit.com/{post.id}")
                else:
                    self.add_to_db(post, is_tweet=0)
            else:
                logger.info(f"Ya visité https://reddit.com/{post.id}")

    def add_to_db(self, post, is_tweet=0):
        now = datetime.datetime.now()
        self.db_cursor.execute("""INSERT INTO posts(
                               post_id, title, author, link, is_tweet, date, subreddit) 
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                               (post.id, post.title, post.author.name,
                                post.url, is_tweet, now,
                                self.subreddit.display_name))
        self.db_connection.commit()

    def visited_db(self, post):
        self.db_cursor.execute("""SELECT * FROM posts WHERE EXISTS 
                               (SELECT 1 FROM posts 
                               WHERE post_id = (?))""", (post.id,))
        return bool(self.db_cursor.fetchone())

    def _is_tweet(self, post):
        return self.TW_REGEX_URL.match(post.url)

    def get_status_id(self, posturl):
        # posturl.split(sep='/')[-1]
        match = self.TW_REGEX_URL.match(posturl)
        return match.group(1)


logger.info(f"\t\t\t\t\t Comencé ejecución a las {d.now()}")

if __name__ == '__main__':
    twargbot = TwargBot('argentina')
    twargbot.comment_tweet_posts()

logger.info(f"\t\t\t\t\t Finalicé ejecución a las {d.now()}")
