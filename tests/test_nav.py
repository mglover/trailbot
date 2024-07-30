from tests.base import TBTest, remote_db

class TestNav(TBTest):
    @remote_db
    def test_drive(self):
        res = self.req1("drive from seattle to portland, or")
        self.assertStartsWith(res, "Driving directions courtesy OSRM")

    @remote_db
    def test_distance(self):
        res = self.req1('distance from seattle to portland, or')
        self.assertStartsWith(res, "Distance courtesy OSRM")

    @remote_db
    def test_drive_here_there(self):
        self.reg1()
        self.assertSuccess(self.req1("here seattle"))
        self.assertSuccess(self.req1("there portland, or"))
        res = self.req1("drive")
        self.assertStartsWith(res, "Driving directions courtesy OSRM")

    @remote_db
    def test_drive_no_here(self):
        self.assertError(self.req1("drive to seattle"))

    @remote_db
    def test_drive_no_there(self):
        self.assertError(self.req1("drive from olympia, wa"))

