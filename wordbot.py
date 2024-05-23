from .bot import ChannelBot
from .word import tournamentWordOfTheDay
from . import tb

class WordBot(ChannelBot):
    handle = '@WordBot'
    phone = '+078070001000'
    tag = '#twotd'
    runhr = 16
    runmin = 16

    def run(self):
        msg= tournamentWordOfTheDay()
        self.send_to_group(msg)


@tb.bp.cli.command('wordbot')
def wordbot():
    WordBot().run()
