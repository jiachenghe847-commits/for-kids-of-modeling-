"""Packaging/lifecycle checks only; no strategy experiments or official requests."""
from pathlib import Path
import tempfile
import threading
import time
import unittest

from session import run_session, validate_inputs


class FakeRobot:
    events = []
    fail_enter = False
    uncertain_measure = False

    def __init__(self, *args):
        self.virtual_time = 0
        self.uncertain = False
        self.deadline = None

    def request(self, path, position=None, channel=None):
        type(self).events.append(path)
        if path == '/enter' and self.fail_enter:
            self.uncertain = True
            raise ConnectionError('No local simulator')
        if path == '/measure' and self.uncertain_measure:
            self.uncertain = True
            raise ConnectionError('Action outcome unknown')
        self.deadline = time.monotonic() + 1200
        return {'accepted': True, 'virtual_time_s': 0}

    def enter(self):
        return self.request('/enter')

    def exit(self):
        return self.request('/exit')


class FakeStrategy:
    def __init__(self, robot, *args, **kwargs):
        self.robot = robot
        self.cleared = set()
        self.measures = self.clear_attempts = self.coverage_visits = 0

    def run(self):
        self.robot.request('/measure', (0, 0), 1)
        return {'cleared_count': 0, 'completion_basis': 'fake packaging check'}


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        FakeRobot.events = []
        FakeRobot.fail_enter = FakeRobot.uncertain_measure = False

    def run_fake(self, stop=None):
        with tempfile.TemporaryDirectory() as directory:
            result = run_session('packaging-only', 'FAKE-CASE', 3, stop or threading.Event(),
                                 lambda event: None, Path(directory), FakeRobot, FakeStrategy)
            self.assertEqual(len(list(Path(directory).rglob('result.json'))), 1)
            self.assertEqual(len(list(Path(directory).rglob('source_snapshot.zip'))), 1)
            return result

    def test_missing_input(self):
        for fields in [('', 'CODE', 3), ('ID', '', 4), ('ID', 'CODE', 2), ('ID\nX', 'CODE', 3)]:
            with self.assertRaises(ValueError):
                validate_inputs(*fields)

    def test_completed_run_exits_and_saves(self):
        result = self.run_fake()
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(result['exit_confirmed'])
        self.assertEqual(FakeRobot.events, ['/enter', '/measure', '/exit'])

    def test_failed_enter_never_claims_completion_or_exits(self):
        FakeRobot.fail_enter = True
        self.assertEqual(self.run_fake()['status'], 'incomplete')
        self.assertEqual(FakeRobot.events, ['/enter'])

    def test_stop_before_enter_sends_no_request(self):
        stop = threading.Event()
        stop.set()
        self.assertEqual(self.run_fake(stop)['status'], 'stopped')
        self.assertEqual(FakeRobot.events, [])

    def test_stop_after_enter_exits(self):
        stop = threading.Event()
        with tempfile.TemporaryDirectory() as directory:
            def emit(event):
                if event.get('action') == '/enter':
                    stop.set()
            result = run_session('ID', 'FAKE', 4, stop, emit, Path(directory), FakeRobot, FakeStrategy)
        self.assertEqual(result['status'], 'stopped')
        self.assertTrue(result['exit_confirmed'])
        self.assertEqual(FakeRobot.events, ['/enter', '/exit'])

    def test_uncertain_action_never_sends_exit(self):
        FakeRobot.uncertain_measure = True
        result = self.run_fake()
        self.assertTrue(result['unresolved_action'])
        self.assertFalse(result['exit_confirmed'])
        self.assertEqual(FakeRobot.events, ['/enter', '/measure'])


if __name__ == '__main__':
    unittest.main()
