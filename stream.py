"""Channels a stream of tweets matching a given term or terms to a JSON file.
Usage: python3 stream.py term1 term2 ... termN [prefix]
The output file will be [prefix].json
Note: the term arguments should be put in quotes to deal with hashtags
"""

from twitter import *
from http.client import IncompleteRead
import sys

class TweetListener(tw.streaming.StreamListener):
    """StreamListener that channels tweets to a JSON file."""
    def __init__(self, pref = None):
        """[pref].json will be the filename to which to channel tweets. If pref = None, does not save the tweets, only displays them."""
        super(TweetListener, self).__init__()
        self.pref = pref
    def on_data(self, data):
        try:
            tweet = Tweet.parse(api, json.loads(data))
            print(tweet)
            if (self.pref is not None):
                with open('%s.json' % self.pref, 'a') as f:
                    f.write(data)
            return True
        except BaseException as e:
            print('Error on_data: %s' % str(e))
        return True
    def on_error(self, status):
        print(status)
        return True  # don't kill the stream
    def on_timeout(self):
        print("Timeout...")
        return True  # don't kill the stream

def channel_tweets(terms, pref = None):
    """Channels tweets with the given terms to the screen, and if pref != None, to a file named [pref].json."""
    if (not isinstance(terms, list)):
        terms = [terms]
    stream = tw.Stream(auth, TweetListener(pref))
    while True:
        try:
            stream.filter(track = terms)
        except IncompleteRead:  # oh well, just keep on trucking
            continue  
        except KeyboardInterrupt:
            stream.disconnect()
            break

def main():
    nargs = len(sys.argv) - 1
    assert (nargs >= 2)
    terms = sys.argv[1:-1]
    prefix = sys.argv[-1]
    channel_tweets(terms, prefix)

if __name__ == "__main__":
    main()
