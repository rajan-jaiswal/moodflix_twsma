from flask import Flask, render_template, request, jsonify
import requests
import os
from textblob import TextBlob
from dotenv import load_dotenv
import urllib.parse
import random
import time

# Load environment variables
load_dotenv()

app = Flask(__name__)

# AI Movie Recommender API configuration
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY', '43774399d4msh623b25b4b75f9d5p1cbae2jsn5b099e5e9e62')
RAPIDAPI_HOST = 'ai-movie-recommender.p.rapidapi.com'
RAPIDAPI_BASE_URL = 'https://ai-movie-recommender.p.rapidapi.com/api'
YOUTUBE_RAPID_HOST = 'youtube-v31.p.rapidapi.com'
YOUTUBE_SEARCH_URL = 'https://youtube-v31.p.rapidapi.com/search'

# Simple in-memory cache for query → movies to reduce API calls and 429s
_CACHE: dict[str, dict] = {}
_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours

def _cache_get(key: str):
    rec = _CACHE.get(key)
    if not rec:
        return None
    if time.time() - rec['ts'] > _CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return rec['val']

def _cache_set(key: str, val):
    _CACHE[key] = {'val': val, 'ts': time.time()}

# Mood to search query mapping (including Indian movies)
MOOD_QUERY_MAP = {
    "happy": "happy comedy movies bollywood",
    "sad": "sad drama movies indian", 
    "angry": "action thriller movies bollywood",
    "relaxed": "calm relaxing movies indian",
    "bored": "exciting adventure movies bollywood",
    "excited": "action adventure movies indian",
    "romantic": "romantic movies bollywood",
    "scared": "horror thriller movies indian",
    "nostalgic": "classic vintage movies bollywood",
    "adventurous": "adventure action movies indian"
}

def analyze_sentiment(text):
    """Analyze sentiment of the input text and return mood category"""
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    
    if polarity > 0.3:
        return "happy"
    elif polarity > 0.1:
        return "excited"
    elif polarity > -0.1:
        return "relaxed"
    elif polarity > -0.3:
        return "bored"
    else:
        return "sad"

def get_mood_emoji(mood):
    """Get emoji for the detected mood"""
    emoji_map = {
        "happy": "😊",
        "sad": "😢",
        "angry": "😠",
        "relaxed": "😌",
        "bored": "😴",
        "excited": "🤩",
        "romantic": "💕",
        "scared": "😨",
        "nostalgic": "😌",
        "adventurous": "🏃‍♂️"
    }
    return emoji_map.get(mood, "😊")

