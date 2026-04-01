# this file seeds default luggage brands into db
from slugify import slugify
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Brand

DEFAULT_BRANDS = [
    "Safari",
    "Skybags",
    "American Tourister",
    "VIP",
    "Aristocrat",
    "Nasher Miles",
]


def main() -> None:
    # this function inserts default brands if missing
    with SessionLocal() as db:
        for name in DEFAULT_BRANDS:
            exists = db.execute(select(Brand).where(Brand.name == name)).scalar_one_or_none()
            if exists:
                continue
            db.add(Brand(name=name, slug=slugify(name)))
        db.commit()


if __name__ == "__main__":
    main()
