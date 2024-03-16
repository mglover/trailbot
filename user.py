##
## status/registration
##
import os, json, shutil
from . import config
from .core import *

HANDLE_MIN = 2
HANDLE_MAX = 15
STATUS_MIN = 1
STATUS_MAX = 460
NAM_MAX   = 10

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

class SharingSpecError(TBError):
    msg = "Can't share with %s: must be handle"
class SharingAlreadyError(TBError):
    msg = "Already sharing with %s"
class SharingNotSharedError(TBError):
    msg = "Not sharing with %s"


class UserDatum(object):
    """ Low-level get/set/erase interface for user data
    """
    def __init__(self, user, nam, bytes=None):
        self.user = user
        self.bytes = bytes
        if len(nam) > NAM_MAX:
            raise DatumNameTooLong(nam)
        if not user or not nam.isalnum():
            raise DatumDoesNotExistError(nam)

        self.nam = nam
        self.path = os.path.join(self.user.dbfile('saved'), self.nam)
        if not os.path.exists(self.user.dbfile('saved')):
            os.mkdir(self.user.dbfile('saved'))

    def save(self):
        if self.bytes:
            with open(self.path, "w") as datafd:
                datafd.write(self.bytes)
        else:
            raise DatumEmptyError(self.nam)

    def load(self):
        if not os.path.exists(self.path):
            return None
        else:
            with open(self.path) as datafd:
               self.bytes = datafd.read()
               return self.bytes

    @classmethod
    def erase(cls, user, nam):
        self = cls(user, nam)
        if os.path.exists(self.path):
            os.unlink(self.path)
        else:
            raise DatumDoesNotExistError(self.nam)


class UserObj(object):
    typ = None
    def __init__(self):
        self.owner = None
        self.readers = []
        self.raw = {}
        self.rawtyp = None

    def toJson(self):
        if self.typ:
            typ = self.typ
            d = self.toDict()
        else:
            typ = self.rawtyp
            d = self.raw
        return json.dumps({
            'type' : typ,
            'owner': self.owner,
            'readers': self.readers,
            'data':  d
        })

    @classmethod
    def fromJson(cls, jsbytes):
        d = json.loads(jsbytes)
        if cls.typ:
            if 'data' in d:
                obj = cls.fromDict(d['data'])
            else:
                obj = cls.fromDict(d)
        else:
            obj = cls()
            obj.raw = d['data']
            obj.rawtyp = d['type']
        obj.readers = d.get('readers', [])
        obj.owner = d.get('owner')
        return obj

    @classmethod
    def lookup(cls, nam, requser):
        if nam.startswith('@'):
            parts = nam.split('.')
            target = User.lookup(parts[0])

            if len(parts) > 1:
                nam = parts[1]
            else:
                nam = cls.getDefault()
        else:
            target = requser
            #nam = nam

        try:
            datum = UserDatum(target, nam)
        except (DatumDoesNotExistError,DatumNameTooLong):
            return None
        bytes = datum.load()
        if not bytes:
            return None
        obj = cls.fromJson(bytes)

        # check access
        if '*' in obj.readers: return obj
        if not requser: return None 
        if requser.handle == target.handle: return obj
        if '@'+requser.handle in obj.readers: return obj
        return None


    def share(self, spec):
        if spec != '*' and not spec.startswith('@'):
            raise SharingSpecError(spec)
        if spec in self.readers:
            raise SharingAlreadyError(spec)
        self.readers.append(spec)

    def unshare(self, spec):
        if spec != '*' and not spec.startswith('@'):
            raise SharingSpecError(spec)
        if spec not in self.readers:
            raise SharingNotSharedError(spec)
        self.readers.remove(spec)



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
        shutil.rmtree(upath)

    def dbfile(self, fname):
        return os.path.join(self.dbpath, self.userdir, fname)

    def __init__(self, userdir):
        self.userdir = userdir
        self.phone, self.handle = userdir.split('@')
        try:
            with open(self.dbfile('status')) as stfd:
                self.status = stfd.read()
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
           with  open(self.dbfile('status'),'w') as stfd:
                stfd.write(self.status)

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

    def saveObj(self, nam, obj, preserve_meta=True):
        prevobj = UserObj.lookup(nam, self)
        if prevobj and preserve_meta:
            obj.readers = prevobj.readers
        # NB @handle.name doesn't get parsed here,
        # so any attempts to modify others data will fail
        datum = UserDatum(self, nam, obj.toJson())
        datum.save()


    def eraseObj(self, nam):
        UserDatum.erase(self, nam)

    def shareObj(self, nam, spec):
        obj = UserObj.lookup(nam, self)
        obj.share(spec)
        self.saveObj(nam, obj, preserve_meta=False)

    def unshareObj(self, nam, spec):
        obj = UserObj.lookup(nam, self)
        obj.unshare(spec)
        self.saveObj(nam, obj, preserve_meta=False)
