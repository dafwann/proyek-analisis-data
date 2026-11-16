import os

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Dashboard E-Commerce Olist", page_icon="🛒", layout="wide")

HIGHLIGHT, MUTED, ALERT = "#72BCD4", "#D3D3D3", "#E4572E"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False})


@st.cache_data
def load_data():
    df = pd.read_csv(os.path.join(BASE_DIR, "main_data.csv"), parse_dates=["order_purchase_timestamp"])
    geo = pd.read_csv(os.path.join(BASE_DIR, "state_geo.csv"))
    return df, geo


def money(x, pos=None):
    return f"R$ {x/1e3:,.0f}K" if x < 1e6 else f"R$ {x/1e6:,.1f}M"


def build_rfm(df):
    ref = df["order_purchase_timestamp"].max().normalize() + pd.Timedelta(days=1)
    rfm = (df.groupby("customer_unique_id")
           .agg(last_order=("order_purchase_timestamp", "max"), frequency=("order_id", "nunique"), monetary=("price", "sum"))
           .reset_index())
    rfm["recency"] = (ref - rfm["last_order"].dt.normalize()).dt.days
    pct = rfm["monetary"].rank(pct=True, method="first")
    high = pct > 2 / 3
    rfm["segment"] = np.select(
        [rfm["frequency"] >= 2, (rfm["recency"] <= 180) & high, rfm["recency"] <= 180, high],
        ["Loyal (repeat buyer)", "Active High Value", "Active Regular", "At-Risk High Value"],
        default="Lost / Dormant")
    return rfm


df_all, geo_df = load_data()

# ---------- Sidebar ----------
st.sidebar.header("Filter Data")
min_d, max_d = df_all["order_purchase_timestamp"].min().date(), df_all["order_purchase_timestamp"].max().date()
date_range = st.sidebar.date_input("Rentang tanggal pembelian", value=(min_d, max_d), min_value=min_d, max_value=max_d)
states = sorted(df_all["customer_state"].unique())
sel_states = st.sidebar.multiselect("State pelanggan", states, default=states)
top_n = st.sidebar.slider("Jumlah kategori ditampilkan", 3, 10, 5)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
else:
    start, end = min_d, max_d
df = df_all[(df_all["order_purchase_timestamp"].dt.date >= start) & (df_all["order_purchase_timestamp"].dt.date <= end)
            & (df_all["customer_state"].isin(sel_states))]

st.title("🛒 Dashboard Analisis E-Commerce Olist")
st.caption("Pesanan berstatus delivered, Januari 2017 - Agustus 2018. Nilai dalam Real Brasil (R$).")

if df.empty:
    st.warning("Tidak ada data untuk filter yang dipilih. Ubah rentang tanggal atau state.")
    st.stop()

orders = df.drop_duplicates("order_id")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Order", f"{orders['order_id'].nunique():,}")
c2.metric("Total Revenue", f"R$ {df['price'].sum():,.0f}")
c3.metric("Skor Review Rata-rata", f"{orders['review_score'].mean():.2f} / 5")
c4.metric("Pesanan Terlambat", f"{orders['is_late'].mean():.1%}")

tab1, tab2, tab3, tab4 = st.tabs(["Kategori Produk", "Tren Bulanan", "Kualitas Layanan per State", "RFM & Geospasial"])

# ---------- Tab 1 ----------
with tab1:
    st.subheader("Kategori produk dengan revenue tertinggi dan terendah")
    cat = df.groupby("category").agg(revenue=("price", "sum"), items=("price", "count")).sort_values("revenue", ascending=False).reset_index()
    cat["share"] = cat["revenue"] / cat["revenue"].sum() * 100
    n = min(top_n, len(cat))
    top, bot = cat.head(n).iloc[::-1], cat.tail(n).iloc[::-1]
    fig, ax = plt.subplots(1, 2, figsize=(16, 5))
    bars = ax[0].barh(top["category"], top["revenue"], color=[MUTED] * (n - 1) + [HIGHLIGHT])
    for b, s in zip(bars, top["share"]):
        ax[0].text(b.get_width(), b.get_y() + b.get_height() / 2, f"  {money(b.get_width())} ({s:.1f}%)", va="center", fontsize=10)
    ax[0].set_title(f"{n} Kategori Revenue Tertinggi", fontsize=14)
    ax[0].set_xlim(0, top["revenue"].max() * 1.35)
    bars = ax[1].barh(bot["category"], bot["revenue"], color=[MUTED] * (n - 1) + [ALERT])
    for b, s in zip(bars, bot["share"]):
        ax[1].text(b.get_width(), b.get_y() + b.get_height() / 2, f"  R$ {b.get_width():,.0f} ({s:.2f}%)", va="center", fontsize=10)
    ax[1].set_title(f"{n} Kategori Revenue Terendah", fontsize=14)
    ax[1].set_xlim(0, max(bot["revenue"].max(), 1) * 1.7)
    for a in ax:
        a.set_xlabel("Revenue (R$)")
    plt.tight_layout()
    st.pyplot(fig)
    st.info(f"Lima kategori teratas menyumbang {cat.head(5)['share'].sum():.1f}% revenue; {(cat['share'].cumsum() <= 80).sum() + 1} dari {len(cat)} kategori sudah menghasilkan 80% revenue.")

