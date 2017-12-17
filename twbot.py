import praw
import tweepy
import re
import sqlite3
import config
import time
import requests
import logging

logger = logging.getLogger(__name__)

SUBREDDIT = "twargbot"
HEADER = "^(Hola, Soy TwargBot y existo para comentar el tweet linkeado y ahorrarte unos clicks) \n\n\n\n "
FOOTER = "\n\n &nbsp; \n\n^[Source](https://github.com/Ambro17/TwitterBot) ^| ^[Creador](https://github.com/Ambro17)"

# DATABASE Initialization
conn = sqlite3.connect('replies5.db')
c = conn.cursor()

# Reddit API initialization
bot = praw.Reddit('TwArgINI')
subreddit = bot.subreddit(SUBREDDIT)
#c.execute("CREATE TABLE visited2 (post_id text, author text, url text, title text)")

# Twitter API Initialization
auth = tweepy.OAuthHandler(config.API_KEY, config.API_SECRET)
auth.set_access_token(config.TOKEN, config.TOKEN_SECRET)
twitter = tweepy.API(auth)

# Compile regex to match twitter urls
TWITTER_REGEX_URL = re.compile("https://twitter\.com/.*")
SHORTENER_URLS = re.compile("(https?:\/\/)(t\.co|bit.ly)(\/[a-zA-Z0-9]*)")


def redir_status(stat):
    return stat in [300, 301, 302, 303, 304, 305, 306, 307, 308]


def unshorten_url(url):
    return requests.head(url, allow_redirects=True).url


def has_shortened_links(atweet):
    return SHORTENER_URLS.search(atweet)


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


def reddit_format_url(bare_url):
    return f"[link]({bare_url})"


def expand_tweet_urls(original_str):
    """
        Si el tweet tiene una shortened url, la reemplazo
        por su full url. Si no, la devuelvo sin modificar
    """
    #matches = SHORTENER_URLS.findall(original_str)
    for match in SHORTENER_URLS.finditer(original_str):
        # for mathcobj in match -- falla porque siempre reemplaza la inmodificada
        short_url = match.group(1)+match.group(2)+match.group(3)
        expanded_url = unshorten_url(short_url)
        formatted_url = reddit_format_url(expanded_url)
        original_str = original_str.replace(short_url, formatted_url)

    return original_str


def parse_tweet(strtweet):
    expanded_tw = expand_tweet_urls(strtweet)
    # paso shurl a full url
    expanded_tw = HEADER + quote(expanded_tw) + FOOTER
    return expanded_tw


def comment_post(apost):
    print("Preparandome para comentar..")
    status_id = extract_status_id(apost.url)
    status = twitter.get_status(status_id, tweet_mode="extended")
    print(vars(status))
    tweet = status.full_text
    print("El tweet que lei del link es: \n" + tweet)
    parsed_tweet = parse_tweet(tweet)
    try:
        apost.reply(parsed_tweet)
        print("Comenté  con éxito.")
        add_to_replied(apost)
        time.sleep(30) # api puta
        print("Sleeping 30 seconds to avoid exceding rate limit")
    except praw.exceptions.APIException as e:
        logger.debug("Couldn't comment on post https://www.reddit.com/{0}".format(apost.id))
        logger.debug(f"APIException: {vars(e)}")


def there_is_a_match(arg):
    return arg is not None


def replied_db(post):
    c.execute("SELECT * FROM replies5 WHERE EXISTS (SELECT 1 FROM replies5 WHERE post_id = (?))", (post.id,))
    return there_is_a_match(c.fetchone())


def on_visited_db(post):
    c.execute("SELECT * FROM visited2 WHERE EXISTS (SELECT 1 FROM visited2 WHERE post_id = (?))", (post.id,))
    return there_is_a_match(c.fetchone())


def add_to_replied(post):
    if not replied_db(post):
        # post_id text, author text, url text, title text
        c.execute('INSERT INTO replies5 VALUES (?,?,?,?)', (post.id, str(post.author), post.url, post.title))
    conn.commit()


def add_to_visited(post):
    if not on_visited_db(post):
        c.execute('INSERT INTO visited2 VALUES (?,?,?,?)', (post.id, str(post.author),post.url,post.title))
    conn.commit()


def buscar_tweets(cant=10):
    print(f"Buscando tweets en /r/{SUBREDDIT}...")
    for i, post in enumerate(subreddit.new(limit=cant)):
        if not on_visited_db(post):
            title = post.title
            print(f"Analizando post {i+1}: {title}...")
            if is_tweet(post) and not replied_db(post):
                comment_post(post)
                print("Title: ", post.title)
                print(f"Link al post: https://www.reddit.com/{post}")
                print("----------------------")
            add_to_visited(post)
            print(f"Fin análisis post {i+1}")
        else:
            print(f"Ya visite el post https://www.reddit.com/{post.id}")
    conn.close()
    print("Finalizó mi busqueda")


# MAIN
buscar_tweets()
# TODO: post tweet with author.
# TODO: execute every X minutes to fetch new posts for replying



