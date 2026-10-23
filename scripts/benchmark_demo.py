"""Reproducible local demo timing, not a production load/capacity claim."""
import argparse,json,os,statistics,tempfile,time,platform
from pathlib import Path
from datetime import timedelta
from uuid import uuid4

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--postgres',action='store_true');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    admin=None;schema=None
    with tempfile.TemporaryDirectory(prefix='hotel-benchmark-') as folder:
        if args.postgres:
            from sqlalchemy import create_engine,text
            from sqlalchemy.engine import make_url
            url=make_url(os.environ['HOTEL_TEST_DATABASE_URL'])
            if url.host not in ('localhost','127.0.0.1','::1'):raise ValueError('Benchmark only permits local PostgreSQL QA')
            admin=create_engine(url);schema='hotel_bench_'+uuid4().hex
            with admin.begin() as connection:connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            os.environ['DATABASE_URL']=url.update_query_dict({'options':f'-csearch_path={schema}'}).render_as_string(hide_password=False)
        else:os.environ['DATABASE_URL']='sqlite:///'+(Path(folder)/'demo.db').as_posix()
        os.environ.update(APP_ENV='testing',SEED_DEMO_DATA='false')
        from core.database import Base,engine,SessionLocal
        from core.security import hash_password
        from core.hotel_time import hotel_today
        from backend.models import Room,RoomType,Customer,Role,User
        from backend.main import app
        from backend.schemas.inputs import BookingIn
        from backend.services.booking_service import create_booking
        from fastapi.testclient import TestClient
        try:
            Base.metadata.create_all(engine)
            today=hotel_today()
            with SessionLocal() as db:
                rt=RoomType(name='Demo',capacity=2,nightly_rate=900000,amenities='WiFi');db.add(rt);db.flush()
                db.add_all([User(username='benchmark',full_name='Demo',role=Role.admin,password_hash=hash_password('Benchmark@2030')),Customer(full_name='Synthetic guest',phone='0000000000')]);db.flush()
                db.add_all([Room(number=str(200+i),floor=2,room_type_id=rt.id) for i in range(30)]);db.commit()
                for i in range(120):
                    start=today+timedelta(days=(i//30)*3)
                    create_booking(db,BookingIn(customer_id=1,room_id=i%30+1,check_in=start,check_out=start+timedelta(days=2),guests=2))
            paths=['/','/bookings',f'/calendar?start={today}&end={today+timedelta(days=14)}','/customers',f'/reports?start={today}&end={today+timedelta(days=14)}','/shifts']
            results=[]
            with TestClient(app) as client:
                assert client.post('/login',data={'username':'benchmark','password':'Benchmark@2030'}).status_code==200
                for path in paths:
                    samples=[]
                    for _ in range(12):
                        start=time.perf_counter();response=client.get(path);samples.append((time.perf_counter()-start)*1000)
                        assert response.status_code==200,path
                    results.append({'path':path,'requests':12,'median_ms':round(statistics.median(samples),2),'p95_sample_ms':round(sorted(samples)[-1],2),'all_http_200':True})
            data={'date':str(today),'backend':engine.dialect.name,'python':platform.python_version(),'rooms':30,'bookings':120,'scope':'local TestClient, single process, sequential, no network/AI; small-sample p95 uses maximum; not production load','results':results}
            args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'backend':data['backend'],'all_http_200':True,'max_sample_ms':max(r['p95_sample_ms'] for r in results)}))
        finally:
            engine.dispose()
            if admin:
                with admin.begin() as connection:connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
                admin.dispose()

if __name__=='__main__':main()
