"""Desktop lifecycle around the validated adaptive strategy and HTTP transport."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import unicodedata
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'frozen'))
from transport import HttpRobot
from strategy import Strategy


class StopRequested(Exception):
    pass


def validate_inputs(robot_id, case_code, question):
    robot_id, case_code = robot_id.strip(), case_code.strip()
    if not robot_id or len(robot_id.encode('utf8')) > 64 or any(
        unicodedata.category(c) in ('Cc', 'Cf') for c in robot_id
    ):
        raise ValueError('机器人编号不能为空，且不能超过 64 字节或包含控制字符。')
    if not case_code or len(case_code) > 100 or any(
        unicodedata.category(c) in ('Cc', 'Cf') for c in case_code
    ):
        raise ValueError('请填写本次演练的案例编码（最多 100 个字符）。')
    if question not in (3, 4):
        raise ValueError('请选择问题 3 或问题 4。')
    return robot_id, case_code, question


def log_root():
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'B-Robot' / 'logs'


def write_json(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')
    temporary.replace(path)


def save_snapshot(folder):
    source = ROOT / 'source_snapshot.zip'
    if source.exists():
        payload = source.read_bytes()
    else:
        import io
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(ROOT.rglob('*.py')):
                archive.write(path, path.relative_to(ROOT))
        payload = buffer.getvalue()
    (folder / 'source_snapshot.zip').write_bytes(payload)
    build = ROOT / 'build-info.json'
    info = json.loads(build.read_text(encoding='utf8')) if build.exists() else {'version': 'development'}
    return dict(build=info, source_snapshot_sha256=hashlib.sha256(payload).hexdigest())


def run_session(robot_id, case_code, question, stop, emit, root=None,
                robot_factory=HttpRobot, strategy_factory=Strategy):
    robot_id, case_code, question = validate_inputs(robot_id, case_code, question)
    folder = (root or log_root()) / f'q{question}-{time.strftime("%Y%m%d-%H%M%S")}-{uuid.uuid4().hex[:8]}'
    folder.mkdir(parents=True, exist_ok=False)
    result = dict(status='prepared', question=question, declared_session_type='practice',
                  declared_case_code=case_code, robot_id=robot_id,
                  provenance='Client label only; official mode and score require simulator export')
    result.update(save_snapshot(folder))
    result_path = folder / 'result.json'
    write_json(result_path, result)
    emit(dict(kind='folder', path=str(folder)))

    class ReportingRobot(robot_factory):
        def request(self, path, position=None, channel=None):
            # Stop only between complete actions; never interrupt an uncertain retry.
            if stop.is_set() and path != '/exit':
                raise StopRequested('用户请求结束演练。')
            response = super().request(path, position, channel)
            emit(dict(kind='action', action=path, channel=channel,
                      virtual_time_s=self.virtual_time, response=response))
            return response

    robot = ReportingRobot(robot_id, 'http://127.0.0.1:2026', folder / 'client.jsonl')
    policy = strategy_factory(robot, question == 4, grid='compact' if question == 4 else 'ring', early_clears=3)
    entered = False
    started = time.perf_counter()
    try:
        result['enter_response'] = robot.enter()
        entered = True
        result['status'] = 'running'
        write_json(result_path, result)
        result.update(policy.run())
        if stop.is_set():
            raise StopRequested('用户请求结束演练。')
        result['exit_response'] = robot.exit()
        result['status'] = 'completed'
        result['exit_confirmed'] = True
    except Exception as exc:
        result.update(status='stopped' if isinstance(exc, StopRequested) else 'incomplete',
                      error=f'{type(exc).__name__}: {exc}',
                      cleared_count=len(policy.cleared), cleared_channels=sorted(policy.cleared),
                      virtual_time_s=robot.virtual_time, measurements=policy.measures,
                      clear_attempts=policy.clear_attempts, coverage_visits=policy.coverage_visits)
        if entered and not robot.uncertain and robot.deadline is not None and time.monotonic() < robot.deadline - 1:
            try:
                result['exit_response'] = robot.exit()
                result['exit_confirmed'] = True
            except Exception as close_error:
                result['exit_error'] = f'{type(close_error).__name__}: {close_error}'
    finally:
        result['action_trace']=getattr(policy,'action_trace',[])
        result.update(wall_seconds=time.perf_counter() - started, unresolved_action=robot.uncertain)
        result.setdefault('exit_confirmed', False)
        write_json(result_path, result)
        emit(dict(kind='finished', result=result, path=str(folder)))
    return result
