import praw
import re
import tweepy
import sqlite3
import config

SUBREDDIT = "argentina"
HEADER = "^(Hola, Soy TwargBot y existo para comentar con el texto del twitt linkeado) \n\n\n\n "
FOOTER = "\n\n &nbsp; \n\n^[Source](https://github.com/Ambro17/TwitterBot) ^| ^[Creador](https://github.com/Ambro17)"
# DATABASE Initialization
conn = sqlite3.connect('replies5.db')
c = conn.cursor()
# Reddit API initialization
bot = praw.Reddit('TwArgINI')
subreddit = bot.subreddit(SUBREDDIT)


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


def quote(text):
    return ">"+text


def comment_post(apost):
    print("Preparandome para comentar..")
    status_id = extract_status_id(apost.url)
    status = twitter.get_status(status_id, tweet_mode="extended")
    tweet = status.full_text
    print("El tweet es: \n" + tweet)
    detailed_tweet = HEADER + quote(tweet) + FOOTER
    apost.reply(detailed_tweet)
    print("Comenté  con éxito.")
    add_reply_to_db(apost)


def there_is_a_match(arg):
    return arg is not None


def replied_db(post):
    c.execute("SELECT * FROM replies5 WHERE EXISTS (SELECT 1 FROM replies5 WHERE post_id = (?))", (post.id,))
    return there_is_a_match(c.fetchone())


def on_visited_db(post):
    c.execute("SELECT * FROM visited WHERE EXISTS (SELECT 1 FROM visited WHERE post_id = (?))", (post.id,))
    return there_is_a_match(c.fetchone())


def add_reply_to_db(post):
    if not replied_db(post):
        # post_id text, author text, url text, title text
        c.execute('INSERT INTO replies5 VALUES (?,?,?,?)', (post.id, str(post.author), post.url, post.title))
    conn.commit()


def add_to_visited(post):
    if not on_visited_db(post):
        c.execute('INSERT INTO visited VALUES (?,?,?,?)', (post.id, str(post.author),post.url,post.title))
    conn.commit()


def buscar_tweets():
    print("Buscando tweets...")
    for i, post in enumerate(subreddit.new(limit=10)):
        if not on_visited_db(post):
            add_to_visited(post)
            title = post.title
            url = post.url
            print(f"Analizando post {i}: {title}...")
            if is_tweet(post) and not replied_db(post):
                comment_post(post)
                print("Title: ", post.title)
                print("self.url: ", post.url)
                print("----------------------")
            print(f"Fin análisis post {i}")
    conn.close()
    print("Finalizó mi busqueda")


# MAIN
buscar_tweets()

# TODO: execute every X minutes to fetch new posts for replying

