import praw
import re
import tweepy
import config


# Reddit API initialization
bot = praw.Reddit('TwArgINI')
subreddit = bot.subreddit('twargbot')
print("Reddit inicializado")
print(bot.user.me())
# Twitter API Initialization
auth = tweepy.OAuthHandler(config.API_KEY, config.API_SECRET)
auth.set_access_token(config.TOKEN, config.TOKEN_SECRET)
twitter = tweepy.API(auth)

# Compile regex to match twitter urls
TWITTER_REGEX_URL = re.compile("https://twitter\.com/.*")


def is_tweet(post):
    # si match_obj es distinto de None, significa que la url es la de un tweet
    match_obj = TWITTER_REGEX_URL.match(post.url)
    return match_obj is not None


def extract_status_id(twurl):
    """"
    Dada una url (str) de la forma "<protocol>//<domain>/<user>/<status>/<statusid>"
    obtengo el ultimo elemento del string separado por '/' que resulta ser el <statusid>
    """
    splitted_url = re.split('/', twurl)
    status_id = splitted_url[-1] # obtengo ultimo elemento
    return status_id


def comment_post(apost):
    # DEPRECATED: comento contenido del link de twitter // si el twitt debe extenderse, status.full_text else .text
    status_id = extract_status_id(apost.url)
    # DEPRECATED: if es_extended texto =.full_text else texto =.text
    status = twitter.get_status(status_id, tweet_mode="extended")
    tweet = status.full_text
    print("El tweet es: \n" + tweet)
    apost.reply(tweet)
    # comentarlo en el post


for post in subreddit.new(limit=5):
    title = post.title
    url = post.url
    # TODO: anadir and not already_visited(post)
    if is_tweet(post):
        comment_post(post)
        print("Title: ", post.title)
        print("self.url: ", post.url)
        print("---------------------------------\n")

