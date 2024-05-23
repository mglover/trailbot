""" twilio.py
    Low-level interface to sending and receiving messages
    through the Twilio API.
"""
from . import config
from .core import escape

class TBMessage(object):
    """
        A single text message to a single phone number,
        must be contained in a TBResponse
    """
    def __init__(self, msg, **kwargs):
        self.msg = msg
        self.kwargs = kwargs

    def __str__(self):
        return self.msg

    def asTwiML(self):
        resp = '<Message'
        if 'to' in self.kwargs:
            resp+= ' to="%s">' % self.kwargs['to']
        else:
            resp+='>'
        resp += escape(self.msg)[:1500]
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

    def addMsg(self, msg, **kwargs):
        self.msgs.append(TBMessage(msg, **kwargs))

    def asTwiML(self):
        assert len(self.msgs) > 0
        resp = '<?xml version="1.0" encoding="UTF-8"?>'
        resp+= "<Response>"
        for m in self.msgs:
            resp+=m.asTwiML()
        resp+= "</Response>"
        return str(resp)


def smsToPhone(phone, meg):
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
