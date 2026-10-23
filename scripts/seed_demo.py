"""Seed only an explicitly configured demo; never prints passwords."""
import json
from core.config import settings
from core.database import SessionLocal
from backend.services.demo_service import seed_demo

def main():
    if not settings.demo_mode:raise SystemExit('Set DEMO_MODE=true only for a dedicated synthetic demo database')
    with SessionLocal() as db:result=seed_demo(db,settings.demo_staff_password.get_secret_value())
    print(json.dumps(result))

if __name__=='__main__':main()
