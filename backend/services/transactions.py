from contextlib import contextmanager
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from backend.models import Room


@contextmanager
def write_transaction(db):
    try:
        yield
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Dữ liệu bị trùng hoặc đang được sử dụng") from None
    except OperationalError:
        db.rollback()
        raise HTTPException(503, "Dữ liệu đang bận. Hãy tải lại và thử lại thao tác.") from None
    except Exception:
        db.rollback()
        raise


def lock_room(db, room_id):
    if db.get_bind().dialect.name == "sqlite":
        # No-op UPDATE takes SQLite's write lock BEFORE reading availability.
        db.execute(update(Room).where(Room.id == room_id).values(id=Room.id).execution_options(synchronize_session=False))
    return db.scalar(select(Room).where(Room.id == room_id).with_for_update().execution_options(populate_existing=True))
