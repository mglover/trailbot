#!/usr/bin/python
__package__ = 'trailbot'

import json, os, sys

from .dispatch import tbroute, tbhelp
from .userdata import UserObj, needsreg
from .core import randomWord
from .db.TWL06 import twl

class FiveError(Exception):
    pass


class FiveWord(UserObj):
    """ Try to guess the secret five-letter word
in six guesses

After each guess, I'll tell you which
letters are right, and which of those 
are in which  are in the correct location
in the secret word. I'll also show you
all of the letters you guessed so far,
and which ones are part of the secret word.

(If you've ever played  'wordle' on the
NY Times website,  you know how to play
5word.)

say '5word' and your five-letter guess  to start playing,
"""
    WLEN=5
    MAXTURN=6
    typ = '5word'

    def __init__(self, word='', guessed=None, **kwargs):
        UserObj.__init__(self, **kwargs)
        self.word = word.lower()
        if not guessed: guessed=[]
        self.guessed = guessed

    @classmethod
    def random(cls, **kwargs):
        word = None
        while not word or len(word) != 5:
            word = randomWord()
        return cls(word=word, **kwargs)

    def toDict(self):
        return {
            'word': self.word,
            'guessed': self.guessed
        }

    def parseData(self, d):
        word = d['word']
        assert len(word) == self.WLEN and twl.check(word)
        self.word = word
        self.guessed = d['guessed']

    @property
    def turn(self):
        return len(self.guessed) + 1

    def display(self):
        if not self.guessed:
            return self.__doc__

        out = [ self.displayGuess(g) for g in self.guessed ]
        out.append( self.displayLetters() )
        return '\n'.join(out)

    def displayGuess(self, guess):
        out = list('*'*5)
        unguessed = list(self.word)

        # check exact location match first
        for idx in range(len(guess)):
            g = guess[idx]
            if self.word[idx] == g:
                out[idx] = g.upper()
                unguessed.remove(g)

        # check letter in word
        for idx in range(len(guess)):
            g = guess[idx]
            if out[idx] == '*' and  g in unguessed:
                out[idx] = g.lower()
                unguessed.remove(g)
        return ' '.join(out)

    def displayLetters(self):
        o=[]
        for l in 'abcdefghijklmnopqrstuvwxyz':
            if l in ''.join(self.guessed):
                if l in self.word:
                    o.append(l.upper())
                else:
                    o.append(' ')
            else:
                o.append(l.lower())
        return ' '.join(o)

    def doGuess(self, guess):
        if len(guess) != 5:
            raise FiveError( "Must guess five letters")

        if not twl.check(guess):
            raise FiveError ('%s is not a word' % guess)

        self.guessed.append(guess)
        if guess == self.word:
            return

        return self.display()

    def didWin(self):
        return  self.guessed and self.guessed[-1] == self.word

    def didLose(self):
        return self.turn > self.MAXTURN

UserObj.register(FiveWord)

def playFiveWord(user, args):
    f = FiveWord.lookup('_5word', requser=user)
    if f is None:
        f = FiveWord.random(requser=user, nam="_5word")


    if not args:
        out =  f.display()
        out+= "\nsay '5word quit' to quit"
        return out

    if args == 'quit':
        f.erase()
        return "You have quit.\nWord was %s" % f.word.upper()

    try:
        out = f.doGuess(args)
    except FiveError as e:
        return str(e)

    won = f.didWin()
    lost = f.didLose()
    word = f.word.upper()
    if not won and not lost:
        f.save()
        return out

    else:
        f.erase()
        if won: out = "You win!"
        else: out = "You lose."
        return out + "\nWord was %s" %  word


@needsreg("to play 5word")
@tbroute('5word')
@tbhelp(FiveWord.__doc__)
def fiveword(req):
    return playFiveWord(req.user, req.args)


if __name__ == '__main__':
    from .user import User
    user = User.lookup('@mg')
    print( playFiveWord(user, ' '.join(sys.argv[1:])) )

