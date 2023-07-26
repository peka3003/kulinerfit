import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

from flask import Flask, request, jsonify
from datetime import datetime

import hitungKalori
import rekomendasi
import serupa

cred = credentials.Certificate("kulinerfit-34e65-firebase-adminsdk-m1qcu-8cda72c2a8.json")
firebase_admin.initialize_app(cred)

app=Flask(__name__)

db=firestore.client()

@app.route('/',methods = ['GET'])
def get_articles():
    return jsonify({"Hello":"WELCOME TO KULINERFIT by PEKA"})

@app.route('/get_resep', methods=['GET'])
def get_resep():
    # Dapatkan referensi koleksi "resep" dari Firestore
    resep_ref = db.collection('resep')

    # Dapatkan semua dokumen dari koleksi "resep"
    resep = []
    for doc in resep_ref.stream():
        resep.append(doc.to_dict())

    # Kembalikan data sebagai respons dalam format JSON
    return jsonify(resep)

@app.route('/add_resep', methods=['POST'])
def add_resep():
    try:
        # Ambil data resep dari permintaan POST
        data = request.get_json()

        # Pastikan data resep yang diterima memiliki semua atribut yang diperlukan
        # required_attributes = ["bahan", "imageUrl", "langkah", "namaResep", "timestamp", "userID", "durasi", "rating", "total_kalori", "userImage", "userName"]
        required_attributes = ["namaResep", "timestamp", "userID", "bahan", "langkah","imageUrl","kategori", "durasi", "porsi"]
        for attr in required_attributes:
            if attr not in data:
                return jsonify({"error": f"Attribute '{attr}' is missing in the request data."}), 400

        # Pastikan data bahan tidak kosong
        if not data["bahan"]:
            return jsonify({"error": "Bahan list is empty."}), 400

        # Konversi string timestamp menjadi format datetime
        try:
            timestamp = datetime.strptime(data["timestamp"], "%a, %d %b %Y %H:%M:%S %Z")
        except ValueError:
            return jsonify({"error": "Invalid timestamp format. Use format 'Day, DD Mon YYYY HH:MM:SS GMT'."}), 400
        
        df = hitungKalori.nutrisi_df()
        hasil = hitungKalori.hitung_kalori(df, data["bahan"])

        durasi_str = data["durasi"]
        durasi = int(durasi_str)

        porsi_str = data["porsi"]
        porsi = int(porsi_str)

        # Buat data resep baru
        new_resep = {
            "namaResep": data["namaResep"],
            "timestamp": timestamp,
            "userID": data["userID"],
            "bahan": data["bahan"],
            "langkah": data["langkah"],
            "imageUrl" : data["imageUrl"],
            "total_kalori" : "{:.2f}".format(hasil[0]),
            "kategori" : data["kategori"],
            "durasi" : durasi,
            "porsi" : porsi,
            "total_karbohidrat" : "{:.2f}".format(hasil[1]/porsi),
            "protein" : "{:.2f}".format(hasil[2]/porsi),
            "total_lemak" : "{:.2f}".format(hasil[3]/porsi)
        }

        # Tambahkan resep baru ke Firestore
        resep_ref = db.collection('resep').document()
        resep_ref.set(new_resep)

        return jsonify({"message": "Resep berhasil ditambahkan.", "id": resep_ref.id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/get_rekomendasi/<string:userId>', methods=['GET'])
def get_rekomendasi(userId):

    resep_df = rekomendasi.resep_df()
    larangan_df = rekomendasi.larangan_df()

    user_ref = db.collection("users").document(userId)
    user_data = user_ref.get()

    exit_flag = False

    if user_data.exists:
        # Jika data pengguna ditemukan dalam Firestore
        favorit = user_data.get("favorit")
        alergi_before = user_data.get("alergi")
        alergi = [item.lower() for item in alergi_before]
        print(alergi)
        penyakit = user_data.get("penyakit")

        if favorit:
            hasil = rekomendasi.get_recommendations(favorit, resep_df=resep_df, larangan_makanan=larangan_df)
            if alergi is not None and len(alergi) > 0:
                hasil = rekomendasi.get_recommendations(favorit,alergi=alergi, resep_df=resep_df, larangan_makanan=larangan_df)
                if penyakit is not None and len(penyakit) > 0:
                    hasil = rekomendasi.get_recommendations(favorit,alergi=alergi, penyakit=penyakit, resep_df=resep_df, larangan_makanan=larangan_df)
                    exit_flag=True
            
            if not exit_flag:
                 if penyakit is not None and len(penyakit) > 0:
                    hasil = rekomendasi.get_recommendations(favorit,penyakit=penyakit,resep_df=resep_df, larangan_makanan=larangan_df)

            # Dapatkan referensi koleksi "resep" dari Firestore
            resep_ref = db.collection('resep')
            # print(hasil)

            # Dapatkan semua dokumen dari koleksi "resep"
            resep = []
            for doc in resep_ref.stream():
                resep.append(doc.to_dict())
                # print(doc.to_dict()['namaResep'])
            resep_hasil = [recipe for recipe in resep if recipe['namaResep'] in hasil.tolist()]
                
            # Kembalikan data sebagai respons dalam format JSON
            print(resep_hasil)
            print(hasil)
            return jsonify(resep_hasil)
        else:
            # Jika data menu_rekom tidak ditemukan, berikan respons dengan pesan sesuai kebutuhan
            return jsonify({"message": "Tidak ada Rekomendasi"}), 404
    else:
        # Jika data pengguna tidak ditemukan dalam Firestore, berikan respons dengan pesan sesuai kebutuhan
        return jsonify({"message": "Pengguna dengan userID tersebut tidak ditemukan"}), 404
    
###TAMBAHAN
@app.route('/get_serupa/<string:makanan>', methods=['GET'])
def get_serupa(makanan):

    resep_df = serupa.resep_df()

    hasil = serupa.get_serupa(makanan, resep_df=resep_df)

    # Dapatkan referensi koleksi "resep" dari Firestore
    resep_ref = db.collection('resep')
    # print(hasil)

    # Dapatkan semua dokumen dari koleksi "resep"
    resep = []
    for doc in resep_ref.stream():
        resep.append(doc.to_dict())
        # print(doc.to_dict()['namaResep'])
    resep_hasil = [recipe for recipe in resep if recipe['namaResep'] in hasil.tolist()]
        
    # Kembalikan data sebagai respons dalam format JSON
    print(resep_hasil)
    print(hasil)
    return jsonify(resep_hasil)
        
if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)