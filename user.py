##
## status/registration
##
import os, json, shutil
from . import config
from .core import TBError

HANDLE_MIN = 2
HANDLE_MAX = 15
STATUS_MIN = 1
STATUS_MAX = 460

class AlreadySubscribedError(TBError):
    msg = "Already subscribed to @%s"
class NotSubscribedError(TBError):
    msg = "You're not subscribed to @%s"
class HandleTooLongError(TBError):
    msg = "Handle '@%s' is too long.  Max. "+str(HANDLE_MAX)+"  characters"
class HandleTooShortError(TBError):
    msg = "Handle '@%s' is too short.  Min. "+str(HANDLE_MIN)+" characters"
class HandleBadCharsError(TBError):
    msg = "Handle '@%s' is invalid. Letters and numbers only!"
class HandleExistsError(TBError):
    msg = "Handle '@%s' already exists"
class HandleAlreadyYoursError(TBError):
    msg = "The handle @%s is already registered to this phone number"
class PhoneExistsError(TBError):
    msg = "This phone number is already registered with the handle @%s"
class HandleUnknownError(TBError):
    msg = "I don't know any %s"
class StatusTooShortError(TBError):
    msg = "Status is too short. Min. "+str(STATUS_MIN)+" characters"
class StatusTooLongError(TBError):
    msg = "Status is too long. Max. "+str(STATUS_MAX)+" characters"


class RegistrationRequired(TBError):
    msg = \
"""You must register a @handle %s

To register a handle, choose @YourNewHandle
and say 'reg @YourNewHandle"""



def needsreg(reason):
    def fxn(inner):
        def require(req, *args, **kwargs):
            if not req.user:
                raise RegistrationRequired(reason)
            return inner(req, *args, **kwargs)
        return require
    return fxn



class User(object):
    """user data is stored in subdirectories of users
       in files named phone@handle """

    dbpath = os.path.join(config.DB_ROOT,'users')


    def __eq__(self, other):
        if type(other) is not User: return print('notuser') and False
        return self.handle.__eq__(other.handle)

    @classmethod
    def lookup(cls, crit, raiseOnFail=True):
        if crit.startswith('@'):
            fxn = lambda x: x.lower().endswith(crit.lower())
        else:
            fxn = lambda x: x.startswith(crit+'@')
        for f in os.listdir(cls.dbpath):
            if fxn(f):
                return cls(f)
        if raiseOnFail:
            raise HandleUnknownError(crit)
        else:
            return None

    @classmethod
    def register(cls, phone, handle):
        if handle.startswith('@'):
            handle = handle.lstrip('@')

        if len(handle) > HANDLE_MAX:
            raise HandleTooLongError(handle)
        if len(handle) < HANDLE_MIN:
            raise HandleTooShortError(handle)
        if not handle.isalnum():
            raise HandleBadCharsError(handle)

        # both the phone and handle must be unique
        pu = cls.lookup(phone, False)
        hu = cls.lookup('@'+handle, False)

        if pu:
            if pu.handle != handle:
                raise PhoneExistsError(pu.handle)
            else:
                raise HandleAlreadyYoursError(handle)
        elif hu and hu.phone != phone:
            raise HandleExistsError(handle)


        userdir = '%s@%s' % (phone, handle)
        os.mkdir(os.path.join(cls.dbpath, userdir))
        return cls(userdir)

    def unregister(self):
        upath = os.path.join(self.dbpath,self.userdir)
        shutil.rmtree(upath)

    def dbfile(self, fname):
        return os.path.join(self.dbpath, self.userdir, fname)

    def __init__(self, userdir):
        self.userdir = userdir
        self.phone, self.handle = userdir.split('@')
        try:
            with open(self.dbfile('status'), 'rb') as stfd:
                self.status = stfd.read().decode('UTF-8')
        except FileNotFoundError:
            self.status = None
        try:
            with open(self.dbfile('subs')) as sfd:
                self.subs = sfd.read().split('\n')

        except FileNotFoundError:
            self.subs = []
        self.save()

    def save(self):
        if '' in self.subs: self.subs.remove('')
        with open(self.dbfile('subs'), 'w') as sfd:
            sfd.write('\n'.join(self.subs))
        if self.status:
           with  open(self.dbfile('status'),'wb') as stfd:
                stfd.write(self.status.encode('UTF-8'))

    def subscribe(self, phone):
        if phone in self.subs:
            raise AlreadySubscribedError(self.handle)
        else:
            self.subs.append(phone)
            self.save()

    def unsubscribe(self, phone):
        if phone in self.subs:
            self.subs.remove(phone)
            self.save()
        else:
           raise NotSubscribedError(self.handle)


    def setStatus(self, status):
        if len(status) > STATUS_MAX:
            raise StatusTooLongError
        if len(status) < STATUS_MIN:
            raise StatusTooShortError
        self.status = status
        self.save()
