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

#  c.execute("CREATE TABLE visited3 (post_id text, author text, title text)")

# Twitter API Initialization
auth = tweepy.OAuthHandler(config.API_KEY, config.API_SECRET)
auth.set_access_token(config.TOKEN, config.TOKEN_SECRET)
twitter = tweepy.API(auth)

# Compile regex to match twitter urls
REDDIT_URL = 'https://www.reddit.com/'
TWITTER_REGEX_URL = re.compile("https://twitter\.com/.*")
SHORTENER_URLS = re.compile("(https?:\/\/)(t\.co|bit.ly)(\/[a-zA-Z0-9]*)")
IMGUR_BASE_URL = "https://api.imgur.com/3/image"


def has_media(stat):
    return "media" in stat.entities


def is_video(mediadict):
    return mediadict["type"] == "video"


def is_image(mediadict):
    return mediadict["type"] == "photo"


def redir_status(stat):
    return stat in [300, 301, 302, 303, 304, 305, 306, 307, 308]


def replied_db(post):
    c.execute("SELECT * FROM replies5 WHERE "
              "EXISTS (SELECT 1 FROM replies5 WHERE post_id = (?))",
              (post.id,))
    return there_is_a_match(c.fetchone())


def on_visited_db(post):
    c.execute("SELECT * FROM visited3 WHERE "
              "EXISTS (SELECT 1 FROM visited3 WHERE post_id = (?))",
              (post.id,))
    return there_is_a_match(c.fetchone())


def add_to_replied(post):
    if not replied_db(post):
        # post_id text, author text, url text, title text
        c.execute('INSERT INTO replies5 VALUES (?,?,?,?)',
                  (post.id, str(post.author), post.url, post.title))
    conn.commit()


def add_to_visited(post):
    if not on_visited_db(post):
        c.execute('INSERT INTO visited3 VALUES (?,?,?,?)',
                  (post.id, str(post.author), post.url, post.title))
    conn.commit()


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
    status_id = splitted_url[-1]  # obtengo ultimo elemento
    return status_id


def quote(text):
    return ">" + text


def get_image_url(status):
    """
        Navega el json en busca del link a la imagen.
        entity_dict (dict): Diccionario que contiene bajo ["media"] una *lista*
                            con toddo el contenido 'media'
        media_dict (dict): Diccionario que contiene el contenido 'media'
        img_url (str): URL de la imagen, alojada bajo la clave 'media_url_https' del "inner_dict"
    """
    entity_dict = status.entities
    media_dict = entity_dict["media"][0]
    #logger.debug(f"Media dict: {media_dict}")
    img_url = media_dict["media_url_https"]
    return img_url


def upload_to_imgur(url):
    response = requests.request("POST", IMGUR_BASE_URL, data=url,
                                headers=config.IMGUR_AUTH_HEADER)
    jsondict = response.json()
    link = jsondict["data"]["link"]
    return link


def sign(twstr):
    return HEADER + quote(twstr) + FOOTER


def reddit_format_url(bare_url, visible_name):
    return f"[{visible_name}]({bare_url}) "


def format_img_url_list(listurls):
    reddit_str = ""
    for i, url in enumerate(listurls):
        reddit_str += reddit_format_url(url,"Imagen")
    return reddit_str


# DEPRECATED
def expand_tweet_urls(original_str):
    '''
        Si el tweet tiene 'n' shortened urls, las reemplazo
        por su full url, y la agrego el formato de reddit [Visible](Link)
        Si no tiene shortened urls, la devuelvo sin modificar
    '''
    for match in SHORTENER_URLS.finditer(original_str):
        # TODO: considerar reemplazar directamente por get_image_url
        short_url = matched_substring(match)
        expanded_url = unshorten_url(short_url)
        # if link is image : upload to imgur
        # img_url_at_imgur = upload_to_imgur(expanded_url)
        formatted_url = reddit_format_url(expanded_url)
        original_str = original_str.replace(short_url, formatted_url)

    return original_str
# ----------


def matched_substring(matchobj):
    """
        Given a match object, returns a string representing only the
        substring where the match occurs.
        example: given a match on "dummystr <protocolo>://<dominio>/<id> lorem",
        it would only return <protocolo>://<dominio>/<id>
    """
    return matchobj.group(1) + matchobj.group(2) + matchobj.group(3)


def is_image_url(shurl):
    # debuggear diferencia en json entre uno con imagen y otro sin. Maybe hasatrr image
    print(f"ISIMAGEURL: Tratando de determinar si {shurl} es una imagen..")
    return True


