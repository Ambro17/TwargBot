import praw
import tweepy
import re
import sqlite3
import config
import time
import requests
import logging

# set up logging instance
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

SUBREDDIT = "argentina"
HEADER = "^(Hola, Soy TwargBot y existo para comentar el tweet linkeado y ahorrarte unos clicks) \n\n\n\n "
FOOTER = "\n\n &nbsp; \n\n^[Source](https://github.com/Ambro17/TwitterBot) ^| " \
         "^[Creador](https://github.com/Ambro17) ^| " \
         "^[Feedback](https://docs.google.com/forms/d/e/1FAIpQLSd5MkOrULTiVjjFWCqAXkJFvVU034vE44l19ot72rxYqE096Q/viewform)"

# DATABASE Initialization
conn = sqlite3.connect('replies5.db')
c = conn.cursor()

# Reddit API initialization
bot = praw.Reddit('TwArgINI')

#c.execute("CREATE TABLE visited3 (post_id text, author text, url text, title text)")

# Twitter API Initialization
auth = tweepy.OAuthHandler(config.API_KEY, config.API_SECRET)
auth.set_access_token(config.TOKEN, config.TOKEN_SECRET)
twitter = tweepy.API(auth)

# Compile regex to match twitter urls
REDDIT_URL = 'https://www.reddit.com/'
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
    logger.debug(f"Intentando extraer status de {twurl}")
    splitted_url = re.split('/', twurl)
    status_id = splitted_url[-1] # obtengo ultimo elemento
    return status_id


def quote(text):
    return ">"+text


def reddit_format_url(bare_url):
    return f"[link]({bare_url})"


def expand_tweet_urls(original_str):
    """
        Si el tweet tiene 'n' shortened urls, las reemplazo
        por su full url, y la agrego el formato de reddit [Visible](Link)
        Si no tiene shortened urls, la devuelvo sin modificar
    """
    for match in SHORTENER_URLS.finditer(original_str):
        short_url = match.group(1)+match.group(2)+match.group(3)
        expanded_url = unshorten_url(short_url)
        formatted_url = reddit_format_url(expanded_url)
        original_str = original_str.replace(short_url, formatted_url)

    return original_str


def parse_tweet(strtweet):
    expanded_tw = expand_tweet_urls(strtweet)
    expanded_tw = HEADER + quote(expanded_tw) + FOOTER
    return expanded_tw


def comment_post(apost):
    logger.info("Preparandome para comentar..")
    status_id = extract_status_id(apost.url)
    try:
        status = twitter.get_status(status_id, tweet_mode="extended")
        tweet = status.full_text
        logger.info(f"El tweet que lei del link es: \n {tweet}")
        parsed_tweet = parse_tweet(tweet)
        apost.reply(parsed_tweet)
        logger.info("Comenté  con éxito.")
        add_to_replied(apost)
        logger.info("Sleeping 30 seconds to avoid exceding rate limit")
        time.sleep(30)

    except tweepy.error.TweepError as StatusNotFound:
        print(f"Status {status_id} could not be found. Maybe it was deleted?")
        print(f"Exception code {StatusNotFound.api_code}, description: {StatusNotFound.reason}")

    except praw.exceptions.APIException as RateLimit:
        print(f"Couldn't reply on post {REDDIT_URL}{apost.id}")
        print(f"APIException: {RateLimit.reason}")


def there_is_a_match(arg):
    return arg is not None


def replied_db(post):
    c.execute("SELECT * FROM replies5 WHERE EXISTS (SELECT 1 FROM replies5 WHERE post_id = (?))", (post.id,))
    return there_is_a_match(c.fetchone())


def on_visited_db(post):
    c.execute("SELECT * FROM visited3 WHERE EXISTS (SELECT 1 FROM visited3 WHERE post_id = (?))", (post.id,))
    return there_is_a_match(c.fetchone())


def add_to_replied(post):
    if not replied_db(post):
        # post_id text, author text, url text, title text
        c.execute('INSERT INTO replies5 VALUES (?,?,?,?)', (post.id, str(post.author), post.url, post.title))
    conn.commit()


def add_to_visited(post):
    if not on_visited_db(post):
        c.execute('INSERT INTO visited3 VALUES (?,?,?,?)', (post.id, str(post.author),post.url,post.title))
    conn.commit()


def buscar_tweets(subreddit='twargbot', cant=20):
    subreddit = bot.subreddit(subreddit)
    logger.info(f"Buscando tweets en los primeros {cant} posts de /r/{subreddit}...")
    for i, post in enumerate(subreddit.new(limit=cant)):
        if not on_visited_db(post):
            title = post.title
            print(f"Analizando post {i+1}: {title}...")
            if is_tweet(post) and not replied_db(post):
                try:
                    comment_post(post)
                    print(f"Link al post: https://www.reddit.com/{post}")
                    print("----------------------")
                except (tweepy.error.TweepError, praw.exceptions.APIException) as e:
                    logger.error("No pude comentar el post {post.title} con link ")

            add_to_visited(post) # TODO; los agrega a pesar de haber fallado, guardar registro de fallidos
            print(f"Fin análisis post {i+1}")
        else:
            logger.info(f"{i}: Ya visite el post \"{post.title}\" (https://www.reddit.com/{post.id})")
    conn.close()
    logger.info("Finalizó mi búsqueda.")


# MAIN
buscar_tweets(cant=20)
# TODO: Review exception handling
# TODO: post tweet with author.
# TODO: execute every X minutes to fetch new posts for replying



