"""Chinese Windows desktop entrypoint. Opening the window never contacts a server."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from session import log_root, run_session, validate_inputs, write_json
from strategy import BUILD_VERSION
from rollout_runtime import selected_settings, native_backend


class App:
    def __init__(self, window):
        self.window = window
        window.title('B 题机器狗 · '+BUILD_VERSION)
        window.geometry('660x530')
        window.minsize(620, 510)
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.running = False
        self.close_after = False
        self.folder = log_root()
        self.cleared = set()
        self.started = 0
        self.robot_id = tk.StringVar()
        self.case_code = tk.StringVar()
        self.question = tk.IntVar(value=3)
        self.status = tk.StringVar(value='待开始')
        self.stats = tk.StringVar(value='已清除 0    虚拟时间 0.00 秒    运行时间 0 秒')
        body = ttk.Frame(window, padding=20)
        body.pack(fill='both', expand=True)
        body.columnconfigure(1, weight=1)
        ttk.Label(body, text='B 题机器狗', font=('Microsoft YaHei UI', 18)).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 16))
        self.inputs = []
        for row, label, variable in ((1, '机器人编号', self.robot_id), (2, '案例编码', self.case_code)):
            ttk.Label(body, text=label).grid(row=row, column=0, sticky='w', padx=(0, 16), pady=7)
            entry = ttk.Entry(body, textvariable=variable)
            entry.grid(row=row, column=1, sticky='ew', pady=7)
            self.inputs.append(entry)
        ttk.Label(body, text='题型').grid(row=3, column=0, sticky='w', pady=7)
        modes = ttk.Frame(body)
        modes.grid(row=3, column=1, sticky='w')
        for question in (3, 4):
            button = ttk.Radiobutton(modes, text=f'问题 {question}', variable=self.question, value=question)
            button.pack(side='left', padx=(0, 25))
            self.inputs.append(button)
        ttk.Label(body, text='演练 · 127.0.0.1:2026').grid(row=4, column=0, columnspan=2, sticky='w', pady=10)
        controls = ttk.Frame(body)
        controls.grid(row=5, column=0, columnspan=2, sticky='ew', pady=8)
        self.start_button = ttk.Button(controls, text='开始演练', command=self.start)
        self.start_button.pack(side='left')
        self.stop_button = ttk.Button(controls, text='结束演练', command=self.request_stop, state='disabled')
        self.stop_button.pack(side='left', padx=10)
        ttk.Button(controls, text='打开日志目录', command=self.open_logs).pack(side='right')
        ttk.Separator(body).grid(row=6, column=0, columnspan=2, sticky='ew', pady=12)
        ttk.Label(body, textvariable=self.status).grid(row=7, column=0, columnspan=2, sticky='w')
        ttk.Label(body, textvariable=self.stats).grid(row=8, column=0, columnspan=2, sticky='w', pady=8)
        self.output = tk.Text(body, height=9, wrap='word', state='disabled', font=('Microsoft YaHei UI', 10))
        self.output.grid(row=9, column=0, columnspan=2, sticky='nsew')
        body.rowconfigure(9, weight=1)
        window.protocol('WM_DELETE_WINDOW', self.close)
        window.after(150, self.poll)

    def append(self, text):
        self.output.configure(state='normal')
        self.output.insert('end', text + '\n')
        if int(self.output.index('end-1c').split('.')[0]) > 250:
            self.output.delete('1.0', '50.0')
        self.output.see('end')
        self.output.configure(state='disabled')

    def start(self):
        if self.running:
            return
        try:
            args = validate_inputs(self.robot_id.get(), self.case_code.get(), self.question.get())
            self.folder = log_root()
            self.folder.mkdir(parents=True, exist_ok=True)
            probe = self.folder / f'.write-check-{os.getpid()}'
            probe.write_text('ok', encoding='ascii')
            probe.unlink()
        except (ValueError, OSError) as exc:
            messagebox.showerror('无法开始', str(exc), parent=self.window)
            return
        if not messagebox.askokcancel('确认本次演练',
                f'问题 {args[2]}\n案例编码：{args[1]}\n\n请确认官方模拟器选择的是演练，倒计时已结束且接口就绪。', parent=self.window):
            return
        self.running = True
        self.started = time.monotonic()
        self.cleared.clear()
        self.virtual_time = 0
        self.stop.clear()
        self.status.set('正在连接')
        self.start_button.configure(state='disabled')
        self.stop_button.configure(state='normal')
        for widget in self.inputs:
            widget.configure(state='disabled')
        self.append(f'开始问题 {args[2]} 演练')
        threading.Thread(target=self.worker, args=args, daemon=False).start()

    def worker(self, *args):
        try:
            run_session(*args, self.stop, self.events.put)
        except Exception as exc:
            self.events.put(dict(kind='fatal', error=f'{type(exc).__name__}: {exc}'))

    def request_stop(self):
        if self.running and messagebox.askyesno('结束演练', '停止后本次运行将记录为未完成。确认结束？', parent=self.window):
            self.stop.set()
            self.stop_button.configure(state='disabled')
            self.status.set('正在结束，等待当前动作确认')

    def close(self):
        if not self.running:
            self.window.destroy()
        elif messagebox.askyesno('退出程序', '本次演练仍在运行。确认结束演练并在收尾后退出？', parent=self.window):
            self.close_after = True
            self.stop.set()
            self.status.set('正在结束，等待当前动作确认')

    def open_logs(self):
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(self.folder))
        except OSError as exc:
            messagebox.showerror('无法打开日志目录', str(exc), parent=self.window)

    def poll(self):
        for _ in range(200):
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            kind = event['kind']
            if kind == 'folder':
                self.folder = Path(event['path'])
            elif kind == 'action':
                self.virtual_time = event['virtual_time_s']
                if event['action'] == '/enter':
                    self.status.set('运行中')
                if event['response'].get('clear_result') == 'success':
                    self.cleared.add(event['channel'])
                    self.append(f'频道 {event["channel"]} 已清除')
            elif kind in ('finished', 'fatal'):
                self.running = False
                self.start_button.configure(state='normal')
                self.stop_button.configure(state='disabled')
                for widget in self.inputs:
                    widget.configure(state='normal')
                result = event.get('result', {})
                status = {'completed': '已完成', 'stopped': '已停止，未完成'}.get(result.get('status'), '未完成')
                self.status.set(status)
                self.append(status)
                if kind == 'fatal' or result.get('error'):
                    self.append(event.get('error') or result['error'])
                if result.get('unresolved_action'):
                    self.append('上次动作结果未确认；请检查官方模拟器状态，勿直接重复进入。')
                    self.start_button.configure(state='disabled')
                elif result and not result.get('exit_confirmed'):
                    self.append('未确认退出，请检查官方模拟器状态。')
                self.append(f'日志：{self.folder}')
                if self.close_after:
                    self.window.destroy()
                    return
        if self.started:
            if self.running:
                self.elapsed = int(time.monotonic() - self.started)
            self.stats.set(f'已清除 {len(self.cleared)}    虚拟时间 {getattr(self, "virtual_time", 0):.2f} 秒    运行时间 {getattr(self, "elapsed", 0)} 秒')
        self.window.after(150, self.poll)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke-test', type=Path)
    args = parser.parse_args()
    mutex = None
    if sys.platform == 'win32':
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        if not args.smoke_test:
            kernel.GetConsoleWindow.restype = ctypes.c_void_p
            console = kernel.GetConsoleWindow()
            if console:
                user = ctypes.WinDLL('user32', use_last_error=True)
                user.ShowWindow.argtypes = (ctypes.c_void_p, ctypes.c_int)
                user.ShowWindow(console, 0)
        kernel.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
        kernel.CreateMutexW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
        mutex = kernel.CreateMutexW(None, False, 'Local\\B-Robot-v4-practice')
        if not mutex:
            raise ctypes.WinError(ctypes.get_last_error())
        if ctypes.get_last_error() == 183:
            kernel.CloseHandle(mutex)
            messagebox.showerror('程序已打开', '机器狗程序已经运行，请使用已有窗口。')
            return
    try:
        window = tk.Tk()
        app = App(window)
        if args.smoke_test:
            window.update()
            args.smoke_test.parent.mkdir(parents=True, exist_ok=True)
            write_json(args.smoke_test, dict(status='passed', tk=window.tk.call('info', 'patchlevel'),
                       window_created=True, network_requests=0, frozen=bool(getattr(sys, 'frozen', False)),
                       native_available=native_backend() is not None,
                       selected_settings={str(q):selected_settings(q) for q in (3,4)}))
            window.destroy()
        else:
            window.mainloop()
    finally:
        if mutex:
            kernel.CloseHandle(mutex)


if __name__ == '__main__':
    main()
