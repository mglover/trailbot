""" twilio.py
    Low-level interface to sending and receiving messages
    through the Twilio API.
"""
import logging, requests
from . import config
from .core import escape

MSG_MAX_LEN=1500

baseurl_sending = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json" % config.TWILIO_ACCOUNT_SID

log = logging.getLogger('twilio')

def twiMLfromMessage(self):
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


def twiMLfromResponse(self):
    assert len(self.msgs) > 0
    resp = '<?xml version="1.0" encoding="UTF-8"?>'
    resp+= "<Response>"
    for m in self.msgs:
        resp+=twiMLfromMessage(m)
    resp+= "</Response>"
    return str(resp)


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
    log.info( "twilio to %s: %s" % (phone, msg) )
    res = requests.post(
        baseurl_sending,
        data=data,
        auth=((config.TWILIO_API_USER, config.TWILIO_API_PASS))
    )