# ---------- Tab 2 ----------
with tab2:
    st.subheader("Tren jumlah order dan revenue per bulan")
    m = df.groupby("order_month").agg(order_count=("order_id", "nunique"), revenue=("price", "sum")).reset_index()
    m["revenue_mom"] = m["revenue"].pct_change() * 100
    pk = m["revenue"].idxmax()
    fig, ax = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    x = np.arange(len(m))
    for a, col, ttl in [(ax[0], "order_count", "Jumlah Order per Bulan"), (ax[1], "revenue", "Total Revenue per Bulan (R$)")]:
        a.plot(x, m[col], marker="o", linewidth=2, color=HIGHLIGHT)
        a.scatter(pk, m.loc[pk, col], color=ALERT, s=90, zorder=5)
        a.set_title(ttl, loc="left", fontsize=13)
        a.set_ylim(0, m[col].max() * 1.15)
    ax[1].yaxis.set_major_formatter(mtick.FuncFormatter(money))
    ax[1].set_xticks(x)
    ax[1].set_xticklabels(m["order_month"], rotation=45, ha="right")
    ax[1].set_xlabel("Bulan pembelian")
    plt.tight_layout()
    st.pyplot(fig)
    st.info(f"Puncak revenue pada {m.loc[pk, 'order_month']}: R$ {m.loc[pk, 'revenue']:,.0f} dari {int(m.loc[pk, 'order_count']):,} order. Titik merah menandai bulan puncak.")
    mom = m.dropna(subset=["revenue_mom"])
    if not mom.empty:
        fig, ax = plt.subplots(figsize=(13, 3.8))
        ax.bar(mom["order_month"], mom["revenue_mom"], color=[HIGHLIGHT if v >= 0 else ALERT for v in mom["revenue_mom"]])
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_title("Pertumbuhan Revenue Month-over-Month (%)", loc="left", fontsize=13)
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        st.pyplot(fig)

# ---------- Tab 3 ----------
with tab3:
    st.subheader("Skor review dan keterlambatan per state")
    min_orders = st.slider("Minimal jumlah order per state (menghindari sampel terlalu kecil)", 10, 500, 100, step=10)
    s = (orders.groupby("customer_state").agg(n=("order_id", "nunique"), avg_review=("review_score", "mean"), late=("is_late", "mean")).reset_index())
    s["late"] *= 100
    s = s[s["n"] >= min_orders].sort_values("avg_review")
    if s.empty:
        st.warning("Tidak ada state yang memenuhi minimal order.")
    else:
        low = set(s.head(5)["customer_state"])
        cols = [ALERT if v in low else MUTED for v in s["customer_state"]]
        fig, ax = plt.subplots(1, 2, figsize=(15, max(5, len(s) * 0.35)), sharey=True)
        ax[0].barh(s["customer_state"], s["avg_review"], color=cols)
        ax[0].axvline(orders["review_score"].mean(), color="black", linestyle="--", linewidth=1)
        ax[0].set_xlim(0, 5)
        ax[0].set_title("Skor review rata-rata (garis putus = rata-rata data terfilter)")
        ax[1].barh(s["customer_state"], s["late"], color=cols)
        ax[1].axvline(orders["is_late"].mean() * 100, color="black", linestyle="--", linewidth=1)
        ax[1].set_title("Pesanan terlambat (%)")
        for i, (r, l) in enumerate(zip(s["avg_review"], s["late"])):
            ax[0].text(r, i, f" {r:.2f}", va="center", fontsize=9)
            ax[1].text(l, i, f" {l:.1f}%", va="center", fontsize=9)
        plt.tight_layout()
        st.pyplot(fig)
    c_a, c_b = st.columns(2)
    with c_a:
        lr = orders.dropna(subset=["review_score"]).groupby("is_late")["review_score"].mean()
        fig, ax = plt.subplots(figsize=(5, 4))
        labels = ["Tepat waktu" if k == 0 else "Terlambat" for k in lr.index]
        ax.bar(labels, lr.values, color=[HIGHLIGHT if k == 0 else ALERT for k in lr.index], width=0.5)
        for i, v in enumerate(lr.values):
            ax.text(i, v + 0.05, f"{v:.2f}", ha="center")
        ax.set_ylim(0, 5)
        ax.set_title("Skor review: tepat waktu vs terlambat")
        st.pyplot(fig)
    with c_b:
        o = orders.dropna(subset=["review_score"]).copy()
        o["bin"] = pd.cut(o["delivery_days"], [-1, 7, 14, 21, 30, np.inf], labels=["0-7", "8-14", "15-21", "22-30", ">30"])
        b = o.groupby("bin", observed=True)["review_score"].mean()
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.bar(b.index.astype(str), b.values, color=[HIGHLIGHT, HIGHLIGHT, MUTED, ALERT, ALERT][:len(b)])
        for i, v in enumerate(b.values):
            ax.text(i, v + 0.05, f"{v:.2f}", ha="center")
        ax.set_ylim(0, 5)
        ax.set_xlabel("Lama pengiriman (hari)")
        ax.set_title("Skor review menurut lama pengiriman")
        st.pyplot(fig)

