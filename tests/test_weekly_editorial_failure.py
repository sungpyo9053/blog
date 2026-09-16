import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from scripts import report_weekly_editorial_failure as failure


class FailureAlertTests(unittest.TestCase):
    def test_sent_once(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(failure, 'ROOT', Path(tmp)), patch.object(failure.subprocess, 'run', return_value=Mock(stdout='a' * 32)), patch.object(failure, 'send') as sender:
            self.assertEqual(failure.main(), 0)
            self.assertEqual(failure.main(), 0)
            sender.assert_called_once()

    def test_uncertain_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(failure, 'ROOT', Path(tmp)), patch.object(failure.subprocess, 'run', return_value=Mock(stdout='b' * 32)), patch.object(failure, 'send', side_effect=RuntimeError('private detail')) as sender:
            self.assertEqual(failure.main(), 1)
            self.assertEqual(failure.main(), 0)
            sender.assert_called_once()
            record = next((Path(tmp) / 'output/weekly-editorial/failure-alerts').glob('*.json')).read_text()
            self.assertNotIn('private detail', record)
            self.assertEqual(json.loads(record)['status'], 'delivery_unconfirmed')

    def test_invalid_identity_never_sends(self):
        with patch.object(failure.subprocess, 'run', return_value=Mock(stdout='../bad')), patch.object(failure, 'send') as sender:
            with self.assertRaises(ValueError):
                failure.main()
            sender.assert_not_called()
