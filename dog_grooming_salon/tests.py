import os
import unittest
from unittest.mock import mock_open, patch, Mock
from django.test import TestCase
from sendgrid import SendGridAPIClient
from sendgrid.base_interface import BaseInterface
from sendgrid.helpers.mail import SendGridException

from .utils import load_config, DogGroomingEmail


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

    @patch('builtins.open', mock_open())
    def test_03_load_config_without_config_file_when_none(self):
        """Tests loading the config file when it does not exist."""
        config = load_config()
        self.assertDictEqual(config, {})


class DogGroomingEmailTestCase(TestCase):
    """
    Test cases for the DogGroomingEmail class.
    """

    def test_01_email_when_not_testing(self):
        """Tests sending an email when it is not in testing mode."""
        with self.settings(TEST_MODE=False):
            with patch.object(DogGroomingEmail, '__init__', return_value=None):
                with patch.object(SendGridAPIClient, '__init__', return_value=None):
                    with patch.object(BaseInterface, 'send', return_value='response'):
                        mail = DogGroomingEmail()
                        mail.email_config = {'sendgrid_api_key': 'abc123'}
                        mail.mail = Mock()
                        response = mail.send()
        self.assertEqual(response, 'response')

    def test_02_email_when_testing(self):
        """Tests sending an email when it is in testing mode."""
        with self.settings(TEST_MODE=True):
            with patch.object(DogGroomingEmail, '__init__', return_value=None):
                mail = DogGroomingEmail()
                response = mail.send()
        self.assertIsNone(response)

    def test_03_email_with_error(self):
        """Tests sending an email when it throws an error."""
        with self.settings(TEST_MODE=False):
            with patch.object(DogGroomingEmail, '__init__', return_value=None):
                with patch.object(SendGridAPIClient, '__init__', return_value=None):
                    with patch.object(BaseInterface, 'send', side_effect=SendGridException):
                        mail = DogGroomingEmail()
                        mail.email_config = {'sendgrid_api_key': 'abc123'}
                        mail.mail = Mock()
                        response = mail.send()
        self.assertIsNone(response)