def get_fallback_movies(mood):
    """Provide fallback movie recommendations when API fails"""
    # Per-mood shortlists (curated, mixed Bollywood/Hollywood) – at least 8 each
    mood_lists = {
        "happy": [
            {"id": "f_h_1", "title": "3 Idiots", "overview": "A comedy-drama about friendship and following your dreams.", "rating": 8.4, "poster_url": "https://image.tmdb.org/t/p/w500/66A9MqXOyVp71a6tB3k1apLNj8S.jpg", "release_date": "2009"},
            {"id": "f_h_2", "title": "The Hangover", "overview": "A comedy about a bachelor party gone wrong in Las Vegas.", "rating": 7.7, "poster_url": "https://image.tmdb.org/t/p/w500/4qM1o4XZfVzPhKxW0a4t8qH5z8J.jpg", "release_date": "2009"},
            {"id": "f_h_3", "title": "Munna Bhai M.B.B.S.", "overview": "A gangster enrolls in medical college to fulfill his father's dream.", "rating": 8.1, "poster_url": "https://image.tmdb.org/t/p/w500/jQG3t2Z2YEl5GQY2QdYwz0S2w3f.jpg", "release_date": "2003"},
            {"id": "f_h_4", "title": "Zindagi Na Milegi Dobara", "overview": "Three friends take a road trip that changes their lives.", "rating": 8.0, "poster_url": "https://image.tmdb.org/t/p/w500/ao0nC0mZ4FcKqJsteVEh9UpAJZK.jpg", "release_date": "2011"},
            {"id": "f_h_5", "title": "PK", "overview": "An alien on Earth loses his communication device and explores humanity.", "rating": 8.0, "poster_url": "https://image.tmdb.org/t/p/w500/k1QUCjNAkfRpWfm1dVJGUmVHzGv.jpg", "release_date": "2014"},
            {"id": "f_h_6", "title": "Superbad", "overview": "Two friends try to enjoy their last weeks of high school.", "rating": 7.6, "poster_url": "https://image.tmdb.org/t/p/w500/ek8e8txUyUwd2BNqj6lFEerJfbq.jpg", "release_date": "2007"},
            {"id": "f_h_7", "title": "Hera Pheri", "overview": "Three men get caught up in a kidnapping gone wrong.", "rating": 8.1, "poster_url": "https://image.tmdb.org/t/p/w500/8oNbyz1Cdm42Hcps225y7sY9qsK.jpg", "release_date": "2000"},
            {"id": "f_h_8", "title": "Jumanji: Welcome to the Jungle", "overview": "Teens get sucked into a video game adventure.", "rating": 6.9, "poster_url": "https://image.tmdb.org/t/p/w500/bXrZ5iHBEjH7WMidbUDQ0U2xbmr.jpg", "release_date": "2017"}
        ],
        "sad": [
            {"id": "f_s_1", "title": "Taare Zameen Par", "overview": "A dyslexic child's life changes when he meets an art teacher.", "rating": 8.1, "poster_url": "https://image.tmdb.org/t/p/w500/2aEoG9V7H5PHeTtNQ2rYZRk5vK1.jpg", "release_date": "2007"},
            {"id": "f_s_2", "title": "The Pursuit of Happyness", "overview": "A struggling salesman takes custody of his son.", "rating": 8.0, "poster_url": "https://image.tmdb.org/t/p/w500/bO9WFb7GZ7YzWxZmf0RduCMsZV3.jpg", "release_date": "2006"},
            {"id": "f_s_3", "title": "Kal Ho Naa Ho", "overview": "A man teaches a woman how to love and live.", "rating": 7.8, "poster_url": "https://image.tmdb.org/t/p/w500/2Yx2oyS9MhUlCT3VkOITkkpZRlm.jpg", "release_date": "2003"},
            {"id": "f_s_4", "title": "Grave of the Fireflies", "overview": "Siblings struggle to survive in wartime Japan.", "rating": 8.5, "poster_url": "https://image.tmdb.org/t/p/w500/4u1vptE8aXuzwNqp1S3z3bWQp6y.jpg", "release_date": "1988"},
            {"id": "f_s_5", "title": "Masaan", "overview": "Four lives intersect along the Ganges.", "rating": 8.0, "poster_url": "https://image.tmdb.org/t/p/w500/9zA3RDeo63HgNbUsVTNff7kwh28.jpg", "release_date": "2015"},
            {"id": "f_s_6", "title": "A Beautiful Mind", "overview": "A brilliant mathematician battles schizophrenia.", "rating": 8.2, "poster_url": "https://image.tmdb.org/t/p/w500/zwzWCmH72OSC9NA0ipoqw5Zjya8.jpg", "release_date": "2001"},
            {"id": "f_s_7", "title": "Barfi!", "overview": "A deaf and mute man navigates love and life.", "rating": 7.4, "poster_url": "https://image.tmdb.org/t/p/w500/a9YVh1SeDsICoZ6irMIXja2fJG0.jpg", "release_date": "2012"},
            {"id": "f_s_8", "title": "Manchester by the Sea", "overview": "A janitor returns to his hometown after a tragedy.", "rating": 7.7, "poster_url": "https://image.tmdb.org/t/p/w500/xt7xQCFaN7G42xvAfoyz1K77QSq.jpg", "release_date": "2016"}
        ],
        "romantic": [
            {"id": "f_r_1", "title": "Kuch Kuch Hota Hai", "overview": "Friendship turns into love across years.", "rating": 7.5, "poster_url": "https://image.tmdb.org/t/p/w500/nC6YewsGmmKzBSSMSmc5QwDFi1C.jpg", "release_date": "1998"},
            {"id": "f_r_2", "title": "The Notebook", "overview": "A summer romance that lasts a lifetime.", "rating": 7.8, "poster_url": "https://image.tmdb.org/t/p/w500/rNzQyW4f8B8cQeg6XyC1XtnG9Sh.jpg", "release_date": "2004"},
            {"id": "f_r_3", "title": "Yeh Jawaani Hai Deewani", "overview": "Friends, travel and love.", "rating": 7.2, "poster_url": "https://image.tmdb.org/t/p/w500/2mW7UZ5EKeosFVJeGb3PcTJS3BM.jpg", "release_date": "2013"},
            {"id": "f_r_4", "title": "Before Sunrise", "overview": "Two strangers meet on a train and wander Vienna.", "rating": 8.1, "poster_url": "https://image.tmdb.org/t/p/w500/9B39S2hY6G4qzM7gc3KJ2YMBX1A.jpg", "release_date": "1995"},
            {"id": "f_r_5", "title": "Tamasha", "overview": "A man struggles between societal expectations and passion.", "rating": 7.2, "poster_url": "https://image.tmdb.org/t/p/w500/gIMiAFDzy83H8XTur2qxGn8pYt8.jpg", "release_date": "2015"},
            {"id": "f_r_6", "title": "La La Land", "overview": "Love and ambition in Los Angeles.", "rating": 8.0, "poster_url": "https://image.tmdb.org/t/p/w500/uDO8zWDhfWwoFdKS4fzkUJt0Rf0.jpg", "release_date": "2016"},
            {"id": "f_r_7", "title": "Dil Bechara", "overview": "A poignant love story inspired by TFiOS.", "rating": 7.6, "poster_url": "https://image.tmdb.org/t/p/w500/h0rXWmWZKD0wC2WkP3cu6Uytzsz.jpg", "release_date": "2020"},
            {"id": "f_r_8", "title": "Notting Hill", "overview": "A bookseller falls for a film star.", "rating": 7.3, "poster_url": "https://image.tmdb.org/t/p/w500/6u1fYtxG5eqjhtCPDx04pJphQRW.jpg", "release_date": "1999"}
        ],
        "excited": [
            {"id": "f_e_1", "title": "Dhoom 3", "overview": "High-octane heists and chases.", "rating": 6.8, "poster_url": "https://image.tmdb.org/t/p/w500/8JQZ2rCA0nVddOZXS6jttuPAHy9.jpg", "release_date": "2013"},
            {"id": "f_e_2", "title": "Mission: Impossible - Fallout", "overview": "Ethan Hunt and team prevent global catastrophe.", "rating": 7.7, "poster_url": "https://image.tmdb.org/t/p/w500/AkJQpZp9WoNdj7pLYSj1L0RcMMN.jpg", "release_date": "2018"},
            {"id": "f_e_3", "title": "War", "overview": "An elite soldier hunts his rogue mentor.", "rating": 6.5, "poster_url": "https://image.tmdb.org/t/p/w500/pV3Hn6Nq35p3xNmPR9U1FVLtZLk.jpg", "release_date": "2019"},
            {"id": "f_e_4", "title": "Mad Max: Fury Road", "overview": "Post-apocalyptic chase saga.", "rating": 8.1, "poster_url": "https://image.tmdb.org/t/p/w500/8tZYtuWezp8JbcsvHYO0O46tFbo.jpg", "release_date": "2015"},
            {"id": "f_e_5", "title": "Pathaan", "overview": "An Indian spy embarks on a dangerous mission.", "rating": 6.6, "poster_url": "https://image.tmdb.org/t/p/w500/ayrG9q24apqYh6g82kTFogyXv3E.jpg", "release_date": "2023"},
            {"id": "f_e_6", "title": "John Wick", "overview": "A retired hitman seeks vengeance.", "rating": 7.4, "poster_url": "https://image.tmdb.org/t/p/w500/fZPSd91yGE9fCcCe6OoQr6E3Bev.jpg", "release_date": "2014"},
            {"id": "f_e_7", "title": "RRR", "overview": "Two legendary revolutionaries forge a bond.", "rating": 7.8, "poster_url": "https://image.tmdb.org/t/p/w500/6WExLObz0SqGZQhQ0imeISFRCGD.jpg", "release_date": "2022"},
            {"id": "f_e_8", "title": "The Dark Knight", "overview": "Batman faces the Joker.", "rating": 9.0, "poster_url": "https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg", "release_date": "2008"}
        ],
        "angry": [
            {"id": "f_a_1", "title": "John Wick", "overview": "A retired hitman seeks vengeance.", "rating": 7.4, "poster_url": "https://image.tmdb.org/t/p/w500/fZPSd91yGE9fCcCe6OoQr6E3Bev.jpg", "release_date": "2014"},
            {"id": "f_a_2", "title": "Mad Max: Fury Road", "overview": "Post-apocalyptic chase saga.", "rating": 8.1, "poster_url": "https://image.tmdb.org/t/p/w500/8tZYtuWezp8JbcsvHYO0O46tFbo.jpg", "release_date": "2015"},
            {"id": "f_a_3", "title": "Kaithi", "overview": "An ex-convict gets caught up in a night-long chase.", "rating": 8.3, "poster_url": "https://image.tmdb.org/t/p/w500/9dI2wAPOQg8nH9n1tFoZT3zhEXI.jpg", "release_date": "2019"},
            {"id": "f_a_4", "title": "Baby", "overview": "An elite Indian counter-intelligence unit hunts terrorists.", "rating": 7.8, "poster_url": "https://image.tmdb.org/t/p/w500/vQ8G2GNJUgIVbawn94Qh1gC7YpN.jpg", "release_date": "2015"},
            {"id": "f_a_5", "title": "The Dark Knight", "overview": "Batman faces the Joker.", "rating": 9.0, "poster_url": "https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg", "release_date": "2008"},
            {"id": "f_a_6", "title": "Extraction", "overview": "A black ops mercenary embarks on a deadly mission in Dhaka.", "rating": 6.8, "poster_url": "https://image.tmdb.org/t/p/w500/wlfDxbGEsW58vGhFljKkcR5IxDj.jpg", "release_date": "2020"},
            {"id": "f_a_7", "title": "Pathaan", "overview": "An Indian spy embarks on a dangerous mission.", "rating": 6.6, "poster_url": "https://image.tmdb.org/t/p/w500/ayrG9q24apqYh6g82kTFogyXv3E.jpg", "release_date": "2023"},
            {"id": "f_a_8", "title": "War", "overview": "An elite soldier hunts his rogue mentor.", "rating": 6.5, "poster_url": "https://image.tmdb.org/t/p/w500/pV3Hn6Nq35p3xNmPR9U1FVLtZLk.jpg", "release_date": "2019"}
        ],
        "relaxed": [
            {"id": "f_rl_1", "title": "The Secret Life of Walter Mitty", "overview": "A daydreamer embarks on a global journey.", "rating": 7.2, "poster_url": "https://image.tmdb.org/t/p/w500/tw1r3qYi58E8CUpbZQhQ0imeOqM.jpg", "release_date": "2013"},
            {"id": "f_rl_2", "title": "Life of Pi", "overview": "A young man survives a disaster at sea on a lifeboat with a tiger.", "rating": 7.9, "poster_url": "https://image.tmdb.org/t/p/w500/3bD5Qn7qSdz8CA0nVddOZXS6jtV.jpg", "release_date": "2012"},
            {"id": "f_rl_3", "title": "Midnight in Paris", "overview": "A writer discovers midnight transports him to the 1920s.", "rating": 7.6, "poster_url": "https://image.tmdb.org/t/p/w500/4wBG5kbfagTQclETblPRRGihk0I.jpg", "release_date": "2011"},
            {"id": "f_rl_4", "title": "The Lunchbox", "overview": "A mistaken delivery connects a young housewife and an older man.", "rating": 7.8, "poster_url": "https://image.tmdb.org/t/p/w500/3hFQm3GEXLMaLLq5yRvCNrI6Vsg.jpg", "release_date": "2013"},
            {"id": "f_rl_5", "title": "Amélie", "overview": "A whimsical depiction of contemporary Parisian life.", "rating": 8.3, "poster_url": "https://image.tmdb.org/t/p/w500/sWGaQbY4Z1cdq9VHtV6nRvWmvMR.jpg", "release_date": "2001"},
            {"id": "f_rl_6", "title": "October", "overview": "A tender coming-of-age story set in Delhi.", "rating": 7.2, "poster_url": "https://image.tmdb.org/t/p/w500/yZK0YvZCENKz7dxyzKDn5XxhxLq.jpg", "release_date": "2018"},
            {"id": "f_rl_7", "title": "Chef", "overview": "A chef starts a food truck to reclaim his creativity.", "rating": 7.3, "poster_url": "https://image.tmdb.org/t/p/w500/zfZ7dUnc8mZKVEtKiMyVZbYbK9F.jpg", "release_date": "2014"},
            {"id": "f_rl_8", "title": "The Hundred-Foot Journey", "overview": "An Indian family opens a restaurant in France.", "rating": 7.3, "poster_url": "https://image.tmdb.org/t/p/w500/bQHIiph0QGlpK1iD7agEXKDkQ5Y.jpg", "release_date": "2014"}
        ],
        "bored": [
            {"id": "f_b_1", "title": "Shutter Island", "overview": "A marshal investigates a disappearance on an island hospital.", "rating": 8.2, "poster_url": "https://image.tmdb.org/t/p/w500/kve20tXwUZpu4GUX8l6X7Z4jmL6.jpg", "release_date": "2010"},
            {"id": "f_b_2", "title": "Kahaani", "overview": "A pregnant woman searches for her missing husband in Kolkata.", "rating": 7.9, "poster_url": "https://image.tmdb.org/t/p/w500/oK8GMDIS9KuX3sI5Yucs5cjox96.jpg", "release_date": "2012"},
            {"id": "f_b_3", "title": "Andhadhun", "overview": "A blind pianist is swept up in a murder mystery.", "rating": 8.1, "poster_url": "https://image.tmdb.org/t/p/w500/67ZdZXXAuv5Z7xL7sRKqzZo4PM5.jpg", "release_date": "2018"},
            {"id": "f_b_4", "title": "Drishyam", "overview": "A father goes to great lengths to protect his family.", "rating": 8.1, "poster_url": "https://image.tmdb.org/t/p/w500/8eQof8I4eAbOeXtfLOcAfeUOLuO.jpg", "release_date": "2013"},
            {"id": "f_b_5", "title": "Tenet", "overview": "A secret agent manipulates time to prevent World War III.", "rating": 7.3, "poster_url": "https://image.tmdb.org/t/p/w500/k68nPLbIST6NP96JmTxmZijEvCA.jpg", "release_date": "2020"},
            {"id": "f_b_6", "title": "Detective Byomkesh Bakshy!", "overview": "A young detective probes a sinister conspiracy in 1940s Calcutta.", "rating": 7.5, "poster_url": "https://image.tmdb.org/t/p/w500/9k2YkdEYY5EYXPLkZX31lrT7xYu.jpg", "release_date": "2015"},
            {"id": "f_b_7", "title": "Arrival", "overview": "A linguist communicates with extraterrestrials.", "rating": 7.9, "poster_url": "https://image.tmdb.org/t/p/w500/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg", "release_date": "2016"},
            {"id": "f_b_8", "title": "Talaash", "overview": "A cop investigates a high-profile death.", "rating": 7.2, "poster_url": "https://image.tmdb.org/t/p/w500/2VtW7UZ5EKeosFVJeGb3PcTJX5r.jpg", "release_date": "2012"}
        ],
        "scared": [
            {"id": "f_sc_1", "title": "The Conjuring", "overview": "Paranormal investigators help a family terrorized by a dark presence.", "rating": 7.5, "poster_url": "https://image.tmdb.org/t/p/w500/wVYREutTvI2tmxr6ujrHT704wGF.jpg", "release_date": "2013"},
            {"id": "f_sc_2", "title": "Tumbbad", "overview": "A mythological horror set in colonial India.", "rating": 8.2, "poster_url": "https://image.tmdb.org/t/p/w500/nPGZ1YgnPZXoqBYwygJyI07212e.jpg", "release_date": "2018"},
            {"id": "f_sc_3", "title": "Stree", "overview": "A small town is haunted by a spirit.", "rating": 7.4, "poster_url": "https://image.tmdb.org/t/p/w500/8Lx7x1YgnM7hZ9E9QnUnxEporX2.jpg", "release_date": "2018"},
            {"id": "f_sc_4", "title": "Hereditary", "overview": "A family unravels terrifying secrets after their matriarch dies.", "rating": 7.3, "poster_url": "https://image.tmdb.org/t/p/w500/bcT8CaBIj086WVD7K529h78eujb.jpg", "release_date": "2018"},
            {"id": "f_sc_5", "title": "The Ring", "overview": "A cursed videotape kills viewers in seven days.", "rating": 7.1, "poster_url": "https://image.tmdb.org/t/p/w500/e2t5CKXQwZ0pniNXh9vDOMkMt2g.jpg", "release_date": "2002"},
            {"id": "f_sc_6", "title": "Bhoot", "overview": "A couple's life turns nightmarish in a haunted apartment.", "rating": 6.3, "poster_url": "https://image.tmdb.org/t/p/w500/f9G4mJcP0xK3opYJwcYqKqRR3YK.jpg", "release_date": "2003"},
            {"id": "f_sc_7", "title": "Train to Busan", "overview": "Passengers fight to survive on a zombie-infested train.", "rating": 7.6, "poster_url": "https://image.tmdb.org/t/p/w500/2oRRTPNtozgPhOa9CYZiVl4GRQ5.jpg", "release_date": "2016"},
            {"id": "f_sc_8", "title": "The Nun", "overview": "A priest and novice uncover unholy secrets.", "rating": 5.8, "poster_url": "https://image.tmdb.org/t/p/w500/sFC1ElvoKGdHJIWRpNB3xWJ9lJA.jpg", "release_date": "2018"}
        ],
        "nostalgic": [
            {"id": "f_n_1", "title": "Lagaan", "overview": "Villagers challenge British officers to a cricket match.", "rating": 8.1, "poster_url": "https://image.tmdb.org/t/p/w500/ucW5Z7WvyaManIeZDV4SSQdlqz7.jpg", "release_date": "2001"},
            {"id": "f_n_2", "title": "Swades", "overview": "An NRI returns to India and rediscovers home.", "rating": 8.2, "poster_url": "https://image.tmdb.org/t/p/w500/y6VAk0nnBYnCTsRmR271GGBqBPd.jpg", "release_date": "2004"},
            {"id": "f_n_3", "title": "Anand", "overview": "A terminally ill man spreads joy.", "rating": 8.1, "poster_url": "https://image.tmdb.org/t/p/w500/1ZJYG1ChB7sCv0xOsyjzAm8h1Hc.jpg", "release_date": "1971"},
            {"id": "f_n_4", "title": "Sholay", "overview": "Two criminals are hired to capture a ruthless bandit.", "rating": 8.2, "poster_url": "https://image.tmdb.org/t/p/w500/j1zAr72Xd23LSeX776BF3nf6tDr.jpg", "release_date": "1975"},
            {"id": "f_n_5", "title": "Hum Aapke Hain Koun..!", "overview": "A family drama about love and relationships.", "rating": 7.5, "poster_url": "https://image.tmdb.org/t/p/w500/6NKxaz2YsmiVjCwXTkA8azhbugi.jpg", "release_date": "1994"},
            {"id": "f_n_6", "title": "Guide", "overview": "A tour guide falls in love and seeks redemption.", "rating": 8.1, "poster_url": "https://image.tmdb.org/t/p/w500/7wY2Gj33jjXNMTvEihQ6VbUaz2Q.jpg", "release_date": "1965"},
            {"id": "f_n_7", "title": "The Sound of Music", "overview": "A governess brings music to a family in Austria.", "rating": 8.0, "poster_url": "https://image.tmdb.org/t/p/w500/qgM1b9DLG3sZ3VAb9YSEuxsjjXN.jpg", "release_date": "1965"},
            {"id": "f_n_8", "title": "Forrest Gump", "overview": "A man witnesses historic events with simple wisdom.", "rating": 8.8, "poster_url": "https://image.tmdb.org/t/p/w500/saHP97rTPS5eLmrLQEcANmKrsFl.jpg", "release_date": "1994"}
        ],
        "adventurous": [
            {"id": "f_adv_1", "title": "Pirates of the Caribbean: The Curse of the Black Pearl", "overview": "A blacksmith teams up with a pirate to save his love.", "rating": 8.0, "poster_url": "https://image.tmdb.org/t/p/w500/1Jw2GNbKwxLBzME2YkdBqtu1o9Y.jpg", "release_date": "2003"},
            {"id": "f_adv_2", "title": "Indiana Jones and the Last Crusade", "overview": "Indiana searches for the Holy Grail.", "rating": 8.2, "poster_url": "https://image.tmdb.org/t/p/w500/4p1N2Qrt8j0H8xMHMHvtRxv9weZ.jpg", "release_date": "1989"},
            {"id": "f_adv_3", "title": "Baahubali 2: The Conclusion", "overview": "Mahendra Baahubali avenges his father.", "rating": 7.9, "poster_url": "https://image.tmdb.org/t/p/w500/3GZbE2wAPO8nH9n1tFoZT3zhEXI.jpg", "release_date": "2017"},
            {"id": "f_adv_4", "title": "Krrish", "overview": "An Indian superhero discovers his powers.", "rating": 6.8, "poster_url": "https://image.tmdb.org/t/p/w500/7pGdb9h9NP7VDaRao7IhiHBpjz2.jpg", "release_date": "2006"},
            {"id": "f_adv_5", "title": "The Jungle Book", "overview": "Mowgli returns to the jungle in this live-action adaptation.", "rating": 7.4, "poster_url": "https://image.tmdb.org/t/p/w500/vOipe2myi26UDwP978hsYOrnUWC.jpg", "release_date": "2016"},
            {"id": "f_adv_6", "title": "Guardians of the Galaxy", "overview": "A group of intergalactic criminals must save the universe.", "rating": 7.9, "poster_url": "https://image.tmdb.org/t/p/w500/y31QB9kn3XSudA15tV7UWQ9XLuW.jpg", "release_date": "2014"},
            {"id": "f_adv_7", "title": "Jumanji: Welcome to the Jungle", "overview": "Teens get sucked into a video game adventure.", "rating": 6.9, "poster_url": "https://image.tmdb.org/t/p/w500/bXrZ5iHBEjH7WMidbUDQ0U2xbmr.jpg", "release_date": "2017"},
            {"id": "f_adv_8", "title": "The Revenant", "overview": "A frontiersman fights for survival in the wilderness.", "rating": 8.0, "poster_url": "https://image.tmdb.org/t/p/w500/oXUWEc5i3wYyFnL1Ycu8ppxxPvs.jpg", "release_date": "2015"}
        ]
    }

    general_pool = [
        {"id": "g_1", "title": "Inception", "overview": "A thief steals corporate secrets through dream-sharing.", "rating": 8.8, "poster_url": "https://image.tmdb.org/t/p/w500/edv5CZvWj09upOsy2Y6IwDhK8bt.jpg", "release_date": "2010"},
        {"id": "g_2", "title": "Dangal", "overview": "A father trains his daughters to become wrestlers.", "rating": 8.3, "poster_url": "https://image.tmdb.org/t/p/w500/p2lVAcPuRPSO8Al6hDDGw0OgMi8.jpg", "release_date": "2016"},
        {"id": "g_3", "title": "Andhadhun", "overview": "A blind pianist is swept up in a murder mystery.", "rating": 8.1, "poster_url": "https://image.tmdb.org/t/p/w500/67ZdZXXAuv5Z7xL7sRKqzZo4PM5.jpg", "release_date": "2018"},
        {"id": "g_4", "title": "Interstellar", "overview": "Explorers travel through a wormhole in space.", "rating": 8.6, "poster_url": "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg", "release_date": "2014"},
        {"id": "g_5", "title": "Drishyam", "overview": "A father does whatever it takes to protect his family.", "rating": 8.1, "poster_url": "https://image.tmdb.org/t/p/w500/8eQof8I4eAbOeXtfLOcAfeUOLuO.jpg", "release_date": "2013"}
    ]

    # Compose at least 12 recommendations by mixing mood list then general pool
    picks = []
    seen = set()
    for item in mood_lists.get(mood, mood_lists["happy"]):
        key = item.get('id') or item.get('title')
        if key not in seen:
            seen.add(key)
            picks.append(item)
            if len(picks) >= 12:
                break
    if len(picks) < 12:
        for item in general_pool:
            key = item.get('id') or item.get('title')
            if key not in seen:
                seen.add(key)
                picks.append(item)
                if len(picks) >= 12:
                    break

    return picks

