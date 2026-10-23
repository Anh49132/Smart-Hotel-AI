"""Bounded in-process AI budget; production demo intentionally runs one worker."""
import time
from threading import Lock
from contextlib import contextmanager
from fastapi import HTTPException

class AIBudget:
    def __init__(self):self.entries={};self.lock=Lock()

    @contextmanager
    def reserve(self,user_id):
        now=time.monotonic()
        with self.lock:
            self.entries={k:v for k,v in self.entries.items() if now-v[0]<60 or v[2]}
            start,count,running=self.entries.get(user_id,(now,0,0))
            if now-start>=60:start,count=now,0
            if count>=10 or running>=2 or (user_id not in self.entries and len(self.entries)>=256):
                raise HTTPException(429,'AI đang bận hoặc đã đạt 10 yêu cầu/phút. Hãy thử lại sau.',headers={'Retry-After':'60'})
            self.entries[user_id]=(start,count+1,running+1)
        try:yield
        finally:
            with self.lock:
                start,count,running=self.entries[user_id];self.entries[user_id]=(start,count,max(0,running-1))

ai_budget=AIBudget()
