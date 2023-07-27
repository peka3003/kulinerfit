import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

import re

from flask import Flask, request, jsonify
from datetime import datetime

import hitungKalori
import rekomendasi
import serupa

cred = credentials.Certificate("kulinerfit-34e65-firebase-adminsdk-m1qcu-8cda72c2a8.json")
firebase_admin.initialize_app(cred)

app=Flask(__name__)

db=firestore.client()

#test
@app.route('/',methods = ['GET'])
def get_articles():
    return jsonify({"Hello":"WELCOME TO KULINERFIT by PEKA"})

#resep
@app.route('/get_popular_resep', methods=['GET'])
def get_popular_resep():
    try:
        # Dapatkan referensi koleksi "resep" dari Firestore, dengan mengurutkan berdasarkan rating secara descending
        resep_ref = db.collection('resep').order_by('rating', direction=firestore.Query.DESCENDING)

        # Batasi hasil yang diambil hanya 7 data teratas
        resep_ref = resep_ref.limit(7)
        
        # Dapatkan semua dokumen dari koleksi "resep"
        resep = []
        for doc in resep_ref.stream():
            resep_data = doc.to_dict()
            # Konversi durasi di atas 60 menit menjadi jam
            if 'durasi' in resep_data:
                hours = resep_data['durasi'] // 60
                minutes = resep_data['durasi'] % 60

                # Atur format jam tanpa menit jika jam dan menitnya 0
                if hours == 0 and minutes == 0:
                    resep_data['durasi'] = "Kurang dari 1 menit"
                elif hours == 0:
                    resep_data['durasi'] = f"{minutes} menit"
                elif minutes == 0:
                    resep_data['durasi'] = f"{hours} jam"
                else:
                    resep_data['durasi'] = f"{hours} jam {minutes} menit"

            resep.append(resep_data)

        # Kembalikan data sebagai respons dalam format JSON
        return jsonify(resep)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_resep', methods=['GET'])
def get_resep():
    # Dapatkan referensi koleksi "resep" dari Firestore
    resep_ref = db.collection('resep')

   # Dapatkan semua dokumen dari koleksi "resep"
    resep = []
    for doc in resep_ref.stream():
        resep_data = doc.to_dict()
        # Konversi durasi di atas 60 menit menjadi jam
        if 'durasi' in resep_data:
            hours = resep_data['durasi'] // 60
            minutes = resep_data['durasi'] % 60

            # Atur format jam tanpa menit jika jam dan menitnya 0
            if hours == 0 and minutes == 0:
                resep_data['durasi'] = "Kurang dari 1 menit"
            elif hours == 0:
                resep_data['durasi'] = f"{minutes} menit"
            elif minutes == 0:
                resep_data['durasi'] = f"{hours} jam"
            else:
                resep_data['durasi'] = f"{hours} jam {minutes} menit"

        resep.append(resep_data)

    # Kembalikan data sebagai respons dalam format JSON
    return jsonify(resep)

@app.route('/search_resep', methods=['GET'])
def search_resep():
    try:
        query = request.args.get('query', '').lower()

        # Use a case-insensitive regex to match the query in the "namaResep" field
        # This will return recipes where the name contains the search query (partial match)
        filter_query = {'namaResep': re.compile(query, re.IGNORECASE)}

        # Get the filtered recipes from Firestore
        resep_ref = db.collection('resep').where('namaResep', 'regex', query).stream()
        filtered_resep = [doc.to_dict() for doc in resep_ref]

        # Kembalikan data sebagai respons dalam format JSON
        return jsonify(filtered_resep)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
     
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
            "rating" : 0,
            "total_karbohidrat" : "{:.2f}".format(hasil[1]),
            "protein" : "{:.2f}".format(hasil[2]),
            "total_lemak" : "{:.2f}".format(hasil[3]),
            "rating" : "0",
            "status" : False
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
        penyakit = user_data.get("penyakit")

        if favorit:
            rekomendasi.get_recommendations(favorit, resep_df=resep_df, larangan_makanan=larangan_df)
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

