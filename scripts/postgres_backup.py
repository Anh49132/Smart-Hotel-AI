"""Consistent PostgreSQL archive + reconciliation manifest; restore refuses any tables."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
from datetime import datetime,timezone
from sqlalchemy import inspect,text
from core.db_engine import build_engine,normalize_database_url

def binary(name):
    root=os.environ.get('PG_BIN')
    candidate=Path(root)/(name+('.exe' if os.name=='nt' else '')) if root else shutil.which(name)
    if not candidate or not Path(candidate).exists():raise ValueError('Install matching PostgreSQL client tools or set PG_BIN')
    return str(candidate)

def pg_environment(value):
    url=normalize_database_url(value)
    if url.get_backend_name()!='postgresql':raise ValueError('PostgreSQL URL required')
    env=dict(os.environ)
    for key in ('PGHOST','PGPORT','PGDATABASE','PGUSER','PGPASSWORD','PGOPTIONS','PGSSLMODE'):env.pop(key,None)
    env.update(PGHOST=url.host or 'localhost',PGPORT=str(url.port or 5432),PGDATABASE=url.database,PGUSER=url.username or '',PGPASSWORD=url.password or '',PGCONNECT_TIMEOUT='10')
    if url.query.get('options'):env['PGOPTIONS']=url.query['options']
    env['PGSSLMODE']=url.query.get('sslmode','disable' if url.host in ('127.0.0.1','localhost','::1') else 'require')
    return env

def checksum(path):
    with Path(path).open('rb') as file:return hashlib.file_digest(file,'sha256').hexdigest()

def fingerprint(connection):
    quote=connection.dialect.identifier_preparer.quote
    tables=inspect(connection).get_table_names(schema='public')
    counts={name:connection.scalar(text(f'SELECT COUNT(*) FROM public.{quote(name)}')) for name in sorted(tables)}
    totals={}
    if 'invoices' in tables:
        for column in ('room_amount','service_amount','surcharge_amount','discount','total','paid_amount'):
            totals[column]=str(connection.scalar(text(f'SELECT COALESCE(SUM({column}),0) FROM public.invoices')))
    ledger={str(k):str(v) for k,v in connection.execute(text('SELECT kind,SUM(amount) FROM public.money_entries GROUP BY kind ORDER BY kind'))} if 'money_entries' in tables else {}
    sequences={}
    for name in connection.scalars(text("SELECT sequencename FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename")):
        value=connection.execute(text(f'SELECT last_value,is_called FROM public.{quote(name)}')).one()
        sequences[name]={'last_value':value[0],'is_called':value[1]}
    revision=connection.scalar(text('SELECT version_num FROM public.alembic_version')) if 'alembic_version' in tables else None
    return {'counts':counts,'invoice_totals':totals,'ledger_totals':ledger,'sequences':sequences,'revision':revision}

def backup_archive(url,output):
    output=Path(output).resolve();manifest_path=output.with_suffix(output.suffix+'.manifest.json')
    if output.exists() or manifest_path.exists():raise ValueError('Output already exists; choose a new backup name')
    output.parent.mkdir(parents=True,exist_ok=True)
    engine=build_engine(url)
    try:
        with engine.connect().execution_options(isolation_level='REPEATABLE READ') as connection:
            with connection.begin():
                connection.execute(text('SET TRANSACTION READ ONLY'))
                snapshot=connection.scalar(text('SELECT pg_export_snapshot()'))
                state=fingerprint(connection)
                if state['revision'] is None:raise ValueError('Source is not a migrated hotel database')
                # Binary streams also support Windows paths containing Vietnamese.
                with output.open('xb') as destination:
                    result=subprocess.run([binary('pg_dump'),'--format=custom','--no-owner','--no-acl','--schema=public','--snapshot='+snapshot],env=pg_environment(url),stdout=destination,stderr=subprocess.PIPE)
                if result.returncode:
                    output.unlink(missing_ok=True)
                    raise RuntimeError('pg_dump failed; credentials and server diagnostics suppressed')
        os.chmod(output,0o600)
        manifest={'created_at':datetime.now(timezone.utc).isoformat(),'sha256':checksum(output),'fingerprint':state,'scope':'public schema; no globals/roles'}
        manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');os.chmod(manifest_path,0o600)
        return manifest
    finally:engine.dispose()

def restore_archive(url,source,confirm_empty=False):
    if not confirm_empty:raise ValueError('Explicit --confirm-empty-target is required')
    source=Path(source).resolve(strict=True)
    manifest=json.loads(source.with_suffix(source.suffix+'.manifest.json').read_text(encoding='utf-8'))
    if checksum(source)!=manifest['sha256']:raise ValueError('Archive checksum mismatch')
    engine=build_engine(url)
    try:
        with engine.connect() as connection:
            tables=connection.scalar(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema')"))
            if tables:raise ValueError('Target has tables; nothing was overwritten')
        # No --clean: existing objects cause a transactional failure, never silent replacement.
        # Fresh databases already contain public. Skip that CREATE only, retaining
        # transactional restore and avoiding --clean or dropping an existing schema.
        with source.open('rb') as archive:
            toc=subprocess.run([binary('pg_restore'),'--list'],stdin=archive,capture_output=True,check=True).stdout
        with tempfile.TemporaryDirectory(prefix='hotel-restore-') as work:
            Path(work,'restore.list').write_bytes(b'\n'.join(line for line in toc.splitlines() if b' SCHEMA - public ' not in line))
            with source.open('rb') as archive:
                result=subprocess.run([binary('pg_restore'),'--no-owner','--no-acl','--exit-on-error','--single-transaction','--use-list=restore.list','--dbname='+pg_environment(url)['PGDATABASE']],cwd=work,env=pg_environment(url),stdin=archive,capture_output=True)
        if result.returncode:raise RuntimeError('pg_restore failed transactionally; credentials and server diagnostics suppressed')
        with engine.connect() as connection:restored=fingerprint(connection)
        if restored!=manifest['fingerprint']:raise RuntimeError('Restore reconciliation failed; preserve target for inspection')
        return restored
    finally:engine.dispose()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=['backup','restore']);parser.add_argument('archive',type=Path);parser.add_argument('--confirm-empty-target',action='store_true');args=parser.parse_args()
    try:
        if args.operation=='backup':backup_archive(os.environ['BACKUP_DATABASE_URL'],args.archive)
        else:restore_archive(os.environ['RESTORE_DATABASE_URL'],args.archive,args.confirm_empty_target)
    except (ValueError,RuntimeError) as error:raise SystemExit(str(error)) from None
    except Exception as error:raise SystemExit('Database operation failed ('+type(error).__name__+'); credentials suppressed') from None
    print('Backup archive and manifest verified' if args.operation=='backup' else 'Restore reconciled: rows, money, sequences and schema revision')

if __name__=='__main__':main()
