import os, shutil

from . import config
from .core import TBError
from .user import User

class GroupAdminDenied(TBError):
    msg = "I'm sorry, only the owner of '#%s' can do that"
class GroupJoinDenied(TBError):
    msg = "I'm sorry, '#%s' requires an invitation to join"
class GroupWriteDenied(TBError):
    msg = "I'm sorry, you don't have posting privileges on'#%s'"
class GroupJoinBanned(TBError):
    msg = "You are banned from '#%s'"
class GroupExistsError(TBError):
    msg = "Group '%s' already exists"
class GroupUnknownError(TBError):
    msg = "I don't know any group named '#%s'"


class ACL(object):
    def __init__(self, grp, nam):
        self.nam = nam
        self.grp = grp
        self.dbpath = os.path.join(grp.dbpath, grp.nam, self.nam)
        self.acl = None

    @classmethod
    def exists(cls, grp, nam):
        dbpath = os.path.join(grp.dbpath, grp.nam, nam)
        return os.path.exists(dbpath)

    @classmethod
    def create(cls, grp, nam):
        self = cls(grp, nam)
        open(self.dbpath, 'w').close()
        return self

    def _load(self):
        fd = open(self.dbpath, 'r')
        self.acl = [a.strip() for a in fd.readlines()]
        fd.close()

    def _save(self):
        fd = open(self.dbpath, 'w')
        fd.writelines("%s\n" % a for a in self.acl)
        fd.close()

    def add(self, user):
        if self.acl is None:
            self._load()
        if user.handle not in self.acl:
            self.acl.append(user.handle)
            self._save()

    def remove(self, user):
        if self.acl is None:
            self._load()
        if user.handle in self.acl:
            self.acl.remove(user.handle)
            self._save()

    def __contains__(self, user):
        if self.acl is None:
            self._load()
        return user.handle in self.acl

    def __iter__(self):
       return iter(self.acl)

class AllowAll(ACL):
    def __init__(self):
        pass

    @classmethod
    def exists(self, *a , **kw):
        return True

    def __contains__(self, user):
        return True

    def add(self, user):
        pass

    def remove(self, user):
        pass


class Group(object):
    dbpath = os.path.join(config.DB_ROOT,'groups')

    def __init__(self, nam, requser):
        self.nam = nam
        self.requser = requser
        self.ohndl, self.tag = nam.split('#')

        self.bans = ACL(self, "ban")
        self.readers = ACL(self, "read")

        if ACL.exists(self, "invite"):
            self.invites = ACL(self, "invite")
        else:
            self.invites = AllowAll()

        if ACL.exists(self, "write"):
            self.writers = ACL(self, 'write')
        else:
            self.writers = self.readers


    @classmethod
    def create(cls, tag, owner, *flags):
        if cls.fromTag(tag, owner, raise_on_fail=False):
            raise GroupExistsError(tag)

        if tag.startswith('#'): tag = tag[1:]
        nam = '#'.join((owner.handle, tag))
        os.mkdir(os.path.join(cls.dbpath, nam))

        self = cls(nam, owner)
        self.bans = ACL.create(self, 'ban')
        self.readers = ACL.create(self, 'read')
        self.readers.add(owner)
        if 'private' in flags:
            self.invites = ACL.create(self, "invite")
        if 'announce' in flags:
            self.writers = ACL.create(self, "write")

        return self

    @classmethod
    def fromTag(cls, tag, requser, raise_on_fail=True):
        if tag.startswith('#'): tag = tag[1:]
        for g in os.listdir(cls.dbpath):
            ohndl, gtag = g.split('#')
            if gtag == tag:
                return cls(g, requser)
        if raise_on_fail:
            raise GroupUnknownError(tag)
        else:
            return None

    def _requireOwner(self):
        if  self.requser.handle != self.ohndl:
            raise GroupAdminDenied(self.tag)

    def destroy(self):
        self._requireOwner()
        shutil.rmtree(os.path.join(self.dbpath, self.nam))

    def invite(self, to_user):
        self._requireOwner()
        self.invites.add(to_user)

    def join(self):
        if self.requser not in self.invites:
            raise GroupJoinDenied(self.tag)
        if self.requser in self.bans:
            raise GroupJoinBanned(self.tag)
        self.readers.add(self.requser)
        self.invites.remove(self.requser)

    def leave(self):
        self.readers.remove(self.requser)

    def kick(self, bad_user):
        self._requireOwner()
        self.readers.remove(bad_user)

    def ban(self, bad_user):
        self._requireOwner()
        self.bans.add(bad_user)

    def getReaders(self):
        if self.requser not in self.writers:
            raise GroupWriteDenied(self.tag)
        else:
            return [User.lookup('@'+nam) for nam in self.readers]


