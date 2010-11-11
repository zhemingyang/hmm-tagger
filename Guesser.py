import re # for finding word suffixes, etc...

class Guesser:
    
    # hard-code lists of certain parts of speech to hetag with guessing
    
    det_list = ['a', 'both', 'all', 'no', 'this', 'that', 'some', 'an', 'these', 
        'every', 'either', 'another', 'each', 'the', 'any', 'those']
        
    prep_list = ['among', 'because', 'besides', 'into', 'within', 'near', 'down', 
        'as', 'via', 'through', 'at', 'in', 'beyond', 'between', 'if', 'throughout', 
        'from', 'for', 'since', 'except', 'per', 'by', 'below', 'behind', 'above', 
        'under', 'before', 'until', 'outside', 'over', 'alongside', 'unless', 
        'around', 'that', 'atop', 'after', 'upon', 'but', 'next', 'although', 
        'despite', 'during', 'along', 'with', 'than', 'on', 'about', 'off', 'like', 
        'unlike', 'whether', 'of', 'up', 'against', 'across', 'while', 'without', 'so', 
        'though', 'amid', 'toward', 'out', 'once']
        
    wdt_list = ['what','whatever','which','that']
    
    punct_list = {'``':['`','``'], "''":["'",'"'], '(':['(','{','['], ')':[')','}',']'], 
        ',':[','], '--':['--'], '.':['.','!','?'],':':[':',';','...']}
    
    def __init__(self, pos_tags, words_given_pos):
        """
        Initialize a Guesser object
        
        :param pos_tags: a list of part of speech tags
        :param words_given_pos: a ConditionalFreqDist object representing P(Wi|Ck)
        """
        
        self.pos_tags = pos_tags
        self.words_given_pos = words_given_pos
        
        # the human-friendly Guesser.punct_list is the inverse of what we want,
        # so let's turn it into something easier to look up POS tag given word
        self.inverted_punct_list = {}
        for pos, wordlist in self.punct_list.iteritems():
            for word in wordlist:
                self.inverted_punct_list[word] = pos
        
    def guess(self, word, scores_without_word_prob):
        """
        Return a guessed part of speech for a given word
        
        :param word: string word
        :param scores_without_word_prob: list of probabilities that the given word is
            a given POS based on the previous POS but not based on the word itself
        """
        
        # create a list of features for a word, for now stored in simple variables
        is_upper = re.search(r'[A-Z]', word[0]) is not None
        ends_in_s = word[len(word)-1] == 's'
        ends_in_ly = word[-2:] == 'ly'
        ends_in_ing = word[-3:] == 'ing'
        ends_in_er = word[-2:] == 'er'
        ends_in_ed = word[-2:] == 'ed'
        ends_in_ize = word[-3:] == 'ize'
        has_hyphen = re.search(r'\-', word) is not None
        has_number = re.search(r'[0-9]+', word) is not None
        
        # test for different features and guess
        
        # are we dealing with punctation?
        if word in self.inverted_punct_list.keys():
            guess_tag = self.inverted_punct_list[word]
            
        # what about a number?
        elif has_number:
            guess_tag = 'CD'
            
        # does our word begin in uppercase?
        elif is_upper:
            if ends_in_s:
                # guess the most likely tag, with default of proper noun
                guess_tag = self._guess_s(word, 'NNPS')
            elif ends_in_ed:
                # guess the most likely tag, with default of verb participle
                guess_tag = self._guess_ed(word, 'VBN')
            else:
                # default to proper noun
                guess_tag = 'NNP'
        
        # if our word begins in lowercase
        else:
            if ends_in_s:
                # search for word by stem, default to common noun
                guess_tag = self._guess_s(word, 'NNS')
            elif ends_in_ize:
                # guess verb
                guess_tag = 'VB'
            elif ends_in_ed:
                # search for word by stem, default to verb
                guess_tag = self._guess_ed(word, 'VBN')
            elif ends_in_ly:
                # guess adverb
                guess_tag = 'RB'
            elif ends_in_ing:
                # guess gerund
                guess_tag = 'VBG'
            elif has_hyphen:
                # guess adjective
                guess_tag = 'JJ'
            else:
                # if the word itself doesn't give us guess clues, look at previous
                # POS and guess the most likely POS to follow it.
                
                # if our POS probabilities are non-zero
                if max(scores_without_word_prob) > 0:
                    
                    # initially, guess the tag which corresponds to highest POS prob
                    guess_tag = self.pos_tags[scores_without_word_prob.index(max(scores_without_word_prob))]
                    
                    # if the result of such guessing is proper noun
                    if guess_tag == 'NNP':
                        # change the guess to common noun (we know word is lowercase)
                        guess_tag = 'NN'
                        
                    # if guess is determiner and we know it's not a det
                    elif guess_tag == 'DT' and word.lower() not in self.det_list:
                        # change guess to common noun
                        guess_tag = 'NN'
                        
                    # if guess is preposition and we know it's not a prep
                    elif guess_tag == 'IN' and word.lower() not in self.prep_list:
                        #change guess to common noun
                        guess_tag = 'NN'
                        
                    # if the guess is adverb and ends in 'er'
                    elif guess_tag == 'RBR' and ends_in_er:
                        # change guess to adjective
                        guess_tag = 'JJR'
                
                # if our POS probabilities are all zero anyway
                else:
                    # make no guess at all!
                    guess_tag = None
                    
        return guess_tag
        
    def fix_tags(self, guessed_pos, pos_tags):
        """
        Examine a list of POS tags, and adjust based on grammatical common sense.
        Use information about whether the tags were guessed in order to fix
        tags based on their position relative to other tags.
        
        :param guessed_pos: list of Booleans corresponding to whether a tag in a
            given sentence position was guessed rather than set by probability
        :param pos_tags: list of POS tags for a sentence
        """
        
        # loop through POS tags
        for j in range(len(pos_tags)):
            
            # if we guessed this tag
            if guessed_pos[j]:
                
                # if we're past the first tag, look at tags which refer to prev tag
                if j > 0:
                    
                    # if we're also not the last, examine tags referring to next tag
                    if j < len(pos_tags) - 1:
                        
                        # if prev tag is det or adj, and next tag is noun or adj,
                        # or next tag was guessed and set to be prep
                        if (pos_tags[j-1] in ['DT','JJ']) and \
                            ((pos_tags[j+1] in ['NNP', 'NNPS', 'NN','NNS','JJ','POS']) or \
                            (guessed_pos[j+1] and pos_tags[j+1] in ['IN'])):
                            
                            # change tag to adjective
                            pos_tags[j] = 'JJ'
                            
                        # if prev tag was guessed and this tag is prep and next tag is ,
                        elif guessed_pos[j-1] and pos_tags[j]=='IN' and pos_tags[j+1]==',':
                            
                            # change tag to noun
                            pos_tags[j] = 'NN'
                    
                    # if this tag is a noun and the prev tag is an adverb
                    if pos_tags[j] in ['NN','NNS'] and pos_tags[j-1] == 'RB':
                        
                        # change tag to adjective
                        pos_tags[j] = 'JJ'
                        
                    # if prev tag is comparative adj or adverb and this tag
                    # is past participle
                    elif pos_tags[j-1] in ['RBR','JJR'] and pos_tags[j]=='VBN':
                        
                        # change tag to adjective
                        pos_tags[j] = 'JJ'
            
            # if tag is 'UNK', change to noun
            if pos_tags[j] == 'UNK':
                pos_tags[j] = 'NN'
                
        return pos_tags
        
    def _best_pos(self, word, pos_list):
        """
        Return the most probable POS for a word given a POS list.
        
        :param word: string word
        :param pos_list: list of POS tuples to consider as options. The first item
            in the tuple is the tag to get probability for. The second is what
            to return if that tag is the highest probability. So ('NN','NNS') means:
            if 'NN' is the highest probability tag for this word, return 'NNS'
        """
        
        max_value = 0 # used to keep track of highest probability
        best_pos = None # used to keep track of high-prob POS tag
        
        # loop through available POS tags
        for pos in pos_list:
            
            # find probability of stem given POS
            prob = self.words_given_pos[pos[0]].freq(word)
            
            # set it to be our candidate if it has highest value
            if prob > max_value:
                max_value = prob
                best_pos = pos[1]
                
        return best_pos
        
    def _guess_s(self, word, def_tag):
        """
        Guess a tag for a word ending in s
        
        :param word: string, word to guess for    
        :param def_tag: tag to return if there is no best guess
        """
        
        # gather additional features about the word
        ends_in_es = word[-2:] == 'es'
        ends_in_ies = word[-3:] == 'ies'
        
        guess_tag = def_tag # set guess_tag to default return value
        ies_tag = None # set 'ies' guess value
        es_tag = None # set 'es' guess value
        tag = None # set default guess value
        
        # if our word ends in ies, e.g., flies
        if ends_in_ies:
            # try finding a noun or verb ending in y
            stem = word[:-3] + "y"
            ies_tag = self._best_pos(stem, [('NN','NNS'), ('VB','VBZ')])
        
        # if we found something, set guess tag
        if ies_tag is not None:
            guess_tag = ies_tag
            
        # otherwise, ask if our word ends in es, e.g. churches
        elif ends_in_es:
            # try finding a noun or verb without the -es
            stem = word[:-2]
            es_tag = self._best_pos(stem, [('NN','NNS'), ('VB','VBZ')])
        
        # if we found something, set guess tag
        if es_tag is not None:
            guess_tag = es_tag
            
        # otherwise, do basic case for word ending in -s, e.g. hides, dogs
        else:
            # try finding a noun/verb without the -s
            stem = word[:-1]
            tag = self._best_pos(stem, [('NN','NNS'), ('VB','VBZ')])
        
        # if we found something, set guess tag
        if tag is not None:
            guess_tag = tag
        
        # otherwise, guess tag is still the default
        return guess_tag
    
    def _guess_ed(self, word, def_tag):
        """
        Guess a tag for a word ending in ed
        
        :param word: string, word to guess for    
        :param def_tag: tag to return if there is no best guess
        """
        
        guess_tag = def_tag # set guess tag to return by default
        
        # find a noun, adjective, or verb participle based on word without 'ed'
        tag = self._best_pos(word[:-2], [('NN','NN'), ('JJ', 'JJ'), ('VB','VBN')])
        
        # if we found something, guess it
        if tag is not None:
            guess_tag = tag
            
        # otherwise, find a verb e.g., chide from chided
        else:
            tag = self._best_pos(word[:-1], [('VB','VBN')])
        
        # if we found something this time, guess it
        if tag is not None:
            guess_tag = tag
            
        return guess_tag