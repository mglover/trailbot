import os, random, datetime
from hashlib import sha1
from flask import request, make_response, render_template

from . import config
from .core import TBError
from .config import DB_ROOT
from .tb import bp
from .dispatch import tbroute, tbhelp, TBUserRequest, internal_dispatch
from .response import TBResponse
from .user import User, RegistrationRequired


AUTH_TIMEOUT=datetime.timedelta(seconds=30*60)

class WebSessionExpired(ValueError):
    pass

class WebUICodeInvalid(TBError):
    msg = "Not a valid WebUI code: %s"

class WebUILoginHelp(TBError):
    msg = "You must provide a handle and a login code."


class WebSession(object):
    cname = "WebUI"
    db =os.path.join(DB_ROOT, 'sessions')
    open_phones = []

    def __init__(self, cookie=None, phone=None, exp=None):
        now = datetime.datetime.now()
        if cookie:
            self.cookie = cookie
        else:
            self.cookie = self._generateCookie()

        if exp and  exp > now:
            self.exp = exp
        else:
            self.exp = None
            phone = None

        if phone:
            self.phone = phone
        else:
            self.phone = self._allocInternalPhone()
            self.exp = now + AUTH_TIMEOUT


    def save(self):
        cf = os.path.join(self.db, self.cookie)
        if self.exp: exps = str(self.exp.timestamp())
        else: exps = ''
        with open(cf, 'w') as fd:
            fd.write("%s\n%s" % (self.phone, exps))

    @property
    def cookies(self):
        return {self.cname: self.cookie or ''}

    @classmethod
    def fromRequest(cls, request):
        try:
            return cls.fromCookie(request.cookies[cls.cname])
        except KeyError:
            return cls(None, None, None)

    @classmethod
    def fromCookie(cls, cookie):
        if not os.path.exists(cls.db):
            os.mkdir(cls.db)
        path = os.path.join(cls.db, cookie)
        if not os.path.exists(path):
            return cls(None, None, None)

        with open(path) as fd:
            phone = fd.readline().strip()
            exps = fd.readline().strip()
            if exps: exp = datetime.datetime.fromtimestamp(float(exps))
            else: exp = None
            return cls(cookie, phone, exp)

    @classmethod
    def _generateCookie(cls):
        rnd = ''.join([ chr(random.randint(0,256)) for r in range(16) ])
        return sha1(rnd.encode()).hexdigest()


    @classmethod
    def _allocInternalPhone(cls):
        pfx = config.INTERNAL_NUMBER_PREFIX
        num = pfx + "%06d" % random.randint(0,9999)
        if num in cls.open_phones:
            return cls._allocInternalPhone()
        cls.open_phones.append(num)
        return num


class LoginCode(object):
    db = os.path.join(DB_ROOT, 'otp')
    if not os.path.exists(db):
        os.mkdir(db)

    @classmethod
    def generate(cls, user):
        code = "%06d" % random.randint(0, 999999)
        exp = datetime.datetime.now()+AUTH_TIMEOUT
        exps = str(exp.timestamp())
        path = os.path.join(cls.db, user.handle)
        with open(path, 'w') as fd:
            fd.write( "%s\n%s" % (code, exps) )
        return code

    @classmethod
    def validate(cls, user, code1):
        path = os.path.join(cls.db, user.handle)
        if not os.path.exists(path):
            raise WebUICodeInvalid(user.handle)
        with open(path) as fd:
            code2 = fd.readline().strip()

            exps = fd.readline().strip()
        exp = datetime.datetime.fromtimestamp(float(exps))
        now = datetime.datetime.now()
        if code1 != code2 or now > exp :
            raise WebUICodeInvalid(code1)
        return exp



@tbroute('webui')
@tbhelp("""webui -- use Trailbot's web interface
you can say: 'webui enable' from your phone to get a web code
    'webui login <handle> <code>' from the web ui to log in
    'webui logout' from anywhere, to close the web session""")
def webui(req):
    args = req.args.split()

    if len(args) < 1:
        return "webui what? say 'help webui' for help"
    cmd = args[0]
    if cmd == 'enable':
        if not req.user:
            raise RegistrationRequired("to enable the WebUI")
        # XXX ensure this is a true user
        otp = LoginCode.generate(req.user)
        return "Your WebUI login code is: %s." % otp

    elif cmd == 'login':
        try:
            handle, code = args[1:3]
        except ValueError:
            raise WebUILoginHelp()

        user = User.lookup(handle)
        session = WebSession.fromRequest(req)
        exp = LoginCode.validate(user, code)
        session.phone = user.phone
        session.save()
        left = exp - datetime.datetime.now()
        return "Signed in as @%s. Expires in %s minutes" % \
            (user.handle, left.seconds//60)

    elif cmd == 'logout':
        session = WebSession.fromRequest(req)
        session.phone = None
        session.save()
        return "Signed out. Thanks for using the WebUI!"

    else:
        return "Err? I don't understand %s" % cmd


@bp.route('/api', methods=['GET','POST'])
def api_reply():
    body = request.args.get('body')
    session = WebSession.fromRequest(request)
    session.save()
    try:
        tbreq = TBUserRequest(session.phone, body, cookies=session.cookies)
    except EmptyRequest:
        return ''
    tbresp = internal_dispatch(tbreq)
    resp = make_response(tbresp.msgs[0].msg)
    for k,v in session.cookies.items():
        resp.set_cookie(k, v)
    return resp

@bp.route('/webui')
def webui_html():
    session = WebSession.fromRequest(request)
    resp = make_response(render_template('webui.html'))
    for k,v in session.cookies.items():
        resp.set_cookie(k, v)
    return resp

