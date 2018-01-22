# -*- coding: utf-8 -*-
import re
from urllib.parse import urlparse
from imgur import Imgur

class RedditFormatter():
    FOOTER_TEMPLATE = (
        "[Tweet-Citado]({tweet_link})" 
        " | [Source](https://github.com/Ambro17/TwitterBot)" 
        " | [Feedback](https://docs.google.com/forms/d/e/1FAIpQLSd5MkOrULTiVjjFWCqAXkJFvVU034vE44l19ot72rxYqE096Q/viewform)"
        " | Desarrollado en 🇦🇷 "
                       )
    REDDIT_BREAK = "\n\n"
    BLANK_LINE = "\n\n &nbsp; \n\n"
    COMMENT_TEMPLATE = (
            BLANK_LINE + "{author_data}" + REDDIT_BREAK + 
            "{message}" + REDDIT_BREAK +
             "{rt_and_favs}"+ BLANK_LINE +
            "{media_data}" + BLANK_LINE + 
            "{signature}"
    )

    TW_SHORT_URL = re.compile("(https?://t.co/[a-zA-Z0-9]*)")

    def format(self, status):
        """Given a status object it creates a reddit comment with the tweet.

        Enriches urls, mentions, adds author and favs
         * escape hashtags
         * enrich user mentions with link to profile, urls with nice link
         * post media below
         * transforms to reddit quote
        """
        author_data = self.author_data(status)
        message = self.parse_message(status)
        rt_and_favs = self.meta_tweet(status)
        media_data = self.format_media(status)
        signature = self.format_signature(status)
        formatted_tweet = self.COMMENT_TEMPLATE.format(
            author_data=author_data,
            message=message,
            rt_and_favs=rt_and_favs,
            media_data=media_data,
            signature=signature
        )
        return formatted_tweet

    def author_data(self, status):
        # r-edit author, quote it
        (full_name, screen_name) = status.author_tuple()
        author_info = f"[{full_name} @{screen_name}](https://twitter.com/{screen_name})"
        return self.quote(author_info)

    def parse_message(self, status):
        self.decorate_hashtags(status)
        self.enrich_user_mentions(status)
        self.enrich_urls(status)
        self.clean_hidden_media_urls(status)
        quoted_message = self.quote_message(status)
        return quoted_message

    def meta_tweet(self, status):
        rt, favs = status.retweets, status.favorited
        return self.quote(f"♻️ {rt} ❤️ {favs}")
    
    def format_media(self, status):
        images, video, gif = status.get_all_media()
        text = ""
        if images:
            if len(images) == 1:
                text += 'Imagen del tweet: ' + self.reddit_format_link(
                    "Imagen", images[0])
            else:
                album_link = self.create_imgur_album(images)
                album_formatted = self.reddit_format_link("Album", album_link)
                text += 'Imagenes del tweet: ' + album_formatted
        elif video:
            text += 'Video del tweet: ' + self.reddit_format_link("Video",
                                                                  video[0])
        elif gif:
            text += 'Gif del tweet: ' + self.reddit_format_link("Gif", gif[0])

        return text

    def create_imgur_album(self, image_urls):
        album_link = Imgur().upload_images_to_album(image_urls)
        return album_link


    def format_signature(self, status):
        sign_text = self.FOOTER_TEMPLATE.format(tweet_link=status.tweet_link())
        return self.script(sign_text)

    def clean_hidden_media_urls(self, status):
        # replace hidden media urls and remove double spaces
        for match in self.TW_SHORT_URL.finditer(status.text):
            status.text = status.text.replace(match.group(0), "")
        status.text = status.text.replace("  ", " ")

    def quote_message(self, status):
        quoted_message = ""
        for line in status.text.split(self.REDDIT_BREAK):
            if line:
                # recover splitted reddit line break and quote the line
                quoted_message += f"{self.REDDIT_BREAK}>{line}"

        return quoted_message

    def decorate_hashtags(self, status):
        for jash in set(status.hashtags()):
            decorated_jash = self.italics('\\' + jash)
            status.text = status.text.replace(jash, decorated_jash)

    def enrich_user_mentions(self, status):
        for user in status.user_mentions():
            _, screen_name = user
            user_mention = '@' + screen_name
            link_to_profile = f"https://twitter.com/{screen_name}"
            reddit_link = self.reddit_format_link(user_mention,
                                                  link_to_profile)
            status.text = status.text.replace(user_mention,
                                              reddit_link)  # Funciona a los tumbos si algun boludo menciona a un user dos veces en el mismo tweet

    def enrich_urls(self, status):
        for url in status.urls(unshorten=False):
            full_url = status.unshorten_url(url)
            domain = urlparse(full_url)[1]
            enriched_url = f"[{domain}]({full_url})"
            status.text = status.text.replace(url, enriched_url)


    def reddit_format_links(self, urllist):
        a = [self.reddit_format_link(f"Imagen {i+1}", image_url) for i, image_url in enumerate(urllist)]
        return a

    def reddit_format_link(self, visible_name, hidden_link):
        return f"[{visible_name}]({hidden_link})"  # formats two given strings into [visible_name](hidden_link)

    def quote(self, astr):
        return f">{astr}"

    def bold(self, astr):
        return f"**{astr}**"

    def italics(self, astr):
        return f"*{astr}*"

    def script(self, astr, level=1):
        mapped_list = [f"{'^'*level}{word}" for word in astr.split()]
        rejoined_str = ' '.join(mapped_list)
        return rejoined_str