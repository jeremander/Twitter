from twitter import *
import numpy as np
import scipy.sparse
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter

plt.style.use('ggplot')


class TermCooccurrenceMatrix(scipy.sparse.lil_matrix):
    """Represents a term cooccurrence matrix for terms within a set of Tweets."""
    def __init__(self, terms, count_single = True, count_retweets = True):
        """terms are list of terms that will be considered. If count_single = True, only counts one instance of each term per Tweet."""
        self.terms = terms 
        self.indices_by_term = {term : i for (i, term) in enumerate(self.terms)}
        self.count_single = count_single
        self.count_retweets = count_retweets
        self.term_counts = Counter()
        super(TermCooccurrenceMatrix, self).__init__((len(terms), len(terms)), dtype = int)
        self.format = 'lil'
    def num_occurrences(self, term):
        """Returns number of occurrences of term."""
        if (term not in self.term_counts):
            raise KeyError(term)
        return self.term_counts[term]
    def num_cooccurrences(self, term1, term2):
        """Returns number of cooccurrences of term1 and term2."""
        if isinstance(term1, str):
            term1 = self.indices_by_term[term1]
        if isinstance(term2, str):
            term2 = self.indices_by_term[term2]
        return self[term1, term2]
    def terms_occurring(self):
        """Returns list of terms occurring along with the number of times they occur."""
        return self.term_counts.most_common(len(self.term_counts))
    def terms_cooccurring(self, term):
        """Returns list of terms cooccurring with the given term, and the number of times they cooccur."""
        if isinstance(term, str):
            term = self.indices_by_term[term]
        return sorted([(self.terms[i], ct) for (i, ct) in zip(self[term].nonzero()[1], self[term].data[0])], key = lambda pair : pair[1], reverse = True)
    def term_occurrence_bars(self, N = 30, filename = None):
        """Makes a bar chart of the top N terms that occur. If filename is set, saves the plot to a file; otherwise, displays it to the screen."""
        fig = plt.figure()
        fig.clf()
        N = min(N, len(self.term_counts))
        pairs = self.term_counts.most_common(N)
        labels, freqs = zip(*pairs)
        labels = [emoji.demojize(label) for label in labels]
        plt.bar(np.arange(N), freqs, align = 'center', alpha = 0.5)
        plt.xticks(np.arange(N), labels, rotation = 'vertical')
        plt.xlim((-1, N))
        plt.title("Most common terms", fontsize = 14, fontweight = 'bold')
        fig.set_tight_layout(True)
        if (filename is None):
            plt.show(block = False)
        else:
            plt.savefig(filename)
    def term_cooccurrence_bars(self, term, N = 30, filename = None):
        """Makes a bar chart of the top N terms that cooccur with the given term. If filename is set, saves the plot to a file; otherwise, displays it to the screen."""
        fig = plt.figure()
        fig.clf()
        pairs = self.terms_cooccurring(term)
        N = min(N, len(pairs))
        pairs = pairs[:N]
        labels, freqs = zip(*pairs)
        labels = [emoji.demojize(label) for label in labels]
        plt.bar(np.arange(N), freqs, align = 'center', alpha = 0.5)
        plt.xticks(np.arange(N), labels, rotation = 'vertical')
        plt.xlim((-1, N))
        plt.title("Terms cooccurring with '%s'" % term, fontsize = 14, fontweight = 'bold')
        fig.set_tight_layout(True)
        if (filename is None):
            plt.show(block = False)
        else:
            plt.savefig(filename)
    def todense(self):
        """Converts to a dense matrix."""
        D = np.asarray(super(TermCooccurrenceMatrix, self).todense())
        return D + D.transpose() - np.diag(D.diagonal())
    def __repr__(self):
        return "<%d x %d sparse term cooccurrence matrix with %d stored elements in LInked List format>"
    @classmethod
    def from_tweets(cls, tweets, tokenizer = None, count_single = True, count_retweets = True, max_terms = None):
        """Given a list of Tweets, and a tokenizer, computes cooccurrence matrix for the Tweets, up to the most common max_terms terms."""
        if (tokenizer is None):
            tokenizer = TweetTokenizer()  # use the default Tokenizer
        tokens_by_tweet = []
        token_counts = Counter()
        for tweet in tweets:
            if hasattr(tweet, 'retweeted_status'):
                if (count_retweets):  # use the retweet text
                    text = tweet.retweeted_status.text
                else:  # don't include retweets
                    continue
            else:  # use the main tweet text
                text = tweet.text
            tokens = tokenizer.tokenize(tweet.text)
            if count_single:  # only count one instance of the token in each tweet
                tokens = list(set(tokens))
            else:
                tokens = list(tokens)
            tokens_by_tweet.append(tokens)
            token_counts.update(tokens)
        max_terms = len(token_counts) if (max_terms is None) else max_terms
        if ((max_terms is not None) and (len(token_counts) > max_terms)):
            print("Warning: max terms (%d) exceeded. Truncating at this many terms." % max_terms)
        pairs = token_counts.most_common(max_terms)
        C = cls([tok for (tok, ct) in pairs], count_single = count_single, count_retweets = count_retweets)
        for tokens in tokens_by_tweet:
            for i in range(len(tokens)):
                for j in range(i + 1, len(tokens)):  # don't include self-cooccurrences?
                    try:
                        ii, jj = sorted([C.indices_by_term[tokens[i]], C.indices_by_term[tokens[j]]])
                        C[ii, jj] += 1
                        if (ii != jj):
                            C[jj, ii] += 1
                    except KeyError:
                        continue
        C.term_counts = token_counts
        return C
    @classmethod 
    def from_file(cls, filename, tokenizer = None, count_single = True, count_retweets = True, max_terms = None):
        return cls.from_tweets(load_tweets(filename), tokenizer = tokenizer, count_single = count_single, count_retweets = count_retweets, max_terms = max_terms)

class TweetSeries():
    """Represents a set of Tweets in time series order."""
    def __init__(self, tweets, rule = '1Min'):
        """Initialize from a list of Tweets and a time interval by which to bin Tweet times."""
        self.tweets = sorted(tweets, key = lambda tweet : tweet.created_at)
        self.rule = rule
        self.dates = [tweet.created_at for tweet in self.tweets]
        ones = [1] * len(self.dates)
        idx = pd.DatetimeIndex(self.dates)
        timeseries = pd.Series(ones, index = idx)
        self.timeseries = timeseries.resample(self.rule, how = 'sum').fillna(0)
    def plot(self, filename = None):
        plt.clf()
        self.timeseries.plot()
        plt.title("Tweets per %s" % self.rule, fontsize = 14, fontweight = 'bold')
        if (filename is None):
            plt.show(block = False)
        else:
            plt.savefig(filename)
    def __getitem__(self, i):
        return self.tweets[i]
    def __len__(self):
        return len(self.tweets)
    def __repr__(self):
        s = ''
        for tweet in self.tweets:
            s += str(tweet) + '\n'
        return s
    @classmethod
    def from_tweets(cls, tweets, rule = '1Min'):
        return cls(tweets, rule = rule)
    @classmethod
    def from_file(cls, filename, rule = '1Min'):
        return cls(load_tweets(filename), rule = rule)

