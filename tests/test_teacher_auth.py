import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from src import app as app_module
from src.auth import hash_password, load_teacher_credentials, verify_password


def make_request(session=None):
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "session": {} if session is None else session,
        }
    )


class TeacherAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.credentials_path = Path(self.temp_dir.name) / "teachers.json"
        self.credentials_path.write_text(
            json.dumps(
                [{"username": "teacher", "password_hash": hash_password("correct horse")}]
            ),
            encoding="utf-8",
        )
        self.credentials_patch = patch.object(
            app_module, "TEACHERS_FILE", self.credentials_path
        )
        self.credentials_patch.start()
        self.activities = deepcopy(app_module.activities)

    def tearDown(self):
        app_module.activities.clear()
        app_module.activities.update(self.activities)
        self.credentials_patch.stop()
        self.temp_dir.cleanup()

    def test_password_hash_verifies_only_matching_password(self):
        password_hash = hash_password("correct horse")

        self.assertTrue(verify_password("correct horse", password_hash))
        self.assertFalse(verify_password("wrong password", password_hash))
        self.assertFalse(verify_password("anything", "not-a-hash"))

    def test_teacher_login_sets_session_and_wrong_password_is_rejected(self):
        session = {}
        request = make_request(session)
        credentials = app_module.TeacherLogin(
            username="teacher", password="correct horse"
        )

        result = app_module.login_teacher(credentials, request)

        self.assertEqual(result["username"], "teacher")
        self.assertEqual(session, {"username": "teacher", "role": "teacher"})

        with self.assertRaises(HTTPException) as error:
            app_module.login_teacher(
                app_module.TeacherLogin(username="teacher", password="incorrect"),
                make_request(),
            )
        self.assertEqual(error.exception.status_code, 401)

    def test_missing_teacher_configuration_returns_service_unavailable(self):
        missing_path = Path(self.temp_dir.name) / "missing.json"
        with patch.object(app_module, "TEACHERS_FILE", missing_path):
            with self.assertRaises(HTTPException) as error:
                app_module.login_teacher(
                    app_module.TeacherLogin(username="teacher", password="password"),
                    make_request(),
                )
        self.assertEqual(error.exception.status_code, 503)

    def test_signup_and_unregister_require_teacher_session(self):
        with self.assertRaises(HTTPException) as error:
            app_module.signup_for_activity(
                "Chess Club", "new-student@mergington.edu", make_request()
            )
        self.assertEqual(error.exception.status_code, 401)

        with self.assertRaises(HTTPException) as error:
            app_module.unregister_from_activity(
                "Chess Club", "michael@mergington.edu", make_request()
            )
        self.assertEqual(error.exception.status_code, 401)

        with self.assertRaises(HTTPException) as error:
            app_module.signup_for_activity(
                "Chess Club",
                "new-student@mergington.edu",
                make_request({"username": "student", "role": "student"}),
            )
        self.assertEqual(error.exception.status_code, 403)

        teacher_request = make_request({"username": "teacher", "role": "teacher"})
        app_module.signup_for_activity(
            "Chess Club", "new-student@mergington.edu", teacher_request
        )
        self.assertIn(
            "new-student@mergington.edu",
            app_module.activities["Chess Club"]["participants"],
        )

        app_module.unregister_from_activity(
            "Chess Club", "new-student@mergington.edu", teacher_request
        )
        self.assertNotIn(
            "new-student@mergington.edu",
            app_module.activities["Chess Club"]["participants"],
        )

    def test_teacher_credentials_file_requires_valid_hashes(self):
        with self.assertRaises(ValueError):
            load_teacher_credentials(self.credentials_path.parent / "missing.json")

        self.credentials_path.write_text(
            json.dumps([{"username": "teacher", "password_hash": "plain-text"}]),
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            load_teacher_credentials(self.credentials_path)


if __name__ == "__main__":
    unittest.main()
