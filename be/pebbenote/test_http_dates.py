from datetime import UTC, datetime, timedelta
from unittest import TestCase

from .http_dates import format_http_date, is_modified_since, last_modified

UPDATED_AT = datetime(2026, 11, 1, 12, 0, 0, 500_000, tzinfo=UTC)


class HttpDatesTestCase(TestCase):
    def test_format(self):
        self.assertEqual(format_http_date(UPDATED_AT), "Sun, 01 Nov 2026 12:00:00 GMT")

    def test_no_header_is_modified(self):
        self.assertTrue(is_modified_since(UPDATED_AT, None))

    def test_same_second_is_not_modified(self):
        header = format_http_date(UPDATED_AT)
        self.assertFalse(is_modified_since(UPDATED_AT, header))

    def test_older_header_is_modified(self):
        self.assertTrue(is_modified_since(UPDATED_AT, "Sun, 01 Nov 2026 11:59:59 GMT"))

    def test_newer_header_is_not_modified(self):
        self.assertFalse(is_modified_since(UPDATED_AT, "Sun, 01 Nov 2026 12:00:01 GMT"))

    def test_garbage_header_is_modified(self):
        self.assertTrue(is_modified_since(UPDATED_AT, "yesterday"))

    def test_last_modified_in_a_past_second(self):
        now = UPDATED_AT + timedelta(seconds=5)
        self.assertEqual(
            last_modified(UPDATED_AT, now), "Sun, 01 Nov 2026 12:00:00 GMT"
        )

    def test_last_modified_never_claims_the_current_second(self):
        now = UPDATED_AT + timedelta(milliseconds=100)
        header = last_modified(UPDATED_AT, now)

        self.assertEqual(header, "Sun, 01 Nov 2026 11:59:59 GMT")
        # A change later in the same second is still seen
        later = UPDATED_AT + timedelta(milliseconds=300)
        self.assertTrue(is_modified_since(later, header))
