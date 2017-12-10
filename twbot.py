import praw
import re
import tweepy
import config
import sqlite3

# DATABASE Initialization
conn = sqlite3.connect('replies.db')
c = conn.cursor()

# Reddit API initialization
bot = praw.Reddit('TwArgINI')
subreddit = bot.subreddit('twargbot')


# Twitter API Initialization
auth = tweepy.OAuthHandler(config.API_KEY, config.API_SECRET)
auth.set_access_token(config.TOKEN, config.TOKEN_SECRET)
twitter = tweepy.API(auth)

# Compile regex to match twitter urls
TWITTER_REGEX_URL = re.compile("https://twitter\.com/.*")


def is_tweet(post):
    # si match_obj es distinto de None, significa que la url es la de un tweet
    match_obj = TWITTER_REGEX_URL.match(post.url)
    return there_is_a_match(match_obj)


def extract_status_id(twurl):
    """"
    Dada una url (str) de la forma "<protocol>//<domain>/<user>/<status>/<statusid>"
    obtengo el ultimo elemento del string separado por '/' que resulta ser el <statusid>
    """
    splitted_url = re.split('/', twurl)
    status_id = splitted_url[-1] # obtengo ultimo elemento
    return status_id

def add_reply_to_db(post):
    # añado el id del post a reddit (puedo contestar dos veces el mismo twitt si lo publican dos diferentes)
    if not in_database(post):
        c.execute('INSERT INTO replies VALUES (?)', (post.id,))
    conn.commit()


def comment_post(apost):
    status_id = extract_status_id(apost.url)
    status = twitter.get_status(status_id, tweet_mode="extended")
    tweet = status.full_text
    print("El tweet es: \n" + tweet)
    ## reformatear comentario con detalles
    detailed_tweet = tweet + "\n\n\n^[Creator](www.google.com.ar) ^| ^[Creator](www.google.com.ar)"
    apost.reply(detailed_tweet)
    add_reply_to_db(apost)
    # comentarlo en el post

def there_is_a_match(arg):
    return arg is not None

def in_database(post):
    c.execute("SELECT * FROM replies WHERE EXISTS (SELECT 1 FROM replies WHERE status_id = (?))", (post.id,))
    return there_is_a_match(c.fetchone())


for post in subreddit.new(limit=10):
    title = post.title
    url = post.url
    print("Analizando post..." + post.title)
    # TODO: anadir and not already_visited(post)
    if is_tweet(post) and not in_database(post):
        comment_post(post)
        print("Title: ", post.title)
        print("self.url: ", post.url)
        print("\n*50")
    print("Fin análisis post " + str(post))
conn.close()
# TODO: Format reply with source, Creator
# TODO: cron to execute every even minutes for searching and every  odd minute for replying

