##
## status/registration
##
import config
import os, json
from core import *

HANDLE_MIN = 2
HANDLE_MAX = 15
STATUS_MIN = 1
STATUS_MAX = 300
NAM_MAX   = 8

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
class NotRegisteredError(TBError):
    msg = "You must register a @handle before you can do that. Text 'reg @handle' to register"
class StatusTooShortError(TBError):
    msg = "Status is too short. Min. "+str(STATUS_MIN)+" characters"
class StatusTooLongError(TBError):
    msg = "Status is too long. Max. "+str(STATUS_MAX)+" characters"
class DatumDoesNotExistError(TBError):
    msg = "No saved data for %s"
class DatumEmptyError(TBError):
    msg = "No data to save for %s"
class DatumNameTooLong(TBError):
    msg = "Name '%s' is to long. Max "+str(NAM_MAX)+" characters"
class DatumNameInvalidChars(TBError):
    msg = "Name '%s' must contain letters and numbers only"
class DatumNameInvalid(TBError):
    msg = "Name '%s' not found"

class UserDatum(object):
    def __init__(self, user, nam, bytes=None):
        self.user = user
        self.bytes = bytes
        if len(nam) > NAM_MAX:
            raise DatumNameTooLong(nam)
        if not nam.isalnum():
            raise DatumNameInvalid(nam)

        self.nam = nam
        self.path = os.path.join(self.user.dbfile('saved'), self.nam)
        if not os.path.exists(self.user.dbfile('saved')):
            os.mkdir(self.user.dbfile('saved'))

    def save(self):
        if self.bytes:
            datafd = open(self.path, "w")
            datafd.write(self.bytes)
        else:
            raise DatumEmptyError(self.nam)

    def load(self):
        if not os.path.exists(self.path):
            return None
        else:
            datafd = open(self.path)
            self.bytes = datafd.read()
            return self.bytes

    @classmethod
    def erase(cls, user, nam):
        self = cls(usr, '', nam)
        if os.path.exists(self.path):
            os.unlink(self.path)
        else:
            raise DatumDoesNotExistError(self.nam)



class User(object):
    """user data is stored in subdirectories of users
       in files named phone@handle """

    dbpath = os.path.join(config.DB_ROOT,'users')

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
        for f in os.listdir(upath):
            os.unlink(self.dbfile(f))
        os.rmdir(upath)

    def dbfile(self, fname):
        return os.path.join(self.dbpath, self.userdir, fname)

    def __init__(self, userdir):
        self.userdir = userdir
        self.phone, self.handle = userdir.split('@')
        try:
            self.status = open(self.dbfile('status')).read()
        except FileNotFoundError:
            self.status = None
        try:
            self.subs = open(self.dbfile('subs')).read().split('\n')
        except FileNotFoundError:
            self.subs = []
        self.save()

    def save(self):
        if '' in self.subs: self.subs.remove('')
        open(self.dbfile('subs'), 'w').write('\n'.join(self.subs))
        if self.status:
            open(self.dbfile('status'),'w').write(self.status)

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

    def getObj(self, nam, cls):
        datum = UserDatum(self, nam)
        bytes = datum.load()
        if not bytes: return None
        return cls.fromJson(bytes)

    def saveObj(self, nam, obj):
        datum = UserDatum(self, nam, obj.toJson())
        datum.save()

    def eraseBytes(self, nam):
        userDatum.erase(self, nam)