def replace_links(status):
    tweetstr = status.full_text
    for match in SHORTENER_URLS.finditer(tweetstr):
        short_url = matched_substring(match)
        print(f"Encontré la url achicada {short_url} en el tweet..")
        if is_image_url(short_url):
            img_url = get_image_url(status)
            reddit_img_url = reddit_format_url(img_url,"reddit")
            tweetstr = tweetstr.replace(short_url, reddit_img_url)
        else:
            tweetstr = unshorten_url(short_url)
    print(f"El resultado de mi replace_links es {tweetstr}")
    return tweetstr


def get_links(status):
    videos, images = [], []
    status = twitter.get_status(status.id, tweet_mode="extended")
    if  has_media(status):
        for media in status.extended_entities["media"]:
            if is_image(media):
                link = media["media_url_https"]
                images.append(link)
            if is_video(media):
                vid_dict = media["video_info"]["variants"][0]
                link = vid_dict["url"]
                videos.append(link)
    return (images,videos)


def remove_shortened_links(status):
    tweetstr = status.full_text
    for match in SHORTENER_URLS.finditer(tweetstr):
        short_url = matched_substring(match)
        tweetstr = tweetstr.replace(short_url,"")
    return tweetstr



def add_media_to_tweet(imgs, vids, original_tweet):
    if imgs != []:
        original_tweet = original_tweet  + "\n\n &nbsp; \n\n Imagenes del tweet: " + format_img_url_list(imgs)
    if vids != []:
        original_tweet = original_tweet + "\n\n &nbsp; \n\n Video del tweet: "+ reddit_format_url(vids[0], "Video") # solo uno

    return original_tweet


def parse_tweet(status):
    videos, imagenes = get_links(status)
    print("Ya obtuve videos e imagenes")
    clean_tweet = remove_shortened_links(status)
    tweet = add_media_to_tweet(videos, imagenes, clean_tweet)
    signed_tw = sign(tweet)
    return signed_tw


def read_tweet(post):
    status_id = extract_status_id(post.url)
    status = twitter.get_status(status_id, tweet_mode="extended")
    logger.info("Tengo la instancia de status")
    parsed_tweet = parse_tweet(status)
    logger.info("Tweet parseado")
    return parsed_tweet


def comment_post2(post, tweetstr):
    post.reply(tweetstr)
    #add_to_replied(post)


### DEPRECATED - delegated into read_tweet and comment_tweet
def comment_post(apost):
    logger.info("Preparandome para comentar..")
    status_id = extract_status_id(apost.url)
    try:
        status = twitter.get_status(status_id, tweet_mode="extended")
        logger.debug("Parseando status...")
        parsed_tweet = parse_tweet(status)
        logger.debug("Parseo exitoso")
        apost.reply(parsed_tweet)
        logger.info("Comenté  con éxito.")
        add_to_replied(apost)
        logger.info("Sleeping 20 seconds to avoid exceding rate limit")
        time.sleep(20)

    except tweepy.error.TweepError as StatusNotFound:
        print(f"Status {status_id} could not be found. Maybe it was deleted?")
        print(f"Exception code {StatusNotFound.api_code},"
              f" description: {StatusNotFound.reason}")

    except praw.exceptions.APIException as RateLimit:
        print(f"Couldn't reply on post {REDDIT_URL}{apost.id}")
        print(f"APIException: {RateLimit.reason}")
###

def there_is_a_match(arg):
    return arg is not None


def buscar_tweets(subreddit='twargbot', cant=5):
    subreddit = bot.subreddit(subreddit)
    logger.info(f"Buscando tweets en los primeros {cant} posts de /r/{subreddit}...")
    for i, post in enumerate(subreddit.new(limit=cant)):
        if not on_visited_db(post):
            title = post.title
            print(f"Analizando post {i+1}: {title}...")
            if is_tweet(post) and not replied_db(post):
                try:
                    red_tweet = read_tweet(post)
                    comment_post2(post, red_tweet)
                    print(f"Link al post comentado: https://www.reddit.com/{post}")
                except (tweepy.error.TweepError, praw.exceptions.APIException) as e:
                    logger.error(f"No pude comentar el post {post.title} con link https://www.reddit.com/{post} ")
                    logger.error(e)

            #add_to_visited(post)
        else:
            logger.info(f"{i}: Ya visite el post \"{post.title}\" https://www.reddit.com/{post.id}")
    conn.close()
    logger.info("Finalizó mi búsqueda.")


# MAIN
buscar_tweets(cant=5)
logger.error("ESTAN COMENTADOS LOS SAVE TO DB")
# TODO: Review exception handling
# TODO: post tweet with author.
# TODO: execute every X minutes to fetch new posts for replying
