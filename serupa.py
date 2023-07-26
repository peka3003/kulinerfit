import pandas as pd
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Inisialisasi Firebase Admin SDK
# cred = credentials.Certificate("kulinerfit-firebase-adminsdk-7qhfd-eb15e48462.json")  # Ganti dengan path ke serviceAccountKey.json Anda
# firebase_admin.initialize_app(cred)

def resep_df():
    # Dapatkan referensi ke koleksi "data_makanan" dalam Firestore
    db = firestore.client()
    data_resep_ref = db.collection("resep")

    # Ambil seluruh data dari koleksi "data_makanan"
    resep = []
    for doc in data_resep_ref.stream():
        resep.append(doc.to_dict())

    # Membuat list untuk menyimpan data namaResep dan bahan
    nama_resep_list = []
    bahan_list = []

    # Mengambil data namaResep dan bahan dari setiap dokumen
    for doc in resep:
        nama_resep_list.append(doc["namaResep"])
        bahan_list.append(", ".join(b["bahan"] for b in doc["bahan"]))

    # Membuat dataframe dari data yang telah diambil
    resep_df = pd.DataFrame({
        "nama_resep": nama_resep_list,
        "bahan": bahan_list
    })
    
    return(resep_df)


# The main recommender code!
def get_serupa(makanan, resep_df=None):

    count = CountVectorizer(stop_words='english')
    count_matrix = count.fit_transform(resep_df['nama_resep'])

    cosine_sim2 = cosine_similarity(count_matrix, count_matrix)

    # Reseting the index and pulling out the names of the food alone from the df dataframe
    resep_df = resep_df.reset_index()
    indices = pd.Series(resep_df.index, index=resep_df['nama_resep']).drop_duplicates()

    idx = indices[makanan]
    sim_scores = list(enumerate(cosine_sim2[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    # Get the scores of the 5 most similar food
    sim_scores = sim_scores[1:6]

    food_indices = [i[0] for i in sim_scores]
    
    return resep_df['nama_resep'].iloc[food_indices]


# ### TEST ###

# # Memiliki bahan alergi berikut
# bahan_alergi = ['kacang polong','telur']
# # riwayat = ["gula tinggi", "stroke"]

# # Panggil fungsi get_recommendations dengan menyertakan bahan alergi
# rekomendasi = get_recommendations('Nasi Lemak', alergi=bahan_alergi)

# # Tampilkan rekomendasi resep masakan
# print(rekomendasi)
