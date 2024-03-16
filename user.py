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



class UserDatum(object):
    def __init__(self, user, typ, nam, data):
        self.user = user
        self.data = data
        self.typ = typ
        self.nam = nam

    def save(self):
        savdb = self.user.dbfile('saved')
        if not os.path.exists(savdb):
            os.mkdir(savdb)
        typdb = os.path.join(savdb, self.typ)
        if not os.path.exists(typdb):
            os.mkdir(typdb)
        datafd = open(os.path.join(typdb, self.nam), "w")
        datafd.write(self.data.toJson())

    @classmethod
    def unsave(cls, user, typ, nam):
        savdb = user.dbfile('saved')
        datafile = os.path.join(savdb, typ, nam)
        if not os.path.exists(datafile):
            raise DatumDoesNotExistError(nam)
        os.unlink(datafile)



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
        if phone not in self.subs:
            raise NotSubscribedError(self.handle)
        else:
            self.subs.remove(phone)
        self.save()

    def setStatus(self, status):
        if len(status) > STATUS_MAX:
            raise StatusTooLongError
        if len(status) < STATUS_MIN:
            raise StatusTooShortError
        self.status = status
        self.save()

    def saveData(self, typ, nam, data):
        data = UserDatum(self, typ, nam, data)
        data.save()


    def getData(self, typ, nam):
        db = self.dbfile('saved')
        datafile = os.path.join(db, typ, nam)
        if not os.path.exists(datafile):
            return None
        data = json.load(open(datafile))
        return UserDatum(self, typ, nam, data)


    def eraseData(self, typ, nam):
        userDatum.unset(self, typ, nam)
