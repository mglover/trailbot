
class TBMessage(object):
    """
        A single text message to a single phone number,
        must be contained in a TBResponse
    """
    def __init__(self, msg, **kwargs):
        self.msg = msg
        self.kwargs = kwargs
        self.more = ''

    def __repr__(self):
        return "%s %s" %( self.msg, self.kwargs)

    def __eq__(self, other):
        assert type(other) is TBMessage
        return self.msg == other.msg \
            and self.kwargs == other.kwargs

class TBResponse(object):
    """
        A set of TBMessages, each possibly to a different number,
    """
    def __init__(self, *msgs):
        self.msgs = [ TBMessage(m) for m in msgs ]

    def __eq__(self, other):
        assert type(other) is TBResponse
        return self.msgs == other.msgs

    def __len__(self):
        return len(self.msgs)

    def getMore(self):
        if not self.msgs: return ''
        return self.msgs[0].more

    def addMsg(self, msg, **kwargs):
        if type(msg) is not TBMessage:
            msg = TBMessage(msg,**kwargs)
        self.msgs.append(msg)
