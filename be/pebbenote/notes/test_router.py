from datetime import UTC, datetime
from unittest import TestCase

from pebbenote.http_dates import format_http_date

from .router import is_not_modified

UPDATED_AT = datetime(2026, 11, 10, 12, 0, 0, tzinfo=UTC)
NOTE_ID = "00000000-0000-0000-0000-000000000001"


class IsNotModifiedTestCase(TestCase):
    def test_up_to_date_note_is_not_modified(self):
        self.assertTrue(
            is_not_modified(NOTE_ID, UPDATED_AT, format_http_date(UPDATED_AT))
        )

    def test_default_is_always_sent(self):
        # The alias may point at another, older note than the client has
        self.assertFalse(
            is_not_modified("default", UPDATED_AT, format_http_date(UPDATED_AT))
        )
