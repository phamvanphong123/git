#kiem thu tu dong vaf kiem tra nguon vao hop ly
import os
import tempfile
import unittest

import app as xyz
import db

PW = db.DEMO_PASSWORD


class Base(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        xyz.app.config.update(DATABASE=self.path, TESTING=True)
        db.init_db(self.path)
        self.c = xyz.app.test_client()

    def tearDown(self):
        os.remove(self.path)

    def login(self, email, pw=PW):
        self.c.get("/login")
        with self.c.session_transaction() as s:
            token = s["csrf"]
        return self.c.post("/login", data={"email": email, "password": pw, "csrf": token})


class LoginTests(Base):
    def test_form_is_shown(self):                                   # US01-AC1
        r = self.c.get("/login")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Email công ty", r.get_data(as_text=True))

    def test_redirect_by_role(self):                                # US01-AC3
        for email, path in [("employee@xyz.com", "/employee"), ("organizer@xyz.com", "/organizer"),
                            ("admin@xyz.com", "/admin")]:
            with self.subTest(email=email):
                self.setUp()
                r = self.login(email)
                self.assertEqual(r.status_code, 302)
                self.assertTrue(r.headers["Location"].endswith(path))

    def test_wrong_password_and_unknown_email(self):               # US01-AC2
        for email, pw in [("employee@xyz.com", "sai"), ("khong.co@xyz.com", PW)]:
            r = self.login(email, pw)
            self.assertEqual(r.status_code, 200)
            self.assertIn("thong tin dang nhap khong chinh xac", r.get_data(as_text=True))

    def test_empty_fields(self):
        r = self.login("", "")
        self.assertIn("Vvui long nhap lai mat khau", r.get_data(as_text=True))

    def test_locked_account(self):
        r = self.login("locked@xyz.com")
        self.assertIn("đã bị khóa", r.get_data(as_text=True))

    def test_post_without_csrf_rejected(self):
        r = self.c.post("/login", data={"email": "employee@xyz.com", "password": PW})
        self.assertEqual(r.status_code, 400)

    def test_must_login_and_role_checked_on_server(self):         # BR08, BR09
        self.assertEqual(self.c.get("/employee").status_code, 302)
        self.login("employee@xyz.com")
        self.assertEqual(self.c.get("/admin").status_code, 403)
        self.assertEqual(self.c.get("/organizer").status_code, 403)

    def test_logout(self):
        self.login("employee@xyz.com")
        self.c.get("/employee")                      # trang có nút Đăng xuất -> có token CSRF
        with self.c.session_transaction() as s:
            token = s["csrf"]
        self.c.post("/logout", data={"csrf": token})
        self.assertEqual(self.c.get("/employee").status_code, 302)


class EventListTests(Base):
    def setUp(self):
        super().setUp()
        self.login("employee@xyz.com")

    def page(self, qs=""):
        return self.c.get("/employee" + qs).get_data(as_text=True)

    def test_columns_and_statuses(self):                            # US02-AC1
        html = self.page()
        for col in ["ten su kien", "thoi gian", "dia diem", "nguoi to chuc", "so luong toi da",
                    "da dang ky", "tranf thai"]:
            self.assertIn(col, html)
        for s in xyz.STATUSES:
            self.assertIn(s, html)

    def test_search_by_name(self):                                  # US02-AC2
        html = self.page("?q=workshop")
        self.assertIn("Workshop AI", html)
        self.assertNotIn("Team building", html)

    def test_search_special_chars_are_literal(self):
        self.assertIn("khong co su kien nao khop", self.page("?q=%25"))
        self.assertIn("khong co su kien nao khop", self.page("?q=' OR 1=1 --"))

    def test_filter_by_status(self):
        html = self.page("?status=Đã+hết+chỗ")
        self.assertIn("kham suc khoe dinh ky", html)
        self.assertNotIn("Workshop AI", html)
        self.assertIn("hoi thao chuyen doi so", self.page("?status=Đã+hủy"))

    def test_filter_by_department(self):
        html = self.page("?dept=2")
        self.assertIn("Team building", html)
        self.assertNotIn("Workshop AI", html)

    def test_filter_by_date(self):
        self.assertIn("khong hop le", self.page("?from=abc"))
        self.assertIn("phai truoc", self.page("?from=2030-02-01&to=2030-01-01"))
        self.assertIn("khong co su kien nao khop", self.page("?from=2000-01-01&to=2000-01-02"))

    def test_registered_count_ignores_cancelled(self):
        with xyz.app.app_context():
            conn = db.get_db()
            conn.execute("UPDATE registrations SET status='Cancelled' WHERE event_id=2")
            conn.commit()
            self.assertEqual(db.query_one("SELECT COUNT(*) c FROM registrations WHERE event_id=2 "
                                          "AND status IN ('Registered','Confirmed','Attended')")["c"], 0)
        html = self.page("?q=Khám")
        self.assertIn('chip open', html)             # hết người đăng ký -> lại còn chỗ
        self.assertNotIn('chip full', html)


if __name__ == "__main__":
    unittest.main()
