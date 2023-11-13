import unittest
from unittest.mock import mock_open, patch

from .utils import load_config


class ProjectUtilsTestCase(unittest.TestCase):
    """
    Test cases for the project utils library.
    """

    @patch('builtins.open', mock_open(read_data='key: value'))
    def test_01_load_config_with_config_file(self):
        """Tests loading the config file when it exists."""
        config = load_config()
        self.assertDictEqual(config, {'key': 'value'})

    def test_02_load_config_without_config_file(self):
        """Tests loading the config file when it does not exist."""
        mo = mock_open()
        with patch('builtins.open', mo) as mocked_open:
            mocked_open.side_effect = FileNotFoundError
            config = load_config()
        self.assertDictEqual(config, {})
