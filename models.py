from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Urun(db.Model):
    __tablename__ = "urun"

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(150), nullable=False)
    baslangic_fiyat = db.Column(db.Float, nullable=False)

    fiyatlar = db.relationship(
        "FiyatGecmisi",
        backref="urun",
        cascade="all, delete-orphan",
        lazy=True
    )

    def __repr__(self):
        return f"<Urun {self.ad}>"


class FiyatGecmisi(db.Model):
    __tablename__ = "fiyat_gecmisi"

    id = db.Column(db.Integer, primary_key=True)

    urun_id = db.Column(
        db.Integer,
        db.ForeignKey("urun.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    fiyat = db.Column(db.Float, nullable=False)
    tarih = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def __repr__(self):
        return f"<Fiyat {self.fiyat} - {self.tarih}>"
