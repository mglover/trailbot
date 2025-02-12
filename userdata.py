import json, logging, os

from flask import render_template

from .core import TBError
from .user import User

NAM_MAX   = 10

class DatumDoesNotExistError(TBError):
    msg = "No saved data for '%s'"
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

log = logging.getLogger('userdata')

typs = {}

class UserDatum(object):
    """ Low-level get/set/erase interface for user data

    """
    def __init__(self, owner, nam, bytes=None):
        if len(nam) > NAM_MAX:
            raise DatumNameTooLong(nam)
        namOk = nam.isalnum() or nam[0] == '_' and nam[1:].isalnum()
        if not owner or not namOk:
            raise DatumDoesNotExistError(nam)

        self.owner = owner
        self.bytes = bytes
        self.nam = nam

        sdir = self.owner.dbfile("saved")
        if not os.path.exists(sdir):
            os.mkdir(sdir)
        self.path = os.path.join(sdir, self.nam)

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
    def erase(cls, owner, nam):
        self = cls(owner, nam)
        if os.path.exists(self.path):
            os.unlink(self.path)
        else:
            raise DatumDoesNotExistError(self.nam)



class UserObj(object):
    """Permissions, data structure, external api
    """
    typs = []
    typ = None # required to override in subclasses

    @classmethod
    def register(cls, sub):
        cls.typs.append(sub)

    @classmethod
    def search(cls, user, typ=None):
        if not typ: typ=cls.typ
        dnam = user.dbfile("saved")
        if not os.path.exists(dnam):
            os.mkdir(dnam)
        return list(filter(
            lambda o: o and o.typ==typ,
            [cls.lookup(f, user) for f in os.listdir(dnam)]
        ))

    @classmethod
    def getDefault(cls):
        return None

    def __init__(self, nam=None, requser=None, owner=None,
                                readers=None, rawdata=None):
        self.nam = nam
        self.requser = requser
        self.owner = owner
        if self.requser and not self.owner:
            self.owner = self.requser
        self.readers = readers or []
        self.rawdata = rawdata or {}

    def toDict(self):
        raise UnimplementedError


    def parseData(self, data):
        raise UnimplementedError

    def toJson(self):
        return json.dumps({
            'type' : self.typ,
            'readers': self.readers,
            'data':  self.rawdata
        })

    def checkAccess(self, requser):
        # check access
        if '*' in self.readers: return True
        if not requser: return False
        if requser.handle == self.owner.handle: return True
        if '@'+requser.handle in self.readers: return True
        return  False

    @classmethod
    def lookup(cls, nam, requser):
        if nam.startswith('@'):
            try:
                tnam, nam = nam.split('.')
                target = User.lookup(tnam)
            except ValueError as e:
                tnam = nam
                nam = cls.getDefault()
                if not nam:
                    raise DatumDoesNotExistError(nam)
            target = User.lookup(tnam)
        else:
            if type(requser) is not User:
                return None
            target = requser

        try:
            datum = UserDatum(target, nam)
            bytes = datum.load()
            if not bytes:
                return None
            d = json.loads(bytes)
            if not d.get('type'): return None

        except (DatumDoesNotExistError, DatumNameTooLong):
            return None

        tcls = [ tcls for tcls in UserObj.typs
            if tcls.typ==d['type'] ]
        if not tcls:
            return None
        tcls =tcls[0]
        obj = tcls(
            nam=nam,
            requser=requser,
            owner=target,
            readers=d.get('readers', []),
            rawdata = d['data']
        )

        if obj.checkAccess(requser):
            obj.parseData(obj.rawdata)
            return obj
        else:
            return None

    def erase(self):
        assert self.nam is not None and type(self.requser) is User
        assert self.owner == self.requser
        UserDatum.erase(self.requser, self.nam)

    def save(self, nam=None, requser=None):
        if nam: self.nam = nam
        if requser: self.requser = requser
        assert self.nam is not None and type(self.requser) is User
        prevobj = UserObj.lookup(self.nam, self.requser)
        if prevobj:
            assert prevobj.owner == self.owner
            self.readers = prevobj.readers
        else:
            self.owner = self.requser
        self.rawdata = self.toDict()
        datum = UserDatum(self.owner, self.nam, self.toJson())
        datum.save()

    def saveMeta(self):
        assert self.nam is not None
        assert type(self.requser) is User
        assert type(self.owner) is User
        assert self.owner == self.requser
        UserDatum(self.owner, self.nam, self.toJson()).save()

    def share(self, spec):
        if spec != '*' and not spec.startswith('@'):
            raise SharingSpecError(spec)
        if spec in self.readers:
            raise SharingAlreadyError(spec)
        self.readers.append(spec)
        self.saveMeta()

    def unshare(self, spec):
        if spec != '*' and not spec.startswith('@'):
            raise SharingSpecError(spec)
        if spec not in self.readers:
            raise SharingNotSharedError(spec)
        self.readers.remove(spec)
        self.saveMeta()


