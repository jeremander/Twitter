import emoji
import tweepy as tw
import json
import re
import string
import itertools
from nltk.corpus import stopwords
from importlib import reload

# Basic API setup
 
owner = 'Morosoph1729'
owner_id = '1532157252' 
consumer_key = 'v0OVBe2GJ6Ezhv7JzAg6NaSlS'
consumer_secret = '4WmFcChLI1oySbKDvC0iIEhcxEtPRcMKPpnn18HVBkjopC1L10'
access_token = '1532157252-zRMNZJjVP1ka41IssBvVsnps7svR8qVui5KTLqp'
access_secret = 'MmCsDvGNbMMKeYlYmmBAZlOCMdb8FWGvVyxUkpitE1Pfs'

auth = tw.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_secret)
 
api = tw.API(auth)

def unencode(s):
    """Replace encoded characters with the correct characters."""
    replacements = {'&amp;' : '&',
                    '&lt;' :'<',
                    '&gt;' : '>'}
    for (source, target) in replacements.items():
        s = re.sub(source, target, s)
    return s

def emoji_regex_str():
    """Returns list of regex strings for all the emoji."""
    modifiers = '[\U0000FE0F|\U0001F3FB|\U0001F3FC|\U0001F3FD|\U0001F3FE|\U0001F3FF]*' 
    p = emoji.get_emoji_regexp().pattern
    ems = p[1:-1].split('|')
    return '(?:' + '|'.join(ems) + ')' + modifiers

def punctuation_str():
    return string.punctuation + ''.join(map(chr, itertools.chain(range(8208, 8232), range(8240,8287))))


class TweetTokenizer():
    """Class for tokenizing tweet strings."""
    emoticons_str = r"""
        (?:
            [:=;] # Eyes
            [oO\-]? # Nose (optional)
            [D\)\]\(\]/\\OpP] # Mouth
        )"""
    url_str = r'http[s]?://(?:[a-z]|[0-9]|[$-_@.&amp;+]|[!*\(\),]|(?:%[0-9a-f][0-9a-f]))+'
    regex_str = [
        emoticons_str, # emoticons
        emoji_regex_str(), # emoji
        r'<[^>]+>', # HTML tags
        r"(?:\#+[\w_]+[\w\'_\-]*[\w_]+)", # hash-tags
        r'(?:@[\w_]+)', # @-mentions
        url_str, # URLs
        #r'(?:(?:\d+,?)+(?:\.?\d+)?)', # numbers
        r"(?:[a-z][a-z'\-_]+[a-z])", # words with - and '
        r'(?:[\w_]+)', # other words
        r'(?:\S)' # anything else
    ]
    tokens_re = re.compile(r'('+'|'.join(regex_str)+')', re.VERBOSE | re.IGNORECASE)
    emoticon_re = re.compile(r'^'+emoticons_str+'$', re.VERBOSE | re.IGNORECASE)
    url_re = re.compile(r'^' + url_str + '$', re.VERBOSE | re.IGNORECASE)
    def __init__(self, lowercase = True, stop = None, hashtags = True, mentions = True, urls = False, terms = True):
        """Initializes a TweetTokenizer. If lowercase = True, tokenization will turn all characters (except emoticons) into lowercase. stop is a set of terms not considered tokens (default stopwords if None). If hashtags = False, excludes hashtags. If mentions = False, excludes mentions. If terms = False, excludes things other than hashtags and mentions."""
        trivial_map = lambda tok : tok 
        if lowercase:
            lowercase_map = lambda tok : tok if TweetTokenizer.emoticon_re.search(tok) else tok.lower()
        else:
            lowercase_map = trivial_map
        self.overall_map = lowercase_map  # function to apply to each token
        if (stop is None):  # punctuation, English stopwords, Twitter-specific strings
            punctuation = punctuation_str()
            stop = set(stopwords.words('english')) | set(punctuation) | {'rt', 'via'}  # NOTE: these are lowercase
        else:
            stop = set(stop)
        stop_filter = lambda tok : (tok not in stop)
        trivial_filter = lambda tok : True
        hashtag_filter = trivial_filter if hashtags else (lambda tok : (tok[0] != '#'))
        mention_filter = trivial_filter if mentions else (lambda tok : (tok[0] != '@'))
        url_filter = trivial_filter if urls else (lambda tok : not TweetTokenizer.url_re.search(tok))
        term_filter = trivial_filter if terms else (lambda tok : (tok[0] in {'#', '@'}))
        self.overall_filter = lambda tok : stop_filter(tok) and hashtag_filter(tok) and mention_filter(tok) and url_filter(tok) and term_filter(tok)  # filter to apply to the tokens
    def tokenize(self, s):
        """Tokenizes a string. If lowercase = True, takes lowercase of all the characters (except emoticons)."""
        tokens = TweetTokenizer.tokens_re.findall(s)
        return list(filter(self.overall_filter, map(self.overall_map, tokens)))

