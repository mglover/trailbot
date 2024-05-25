from tests.base import TBTest

class TestGroupCreate(TBTest):
    def tearDown(self):
        self.req1('ungroup #chat1')
        super().tearDown()

    def test_group(self):
        self.reg1()
        res = self.req1('group #chat1')
        self.assertSuccess(res)

    def test_group_exists(self):
        self.reg1()
        self.req1('group #chat1')
        res= self.req1('group #chat1')
        self.assertStartsWith(res, "Group '#chat1' already exists")
        pass

    def test_group_unreg(self):
        res = self.req1("group #chat1")
        self.assertStartsWith(res, "You must register")

    def test_group_empty(self):
        self.reg1()
        res = self.req1("group")
        self.assertStartsWith(res, "Err?")

    def test_ungroup(self):
        self.reg1()
        self.req1("group #chat1")
        res = self.req1("ungroup #chat1")
        self.assertSuccess(res)

    def test_ungroup_notyours(self):
        self.reg1()
        self.reg2()
        self.req2("group #chat2")
        res = self.req1("ungroup #chat2")
        self.assertStartsWith(res, "I'm sorry, only the owner")

    def test_ungroup_empty(self):
        self.reg1()
        res = self.req1("ungroup")
        self.assertStartsWith(res, "Err?")


class TestGroupUse(TBTest):
    def setUp(self):
        super().setUp()
        self.reg1()
        self.reg2()
        self.req1("group #chat1")
        self.req2("group #chat2 private")
        self.req1("group #chat3 open")

    def tearDown(self):
        self.req1("ungroup #chat1")
        self.req2("ungroup #chat2")
        super().tearDown()

    def test_invite(self):
        res = self.req1('invite @test2 to #chat1', only_first=False)
        self.assertEqual(len(res), 2)
        m1,m2 = res.msgs
        self.assertSuccess(str(m2))
        self.assertStartsWith(str(m1), "@test1 has invited")

    def test_invite_notyours(self):
        res = self.req1('invite @test2 to #chat2')
        self.assertStartsWith(res, "I'm sorry, only the owner")

    def test_invite_empty(self):
        res = self.req1("invite")
        self.assertStartsWith(res, "Err?")

    def test_join_public(self):
        res = self.req2('join #chat1')
        self.assertSuccess(res)

    def test_join_invite(self):
        self.req2("invite @test1 to #chat2")
        res = self.req1("join #chat2")
        self.assertSuccess(res)

    def test_join_no_invite(self):
        res = self.req1("join #chat2")
        self.assertStartsWith(res, "I'm sorry, '#chat2' requires an invitation")

    def test_join_empty(self):
        res = self.req1("join")
        self.assertStartsWith(res, "Err?")

    def test_leave(self):
        pass


class TestGroupChat(TestGroupUse):
    def test_chat(self):
        self.req2("join #chat1")
        res = self.req2("#chat1 hello", only_first=False)
        self.assertEqual(2, len(res))

    def test_chat_nojoin(self):
        res = self.req2("#chat1 hello")
        self.assertStartsWith(res, "I'm sorry, you don't have posting")

    def test_chat_nojoin_open(self):
        res = self.req2("#chat3 hello", only_first=False)
        self.assertEqual(1, len(res))
        self.assertStartsWith(str(res.msgs[0]),"From @test2 in #chat3:\nhello")
