import unittest
from testrail_mcp.testrail_client import TestRailClient


def make_client(responses):
    """Client whose _send_request returns queued responses and records URIs."""
    c = TestRailClient("https://example.testrail.io", "u", "k")
    c.calls = []
    queue = list(responses)

    def fake(method, uri, data=None):
        c.calls.append(uri)
        return queue.pop(0)

    c._send_request = fake
    return c


def wrapper(key, items, offset=0, nxt=None):
    return {"offset": offset, "limit": 250, "size": len(items),
            "_links": {"next": nxt, "prev": None}, key: items}


class GetListTests(unittest.TestCase):
    def test_unwraps_paginated_projects(self):
        c = make_client([wrapper("projects", [{"id": 1}, {"id": 2}])])
        self.assertEqual(c.get_projects(), [{"id": 1}, {"id": 2}])

    def test_accepts_bare_list(self):
        c = make_client([[{"id": 1}]])
        self.assertEqual(c.get_runs(5), [{"id": 1}])

    def test_follows_pages_with_offset(self):
        c = make_client([
            wrapper("cases", [{"id": 1}, {"id": 2}], nxt="/api/v2/get_cases/9&offset=2"),
            wrapper("cases", [{"id": 3}], offset=2),
        ])
        self.assertEqual(c.get_cases(9), [{"id": 1}, {"id": 2}, {"id": 3}])
        self.assertEqual(c.calls, ["get_cases/9", "get_cases/9&offset=2"])

    def test_suite_id_and_offset_combine(self):
        c = make_client([
            wrapper("cases", [{"id": 1}], nxt="x"),
            wrapper("cases", [{"id": 2}]),
        ])
        c.get_cases(9, suite_id=4)
        self.assertEqual(c.calls, ["get_cases/9&suite_id=4", "get_cases/9&suite_id=4&offset=1"])

    def test_no_suite_id_adds_no_query(self):
        c = make_client([wrapper("sections", [])])
        self.assertEqual(c.get_sections(3), [])
        self.assertEqual(c.calls, ["get_sections/3"])

    def test_unexpected_shape_raises(self):
        c = make_client([{"error": "nope"}])
        with self.assertRaises(Exception):
            c.get_projects()

    def test_page_limit_raises_not_truncates(self):
        c = make_client([wrapper("tests", [{"id": 1}], nxt="x")] * 3)
        c.MAX_PAGES = 3
        with self.assertRaises(Exception):
            c.get_tests(7)

    def test_endpoint_keys(self):
        for method, arg, uri, key in [
            ("get_tests", 7, "get_tests/7", "tests"),
            ("get_suites", 2, "get_suites/2", "suites"),
            ("get_results", 8, "get_results/8", "results"),
            ("get_results_for_run", 7, "get_results_for_run/7", "results"),
            ("get_datasets", 2, "get_datasets/2", "datasets"),
        ]:
            c = make_client([wrapper(key, [{"id": 1}])])
            self.assertEqual(getattr(c, method)(arg), [{"id": 1}])
            self.assertEqual(c.calls, [uri])


if __name__ == "__main__":
    unittest.main()
