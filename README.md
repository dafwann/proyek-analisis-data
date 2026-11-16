# Proyek Analisis Data: E-Commerce Olist Dashboard 🛒

Analisis data transaksi marketplace Olist (Brasil), periode **Januari 2017 - Agustus 2018**, oleh **Andi Muh. Daffa' Dermawan**.

## Pertanyaan Bisnis
1. Kategori produk apa yang menghasilkan revenue tertinggi dan terendah?
2. Bagaimana tren jumlah order dan revenue bulanan, kapan puncaknya, dan berapa pertumbuhan MoM-nya?
3. State mana yang memiliki skor review terendah dan persentase keterlambatan tertinggi, serta seberapa besar pengaruh keterlambatan terhadap skor review?

Analisis lanjutan: RFM Analysis, Geospatial Analysis, Clustering manual (manual grouping & binning).

## Struktur Direktori
```
submission
├───dashboard
│   ├───main_data.csv
│   ├───state_geo.csv
│   └───dashboard.py
├───data
│   └───*.csv (dataset asli Olist)
├───Proyek_Analisis_Data.ipynb
├───README.md
└───requirements.txt
```

## Setup Environment - Anaconda
```
conda create --name main-ds python=3.9
conda activate main-ds
pip install -r requirements.txt
```

## Setup Environment - Shell/Terminal
```
mkdir proyek_analisis_data
cd proyek_analisis_data
pipenv install
pipenv shell
pip install -r requirements.txt
```

## Run Streamlit App
Jalankan dari folder utama proyek:
```
streamlit run dashboard/dashboard.py
```
Dashboard akan terbuka di `http://localhost:8501`. Gunakan filter di sidebar (rentang tanggal, state, jumlah kategori) untuk mengeksplorasi data.
