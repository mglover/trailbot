""" twilio.py
    Low-level interface to sending and receiving messages
    through the Twilio API.
"""
import requests
from . import config
from .core import escape

MSG_MAX_LEN=1500

class TBMessage(object):
    """
        A single text message to a single phone number,
        must be contained in a TBResponse
    """
    def __init__(self, msg, **kwargs):
        self.msg = msg
        self.kwargs = kwargs
        self.more = ''

    def __str__(self):
        return self.msg

    def asTwiML(self):
        resp = '<Message'
        if 'to' in self.kwargs:
            resp+= ' to="%s">' % self.kwargs['to']
        else:
            resp+='>'
        if  self.kwargs.get('noescape'):
            emsg = self.msg
        else:
            emsg = escape(self.msg)
        resp += emsg[:MSG_MAX_LEN]
        self.more = emsg[MSG_MAX_LEN:]
        resp += "</Message>"
        return resp


class TBResponse(object):
    """
        A set of TBMessages, each possibly to a different number,
        sent in response to an incoming message
    """
    def __init__(self):
        self.msgs = []

    def __len__(self):
        return len(self.msgs)

    def getMore(self):
        if not self.msgs: return ''
        return self.msgs[0].more

    def addMsg(self, msg, **kwargs):
        if type(msg) is not TBMessage:
            msg = TBMessage(msg,**kwargs)
        self.msgs.append(msg)

    def asTwiML(self):
        assert len(self.msgs) > 0
        resp = '<?xml version="1.0" encoding="UTF-8"?>'
        resp+= "<Response>"
        for m in self.msgs:
            resp+=m.asTwiML()
        resp+= "</Response>"
        return str(resp)


baseurl_sending = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json" % config.TWILIO_ACCOUNT_SID

def smsToPhone(phone, msg):
    """
        A single message, sent to a single phone number,
        *not* in  response to an incoming message
    """
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
