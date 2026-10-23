"""Bounded, per-process login protection for the single-worker demo service."""
from collections import OrderedDict
from threading import Lock
from time import monotonic
from hashlib import sha256
from fastapi import HTTPException


class LoginLimiter:
    def __init__(self, window=300, clock=monotonic):
        self.window, self.clock = window, clock
        self.entries = OrderedDict()
        self.lock = Lock()

    def check(self, ip, username):
        now = self.clock()
        with self.lock:
            for key in list(self.entries):
                if now - self.entries[key][0] >= self.window:
                    del self.entries[key]
            keys = [('ip:' + ip, 30), ('user:' + sha256(username.encode()).hexdigest(), 5)]
            if any(self.entries.get(key, (now, 0))[1] >= limit for key, limit in keys):
                raise HTTPException(429, 'Thử đăng nhập quá nhiều. Vui lòng chờ 5 phút', headers={'Retry-After': str(self.window)})
            for key, _ in keys:
                start, count = self.entries.get(key, (now, 0))
                self.entries[key] = (start, count + 1)
                self.entries.move_to_end(key)
            while len(self.entries) > 4096:
                self.entries.popitem(last=False)


login_limiter = LoginLimiter()
