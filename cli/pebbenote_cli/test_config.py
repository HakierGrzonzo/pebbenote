import tempfile
from pathlib import Path
from unittest import TestCase, mock

from .config import DEFAULT_BACKEND_URL, DEFAULT_CONFIG, DEFAULT_ISSUER, load_config
from .errors import CliError


class LoadConfigTestCase(TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.config_file = Path(tmp.name) / "pebbenote" / "config.toml"
        patcher = mock.patch("pebbenote_cli.config.CONFIG_FILE", self.config_file)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, text: str) -> None:
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(text)

    def test_missing_file_writes_defaults(self):
        config = load_config()

        self.assertEqual(self.config_file.read_text(), DEFAULT_CONFIG)
        self.assertEqual(config.backend_url, DEFAULT_BACKEND_URL)
        self.assertEqual(config.issuer, DEFAULT_ISSUER)

    def test_custom_values_strip_trailing_slash(self):
        self.write(
            'backend_url = "http://localhost:8000/"\n'
            'issuer = "http://localhost:8080/realms/pebbenote/"\n'
        )
        config = load_config()

        self.assertEqual(config.backend_url, "http://localhost:8000")
        self.assertEqual(config.issuer, "http://localhost:8080/realms/pebbenote")

    def test_missing_keys_fall_back_to_defaults(self):
        self.write('backend_url = "http://localhost:8000"\n')
        config = load_config()

        self.assertEqual(config.backend_url, "http://localhost:8000")
        self.assertEqual(config.issuer, DEFAULT_ISSUER)

    def test_invalid_toml(self):
        self.write("backend_url = \n")
        with self.assertRaises(CliError):
            load_config()
