#!/usr/bin/python
__package__ = 'trailbot'

import json, os, sys

from .dispatch import tbroute, tbhelp
from .user import needsreg
from .userdata import UserObj
from .core import TBError, shapedRandomWord
from .db.TWL06 import twl

class FiveError(TBError):
    pass

class NotAWord(FiveError):
    msg = "%s is not a word."


class FiveWord(UserObj):
    """Try to guess the secret five-letter word
in five guesses

After each guess, I'll tell you which letters are
right, and which of those are in the correct
location in the secret word. I'll also show you
all of the letters you guessed so far,
and which ones are part of the secret word.

(If you've ever played  'wordle' on the
NY Times website,  you know how to play
5word.)

say '5word' and your five-letter guess  to start playing,
"""
    WLEN=5
    MAXTURN=5
    MAXSTRIKES=3
    typ = '5word'

    def __init__(self, word='', guessed=None, strikes=None, **kwargs):
        UserObj.__init__(self, **kwargs)
        self.word = word.lower()

        if not guessed: guessed=[]
        self.guessed = guessed

        if not strikes: strikes=[]
        self.strikes = strikes

    @classmethod
    def random(cls, **kwargs):
        word = shapedRandomWord(maxlen=5, minlen=5)
        return cls(word=word, **kwargs)

    def toDict(self):
        return {
            'word': self.word,
            'guessed': self.guessed,
            'strikes' : self.strikes or []
        }

    def parseData(self, d):
        word = d['word']
        assert len(word) == self.WLEN and twl.check(word)
        self.word = word
        self.guessed = d['guessed']
        self.strikes = d.get('strikes') or []

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
        return '\t'.join(out)

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
            self.strikes.append(guess)
            raise NotAWord(guess)

        self.guessed.append(guess)
        if guess == self.word:
            return

        return self.display()

    def didWin(self):
        return  self.guessed and self.guessed[-1] == self.word

    def didLose(self):
        return self.turn > self.MAXTURN or len(self.strikes) >= self.MAXSTRIKES

UserObj.register(FiveWord)

def playFiveWord(user, args):
    args = args.lower()
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

    except NotAWord as e:
        out = str(e)
        left = f.MAXSTRIKES - len(f.strikes)
        if left > 1:
            out += "You have %d strikes left." % left
        elif left == 1:
            out += "One more strike left."
        else:
            out += "No strikes left."

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
        else: out += "\nYou lose."
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

