from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


def commit_or_conflict(db, detail="Dữ liệu bị trùng hoặc đang được tham chiếu"):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, detail) from None
