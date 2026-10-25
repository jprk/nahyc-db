"""Base class of the browser (Playwright / Chromium) scenarios in this
directory. They are run by `src/tools/run_tests.py`, which starts the Flask
debug server on the test database and sets H2DB_BASE_URL; run on their own
(no base URL) they are skipped, never pointed at some default server.

Every scenario saves screenshots to H2DB_SHOT_DIR (the runner sets one folder
per session under data/test_screenshots/, gitignored), and fails when a page
raises a JavaScript error, or when a request to OUR server fails or answers
>= 400 without the scenario announcing it with `expect_status()`. Requests to
other hosts (Google Fonts, the icon CDN) are not judged: an outage there is
not a defect of this application."""
import os
import pathlib
import unittest
from urllib.parse import urlparse

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
BASE_URL = os.environ.get("H2DB_BASE_URL")
SHOT_DIR = pathlib.Path(os.environ.get("H2DB_SHOT_DIR")
                        or REPO_ROOT / "data" / "test_screenshots" / "manual")

DESKTOP = {"width": 1280, "height": 900}
PHONE = {"width": 390, "height": 844}


def database_connection():
    """A connection to the TEST database named by the environment, refusing
    anything else — the scenarios create and delete fixture rows."""
    import pymysql
    name = os.environ.get("DB_NAME", "")
    if not name.endswith("_test"):
        raise RuntimeError(f"refusing to touch database {name!r}: not a *_test database")
    return pymysql.connect(host=os.environ["DB_HOST"], port=int(os.environ.get("DB_PORT") or 3306),
                           user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
                           database=name, autocommit=True, cursorclass=pymysql.cursors.DictCursor)


class BrowserTestCase(unittest.TestCase):
    viewport = DESKTOP

    @classmethod
    def setUpClass(cls):
        if not BASE_URL:
            raise unittest.SkipTest("H2DB_BASE_URL is not set — run through src/tools/run_tests.py")
        from playwright.sync_api import sync_playwright
        cls._playwright = sync_playwright().start()
        cls._browser = cls._playwright.chromium.launch()
        SHOT_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "_browser", None):
            cls._browser.close()
            cls._playwright.stop()

    def new_page(self, viewport=None):
        context = self._browser.new_context(viewport=viewport or self.viewport, locale="cs-CZ")
        self.addCleanup(context.close)
        page = context.new_page()
        self.page_errors, self.bad_responses, self._expected = [], [], {}
        host = urlparse(BASE_URL).netloc
        page.on("pageerror", lambda e: self.page_errors.append(str(e)))
        page.on("response", lambda r: self.bad_responses.append((r.status, r.url))
                if urlparse(r.url).netloc == host and r.status >= 400 else None)
        self.addCleanup(self._assert_no_problems)
        page.set_default_timeout(15000)
        return page

    def expect_status(self, path, status):
        """Announce that a request to `path` is meant to answer `status`."""
        self._expected[BASE_URL + path] = status

    def _assert_no_problems(self):
        unexpected = [(s, u) for s, u in self.bad_responses if self._expected.get(u) != s]
        self.assertEqual(self.page_errors, [], "JavaScript errors on the page")
        self.assertEqual(unexpected, [], "requests to the application that failed")

    def goto(self, page, path):
        response = page.goto(BASE_URL + path, wait_until="load")
        page.evaluate("document.fonts.ready")
        return response

    def shot(self, page, name, full_page=True):
        path = SHOT_DIR / f"{type(self).__name__}-{name}.png"
        page.screenshot(path=str(path), full_page=full_page, animations="disabled")
        self.assertGreater(path.stat().st_size, 2000, f"screenshot {path.name} is empty")
        print(f"  screenshot: {path}")
        return path

    def shot_element(self, locator, name):
        path = SHOT_DIR / f"{type(self).__name__}-{name}.png"
        locator.screenshot(path=str(path), animations="disabled")
        self.assertGreater(path.stat().st_size, 2000, f"screenshot {path.name} is empty")
        print(f"  screenshot: {path}")
        return path
