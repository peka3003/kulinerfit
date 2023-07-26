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


def larangan_df():
    # Dapatkan referensi ke koleksi "data_makanan" dalam Firestore
    db = firestore.client()
    larangan_penyakit_ref = db.collection("penyakit_larangan")

    # Ambil seluruh data dari koleksi "data_makanan"
    larangan = []
    for doc in larangan_penyakit_ref.stream():
        larangan.append(doc.to_dict())

    # Ubah data menjadi kamus dengan penyakit sebagai kunci dan daftar bahan yang dilarang sebagai nilai
    larangan_makanan_dict = {data['penyakit']: data['larangan'] for data in larangan}

    return larangan_makanan_dict



# The main recommender code!
def get_recommendations(makanan_favorit, alergi=None, penyakit=None, resep_df=None, larangan_makanan=None):

    count = CountVectorizer(stop_words='english')
    count_matrix = count.fit_transform(resep_df['bahan'])

    cosine_sim2 = cosine_similarity(count_matrix, count_matrix)

    # Reseting the index and pulling out the names of the food alone from the df dataframe
    resep_df = resep_df.reset_index()
    indices = pd.Series(resep_df.index, index=resep_df['nama_resep']).drop_duplicates()

    idx = indices[makanan_favorit]
    sim_scores = list(enumerate(cosine_sim2[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    # Get the scores of the 5 most similar food
    sim_scores = sim_scores[1:6]

    food_indices = [i[0] for i in sim_scores]
    if alergi is not None:
        # Filter resep masakan yang tidak mengandung bahan alergi
        food_indices = [idx for idx in food_indices if not any(ingredient in resep_df['bahan'][idx] for ingredient in alergi)]

    if penyakit is not None and isinstance(penyakit, list):
        # Inisialisasi list kosong untuk menyimpan hasil rekomendasi dari setiap penyakit
        recommended_food_indices = []

        for disease in penyakit:
            # Pastikan setiap penyakit adalah string dan sesuai dengan kunci dalam kamus larangan_makanan
            if isinstance(disease, str) and disease in larangan_makanan:
                # Filter resep masakan yang tidak mengandung bahan larangan untuk penyakit yang diberikan
                filtered_indices = [idx for idx in food_indices if not any(ingredient in resep_df['bahan'][idx] for ingredient in larangan_makanan[disease])]
                recommended_food_indices.append(filtered_indices)

        # Ambil intersect dari semua hasil filter penyakit
        if recommended_food_indices:
            intersect_indices = set(recommended_food_indices[0]).intersection(*recommended_food_indices[1:])
            intersect_indices = list(intersect_indices)
            recommended_food_indices = intersect_indices[:5]
        else:
            recommended_food_indices = []

        return resep_df['nama_resep'].iloc[recommended_food_indices]

    # Jika tidak ada penyakit yang diberikan, langsung kembalikan hasil rekomendasi
    return resep_df['nama_resep'].iloc[food_indices]


# ### TEST ###

# # Memiliki bahan alergi berikut
# bahan_alergi = ['kacang polong','telur']
# # riwayat = ["gula tinggi", "stroke"]

# # Panggil fungsi get_recommendations dengan menyertakan bahan alergi
# rekomendasi = get_recommendations('Nasi Lemak', alergi=bahan_alergi)

# # Tampilkan rekomendasi resep masakan
# print(rekomendasi)
