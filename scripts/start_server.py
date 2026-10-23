"""One-worker demo runtime; migrations complete before accepting HTTP traffic."""
import os,sys
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from core.config import PROJECT_ROOT,settings
from core.database import engine

def migrate():
    if settings.app_env=='production' and engine.dialect.name!='postgresql':raise RuntimeError('Production startup requires PostgreSQL, never ephemeral SQLite')
    config=Config(str(PROJECT_ROOT/'alembic.ini'));config.set_main_option('script_location',str(PROJECT_ROOT/'migrations'))
    if engine.dialect.name=='postgresql':
        with engine.connect() as lock:
            lock.execute(text('SELECT pg_advisory_lock(3318027000)'))
            try:command.upgrade(config,'head')
            finally:lock.execute(text('SELECT pg_advisory_unlock(3318027000)'))
    else:command.upgrade(config,'head')

def main():
    migrate();engine.dispose()
    port=int(os.environ.get('PORT','8000'))
    if not 1<=port<=65535:raise ValueError('Invalid PORT')
    os.execv(sys.executable,[sys.executable,'-m','uvicorn','main:app','--host','0.0.0.0','--port',str(port),'--workers','1','--proxy-headers','--forwarded-allow-ips',os.environ.get('FORWARDED_ALLOW_IPS','127.0.0.1')])

if __name__=='__main__':main()
