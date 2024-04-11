import datetime, time

from flask import render_template

from trailbot import tb
from trailbot.bot import Bot
from trailbot.group import Group, GroupUnknownError
from trailbot.word import tournamentWordOfTheDay

runhr = 16
runmi = 16

class WordBot(Bot):
    handle = '@WordBot'
    phone = '+078070001000'
    tag = '#twotd'

    def __init__(self):
        Bot.__init__(self)
        print("%s at %d:%02d" % (self.handle, runhr, runmi))
        try:
            self.group = Group.fromTag(self.tag, self.user)
        except GroupUnknownError:
            self.group = Group.create(self.tag, self.user, 'announce')
        print("Ready.")

    def trigger(self):
        now = datetime.datetime.now()
        return now.hour== runhr and now.minute==runmi

    def send_to_group(self, body):
        head = "From @%s in #%s" % (self.user.handle, self.group.tag)
        msg = '#%s: %s' % (head, body)
        msg = render_template(
            'chat.txt',
            user=self.user, group=self.group, msg=body
        )
        i=0
        for user in self.group.getReaders():
            self.send_to_phone(user.phone, msg)
            i+=1
        print('sent to %d users' % i)

    def run(self):
        msg= tournamentWordOfTheDay()
        self.send_to_group(msg)


@tb.bp.cli.command('wordbot')
def wordbot():
    bot = WordBot()
    while True:
        now = datetime.datetime.now()
        if bot.trigger():
            print("Sending")
            bot.run()
            time.sleep(60)
        time.sleep(60)
