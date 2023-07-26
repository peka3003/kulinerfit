# Pastikan Anda telah menginstal pustaka firebase-admin dengan perintah:
# pip install firebase-admin

import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd

# # Inisialisasi Firebase Admin SDK
# cred = credentials.Certificate("kulinerfit-firebase-adminsdk-7qhfd-eb15e48462.json")  # Ganti dengan path ke serviceAccountKey.json Anda
# firebase_admin.initialize_app(cred)

def nutrisi_df():

    # Dapatkan referensi ke koleksi "data_makanan" dalam Firestore
    db = firestore.client()
    data_makanan_ref = db.collection("data_makanan")

    # Ambil seluruh data dari koleksi "data_makanan"
    nutrisi_data = []
    for doc in data_makanan_ref.stream():
        nutrisi_data.append(doc.to_dict())

    # Konversi data menjadi DataFrame
    nutrisi_df = pd.DataFrame(nutrisi_data)

    return nutrisi_df

def hitung_kalori(nutrisi_df, inputan):
    total_kalori = 0
    total_karbohidrat = 0
    total_protein = 0
    total_lemak = 0

    for item in inputan:
        bahan = item['bahan'].lower()
        jumlah = float(item['jumlah'])
        satuan = item['satuan']

        # Cari data nutrisi dari dataset berdasarkan nama bahan
        data_bahan = nutrisi_df[nutrisi_df["nama"] == bahan]

        if not data_bahan.empty:
            # Ambil nilai kalori per 100 gram dari data bahan
            kalori = data_bahan["kalori"].values[0]
            karbohidrat = data_bahan["karbohidrat"].values[0]
            protein = data_bahan["protein"].values[0]
            lemak_total = data_bahan["lemakTotal"].values[0]
            ukuran = data_bahan["ukuran"].values[0]

            # Satuan dalam gram

            # Hitung total kalori untuk bahan ini
            kalori_bahan = (jumlah * kalori) / ukuran
            total_kalori += kalori_bahan

            karbohidrat_bahan = (jumlah * karbohidrat) / ukuran
            total_karbohidrat += karbohidrat_bahan

            protein_bahan = (jumlah * protein) / ukuran
            total_protein += protein_bahan

            lemak_bahan = (jumlah * lemak_total) / ukuran
            total_lemak += lemak_bahan

    return total_kalori, total_karbohidrat, total_protein, total_lemak



# input = [{"bahan":"nasi", "jumlah":150, "satuan":"gram"},
#         {"bahan":"minyak goreng", "jumlah":15, "satuan":"gram"},
#         {"bahan":"bawang putih", "jumlah":5, "satuan":"gram"},
#         {"bahan":"bawang merah", "jumlah":10, "satuan":"gram"},
#         {"bahan":"telur", "jumlah":50, "satuan":"gram"},
#         {"bahan":"ayam", "jumlah":100, "satuan":"gram"},
#         {"bahan":"kecap manis", "jumlah":20, "satuan":"gram"}
#          ]

# total_kalori_resep = hitung_kalori(nutrisi_df(), input)
# print("Total Kalori Resep Masakan:", total_kalori_resep[0])
# print("Total karbohidrat Resep Masakan:", total_kalori_resep[1])
# print("Total protein Resep Masakan:", total_kalori_resep[2])
# print("Total lemak Resep Masakan:", total_kalori_resep[3])
