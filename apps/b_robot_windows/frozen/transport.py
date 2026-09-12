"""Sequential official HTTP client; identical action bytes survive bounded retries."""
from __future__ import annotations
import http.client
import json
import math
from pathlib import Path
import time
import unicodedata
import urllib.error
import urllib.request
import uuid


class ProtocolError(RuntimeError):
    pass


class BudgetExpired(RuntimeError):
    pass


class HttpRobot:
    def __init__(self, robot_id, base_url='http://127.0.0.1:2026',
                 log='logs/client.jsonl', timeout=5, retries=3):
        if not robot_id or len(robot_id.encode('utf8')) > 64 or any(
            unicodedata.category(c) in ('Cc', 'Cf') for c in robot_id
        ):
            raise ValueError('Invalid robot_id')
        self.robot_id = robot_id
        self.url = base_url.rstrip('/')
        self.log = Path(log)
        self.log.parent.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.retries = retries
        self.virtual_time = 0.
        self.position = (0., 0.)
        self.channel = 1
        self.deadline = None
        self.uncertain = False

    def _record(self, entry):
        entry['recorded_unix_s'] = time.time()
        with self.log.open('a', encoding='utf8') as f:
            f.write(json.dumps(entry, ensure_ascii=False, allow_nan=False) + '\n')

    def _timeout(self, path):
        if self.deadline is None:
            return self.timeout
        reserve = 1 if path == '/exit' else 15
        remaining = self.deadline - time.monotonic() - reserve
        if remaining <= 0:
            raise BudgetExpired('Actual remaining wall-clock budget exhausted; partial result only')
        return min(self.timeout, remaining)

    def request(self, path, position=None, channel=None):
        if self.uncertain:
            raise ProtocolError('Previous action outcome unresolved; do not send a different action')
        if path not in ('/enter', '/measure', '/clear', '/exit'):
            raise ValueError('Undeclared endpoint')
        if (path in ('/measure', '/clear')) != (position is not None):
            raise ValueError('Position required only for measure/clear')
        payload = {'arena_id': 'default', 'robot_id': self.robot_id, 'request_id': str(uuid.uuid4())}
        if position is not None:
            if len(position) != 2 or not all(math.isfinite(float(x)) and abs(float(x)) <= 2e6 for x in position):
                raise ValueError('Invalid coordinates')
            if isinstance(channel, bool) or not isinstance(channel, int) or not 1 <= channel <= 20:
                raise ValueError('Invalid channel')
            payload.update(position={'x': float(position[0]), 'y': float(position[1])}, channel=channel)
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode('utf8')
        first_started = time.monotonic()
        last = None
        for attempt in range(self.retries + 1):
            timeout = self._timeout(path)
            req = urllib.request.Request(self.url + path, data=encoded,
                                         headers={'Content-Type': 'application/json'}, method='POST')
            started = time.monotonic()
            self.uncertain = True
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    status = r.status
                    response = json.loads(r.read().decode('utf8'))
            except urllib.error.HTTPError as exc:
                self._record({'request': payload, 'path': path, 'attempt': attempt, 'http_error': exc.code})
                if 400 <= exc.code < 500:
                    self.uncertain = False
                raise ProtocolError(f'HTTP {exc.code}; no blind new action') from exc
            except (urllib.error.URLError, TimeoutError, ConnectionError,
                    http.client.IncompleteRead, json.JSONDecodeError, UnicodeDecodeError) as exc:
                last = exc
                self._record({'request': payload, 'path': path, 'attempt': attempt, 'connection_error': str(exc)})
                if attempt < self.retries:
                    pause = min(.2 * 2 ** attempt, 1.)
                    if self.deadline is not None:
                        pause = min(pause, max(0., self.deadline - time.monotonic() - 16))
                    time.sleep(pause)
                continue
            self._record({'request': payload, 'path': path, 'attempt': attempt, 'status': status,
                          'response': response, 'wall_seconds': time.monotonic() - started})
            if status != 200 or not isinstance(response, dict):
                raise ProtocolError('Malformed HTTP response; outcome unresolved')
            if response.get('accepted') is False:
                self.uncertain = False
                raise ProtocolError('Action rejected; cached position and time unchanged')
            if response.get('accepted') is not True:
                raise ProtocolError('Malformed acceptance value; outcome unresolved')
            try:
                virtual = float(response['virtual_time_s'])
                if not math.isfinite(virtual) or virtual < self.virtual_time - 1e-5:
                    raise ValueError('Invalid virtual time')
                if path == '/measure':
                    kind = response['measure_result']
                    if kind not in ('no_signal', 'near', 'direction'):
                        raise ValueError('Unknown measure result')
                    if kind == 'direction' and not 0 <= float(response['svd_deg']) < 360:
                        raise ValueError('Invalid bearing')
                if path == '/clear' and response['clear_result'] not in ('success', 'no_target_in_range'):
                    raise ValueError('Unknown clear result')
                if path == '/enter':
                    remaining = float(response['remaining_real_duration_s'])
                    if not 0 <= remaining <= 1200:
                        raise ValueError('Invalid remaining duration')
                    # Use the FIRST attempt: a cached retry cannot extend this deadline.
                    self.deadline = first_started + remaining
                if path == '/exit' and response['exit_reason'] != 'user_exit':
                    raise ValueError('Unexpected exit reason')
            except (KeyError, TypeError, ValueError) as exc:
                raise ProtocolError(f'Malformed accepted response: {exc}; outcome unresolved') from exc
            self.virtual_time = virtual
            if position is not None:
                self.position = tuple(map(float, position))
            if path == '/measure':
                self.channel = channel
            self.uncertain = False
            return response
        raise ConnectionError('Same action retry budget exhausted; do not issue a different action') from last

    def enter(self):
        return self.request('/enter')

    def measure(self, p, c):
        return self.request('/measure', p, c)

    def clear(self, p, c):
        return self.request('/clear', p, c)

    def exit(self):
        return self.request('/exit')