class Tweet(tw.Status):
    """Subclass of tweepy Status, with some added functionality."""
    def __init__(self, *args, **kwargs):
        if ((len(args) > 0) and isinstance(args[0], tw.Status)):  # make Tweet from Status
            super(Tweet, self).__init__()
            self.__dict__ = args[0].__dict__
        else:
            super(Tweet, self).__init__(*args, **kwargs)
        if hasattr(self, 'text'):
            self.text = unencode(self.text)
    def extract_salient_info(self):
        return {'tweet_id' : self.id, 'author_id' : self.author.id, 'author_name' : self.author.name, 'author_location' : self.author.location, 'time' : str(self.created_at), 'text' : self.text}
    def contains_token(self, token, tokenizer = None):
        """Returns True if the given token is part of the Tweet, using a specified tokenizer."""
        if (tokenizer is None):  # most permissive definition of token
            tokenizer =  TweetTokenizer(lowercase = True, stop = set(), hashtags = True, mentions = True, urls = True, terms = True)
        tokens = tokenizer.tokenize(self.text)
        return (tokenizer.overall_map(token) in tokens)
    def __contains__(self, s):
        return (s in self.text)
    def __repr__(self):
        s  = "tweet_id:    %s\n" % str(self.id)
        s += "author_id:   %s\n" % str(self.author.id)
        s += "author_name: %s\n" % str(self.author.name)
        if (self.author.location and (len(self.author.location) > 0)):
            s += "author_loc:  %s\n" % str(self.author.location)
        s += "time:        %s\n" % str(self.created_at)
        if hasattr(self, 'retweeted_status'):
            text = "text:\nRT @%s: %s\n" % (self.retweeted_status.author.screen_name, self.retweeted_status.text)
        else:
            text = "text:\n%s\n" % self.text
        s += "text:\n%s\n" % self.text
        s += '\n'
        return s
    @classmethod
    def parse(cls, api, js):
        """Parse a JSON object into a Tweet using the given API."""
        tweet = super(Tweet, cls).parse(api, js)
        if hasattr(tweet, 'text'):
            tweet.text = unencode(tweet.text)
        return tweet

def load_tweets(filename):
    """Gets a list of tweets from a JSON file."""
    tweets = []
    with open(filename) as f:
        for line in f:
            tweets.append(Tweet.parse(api, json.loads(line)))
    return tweets

def timeline_generator():
    """Produces a generator of tweets appearing in my timeline."""
    timeline = tw.Cursor(api.home_timeline).items()
    for status in timeline:
        yield Tweet(status)

def get_my_friends():
    """Returns a list of my friends."""
    return list(tw.Cursor(api.friends).items())

def get_my_tweets(n = None):
    """Returns a list of my tweets. If n is specified, only gets the most recent n tweets."""
    return [Tweet(status) for status in tw.Cursor(api.user_timeline).items(-1 if (n is None) else n)]