# ---------- Tab 4 ----------
with tab4:
    st.subheader("Segmentasi pelanggan (RFM Analysis)")
    st.caption("Recency = hari sejak pembelian terakhir; Frequency = jumlah order; Monetary = total belanja. Segmen dibuat dengan aturan bisnis (manual grouping).")
    rfm = build_rfm(df)
    seg = rfm.groupby("segment").agg(customers=("customer_unique_id", "count"), revenue=("monetary", "sum"), avg_recency=("recency", "mean")).reset_index()
    seg["customer_pct"] = seg["customers"] / seg["customers"].sum() * 100
    seg["revenue_pct"] = seg["revenue"] / seg["revenue"].sum() * 100
    seg = seg.sort_values("revenue_pct")
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.5), sharey=True)
    for a, col, t in [(ax[0], "customer_pct", "% jumlah pelanggan"), (ax[1], "revenue_pct", "% revenue")]:
        a.barh(seg["segment"], seg[col], color=HIGHLIGHT)
        for i, v in enumerate(seg[col]):
            a.text(v, i, f" {v:.1f}%", va="center")
        a.set_xlim(0, 100)
        a.set_title(t)
    plt.tight_layout()
    st.pyplot(fig)
    m1, m2, m3 = st.columns(3)
    m1.metric("Rata-rata Recency", f"{rfm['recency'].mean():.0f} hari")
    m2.metric("Rata-rata Frequency", f"{rfm['frequency'].mean():.2f} order")
    m3.metric("Rata-rata Monetary", f"R$ {rfm['monetary'].mean():,.2f}")
    st.dataframe(seg.sort_values("revenue_pct", ascending=False).round(1).rename(columns={
        "segment": "Segmen", "customers": "Pelanggan", "revenue": "Revenue (R$)", "avg_recency": "Rata-rata recency (hari)",
        "customer_pct": "% pelanggan", "revenue_pct": "% revenue"}), hide_index=True)

    st.subheader("Analisis geospasial: sebaran pelanggan dan skor review")
    g = (orders.groupby("customer_state").agg(customers=("customer_unique_id", "nunique"), avg_review=("review_score", "mean"), n=("order_id", "nunique"))
         .reset_index().merge(geo_df, left_on="customer_state", right_on="state"))
    fig, ax = plt.subplots(figsize=(8, 7))
    sc = ax.scatter(g["lng"], g["lat"], s=g["customers"] / g["customers"].max() * 1500 + 8, c=g["avg_review"],
                    cmap="RdYlBu", vmin=3.5, vmax=4.4, alpha=0.85, edgecolor="grey")
    for _, r in g.nlargest(5, "customers").iterrows():
        ax.annotate(f"{r['customer_state']} ({r['customers']:,})", (r["lng"], r["lat"]), fontsize=9, ha="center", xytext=(0, 12), textcoords="offset points")
    plt.colorbar(sc, label="Skor review rata-rata")
    ax.set_xlabel("Bujur")
    ax.set_ylabel("Lintang")
    ax.set_title("Ukuran = jumlah pelanggan, warna = skor review")
    plt.tight_layout()
    st.pyplot(fig)

st.caption("Proyek Analisis Data - Andi Muh. Daffa' Dermawan | Dataset: Brazilian E-Commerce Public Dataset by Olist")