def get_movies_by_mood(mood_query, limit=10):
    """Fetch movies from AI Movie Recommender API based on mood query"""
    try:
        # Cache first
        cache_key = f"amr::{mood_query.lower()}::{limit}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
        # Encode the query for URL
        encoded_query = urllib.parse.quote(mood_query)
        url = f"{RAPIDAPI_BASE_URL}/search"
        
        headers = {
            'x-rapidapi-host': RAPIDAPI_HOST,
            'x-rapidapi-key': RAPIDAPI_KEY
        }
        
        params = {
            'q': mood_query
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        movies = []
        
        # Handle the specific response format from AI Movie Recommender API
        movie_results = data.get('movies', [])
        
        for movie in movie_results[:limit]:
            # Prefer TMDB poster_path/backdrop_path when present
            poster_url = None
            poster_path = movie.get('poster_path')
            if poster_path:
                if not str(poster_path).startswith('/'):
                    poster_path = f"/{poster_path}"
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
            elif movie.get('backdrop_path'):
                bp = movie.get('backdrop_path')
                if not str(bp).startswith('/'):
                    bp = f"/{bp}"
                poster_url = f"https://image.tmdb.org/t/p/w500{bp}"
            else:
                # Fallback fields sometimes provided by other APIs
                raw = movie.get('poster_url') or movie.get('poster') or movie.get('image')
                # Some sources return relative TMDB path without host
                if raw and isinstance(raw, str):
                    if raw.startswith('/'):  # TMDB-like
                        poster_url = f"https://image.tmdb.org/t/p/w500{raw}"
                    elif raw.startswith('http'):  # absolute
                        poster_url = raw
                    else:
                        poster_url = None
                else:
                    poster_url = None

            # Parse movie data from the API response
            movie_data = {
                'id': movie.get('id'),
                'title': movie.get('title') or movie.get('name'),
                'overview': movie.get('overview', 'No overview available'),
                'rating': round(float(movie.get('vote_average', 0) or 0), 1),
                'poster_url': poster_url,
                'release_date': movie.get('release_date', movie.get('year', 'Unknown'))
            }
            
            # Clean up the data
            if movie_data['overview'] and len(movie_data['overview']) > 500:
                movie_data['overview'] = movie_data['overview'][:500] + "..."
            
            movies.append(movie_data)
        
        _cache_set(cache_key, movies)
        return movies
    
    except requests.exceptions.HTTPError as e:
        # If rate limited or other HTTP error, log and return empty
        status = getattr(e.response, 'status_code', None)
        print(f"HTTP error for query '{mood_query}': {status} -> {e}")
        if status == 429:
            print("Rate limit hit, will try simpler queries and cached results where possible")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Request error for query '{mood_query}': {e}")
        return []
    except Exception as e:
        print(f"Unexpected error for query '{mood_query}': {e}")
        return []

@app.route('/trailer', methods=['GET'])
def get_trailer():
    """Fetch top YouTube trailer for a movie title using RapidAPI YouTube v3.1"""
    try:
        title = request.args.get('title', '').strip()
        year = request.args.get('year', '').strip()
        if not title:
            return jsonify({'error': 'Missing title'}), 400
        query = f"{title} official trailer {year}".strip()
        headers = {
            'x-rapidapi-host': YOUTUBE_RAPID_HOST,
            'x-rapidapi-key': RAPIDAPI_KEY
        }
        params = {
            'q': query,
            'part': 'id,snippet',
            'type': 'video',
            'maxResults': 1
        }
        resp = requests.get(YOUTUBE_SEARCH_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get('items', [])
        if not items:
            return jsonify({'videoId': None})
        video_id = items[0].get('id', {}).get('videoId')
        return jsonify({'videoId': video_id})
    except Exception as e:
        print(f"Error fetching trailer: {e}")
        return jsonify({'videoId': None})

@app.route('/')
def index():
    """Render the home page"""
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend_movies():
    """Analyze sentiment and recommend movies"""
    try:
        data = request.get_json()
        user_input = data.get('mood_text', '').strip()
        # Optional controls from frontend
        preference = (data.get('preference') or 'mixed').lower()  # mixed | indian | hollywood
        try:
            limit = int(data.get('limit', 10))
        except Exception:
            limit = 10
        limit = max(4, min(limit, 20))
        
        if not user_input:
            return jsonify({'error': 'Please enter how you are feeling'}), 400
        
        # Analyze sentiment; allow emoji override
        emoji_input = (data.get('emoji') or '').strip()
        emoji_to_mood = {
            "😊": "happy", "😢": "sad", "😠": "angry", "😌": "relaxed", "😴": "bored",
            "🤩": "excited", "💕": "romantic", "😨": "scared", "🕵️": "bored", "🚀": "adventurous"
        }
        if emoji_input in emoji_to_mood:
            mood = emoji_to_mood[emoji_input]
        else:
            mood = analyze_sentiment(user_input)
        emoji = get_mood_emoji(mood)
        
        # Get search query for the mood (Indian movies)
        mood_query_indian = MOOD_QUERY_MAP.get(mood, MOOD_QUERY_MAP['happy'])  # Default to happy if mood not found
        
        # Also create Hollywood query
        mood_query_hollywood = mood_query_indian.replace('bollywood', '').replace('indian', '').strip()
        
        # Try multiple queries with better fallbacks (stop early). Always target 8.
        target_count = 8
        limit = max(target_count, limit)
        movies = []
        used_queries = []
        
        # Build list of queries to try based on preference
        base_queries = []
        # Simple mood-based queries first
        if preference in ('mixed', 'hollywood'):
            base_queries.extend([
                f"{mood} movies",
                f"{mood} comedy movies" if mood == "happy" else f"{mood} drama movies",
                f"{mood} action movies" if mood in ["angry", "excited", "adventurous"] else f"{mood} romantic movies",
            ])
        if preference in ('mixed', 'indian'):
            base_queries.extend([
                f"{mood} bollywood movies",
                f"{mood} bollywood action movies" if mood in ["angry", "excited", "adventurous"] else f"{mood} bollywood romantic movies",
            ])
        # More specific queries from user input (only if short to avoid noisy searches)
        if len(user_input.split()) <= 4 and user_input:
            if preference in ('mixed', 'hollywood'):
                base_queries.append(f"{mood} movies {user_input.lower()}")
            if preference in ('mixed', 'indian'):
                base_queries.append(f"{mood} bollywood {user_input.lower()}")
        
        # Shuffle slightly to avoid same ordering across sentiments
        random.shuffle(base_queries)
        queries_to_try = base_queries
        
        # Try each query until we get enough movies
        for idx, query in enumerate(queries_to_try):
            if len(movies) >= target_count:  # Stop if we have enough movies
                break
                
            try:
                # progressively reduce requested page size to be gentle on API
                req_limit = max(4, target_count - len(movies))
                new_movies = get_movies_by_mood(query, limit=req_limit)
                if new_movies:
                    movies.extend(new_movies)
                    used_queries.append(query)
                    print(f"✅ Query '{query}' returned {len(new_movies)} movies")
                else:
                    print(f"❌ Query '{query}' returned no movies")
            except Exception as e:
                print(f"❌ Query '{query}' failed: {e}")
                continue
        
        # Remove duplicates based on movie ID or title
        seen_ids = set()
        unique_movies = []
        for movie in movies:
            dedup_key = (movie.get('id') or movie.get('title'))
            if dedup_key and dedup_key not in seen_ids:
                seen_ids.add(dedup_key)
                unique_movies.append(movie)
        
        # Introduce lightweight diversification by sorting depending on mood
        def score(m):
            r = float(m.get('rating') or 0)
            # mood-based bias
            if mood in ("happy", "romantic"):
                return r + 0.3
            if mood in ("angry", "excited", "adventurous"):
                return r + 0.2
            if mood in ("sad", "relaxed", "bored"):
                return r  # neutral
            return r
        unique_movies.sort(key=score, reverse=True)

        # Enforce exactly 8 if we have at least that many, else fallback later
        movies = unique_movies[:target_count] if len(unique_movies) >= target_count else unique_movies
        
        # If fewer than 8 movies, top-up with curated fallback to reach 8
        if len(movies) < target_count:
            print("No movies found from API, providing fallback recommendations")
            fallback_movies = get_fallback_movies(mood)
            if fallback_movies:
                # add non-duplicated fallback movies
                existing_keys = { (m.get('id') or m.get('title')) for m in movies }
                # shuffle fallbacks so different moods see different mixes
                shuffled_fb = list(fallback_movies)
                random.shuffle(shuffled_fb)
                for fb in shuffled_fb:
                    key = fb.get('id') or fb.get('title')
                    if key not in existing_keys:
                        movies.append(fb)
                        existing_keys.add(key)
                        if len(movies) >= target_count:
                            break
            if movies:
                return jsonify({
                    'mood': mood,
                    'emoji': emoji,
                    'movies': movies[:target_count],
                    'user_input': user_input,
                    'search_queries': {
                        'indian': f"{mood} bollywood movies",
                        'hollywood': f"{mood} movies"
                    },
                    'total_movies': len(movies[:target_count]),
                    'fallback': True
                })
            else:
                return jsonify({'error': 'No movies found. Please try again.'}), 500
        
        return jsonify({
            'mood': mood,
            'emoji': emoji,
            'movies': movies,
            'user_input': user_input,
            'preference': preference,
            'queries': used_queries,
            'total_movies': len(movies)
        })
    
    except Exception as e:
        print(f"Error in recommend_movies: {e}")
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