# Route untuk menambah user baru
@app.route('/add_user', methods=['POST'])
def add_user():
    try:
        # Mendapatkan data user dari body request
        data = request.json
        
        # Pastikan data yang dibutuhkan ada
        required_fields = ['beratBadan', 'email', 'jenisKelamin',
                           'nama', 'tinggiBadan', 'ttl', 'userID', 'userImage']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f"Field '{field}' tidak ditemukan dalam data."}), 400

        # Cek apakah userID sudah ada di Firestore
        email = data['email']
        user_ref = db.collection('users').document(email)
        if user_ref.get().exists:
            return jsonify({'error': 'User dengan email tersebut sudah ada.'}), 400

        # Proses data tanggal lahir
        ttl_str = data['ttl']
        try:
            ttl = datetime.strptime(ttl_str, "%a, %d %b %Y")
        except ValueError:
            return jsonify({'error': 'Format tanggal lahir tidak valid. Gunakan format: "Wed, 28 Feb 1990".'}), 400
        
        # Cek dan ubah inputan alergi makanan, riwayat penyakit, dan makanan favorit jika diperlukan
        alergi = data.get('alergi', [])
        penyakit = data.get('penyakit', [])
        favorit = data.get('favorit', '-')
        
        if alergi == "-":
            alergi = []
        if penyakit == "-":
            penyakit = []
        if favorit == "-":
            favorit = []
        
        # Buat dictionary data user
        user_data = {
            'alergi': alergi,
            'beratBadan': data['beratBadan'],
            'email': data['email'],
            'favorit': favorit,
            'jenisKelamin': data['jenisKelamin'],
            'nama': data['nama'],
            'penyakit': penyakit,
            'tinggiBadan': data['tinggiBadan'],
            'ttl': ttl_str,
            'userID': data['userID'],
            'userImage': data['userImage']
        }
        
        # Tambahkan data user ke Firestore
        user_ref.set(user_data)
        
        return jsonify({'message': 'User berhasil ditambahkan.'}), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Fungsi untuk menghitung usia berdasarkan tanggal lahir
def calculate_age(date_of_birth):
    # Ubah objek DatetimeWithNanoseconds menjadi string
    date_of_birth_str = date_of_birth.strftime("%a, %d %b %Y")

    # Konversi string tanggal lahir menjadi objek datetime
    date_format = "%a, %d %b %Y"
    birth_date = datetime.strptime(date_of_birth_str, date_format)

    # Dapatkan tanggal saat ini
    current_date = datetime.utcnow()

    # Hitung selisih tanggal lahir dan tanggal saat ini
    age_timedelta = current_date - birth_date

    # Ambil bagian usia dalam tahun saja
    age = age_timedelta.days // 365

    return age

#users
@app.route('/get_users_all', methods=['GET'])
def get_users_all():
    # Dapatkan referensi koleksi "users" dari Firestore
    users_ref = db.collection('users')

    # Dapatkan semua dokumen dari koleksi "users"
    users = []
    for doc in users_ref.stream():
        users_data = doc.to_dict()

        users.append(users_data)

    # Kembalikan data sebagai respons dalam format JSON
    return jsonify(users)

@app.route('/get_users', methods=['GET'])
def get_users():
    # Dapatkan parameter userID dari URL
    user_id = request.args.get('userID')

    if not user_id:
        return jsonify({'error': 'Parameter userID tidak ditemukan.'}), 400

    # Dapatkan referensi koleksi "users" dari Firestore
    users_ref = db.collection('users')

    # Dapatkan data pengguna berdasarkan userID
    user_doc = users_ref.document(user_id).get()
    if not user_doc.exists:
        return jsonify({'error': 'User dengan userID tersebut tidak ditemukan.'}), 404

    # Dapatkan data pengguna dalam bentuk dictionary
    user_data = user_doc.to_dict()

    # Peroleh tanggal lahir dari data Firestore dengan key 'ttl'
    date_of_birth = user_data.get('ttl')

    # Jika ada tanggal lahir, hitung usia dan tambahkan informasi usia ke dalam data pengguna
    if date_of_birth:
        # Convert date_of_birth string to a datetime object
        date_of_birth = datetime.strptime(date_of_birth, "%A, %d %B %Y")
        age = calculate_age(date_of_birth)
        user_data['age'] = age

        # Ubah tanggal lahir menjadi format yang hanya menampilkan tanggal, bulan, dan tahun
        date_of_birth_str = date_of_birth.strftime("%d %B %Y")
        user_data['ttl'] = date_of_birth_str

    # Kembalikan data pengguna dalam format JSON
    return jsonify(user_data)

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
