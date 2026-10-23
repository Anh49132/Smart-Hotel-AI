"""Destructive only to newly generated local QA databases; never operational targets."""
import json,os,subprocess,sys,uuid
from pathlib import Path
from sqlalchemy import create_engine,text
from scripts.postgres_backup import backup_archive,restore_archive

def main():
    base='postgresql+psycopg://postgres@127.0.0.1:55439/'
    names=['hotel_backup_qa_'+uuid.uuid4().hex for _ in range(2)]
    admin=create_engine(base+'postgres',isolation_level='AUTOCOMMIT')
    archive=Path('data/backups')/(names[0]+'.dump')
    try:
        with admin.connect() as c:
            for name in names:c.execute(text('CREATE DATABASE '+name))
        env=dict(os.environ,DATABASE_URL=base+names[0],APP_ENV='testing',DEMO_MODE='false',DEMO_SEED_ON_START='false')
        subprocess.run([sys.executable,'-m','alembic','upgrade','head'],env=env,check=True,capture_output=True)
        seed="from core.database import SessionLocal; from core.security import hash_password; from backend.models import User,Role; from backend.services.demo_service import seed_demo; d=SessionLocal(); d.add(User(username='admin',full_name='QA',password_hash=hash_password('PrivateQA@2030'),role=Role.admin)); d.commit(); seed_demo(d,'PrivateQAStaff@2030'); d.close()"
        subprocess.run([sys.executable,'-c',seed],env=env,check=True,capture_output=True)
        manifest=backup_archive(base+names[0],archive)
        result=restore_archive(base+names[1],archive,True)
        assert result==manifest['fingerprint']
        try:restore_archive(base+names[1],archive,True)
        except ValueError as e:assert 'Target has tables' in str(e)
        else:raise AssertionError('Populated target was accepted')
        evidence={'scope':'new local QA databases only','revision':result['revision'],'counts':result['counts'],'invoice_totals':result['invoice_totals'],'ledger_totals':result['ledger_totals'],'sequences_compared':len(result['sequences']),'populated_target_refused':True,'archive_sha256':manifest['sha256']}
        Path('docs/backup-restore-evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
        print('Backup/restore verified, including populated target refusal')
    finally:
        with admin.connect() as c:
            for name in names:
                assert name.startswith('hotel_backup_qa_') and name.replace('_','').isalnum()
                c.execute(text('DROP DATABASE IF EXISTS '+name+' WITH (FORCE)'))
        admin.dispose()

if __name__=='__main__':main()
