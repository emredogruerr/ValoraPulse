from flask import Flask, render_template, request, jsonify, redirect
from models import db, Urun, FiyatGecmisi
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
from datetime import datetime, date
import random
import numpy as np

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///valora.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

plt.rcParams['axes.edgecolor'] = '#333'
plt.rcParams['axes.linewidth'] = 1.2
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['figure.facecolor'] = '#111'
plt.rcParams['axes.facecolor'] = '#111'
plt.rcParams['savefig.facecolor'] = '#111'
plt.rcParams['text.color'] = '#eee'
plt.rcParams['axes.labelcolor'] = '#eee'
plt.rcParams['xtick.color'] = '#ccc'
plt.rcParams['ytick.color'] = '#ccc'


# ----------------------------------
#   FİYAT ÜRETME
# ----------------------------------
def fiyat_uret(onceki_fiyat: float) -> float:
    degisim = random.uniform(-0.05, 0.05)
    yeni_fiyat = round(onceki_fiyat * (1 + degisim), 2)
    return max(1, yeni_fiyat)


# ----------------------------------
#   FİYAT KAYDETME
# ----------------------------------
def fiyat_kaydet(urun_id: int):
    urun = Urun.query.get(urun_id)
    onceki = FiyatGecmisi.query.filter_by(urun_id=urun_id).order_by(FiyatGecmisi.id.desc()).first()
    baslangic = onceki.fiyat if onceki else urun.baslangic_fiyat

    yeni = fiyat_uret(baslangic)

    kayit = FiyatGecmisi(
        urun_id=urun_id,
        fiyat=yeni,
        tarih=datetime.now()
    )
    db.session.add(kayit)
    db.session.commit()

    return yeni


# ----------------------------------
#   GRAFİK ÜRETME
# ----------------------------------
def grafik_uret(urun_id: int):
    kayitlar = FiyatGecmisi.query.filter_by(urun_id=urun_id).order_by(FiyatGecmisi.tarih.asc()).all()

    fiyatlar = [k.fiyat for k in kayitlar]
    tarih = [k.tarih.strftime('%H:%M:%S') for k in kayitlar]

    if not fiyatlar:
        return None

    x = np.arange(len(fiyatlar))
    smooth = np.interp(np.linspace(0, len(fiyatlar)-1, 300), x, fiyatlar)

    plt.figure(figsize=(10, 4))
    plt.plot(np.linspace(0, len(tarih)-1, 300), smooth, color='#00c3ff', linewidth=3, alpha=0.95)
    for i, f in enumerate(fiyatlar):
        plt.scatter(i, f, color='#00c3ff', s=50, edgecolors='#fff', linewidths=1.2)

    plt.grid(color='#444', linestyle='--', linewidth=0.5, alpha=0.5)
    plt.xticks(range(len(tarih)), tarih, rotation=45)
    plt.tight_layout()

    yol = os.path.join("static", f"grafik_{urun_id}.png")
    plt.savefig(yol, dpi=120, bbox_inches='tight')
    plt.close()

    return yol


# ----------------------------------
#   ANA SAYFA
# ----------------------------------
@app.route('/')
def index():
    urunler = Urun.query.all()
    return render_template('index.html', urunler=urunler)


# ----------------------------------
#   ÜRÜN DETAY SAYFASI
# ----------------------------------
@app.route('/urun/<int:id>')
def urun_detay(id):
    yol = grafik_uret(id)
    urun = Urun.query.get_or_404(id)
    return render_template("product_detail.html", urun=urun, grafik_yol=yol)


# ----------------------------------
#   CANLI FİYAT API
# ----------------------------------
@app.route('/api/canli-fiyat/<int:id>')
def canli_fiyat(id):
    yeni = fiyat_kaydet(id)
    grafik = grafik_uret(id)

    return jsonify({
        "fiyat": yeni,
        "grafik": grafik,
        "zaman": datetime.now().strftime("%H:%M:%S")
    })


# ----------------------------------
#   ÜRÜN EKLEME
# ----------------------------------
@app.route('/urun/ekle', methods=["GET", "POST"])
def urun_ekle():
    if request.method == "POST":
        ad = request.form["ad"]
        f = float(request.form["fiyat"])

        yeni = Urun(ad=ad, baslangic_fiyat=f)
        db.session.add(yeni)
        db.session.commit()

        return redirect("/")
    return render_template("add_product.html")


# ----------------------------------
#   ÜRÜN SİLME
# ----------------------------------
@app.route('/urun/sil/<int:id>')
def urun_sil(id):
    urun = Urun.query.get_or_404(id)

    FiyatGecmisi.query.filter_by(urun_id=id).delete()
    db.session.delete(urun)
    db.session.commit()

    return redirect("/")


# ----------------------------------
#   DASHBOARD API
# ----------------------------------
@app.route('/api/dashboard')
def dashboard_api():
    toplam_urun = Urun.query.count()

    bugun = date.today()
    bugunku = FiyatGecmisi.query.filter(
        FiyatGecmisi.tarih >= datetime(bugun.year, bugun.month, bugun.day)
    ).count()

    volatil_list = []
    stabil_list = []

    for urun in Urun.query.all():
        fiyatlar = FiyatGecmisi.query.filter_by(urun_id=urun.id).order_by(FiyatGecmisi.id.asc()).all()
        if len(fiyatlar) < 2:
            continue

        degisimler = [abs(fiyatlar[i].fiyat - fiyatlar[i-1].fiyat) for i in range(1, len(fiyatlar))]
        ort_degisim = round(np.mean(degisimler), 2)

        volatil_list.append({"ad": urun.ad, "degisim": ort_degisim})
        stabil_list.append({"ad": urun.ad, "degisim": ort_degisim})

    volatil_list = sorted(volatil_list, key=lambda x: x["degisim"], reverse=True)
    stabil_list = sorted(stabil_list, key=lambda x: x["degisim"])

    en_volatil = volatil_list[0]["ad"] if volatil_list else "—"

    grafik_tarih = []
    grafik_fiyat = []

    for u in Urun.query.all():
        fiyatlar = FiyatGecmisi.query.filter_by(urun_id=u.id).order_by(FiyatGecmisi.tarih.asc()).all()
        grafik_tarih.extend([k.tarih.strftime("%H:%M:%S") for k in fiyatlar])
        grafik_fiyat.extend([k.fiyat for k in fiyatlar])

    return jsonify({
        "toplam_urun": toplam_urun,
        "bugunku_guncelleme": bugunku,
        "en_volatil_urun": en_volatil,
        "volatil_list": volatil_list[:5],
        "stabil_list": stabil_list[:5],
        "grafik": {
            "tarih": grafik_tarih,
            "fiyat": grafik_fiyat
        }
    })


# ----------------------------------
#   DB INIT
# ----------------------------------
@app.cli.command('init-db')
def init_db():
    db.drop_all()
    db.create_all()
    print("Veritabanı oluşturuldu.")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
