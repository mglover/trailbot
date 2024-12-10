import os, shutil, re
from flask import render_template

from . import config
from .core import success, TBError, parseArgs
from .response import TBResponse
from .user import User, needsreg
from .dispatch import tbroute, tbhelp

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
    @classmethod
    def _pathFor(cls, grp, nam):
        return os.path.join(grp.dbpath, grp.nam, nam)

    def __init__(self, grp, nam):
        self.nam = nam
        self.grp = grp
        self.dbpath = self._pathFor(grp, nam)
        self.acl = None

    @classmethod
    def exists(cls, grp, nam):
        return os.path.exists(cls._pathFor(grp, nam))

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

    def symlink(self, nam):
        os.symlink(self.dbpath, self._pathFor(self.grp, nam))

    def __contains__(self, user):
        if self.acl is None:
            self._load()
        return user.handle in self.acl

    def __iter__(self):
        self._load()
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

    @classmethod
    def list(cls):
        return [g for g in os.listdir(cls.dbpath)]

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
            self.writers = AllowAll()


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
        if 'open' not in flags:
            if 'announce' in flags:
                self.writers = ACL.create(self, "write")
            else:
                self.writers = self.readers.symlink("write")
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

    def _isOwner(self):
        return self.requser.handle == self.ohndl

    def _requireOwner(self):
        if not self._isOwner():
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
        if self.requser not in self.writers and not self._isOwner():
            raise GroupWriteDenied(self.tag)
        else:
            return [User.lookup('@'+nam) for nam in self.readers]





@tbroute('group',  cat="chat")
@tbhelp(
"""group -- create a chat group

say 'group #yourgroup'

by default, registered user  can join a group, 
and any member can post messages tothe group.

use the keyword 'private' to require an invitation to join, like this

 group #yourgroup private

use the keyword 'announce' to prevent other members from posting.

to post a message to a group, start your message with the group's #hashtag:

 #yourgroup Hey my peeps!

related commands: ungroup, invite, join, leave
"""
)
@needsreg("to use chat groups")
def group(req):
    flags = req.args.split()
    if len(flags) < 1:
        return "Err? What group do you want to create? say 'group #tag'"
    tag = flags.pop(0)
    g = Group.create(tag, req.user, *flags)
    return success("Group '%s' created" % g.tag)

@tbroute('ungroup', cat="chat")
@tbhelp(
"""ungroup -- remove a chat group

say 'ungroup #yourgroup'

you must be the creator of the group to remove it
this will immediately destroy the group and the list of group members
""")
@needsreg("to use chat groups")
def ungroup(req):
    if not req.args:
        return "Err? You need to give me a group to remove. Say 'ungroup #tag'"
    g = Group.fromTag(req.args, req.user)
    g.destroy()
    return success("Group '%s' removed" % g.tag)

@tbroute('invite', cat='chat')
@tbhelp(
"""invite -- invite a registered user to a chat group

say "invite @handle to #yourgroup"

@handle will be sent a message inviting them to #yourgroup, and if this is
a private group, be allowed to join.

related commands: group, join

""")
@needsreg("to use chat groups")
def invite(req):
    resp = TBResponse()
    parts = dict(parseArgs(req.args, ['to']))
    if '' not in parts:
        return "Err? Invite whom? Say 'invite @handle to @tag'"
    if 'to' not in parts:
        return "Err? Invite to what group? Say 'invite @handle to @tag"
    handle, tag = parts[''], parts['to']
    g = Group.fromTag(tag, req.user)
    to_user = User.lookup(handle)
    g.invite(to_user)
    resp.addMsg(f"@{req.user.handle} has invited you to {tag}." 
        + f"say 'join {tag}' to join",
        to=to_user.phone)
    resp.addMsg(success("%s invited to %s" % (handle, tag)))
    return resp

@tbroute('join', cat="chat")
@tbhelp(
"""join -- join a chat group

say "join #yourgroup"

You will receive all messages posted to the group, and be able to post 
messages to the group (if the group has been set up to allow it).

related commands: group, invite, leave
""")
@needsreg("to use chat groups")
def join(req):
    if not req.args:
        return "Err? What group do you want to join?  Say 'join #tag'"
    g = Group.fromTag(req.args, req.user)
    g.join()
    return success("You have joined #%s" % g.tag)

@tbroute('leave', cat="chat")
@tbhelp(
"""leave -- leave a chat group

say "leave #yourgroup"

You will no longer receive posts from or post messages to #yourgroup

related commands: group, join
""")
@needsreg("to use chat groups")
def leave(req):
    g = Group.fromTag(req.args, req.user)
    g.leave()
    return success("You have left #%s" % g.tag)

@tbroute(re.compile('^#.*$'), cat="chat")
@needsreg("to use chat groups")
def chat(req):
    resp = TBResponse()
    g = Group.fromTag(req.cmd, req.user)
    msg = render_template(
        'chat.txt', group=g, user=req.user, msg=req.args
    )
    for r in g.getReaders():
        resp.addMsg(msg, to=r.phone)
    return resp
