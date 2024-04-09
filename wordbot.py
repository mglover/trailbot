import datetime, time, requests

from flask import render_template

from trailbot import config, tb
from trailbot.user import User, HandleUnknownError
from trailbot.group import Group, GroupUnknownError
from trailbot.word import tournamentWordOfTheDay

baseurl_sending = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json" % config.TWILIO_ACCOUNT_SID

runhr = 18
runmi = 37

class WordBot():
    handle = '@WordBot'
    phone = '+078070001000'
    tag = '#twotd'

    def __init__(self):
        try:
            self.user = User.lookup(self.handle)
            assert self.phone == self.user.phone
        except HandleUnknownError:
            self.user = User.create(self.phone, self.handle)

        try:
            self.group = Group.fromTag(self.tag, self.user)
        except GroupUnknownError:
            self.group = Group.create(self.tag, self.user, 'announce')
        print("Ready")

    def send_to_phone(self, phone, msg):
        data = {
            'Body': msg,
            'MessagingServiceSid': config.TWILIO_MSG_SID,
            'To': phone
        }
        res = requests.post(
            baseurl_sending,
            data=data,
            auth=((config.TWILIO_API_USER, config.TWILIO_API_PASS))
        )
    # XXX check return code?

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
    while True:
        now = datetime.datetime.now()
        if now.hour==runhr and now.minute==runmi:
            print("Sending")
            WordBot().run()
            time.sleep(60)
        time.sleep(60)
