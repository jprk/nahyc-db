"""src/tools/backup_db.py without a database: the name of the backup file and the
dump command (one transaction, no password on the command line)."""
import datetime
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import backup_db  # noqa: E402


class BackupDbTestCase(unittest.TestCase):
    def test_the_file_name_follows_the_backups_made_by_hand(self):
        path = backup_db.backup_path("/b", "h2regdocs", "before harvest/weekly", datetime.datetime(2026, 11, 19, 8, 5, 1))
        self.assertEqual(path, pathlib.Path("/b/h2regdocs_20261119_080501_before_harvest_weekly.sql.gz"))

    def test_the_dump_runs_in_one_transaction_without_the_password(self):
        env = {"DB_HOST": "localhost", "DB_PORT": "3306", "DB_USER": "u", "DB_PASSWORD": "secret", "DB_NAME": "h2"}
        with mock.patch.object(backup_db.testdb, "_client", return_value="/usr/bin/mariadb-dump"):
            command = backup_db.dump_command(env)
        self.assertIn("--single-transaction", command)
        self.assertEqual(command[-1], "h2")
        self.assertNotIn("secret", " ".join(command))


if __name__ == "__main__":
    unittest.main()
