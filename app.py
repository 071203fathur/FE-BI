# Import modul-modul yang diperlukan dari Flask dan lainnya
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
import requests
from datetime import datetime, timedelta # Import timedelta untuk manajemen waktu sesi
import json
import os
# import flash # Removed as flash is not imported or used elsewhere directly
from werkzeug.utils import secure_filename
from flask_cors import CORS # Import CORS dari flask_cors

# Inisialisasi aplikasi Flask
# Konfigurasi static_folder dan static_url_path untuk melayani aset dari templates/user/forms/assets
app = Flask(
    __name__,
    static_folder=os.path.join('templates', 'user', 'forms', 'assets'),
    static_url_path='/form/assets'
)
CORS(app) # Mengaktifkan CORS untuk semua rute di aplikasi Flask

# Konfigurasi kunci rahasia untuk sesi. Ini sangat penting untuk keamanan sesi.
# Ganti ini dengan string acak yang kuat di produksi.
app.secret_key = "supersecretkey" # Kunci rahasia untuk pengelolaan sesi

# Konfigurasi durasi sesi permanen (misalnya, 30 menit)
# Ini akan membuat sesi kedaluwarsa setelah waktu ini jika tidak ada aktivitas.
app.permanent_session_lifetime = timedelta(minutes=30) # Sesuaikan waktu sesuai kebutuhan Anda

# URL dasar untuk API backend Anda
API_BASE_URL = "https://silap-backend.my.id/api/"

# Konfigurasi upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Batas ukuran file 16MB

# Data dummy bank (sesuaikan dengan kebutuhan produksi Anda jika diperlukan)
# Data ini digunakan untuk mengisi dropdown "Nama PJP" di form KPSP
banks = [
    {"id": 1, "nama": "PT Fliptech Lentera Inspirasi Pertiwi", "kategori": "Penyedia Jasa Pembayaran - Kategori Izin 3",
     "no_izin": "18/196/DKSP/68", "tgl_izin": "04 Oktober 2016"},
    {"id": 2, "nama": "PT Contoh Bank Digital", "kategori": "Bank Umum",
     "no_izin": "SK-001/OJK/2020", "tgl_izin": "15 Januari 2020"},
    {"id": 3, "nama": "PT Pembayaran Cepat", "kategori": "Penyedia Jasa Pembayaran - Kategori Izin 2",
     "no_izin": "19/200/DKSP/70", "tgl_izin": "10 Maret 2018"}
]

# Fungsi pembantu untuk mengonversi nama bidang yang mudah dibaca menjadi nama payload snake_case
def to_snake_case(name):
    """
    Mengubah nama field dari format spasi/judul ke snake_case.
    Contoh: "Nama PJP" menjadi "nama_pjp"
    """
    name = name.replace(" ", "_").replace("/", "_").replace("-", "_")
    name = name.replace("(", "").replace(")", "").replace("%", "")
    name = name.lower()
    return name

# --- Penyimpanan data KPSP di memori (untuk demonstrasi sederhana) ---
# CATATAN PENTING: Data ini akan HILANG setiap kali server Flask di-restart.
# Untuk persistensi data di aplikasi produksi, Anda harus mengimplementasikan
# penggunaan database (misalnya, SQLite, PostgreSQL, MySQL) dengan ORM (seperti SQLAlchemy).
kpsp_reports = []
report_id_counter = 1 # Penghitung untuk memberikan ID unik pada setiap laporan

# --- Fungsi utilitas untuk simulasi perhitungan KPSP ---
# Anda SANGAT PERLU mengganti logika ini dengan rumus perhitungan KPSP yang sebenarnya
# dari file JavaScript (core.js) atau dokumentasi rumus KPSP Anda.
# Fungsi ini hanya akan menjadi placeholder atau untuk validasi sederhana jika diperlukan.
def calculate_kpsp_backend(form_data):
    """
    Placeholder untuk perhitungan KPSP di backend.
    Dalam implementasi ini, perhitungan utama ada di frontend (JavaScript).
    Fungsi ini bisa digunakan untuk validasi data atau perhitungan kompleks
    yang tidak bisa dilakukan di frontend.
    """
    # Contoh sederhana: mengambil nilai dan mengembalikannya
    # Anda bisa menambahkan logika validasi atau perhitungan parsial di sini.
    try:
        modal_inti = float(form_data.get('modalInti', '0').replace('.', '').replace(',', '.'))
        total_ongoing_capital_str = form_data.get('totalOngoingCapitalDisplay', '0').replace('Rp ', '').replace('.', '').replace(',', '.')
        total_ongoing_capital = float(total_ongoing_capital_str)

        # Asumsi rasio sederhana untuk contoh backend
        if modal_inti > 0:
            dummy_ratio = (total_ongoing_capital / modal_inti) * 100
        else:
            dummy_ratio = 0

        return {
            "status_validasi_backend": "OK",
            "dummy_calculated_ratio": round(dummy_ratio, 2),
            "message": "Data berhasil diterima dan divalidasi oleh backend (perhitungan utama di frontend)."
        }
    except ValueError:
        return {"error": "Input numerik tidak valid pada backend."}
    except Exception as e:
        return {"error": f"Kesalahan backend saat memproses data: {str(e)}"}

@app.before_request
def before_request():
    """
    Fungsi ini berjalan sebelum setiap permintaan.
    Memeriksa apakah sesi pengguna aktif. Jika tidak, arahkan ke halaman login.
    """
    # Izinkan akses ke halaman login dan rute statis tanpa autentikasi
    # Ini penting untuk mencegah loop pengalihan tak terbatas
    # Memperbarui agar juga mengizinkan akses ke static_url_path yang baru
    if request.endpoint == 'login' or \
       request.path.startswith('/static/') or \
       request.path.startswith('/form/assets/') or \
       request.path.startswith('/api/laporan/all-status'): # Izinkan akses ke endpoint status laporan
        session.permanent = True # Pastikan sesi login juga diperbarui
        return

    # Jika sesi tidak memiliki 'username' (berarti tidak login atau sesi kedaluwarsa)
    if 'username' not in session:
        # Hapus semua data sesi yang mungkin tersisa
        session.clear()
        # Arahkan ke halaman login
        return redirect(url_for('login'))

    # Perbarui waktu sesi agar tetap aktif selama ada aktivitas
    # Ini akan memperpanjang masa pakai sesi setiap kali ada permintaan
    session.permanent = True
    g.user = session.get('username') # Menyimpan username di objek g untuk akses mudah di seluruh permintaan

@app.route("/", methods=["GET", "POST"])
def login():
    """
    Menangani login pengguna. Mengirim kredensial ke endpoint login API backend.
    Jika berhasil, menyimpan token akses dalam sesi dan mengarahkan ke dasbor berdasarkan peran.
    """
    if request.method == "POST":
        # PERBAIKAN: Mengubah 'username' menjadi 'sandi_pjp' untuk mencocokkan nama field di HTML
        sandi_pjp = request.form["sandi_pjp"]
        password = request.form["password"]

        login_data = {"sandi_pjp": sandi_pjp, "password": password}
        try:
            response = requests.post(f"{API_BASE_URL}auth/login/", json=login_data)
            response_data = response.json()
            if response.status_code == 200 and response_data.get("data") and response_data["data"].get("access"):
                session["username"] = sandi_pjp
                session["access_token"] = response_data["data"]["access"]
                session["refresh_token"] = response_data["data"].get("refresh") # Simpan refresh token jika ada
                session.permanent = True # Set sesi menjadi permanen setelah login berhasil
                # Menentukan peran berdasarkan username (mengasumsikan 'admin' untuk admin, lainnya untuk user)
                if sandi_pjp == "admin":
                    session["role"] = "admin"
                    return redirect(url_for("admin_dashboard"))
                else:
                    session["role"] = "user"
                    return redirect(url_for("user_dashboard"))
            else:
                error_message = response_data.get("message", "Username atau password salah!")
                # Menampilkan pesan error dari backend, termasuk pesan 'sandi_pjp' jika ada
                if response_data.get("sandi_pjp"):
                    error_message = f"Error: {response_data['sandi_pjp'][0]}"
                return render_template("login.html", error=error_message)

        except requests.exceptions.RequestException as e:
            # Menangani kesalahan jaringan atau server tidak dapat dijangkau
            error_message = f"Gagal terhubung ke server API: {e}"
            return render_template("login.html", error=error_message)
    return render_template("login.html")



@app.route("/admin/dashboard")
def admin_dashboard():
    """Merender dasbor admin, memerlukan peran admin."""
    # before_request akan menangani pengalihan jika sesi tidak valid
    if session.get("role") != "admin":
        return redirect(url_for("login")) # Redireksi eksplisit jika peran tidak cocok
    return render_template("admin/dashboardadmin.html", banks=banks)

@app.route("/user/dashboard")
def user_dashboard():
    """Merender dasbor pengguna, memerlukan login pengguna."""
    # before_request akan menangani pengalihan jika sesi tidak valid
    if "username" not in session: # Redireksi eksplisit jika username tidak ada
        return redirect(url_for("login"))
    return render_template("user/dashboarduser.html")

@app.route("/admin/profile", endpoint="admin_profile")
def profile_admin():
    """Merender halaman profil admin, memerlukan peran admin."""
    # before_request akan menangani pengalihan jika sesi tidak valid
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("admin/profile.html")

@app.route('/user/profile')
def user_profile():
    """Merender halaman profil pengguna, memerlukan login pengguna."""
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/profile.html")

# --- Fungsi baru untuk mengambil data profil dari backend ---
def fetch_profile_from_backend(is_retry=False):
    """
    Mengambil data profil pengguna dari backend API.
    Args:
        is_retry (bool): Menunjukkan apakah ini percobaan ulang setelah refresh token.
    Returns:
        tuple: Sebuah tuple yang berisi (boolean_sukses, data_profil, kode_status).
    """
    if "username" not in session:
        print("DEBUG: Sesi tidak valid, tidak ada username dalam sesi.")
        return False, "Sesi tidak valid, silakan login kembali.", 401

    access_token = session.get('access_token')

    if not access_token:
        print("DEBUG: Tidak ada access_token dalam sesi. Pengguna mungkin tidak login atau tidak diotorisasi API.")
        return False, "Autentikasi gagal, silakan login kembali atau hubungi admin.", 401

    headers = {"Authorization": f"Bearer {access_token}"}
    full_api_url = f"{API_BASE_URL}auth/profile/"
    
    print(f"\n--- DEBUG: Mengambil profil dari API Backend ---")
    print(f"URL: {full_api_url}")
    print(f"Method: GET")
    print(f"Percobaan Ulang: {is_retry}")

    try:
        response = requests.get(full_api_url, headers=headers, timeout=30)
        
        print(f"--- DEBUG: Respons dari API Backend ---")
        print(f"Status Code: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"Response JSON: {json.dumps(response_data, indent=2)}")
        except json.JSONDecodeError:
            response_data = {"message": response.text}
            print(f"Response Text (bukan JSON): {response.text}")
        
        if response.status_code == 401 and not is_retry:
            print("DEBUG: Menerima 401. Mencoba refresh token dan mengulang permintaan profil.")
            if refresh_access_token():
                return fetch_profile_from_backend(is_retry=True)
            else:
                print("DEBUG: Gagal refresh token. Memaksa logout.")
                session.clear()
                return False, "Sesi kedaluwarsa atau tidak valid. Silakan login kembali.", 401
        
        if 200 <= response.status_code < 300:
            return True, response_data, response.status_code
        else:
            error_message = response_data.get("message", "Gagal mengambil data profil.")
            if isinstance(response_data, dict):
                for key, value in response_data.items():
                    if key != "message":
                        if isinstance(value, list):
                            error_message += f"\n{key}: {', '.join(value)}"
                        else:
                            error_message += f"\n{key}: {value}"
            return False, error_message, response.status_code
    except requests.exceptions.ConnectionError as e:
        print(f"DEBUG: Kesalahan Koneksi saat mengambil profil: {e}")
        return False, f"Gagal terhubung ke server API (koneksi ditolak atau server tidak tersedia)", 500
    except requests.exceptions.Timeout as e:
        print(f"DEBUG: Permintaan profil ke API Backend timeout: {e}")
        return False, f"Permintaan ke server API melebihi batas waktu (Time Out)", 504
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Terjadi kesalahan saat mengirim permintaan profil ke server API: {e}")
        return False, f"Terjadi kesalahan saat mengirim permintaan profil ke server API: {e}", 500
    except json.JSONDecodeError:
        print(f"DEBUG: Respon API profil bukan JSON yang valid atau kosong.")
        return False, "Respon API profil bukan JSON yang valid atau kosong.", 500


# --- Rute API untuk Profil Pengguna ---
@app.route('/api/user/profile', methods=['GET'])
def get_user_profile_api():
    """
    Mengambil data profil pengguna dari backend API.
    """
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401

    # Memanggil fungsi baru yang terpisah untuk GET profil
    success, message, status_code = fetch_profile_from_backend()
    
    if success:
        return jsonify(message), status_code
    else:
        return jsonify({"success": False, "message": message}), status_code

@app.route('/api/user/profile/update', methods=['PUT'])
def update_user_profile_api():
    """
    Memperbarui data profil pengguna di backend API.
    Menerima payload JSON dari frontend.
    """
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401

    # Ambil data JSON dari request body
    data_to_update = request.get_json()
    if not data_to_update:
        return jsonify({"success": False, "message": "Tidak ada data yang diberikan untuk pembaruan."}), 400

    success, message, status_code = send_report_to_backend(
        endpoint_path="auth/profile/update/",
        method="PUT",
        json_payload=data_to_update
    )

    if success:
        return jsonify(message), status_code # message di sini adalah respons JSON dari BE
    else:
        return jsonify({"success": False, "message": message}), status_code


@app.route("/admin/add_bank", methods=["POST"])
def add_bank():
    """
    Menangani penambahan bank baru (data dummy untuk saat ini).
    Fungsi ini tidak berinteraksi dengan API berdasarkan dokumentasi yang diberikan.
    """
    if "username" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    nama = request.form["nama"]
    kategori = request.form["kategori"]
    no_izin = request.form["no_izin"]
    tgl_izin = request.form["tgl_izin"]
    banks.append({"id": len(banks) + 1, "nama": nama, "kategori": kategori, "no_izin": no_izin, "tgl_izin": tgl_izin})
    return redirect(url_for("admin_dashboard"))

@app.route("/user/laporan")
def user_laporan():
    """Mengarahkan ke dasbor pengguna (mengasumsikan laporan dapat diakses dari sana)."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    # Rute ini mungkin berlebihan jika user_dashboard sudah mencantumkan laporan.
    # Pertimbangkan untuk menghapus jika dashboarduser.html adalah halaman laporan utama.
    return render_template("user/dashboarduser.html")

@app.route("/admin/laporan")
def admin_laporan():
    """Placeholder untuk halaman laporan admin."""
    if "username" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    return "Halaman Laporan Admin (Dalam Pengembangan)"

@app.route('/admin/history')
def admin_history():
    """Merender halaman riwayat admin, memerlukan peran admin."""
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template('admin/history.html')

@app.route('/admin/peraturan')
def admin_peraturan():
    """Merender halaman peraturan admin, memerlukan peran admin."""
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template('admin/peraturan.html')

@app.route("/base")
def base_page():
    """Merender template dasar admin (untuk tujuan debugging/pengujian)."""
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("admin/base.html")

def refresh_access_token():
    """
    Mencoba untuk memperbarui token akses menggunakan refresh token yang tersimpan di sesi.
    Mengembalikan True jika berhasil, False jika gagal.
    """
    refresh_token = session.get('refresh_token')
    if not refresh_token:
        print("DEBUG: Tidak ada refresh token dalam sesi.")
        return False
    
    refresh_url = f"{API_BASE_URL}auth/token/refresh/"
    try:
        refresh_response = requests.post(refresh_url, json={"refresh": refresh_token})
        refresh_response.raise_for_status() # Angkat HTTPError untuk status kode 4xx/5xx

        refresh_data = refresh_response.json()
        new_access_token = refresh_data.get("access")

        if new_access_token:
            session["access_token"] = new_access_token
            print("DEBUG: Token akses berhasil diperbarui.")
            return True
        else:
            print(f"DEBUG: Gagal memperbarui token: {refresh_data.get('detail', 'Respons tidak valid.')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Kesalahan saat memperbarui token: {e}")
        return False

def send_report_to_backend(endpoint_path, method="POST", form_data=None, file_obj=None, is_retry=False, json_payload=None):
    """
    Fungsi generik untuk mengirim data laporan dan file ke API backend.
    Mencakup logika percobaan ulang dengan refresh token.
    Args:
        endpoint_path (str): Jalur endpoint API tertentu (misalnya, "laporan/fraud/submit").
        method (str): Metode HTTP (GET, POST, PUT, dll.). Default: "POST".
        form_data (dict, optional): Kamus bidang formulir dan nilainya (untuk multipart/form-data). Defaults to None.
        file_obj (werkzeug.datastructures.FileStorage, optional): Objek file yang diunggah. Defaults to None.
        is_retry (bool): Menunjukkan apakah ini percobaan ulang setelah refresh token.
        json_payload (dict, optional): Kamus data JSON (untuk application/json). Defaults to None.
    Returns:
        tuple: Sebuah tuple yang berisi (boolean_sukses, pesan, kode_status).
    """
    if "username" not in session:
        print("DEBUG: Sesi tidak valid, tidak ada username dalam sesi.")
        return False, "Sesi tidak valid, silakan login kembali.", 401

    access_token = session.get('access_token')

    if not access_token:
        print("DEBUG: Tidak ada access_token dalam sesi. Pengguna mungkin tidak login atau tidak diotorisasi API.")
        return False, "Autentikasi gagal, silakan login kembali atau hubungi admin.", 401

    headers = {"Authorization": f"Bearer {access_token}"}
    
    full_api_url = f"{API_BASE_URL}{endpoint_path}"
    print(f"\n--- DEBUG: Mengirim permintaan ke API Backend ---")
    print(f"URL: {full_api_url}")
    print(f"Method: {method}")
    print(f"Headers (tanpa token): {json.dumps({k: v for k, v in headers.items() if k != 'Authorization'}, indent=2)}")

    request_kwargs = {}
    request_kwargs["timeout"] = 30 # Timeout 30 detik

    if json_payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(json_payload)
        print(f"Request Body (JSON): {body}")
        request_kwargs["json"] = json_payload
    elif form_data is not None:
        data_to_send = {}
        for key, value in form_data.items():
            data_to_send[key] = str(value) if value is not None else ''

        # Hapus sandi_pjp dan nama_pjp jika tidak diharapkan oleh endpoint API tertentu.
        if to_snake_case("Sandi PJP") in data_to_send:
            print(f"DEBUG: Menghapus field '{to_snake_case('Sandi PJP')}' dari payload laporan.")
            del data_to_send[to_snake_case("Sandi PJP")]
        if to_snake_case("Nama PJP") in data_to_send:
            print(f"DEBUG: Menghapus field '{to_snake_case('Nama PJP')}' dari payload laporan.")
            del data_to_send[to_snake_case("Nama PJP")]
        
        files = {}
        if file_obj and file_obj.filename:
            files = {"file": (file_obj.filename, file_obj.stream, file_obj.mimetype)}
            print(f"DEBUG: File akan dikirim: {file_obj.filename}, MimeType: {file_obj.mimetype}")
        else:
            print("DEBUG: Tidak ada file yang akan dikirim.")

        print(f"Data Form (sebelum pengiriman): {data_to_send}")
        print(f"Files: {files.keys() if files else 'No files'}")
        request_kwargs["data"] = data_to_send
        request_kwargs["files"] = files
    else:
        print("DEBUG: Tidak ada form_data, json_payload, atau file yang disediakan.")

    print(f"Percobaan Ulang: {is_retry}")

    try:
        # Menggunakan requests.request untuk mendukung berbagai metode HTTP
        response = requests.request(method, full_api_url, headers=headers, **request_kwargs)
        
        print(f"--- DEBUG: Respons dari API Backend ---")
        print(f"Status Code: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"Response JSON: {json.dumps(response_data, indent=2)}")
        except json.JSONDecodeError:
            response_data = {"message": response.text}
            print(f"Response Text (bukan JSON): {response.text}")
        
        # Penanganan 401 Unauthorized (mungkin karena token kedaluwarsa)
        if response.status_code == 401 and not is_retry:
            print("DEBUG: Menerima 401. Mencoba refresh token dan mengulang permintaan.")
            if refresh_access_token():
                # Ulangi permintaan dengan token baru
                return send_report_to_backend(endpoint_path, method, form_data, file_obj, is_retry=True, json_payload=json_payload)
            else:
                print("DEBUG: Gagal refresh token. Memaksa logout.")
                session.clear()
                return False, "Sesi kedaluwarsa atau tidak valid. Silakan login kembali.", 401
        
        # Periksa status code untuk sukses
        if 200 <= response.status_code < 300: # 2xx codes indicate success
            return True, response_data, response.status_code # Mengembalikan response_data penuh
        else:
            error_message = response_data.get("message", "Gagal mengirim laporan.")
            if isinstance(response_data, dict):
                for key, value in response_data.items():
                    if key != "message":
                        if isinstance(value, list):
                            error_message += f"\n{key}: {', '.join(value)}"
                        else:
                            error_message += f"\n{key}: {value}"
            return False, error_message, response.status_code
    except requests.exceptions.ConnectionError as e:
        print(f"DEBUG: Kesalahan Koneksi: {e}")
        return False, f"Gagal terhubung ke server API (koneksi ditolak atau server tidak tersedia)", 500
    except requests.exceptions.Timeout as e:
        print(f"DEBUG: Permintaan ke API Backend timeout: {e}")
        return False, f"Permintaan ke server API melebihi batas waktu", 504
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Terjadi kesalahan saat mengirim permintaan ke server API: {e}")
        return False, f"Terjadi kesalahan saat mengirim permintaan ke server API", 500
    except json.JSONDecodeError:
        print(f"DEBUG: Respon API bukan JSON yang valid atau kosong.")
        return False, "Respon API bukan JSON yang valid atau kosong.", 500

# --- Endpoint Proxy Baru untuk Status Seluruh Laporan ---
@app.route('/api/laporan/all-status', methods=['GET'])
def get_all_report_status():
    """
    Endpoint proxy untuk mengambil status keberadaan laporan dari backend.
    """
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401

    access_token = session.get('access_token')
    if not access_token:
        return jsonify({"success": False, "message": "Autentikasi gagal, tidak ada token akses."}), 401

    headers = {"Authorization": f"Bearer {access_token}"}
    api_url = f"{API_BASE_URL}laporan/all-status"

    print(f"\n--- DEBUG: Mengambil status laporan dari API Backend via proxy ---")
    print(f"URL: {api_url}")
    print(f"Method: GET")

    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        response_data = response.json()

        print(f"--- DEBUG: Respons dari API Backend (status laporan) ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response JSON: {json.dumps(response_data, indent=2)}")

        # Jika API backend mengembalikan 401, coba refresh token
        if response.status_code == 401:
            print("DEBUG: Menerima 401 dari backend saat mengambil status laporan. Mencoba refresh token.")
            if refresh_access_token():
                # Jika refresh berhasil, coba lagi permintaan asli
                new_access_token = session.get('access_token')
                headers["Authorization"] = f"Bearer {new_access_token}"
                response = requests.get(api_url, headers=headers, timeout=30)
                response_data = response.json()
                print(f"DEBUG: Percobaan ulang status laporan. Status Code: {response.status_code}")
                print(f"DEBUG: Percobaan ulang status laporan. Response JSON: {json.dumps(response_data, indent=2)}")
            else:
                print("DEBUG: Gagal refresh token saat mengambil status laporan. Memaksa logout.")
                session.clear()
                return jsonify({"success": False, "message": "Sesi kedaluwarsa atau tidak valid. Silakan login kembali."}), 401
        
        # Mengembalikan respons dari backend langsung ke frontend
        return jsonify(response_data), response.status_code

    except requests.exceptions.ConnectionError as e:
        print(f"DEBUG: Kesalahan Koneksi saat mengambil status laporan: {e}")
        return jsonify({"success": False, "message": f"Gagal terhubung ke server API (koneksi ditolak atau server tidak tersedia): {e}"}), 500
    except requests.exceptions.Timeout as e:
        print(f"DEBUG: Permintaan status laporan ke API Backend timeout: {e}")
        return jsonify({"success": False, "message": f"Permintaan ke server API melebihi batas waktu (Time Out): {e}"}), 504
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Terjadi kesalahan saat mengirim permintaan status laporan ke server API: {e}")
        return jsonify({"success": False, "message": f"Terjadi kesalahan saat mengirim permintaan status laporan ke server API: {e}"}), 500
    except json.JSONDecodeError:
        print(f"DEBUG: Respon API status laporan bukan JSON yang valid atau kosong.")
        return jsonify({"success": False, "message": "Respon API status laporan bukan JSON yang valid atau kosong."}), 500


# --- Rute Pengiriman Laporan ---
@app.route("/submit/laporan-fraud", methods=["POST"])
def submit_laporan_fraud():
    """Menangani pengiriman Laporan Fraud."""
    try:
        # Backend mengharapkan DD/MM/YYYY untuk tanggal_surat
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "jumlah_fraud": int(request.form.get("jumlah_fraud")),
        # Menggunakan nama field API: besar_potensi_kerugian
        "besar_potensi_kerugian": int(request.form.get("besar_potensi_kerugian")),  
        "keterangan_fraud": request.form.get("keterangan_fraud"),
        "keterangan_tindak_lanjut": request.form.get("keterangan_tindak_lanjut")
    }
    # Mengambil file menggunakan nama 'file' sesuai API
    file_laporan = request.files.get("file")  

    success, message, status_code = send_report_to_backend("laporan/fraud/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

@app.route("/form/laporan-fraud")
def form_laporan_fraud():
    """Merender formulir untuk Laporan Fraud."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    # Mendapatkan tahun saat ini untuk dropdown tahun laporan
    current_year = datetime.now().year
    return render_template("user/forms/laporan_fraud.html", current_year=current_year)

@app.route("/submit/laporan-dttot", methods=["POST"])
def submit_laporan_dttot():
    """
    Menangani pengiriman Laporan DTTOT.
    """
    try:
        # Format tanggal_surat ke DD/MM/YYYY
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        "nomor_surat_kepolisian": request.form.get("nomor_surat_kepolisian"), # Sesuai API
        "tanggal_surat": formatted_tanggal_surat,
        "perihal": request.form.get("perihal"),
        "jumlah_terduga_teroris": int(request.form.get("jumlah_terduga_teroris")),
        "organisasi_teroris": request.form.get("organisasi_teroris"), # Sesuai API
        "keterangan": request.form.get("keterangan"),
    }
    file_laporan = request.files.get("file") # Nama field di form sekarang adalah 'file' sesuai API

    success, message, status_code = send_report_to_backend("laporan/dttot/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

@app.route("/form/laporan-dttot")
def form_laporan_dttot():
    """Merender formulir untuk Laporan DTTOT."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    # Mendapatkan tahun saat ini untuk dropdown tahun laporan
    current_year = datetime.now().year
    return render_template("user/forms/laporan_dttot.html", current_year=current_year)

@app.route("/form/laporan-keuangan-tahunan")
def form_laporan_keuangan_tahunan():
    """Merender formulir untuk Laporan Keuangan Tahunan Audited."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    # Mendapatkan tahun saat ini untuk dropdown tahun laporan
    current_year = datetime.now().year
    return render_template("user/forms/laporan_keuangan_tahunan.html", current_year=current_year)

@app.route("/submit/laporan-keuangan-tahunan", methods=["POST"])
def submit_laporan_keuangan_tahunan():
    """
    Menangani pengiriman Laporan Keuangan Tahunan Audited.
    """
    try:
        # Tanggal surat dan tanggal opini harus dalam formatYYYY-MM-DD
        # Input HTML type="date" sudah mengirimkan dalam formatYYYY-MM-DD
        formatted_tanggal_surat = request.form.get("tanggal_surat")
        
        tanggal_opini = request.form.get("tanggal_opini")
        formatted_tanggal_opini = ''
        if tanggal_opini:
            formatted_tanggal_opini = tanggal_opini # Sudah dalamYYYY-MM-DD dari input type="date"

    except ValueError:
        # Ini seharusnya tidak terjadi jika input type="date" digunakan dengan benar
        return jsonify({"success": False, "message": "Format tanggal surat atau opini tidak valid"}), 400
    
    try:
        # Data Numerik - Asumsi dari input type="number" di HTML, jadi tidak perlu .replace('.', '')
        # Jika frontend melakukan pemformatan angka dengan titik/koma, Anda perlu menambahkan kembali .replace('.', '')
        tahun_laporan = int(request.form.get("tahun_laporan")) # Sesuai API doc
        modal_dasar = int(request.form.get("modal_dasar"))  
        modal_disetor = int(request.form.get("modal_disetor"))
        total_aset = int(request.form.get("total_aset"))
        aset_lancar = int(request.form.get("aset_lancar"))  
        kas_dan_setara_kas = int(request.form.get("kas_dan_setara_kas"))  
        aset_tetap = int(request.form.get("aset_tetap"))  
        total_hutang = int(request.form.get("total_hutang")) # Sesuai API doc
        hutang_jangka_pendek = int(request.form.get("hutang_jangka_pendek"))  
        hutang_jangka_panjang = int(request.form.get("hutang_jangka_panjang"))  
        total_ekuitas = int(request.form.get("total_ekuitas"))  
        total_pendapatan = int(request.form.get("total_pendapatan"))
        pendapatan_fee = int(request.form.get("pendapatan_fee")) # Sesuai API doc
        total_beban = int(request.form.get("total_beban")) # Sesuai API doc
        beban_operasional = int(request.form.get("beban_operasional")) # Sesuai API doc
        laba = int(request.form.get("laba"))
        rugi = int(request.form.get("rugi"))
        
    except ValueError as e:
        return jsonify({"success": False, "message": f"Format angka tidak valid: {e}. Pastikan hanya memasukkan angka."}), 400

    form_data = {
        "tahun_laporan": tahun_laporan, 
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat, # Dikirim sebagaiYYYY-MM-DD
        "jenis_audit": request.form.get("jenis_audit"),  # Sesuai API doc
        "nama_kap": request.form.get("nama_kap"),  # Sesuai API doc
        "tanggal_opini": formatted_tanggal_opini,  # Sesuai API doc
        "opini_auditor": request.form.get("opini_auditor"), # Sesuai API doc
        "modal_dasar": modal_dasar,  
        "modal_disetor": modal_disetor,
        "total_aset": total_aset,
        "aset_lancar": aset_lancar,  
        "kas_dan_setara_kas": kas_dan_setara_kas,  
        "aset_tetap": aset_tetap,  
        "total_hutang": total_hutang, 
        "hutang_jangka_pendek": hutang_jangka_pendek,  
        "hutang_jangka_panjang": hutang_jangka_panjang,  
        "total_ekuitas": total_ekuitas,  
        "total_pendapatan": total_pendapatan,
        "pendapatan_fee": pendapatan_fee,
        "total_beban": total_beban,
        "beban_operasional": beban_operasional,
        "laba": laba,
        "rugi": rugi,
    }
    file_laporan = request.files.get("file") # Sesuai API doc

    success, message, status_code = send_report_to_backend("laporan/keuangan-tahunan/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

@app.route("/form/laporan-keuangan-triwulan")
def form_laporan_keuangan_triwulan():
    """Merender formulir untuk Laporan Keuangan Triwulan."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    current_year = datetime.now().year # Mendapatkan tahun saat ini
    return render_template("user/forms/laporan_keuangan_triwulan.html", current_year=current_year)

@app.route("/submit/laporan-keuangan-triwulan", methods=["POST"])
def submit_laporan_keuangan_triwulan():
    """
    Menangani pengiriman Laporan Keuangan Triwulan.
    Disambungkan ke endpoint laporan/keuangan-triwulanan/submit.
    """
    try:
        # Format tanggal_surat ke DD/MM/YYYY
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400
    
    # Memastikan semua nilai numerik dikonversi ke integer.
    # Asumsi nilai dari input type="number" tidak memiliki tanda titik (ribuan)
    try:
        modal_dasar = int(request.form.get("modal_dasar")) # From API doc
        modal_disetor = int(request.form.get("modal_disetor"))
        total_aset = int(request.form.get("total_aset"))
        aset_lancar = int(request.form.get("aset_lancar")) # From API doc
        kas_dan_setara_kas = int(request.form.get("kas_dan_setara_kas")) # From API doc
        aset_tetap = int(request.form.get("aset_tetap")) # From API doc
        total_hutang = int(request.form.get("total_hutang")) # From API doc
        hutang_jangka_pendek = int(request.form.get("hutang_jangka_pendek")) # From API doc
        hutang_jangka_panjang = int(request.form.get("hutang_jangka_panjang")) # From API doc
        total_ekuitas = int(request.form.get("total_ekuitas")) # From API doc
        total_pendapatan = int(request.form.get("total_pendapatan")) # From API doc
        pendapatan_fee = int(request.form.get("pendapatan_fee")) # From API doc
        total_beban = int(request.form.get("total_beban")) # From API doc
        beban_operasional = int(request.form.get("beban_operasional")) # From API doc
        laba = int(request.form.get("laba"))
        rugi = int(request.form.get("rugi"))
    except ValueError as e:
        return jsonify({"success": False, "message": f"Format angka tidak valid: {e}. Pastikan hanya memasukkan angka."}), 400

    form_data = {
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"), # Periode Laporan (Triwulan)
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "modal_dasar": modal_dasar,
        "modal_disetor": modal_disetor,
        "total_aset": total_aset,
        "aset_lancar": aset_lancar,
        "kas_dan_setara_kas": kas_dan_setara_kas,
        "aset_tetap": aset_tetap,
        "total_hutang": total_hutang,
        "hutang_jangka_pendek": hutang_jangka_pendek,
        "hutang_jangka_panjang": hutang_jangka_panjang,
        "total_ekuitas": total_ekuitas,
        "total_pendapatan": total_pendapatan,
        "pendapatan_fee": pendapatan_fee,
        "total_beban": total_beban,
        "beban_operasional": beban_operasional,
        "laba": laba,
        "rugi": rugi,
        # "keterangan": request.form.get("keterangan"), # Not in API doc for Keuangan Triwulanan
    }
    file_laporan = request.files.get("file") # Sesuai tabel

    success, message, status_code = send_report_to_backend("laporan/keuangan-triwulanan/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Gangguan IT ---
@app.route("/form/laporan-gangguanit")
def form_laporan_gangguanit():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_gangguanit.html")

@app.route("/submit/laporan-gangguanit", methods=["POST"])
def submit_laporan_gangguanit():
    try:
        # Format tanggal_surat ke DD/MM/YYYY
        tanggal_surat_raw = request.form.get("tanggal_surat")
        formatted_tanggal_surat = datetime.strptime(tanggal_surat_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
        
        # Format waktu_kejadian ke DD/MM/YYYY HH:MM
        waktu_kejadian_raw = request.form.get("waktu_kejadian")
        formatted_waktu_kejadian = None
        if waktu_kejadian_raw:
            try:
                dt_object = datetime.strptime(waktu_kejadian_raw, '%Y-%m-%dT%H:%M')
                formatted_waktu_kejadian = dt_object.strftime('%d/%m/%Y %H:%M')
            except ValueError:
                return jsonify({"success": False, "message": "Format Waktu Kejadian tidak valid. Harap gunakan '%Y-%m-%dT%H:%M'."}), 400

        # Format tanggal_penyelesaian ke DD/MM/YYYY (API hanya mengharapkan tanggal)
        tanggal_penyelesaian_raw = request.form.get("tanggal_penyelesaian")
        formatted_tanggal_penyelesaian = None
        if tanggal_penyelesaian_raw:
            try:
                # Karena HTML sekarang mengirimkan type="date", formatnya '%Y-%m-%d'
                formatted_tanggal_penyelesaian = datetime.strptime(tanggal_penyelesaian_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
            except ValueError:
                return jsonify({"success": False, "message": "Format Tanggal Penyelesaian tidak valid. Harap gunakan '%Y-%m-%d'."}), 400

    except ValueError as e:
        return jsonify({"success": False, "message": f"Format tanggal/waktu tidak valid: {e}"}), 400

    form_data = {
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "waktu_kejadian": formatted_waktu_kejadian,
        "jenis_gangguan": request.form.get("jenis_gangguan"),
        "ringkasan": request.form.get("ringkasan"), # Ditambahkan sesuai API
        "potensi_kerugian": int(request.form.get("potensi_kerugian")), # Ditambahkan sesuai API
        "upaya_perbaikan": request.form.get("upaya_perbaikan"),
        "tanggal_penyelesaian": formatted_tanggal_penyelesaian,
    }
    
    # Hapus field yang mungkin kosong jika tidak wajib di API
    # tanggal_penyelesaian bersifat opsional jika status_penyelesaian bukan "Terselesaikan"
    if not form_data["tanggal_penyelesaian"]:
        form_data.pop("tanggal_penyelesaian")

    file_laporan = request.files.get("file") # Nama field di form sekarang adalah 'file' sesuai API

    success, message, status_code = send_report_to_backend("laporan/gangguan-it/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Keamanan Siber --- (Not in detailed spec, inferring based on existing app.py code)
@app.route("/form/laporan-keamanan-siber")
def form_laporan_keamanan_siber():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_keamanan_siber.html")

@app.route("/submit/laporan-keamanan-siber", methods=["POST"])
def submit_laporan_keamanan_siber():
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun_laporan")),
        to_snake_case("Periode Laporan"): request.form.get("periode_laporan"),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Jenis Kejadian"): request.form.get("jenis_kejadian"),
        to_snake_case("Upaya Penanganan"): request.form.get("upaya_penanganan"),
        to_snake_case("Status Penyelesaian"): request.form.get("status_penyelesaian")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/keamanan-siber/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Kepatuhan IT --- (Not in detailed spec, inferring based on existing app.py code)
@app.route("/form/laporan-kepatuhan-it")
def form_laporan_kepatuhan_it():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_kepatuhan_it.html")

@app.route("/submit/laporan-kepatuhan-it", methods=["POST"])
def submit_laporan_kepatuhan_it():
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun_laporan")),
        to_snake_case("Periode Laporan"): request.form.get("periode_laporan"),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Jenis Audit"): request.form.get("jenis_audit"),
        to_snake_case("Hasil Audit"): request.form.get("hasil_audit"),
        to_snake_case("Tindak Lanjut"): request.form.get("tindak_lanjut")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/kepatuhan-it/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Manajemen Risiko IT --- (Not in detailed spec, inferring based on existing app.py code)
@app.route("/form/laporan-manajemen-risiko-it")
def form_laporan_manajemen_risiko_it():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_manajemen_risiko_it.html")

@app.route("/submit/laporan-manajemen-risiko-it", methods=["POST"])
def submit_laporan_manajemen_risiko_it():
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun_laporan")),
        to_snake_case("Periode Laporan"): request.form.get("periode_laporan"),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Jenis Risiko"): request.form.get("jenis_risiko"),
        to_snake_case("Dampak Risiko"): request.form.get("dampak_risiko"),
        to_snake_case("Langkah Mitigasi"): request.form.get("langkah_mitigasi")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/manajemen-risiko-it/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Insiden Siber --- (Not in detailed spec, inferring based on existing app.py code)
@app.route("/form/laporan-insiden-siber")
def form_laporan_insiden_siber():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_insiden_siber.html")

@app.route("/submit/laporan-insiden-siber", methods=["POST"])
def submit_laporan_insiden_siber():
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun_laporan")),
        to_snake_case("Periode Laporan"): request.form.get("periode_laporan"),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Jenis Insiden"): request.form.get("jenis_insiden"),
        to_snake_case("Dampak Insiden"): request.form.get("dampak_insiden"),
        to_snake_case("Status Penyelesaian"): request.form.get("status_penyelesaian"),
        to_snake_case("Upaya Penanganan"): request.form.get("upaya_penanganan")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/insiden-siber/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Risiko IT (Kuartal) --- (Not in detailed spec, inferring based on existing app.py code)
@app.route("/form/laporan-risiko-it")
def form_laporan_risiko_it():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_risiko_it.html")

@app.route("/submit/laporan-risiko-it", methods=["POST"])
def submit_laporan_risiko_it():
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun_laporan")),
        to_snake_case("Periode Laporan"): request.form.get("periode_laporan"),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Jumlah Risiko Tinggi"): int(request.form.get("jumlah_risiko_tinggi")),
        to_snake_case("Jumlah Risiko Menengah"): int(request.form.get("jumlah_risiko_menengah")),
        to_snake_case("Jumlah Risiko Rendah"): int(request.form.get("jumlah_risiko_rendah")),
        to_snake_case("Keterangan Risiko"): request.form.get("keterangan_risiko"),
        to_snake_case("Rencana Mitigasi"): request.form.get("rencana_mitigasi")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/risiko-it/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Tata Kelola IT (Semester) --- (Not in detailed spec, inferring based on existing app.py code)
@app.route("/form/laporan-tata-kelola-it")
def form_laporan_tata_kelola_it():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_tata_kelola_it.html")

@app.route("/submit/laporan-tata-kelola-it", methods=["POST"])
def submit_laporan_tata_kelola_it():
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun_laporan")),
        to_snake_case("Periode Laporan"): request.form.get("periode_laporan"),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Aspek Tata Kelola"): request.form.get("aspek_tata_kelola"),
        to_snake_case("Hasil Evaluasi"): request.form.get("hasil_evaluasi"),
        to_snake_case("Rekomendasi Perbaikan"): request.form.get("rekomendasi_perbaikan")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/tata-kelola-it/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Rencana Strategis IT (Tahunan) --- (Not in detailed spec, inferring based on existing app.py code)
@app.route("/form/laporan-rencana-strategis-it")
def form_laporan_rencana_strategis_it():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_rencana_strategis_it.html")

@app.route("/submit/laporan-rencana-strategis-it", methods=["POST"])
def submit_laporan_rencana_strategis_it():
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun_laporan")),
        to_snake_case("Periode Laporan"): request.form.get("periode_laporan"),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Strategi Utama"): request.form.get("strategi_utama"),
        to_snake_case("Target Pencapaian"): request.form.get("target_pencapaian"),
        to_snake_case("Realisasi Saat Ini"): request.form.get("realisasi_saat_ini")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/rencana-strategis-it/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Pengelolaan Data Pribadi (Tahunan) --- (Not in detailed spec, inferring based on existing app.py code)
@app.route("/form/laporan-pengelolaan-data-pribadi")
def form_laporan_pengelolaan_data_pribadi():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_pengelolaan_data_pribadi.html")

@app.route("/submit/laporan-pengelolaan-data-pribadi", methods=["POST"])
def submit_laporan_pengelolaan_data_pribadi():
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun_laporan")),
        to_snake_case("Periode Laporan"): request.form.get("periode_laporan"),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Jenis Data"): request.form.get("jenis_data"),
        to_snake_case("Tujuan Penggunaan"): request.form.get("tujuan_penggunaan"),
        to_snake_case("Langkah Keamanan"): request.form.get("langkah_keamanan")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/pengelolaan-data-pribadi/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Implementasi Kebijakan IT (Tahunan) --- (Not in detailed spec, inferring based on existing app.py code)
@app.route("/form/laporan-implementasi-kebijakan-it")
def form_laporan_implementasi_kebijakan_it():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_implementasi_kebijakan_it.html")

@app.route("/submit/laporan-implementasi-kebijakan-it", methods=["POST"])
def submit_laporan_implementasi_kebijakan_it():
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun_laporan")),
        to_snake_case("Periode Laporan"): request.form.get("periode_laporan"),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Nama Kebijakan"): request.form.get("nama_kebijakan"),
        to_snake_case("Status Implementasi"): request.form.get("status_implementasi"),
        to_snake_case("Kendala Implementasi"): request.form.get("kendala_implementasi"),
        to_snake_case("Tindak Lanjut Kendala"): request.form.get("tindak_lanjut_kendala")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/implementasi-kebijakan-it/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Ketersediaan Layanan IT (Tahunan) --- (Not in detailed spec, inferring based on existing app.py code)
@app.route("/form/laporan-ketersediaan-layanan-it")
def form_laporan_ketersediaan_layanan_it():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_ketersediaan_layanan_it.html")

@app.route("/submit/laporan-ketersediaan-layanan-it", methods=["POST"])
def submit_laporan_ketersediaan_layanan_it():
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun_laporan")),
        to_snake_case("Periode Laporan"): request.form.get("periode_laporan"),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Nama Layanan"): request.form.get("nama_layanan"),
        to_snake_case("Persentase Ketersediaan"): float(request.form.get("persentase_ketersediaan")),
        to_snake_case("Penyebab Gangguan"): request.form.get("penyebab_gangguan"),
        to_snake_case("Dampak Gangguan"): request.form.get("dampak_gangguan"),
        to_snake_case("Upaya Pemulihan"): request.form.get("upaya_pemulihan")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/ketersediaan-layanan-it/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Keamanan Informasi (Tahunan) --- (Not in detailed spec, inferring based on existing app.py code)
@app.route("/form/laporan-keamanan-informasi")
def form_laporan_keamanan_informasi():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_keamanan_informasi.html")

@app.route("/submit/laporan-keamanan-informasi", methods=["POST"])
def submit_laporan_keamanan_informasi():
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun_laporan")),
        to_snake_case("Periode Laporan"): request.form.get("periode_laporan"),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Aspek Keamanan"): request.form.get("aspek_keamanan"),
        to_snake_case("Hasil Evaluasi"): request.form.get("hasil_evaluasi"),
        to_snake_case("Rekomendasi Perbaikan"): request.form.get("rekomendasi_perbaikan")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/keamanan-informasi/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code


# --- Rute placeholder untuk formulir tanpa endpoint API pengiriman eksplisit ---
# Rute ini akan merender formulir, tetapi pengirimannya akan disimulasikan karena
# dokumentasi API tidak menyediakan endpoint khusus untuk mereka.

@app.route("/form/laporan-apuppt")
def form_laporan_apuppt():
    """Merender formulir untuk Laporan APU PPT."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_apuppt.html")

@app.route("/submit/laporan-apuppt", methods=["POST"])
def submit_laporan_apuppt():
    """
    Menangani pengiriman Laporan APU PPT.
    """
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        "tahun_laporan": int(request.form.get("tahun_laporan")), # Sesuai HTML dan tabel
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "nama_petugas": request.form.get("nama_petugas"),
        "sk_penunjukkan": request.form.get("sk_penunjukan"), # Sesuai tabel
        "user_id_goaml": request.form.get("user_id_goaml"),
        "user_id_sipesat": request.form.get("user_id_sipesat"),
        "user_id_pep": request.form.get("user_id_pep"),
        "user_id_sipendar": request.form.get("user_id_sipendar"),
        "jumlah_ltkt": int(request.form.get("jumlah_ltkt")),
        "jumlah_ltkm": int(request.form.get("jumlah_ltkm")),
        "jumlah_ltkl": int(request.form.get("jumlah_ltkl")),
        # API Doc fields (bools)
        "lapor_sipesat_tw1": request.form.get("lapor_sipesat_tw_1") == 'True',  
        "lapor_sipesat_tw2": request.form.get("lapor_sipesat_tw_2") == 'True',  
        "lapor_sipesat_tw3": request.form.get("lapor_sipesat_tw_3") == 'True',  
        "lapor_sipesat_tw4": request.form.get("lapor_sipesat_tw_4") == 'True',  
        
        # Mengambil nilai lapor_pemblokiran_dttot dan lapor_pemblokiran_dppspm dari hidden input
        "jumlah_lapor_pemblokiran_dttot": int(request.form.get("jumlah_lapor_pemblokiran_dttot")),
        "expected_lapor_pemblokiran_dttot": int(request.form.get("expected_lapor_pemblokiran_dttot")),
        "keterangan_lapor_pemblokiran_dttot": request.form.get("keterangan_lapor_pemblokiran_dttot"),
        "jumlah_lapor_pemblokiran_dppspm": int(request.form.get("jumlah_lapor_pemblokiran_dppspm")),
        "expected_lapor_pemblokiran_dppspm": int(request.form.get("expected_lapor_pemblokiran_dppspm")),
        "keterangan_lapor_pemblokiran_dppspm": request.form.get("keterangan_lapor_pemblokiran_dppspm"),

        "tanggung_jawab_direksi": request.form.get("tanggung_jawab_direksi"),
        "kebijakan_prosedur": request.form.get("kebijakan_prosedur"),
        "metode_pmpj": request.form.get("metode_pmpj"),
        "manajemen_risiko": request.form.get("manajemen_risiko"),
        "manajemen_sdm": request.form.get("manajemen_sdm"),
        "sistem_pengendalian": request.form.get("sistem_pengendalian"),
        "nama_penginput": request.form.get("nama_penginput"),
        "email_penginput": request.form.get("email_penginput"),
        "email_perusahaan": request.form.get("email_perusahaan"),
        "nomor_hp": request.form.get("nomor_hp"),
    }
    file_laporan = request.files.get("file") # Sesuai HTML

    success, message, status_code = send_report_to_backend("laporan/apuppt/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code


@app.route("/form/laporan-auditsi")
def form_laporan_auditsi():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_auditsi.html")

@app.route("/submit/laporan-auditsi", methods=["POST"])
def submit_laporan_auditsi():
    """
    Menangani pengiriman Laporan Audit Sistem Informasi.
    """
    try:
        # Tanggal harus dalam formatYYYY-MM-DD untuk API
        # HTML input type="date" sudah mengirimkan dalam formatYYYY-MM-DD
        formatted_tanggal_surat = request.form.get("tanggal_surat")
        formatted_tanggal_selesai_audit = request.form.get("tanggal_selesai_audit")
    except ValueError:
        # Ini seharusnya tidak terjadi jika input type="date" digunakan dengan benar
        return jsonify({"success": False, "message": "Format tanggal tidak valid. Harap gunakanYYYY-MM-DD."}), 400

    form_data = {
        "tahun_laporan": int(request.form.get("tahun_laporan")), # Sesuai API doc
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat, # Dikirim sebagaiYYYY-MM-DD
        "tanggal_selesai_audit": formatted_tanggal_selesai_audit, # Dikirim sebagaiYYYY-MM-DD
        "nama_auditor": request.form.get("nama_auditor"),
        "confidentiality": int(request.form.get("confidentiality")),
        "keterangan_confidentiality": request.form.get("keterangan_confidentiality"),
        "integrity": int(request.form.get("integrity")),
        "keterangan_integrity": request.form.get("keterangan_integrity"),
        "availability": int(request.form.get("availability")),
        "keterangan_availability": request.form.get("keterangan_availability"),
        "authenticity": int(request.form.get("authenticity")),
        "keterangan_authenticity": request.form.get("keterangan_authenticity"),
        "non_repudiation": int(request.form.get("non_repudiation")),
        "keterangan_non_repudiation": request.form.get("keterangan_non_repudiation"),
        "jumlah_temuan": int(request.form.get("jumlah_temuan")),
        "jumlah_temuan_diselesaikan": int(request.form.get("jumlah_temuan_diselesaikan")),
        "keterangan_temuan_diselesaikan": request.form.get("keterangan_temuan_diselesaikan"),
        "jumlah_temuan_belum_diselesaikan": int(request.form.get("jumlah_temuan_belum_diselesaikan")),
        "keterangan_temuan_belum_diselesaikan": request.form.get("keterangan_temuan_belum_diselesaikan"),
        "kesimpulan_auditor": request.form.get("kesimpulan_auditor"), # Sesuai API doc
    }
    file_laporan = request.files.get("file") # Nama field di form sekarang adalah 'file' sesuai API

    success, message, status_code = send_report_to_backend("laporan/audit-sistem-informasi/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code


@app.route("/form/laporan-dana-bukan-bank")
def form_laporan_dana_bukan_bank():
    """Merender formulir untuk Laporan Transaksi Dana Bukan Bank (LTDBB)."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    # Mendapatkan tahun saat ini untuk dropdown tahun laporan
    current_year = datetime.now().year
    return render_template("user/forms/laporan_dana_bukan_bank.html", current_year=current_year)

@app.route("/submit/laporan-dana-bukan-bank", methods=["POST"])
def submit_laporan_dana_bukan_bank():
    """
    Menangani pengiriman Laporan Transaksi Dana Bukan Bank (LTDBB).
    """
    try:
        # Menghapus parsing tanggal_surat karena tidak lagi dikirim ke API
        # tanggal_surat_raw = request.form.get("tanggal_surat")
        # formatted_tanggal_surat = datetime.strptime(tanggal_surat_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
        pass # Placeholder for removed date parsing
    except ValueError:
        # Error ini tidak akan terjadi lagi jika tanggal_surat dihapus dari form_data
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid. Gunakan '%Y-%m-%d'."}), 400

    form_data = {
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        # Menghapus nomor_surat dan tanggal_surat dari form_data
        # "nomor_surat": request.form.get("nomor_surat"),
        # "tanggal_surat": formatted_tanggal_surat,
        "number_outgoing_transactions": int(request.form.get("number_outgoing_transactions")),
        "amount_outgoing_transactions": int(request.form.get("amount_outgoing_transactions")),
        "number_incoming_transactions": int(request.form.get("number_incoming_transactions")),
        "amount_incoming_transactions": int(request.form.get("amount_incoming_transactions")),
        "number_domestic_transactions": int(request.form.get("number_domestic_transactions")),
        "amount_domestic_transactions": int(request.form.get("amount_domestic_transactions")),
        "keterangan": request.form.get("keterangan"),
    }
    
    file_laporan = request.files.get("file")

    success, message, status_code = send_report_to_backend("laporan/ltdbb/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

# --- Rute KPSP Baru (menggunakan perhitungan frontend) ---
@app.route("/form/laporan-kpsp")
def form_laporan_kpsp():
    """
    Menampilkan form untuk Laporan Perhitungan KPSP.
    Memerlukan pengguna yang sudah login dengan peran 'user'.
    Melewatkan data 'banks' ke template untuk mengisi dropdown PJP.
    """
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    current_year = datetime.now().year # Mendapatkan tahun saat ini
    # Melewatkan data banks ke template
    return render_template("user/forms/main.html", banks=banks, current_year=current_year)

@app.route("/submit/laporan-kpsp", methods=["POST"])
def submit_laporan_kpsp():
    """
    Menerima data form KPSP dari frontend (termasuk hasil perhitungan dari JS),
    dan mengirim laporan ke backend.
    """
    if "username" not in session or session.get("role") != "user":
        return jsonify({"success": False, "message": "Anda tidak memiliki otorisasi untuk mengakses fungsi ini."}), 401

    try:
        # Tanggal surat dari frontend sudah dalam format YYYY-MM-DD
        tanggal_surat_raw = request.form.get("tanggal_surat")
        # Konversi ke DD/MM/YYYY untuk API jika diperlukan, atau biarkan YYYY-MM-DD jika API mendukung
        formatted_tanggal_surat = datetime.strptime(tanggal_surat_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    # Ambil data dari form
    form_data_raw = request.form.to_dict()

    # Bangun payload sesuai definisi dengan snake_case
    payload = {
        "tahun_laporan": int(form_data_raw.get("klp_periode").split('-')[0]), # Ambil tahun dari klp_periode (YYYY-MM-DD)
        "periode_laporan": form_data_raw.get("klp_periode"), # Menggunakan tanggal penuh sebagai periode laporan
        "nomor_surat": "AUTO-GENERATED", # Asumsi nomor surat dibuat di backend
        "tanggal_surat": formatted_tanggal_surat, # Dikirim sebagai DD/MM/YYYY
        "nama_pjp": form_data_raw.get("klp_namaPelapor"), # Nama PJP dari dropdown
        "kategori_izin": form_data_raw.get("klp_kategoriIzin"),
        "klasifikasi_pjp_pip": form_data_raw.get("klp_klasifikasiPJPPIP"),
        "aktivitas_pjp_pip": form_data_raw.get("klp_aktivitas").split(','), # Mengubah string koma-separated menjadi list
        
        # Pemenuhan Initial Capital
        "jumlah_modal_disetor": int(float(form_data_raw.get("1_jumlahModalDisetor"))),
        "kewajiban_initial_capital": int(float(form_data_raw.get("1_kewajibanInitCapital"))),
        "status_pemenuhan_initial_capital": form_data_raw.get("1_statusPemenuhan_initialCapital"),
        "total_kebutuhan_tambahan_initial_capital": int(float(form_data_raw.get("1_tambahanInitCapital"))),
        "flag_gl_pip_asing": form_data_raw.get("flagGL_PIPasing") == 'true', # Konversi string 'true'/'false' ke boolean

        # Perhitungan Ongoing Capital - TTMR
        "jumlah_bulan_trx": int(form_data_raw.get("2_jumlahBulanTrx")),
        "total_trx_atm_debet": int(float(form_data_raw.get("2_totalTrx_ATMDebet"))),
        "total_trx_atm_debet_rata": int(float(form_data_raw.get("2_totalTrx_ATMDebet_rata"))),
        "total_trx_kk": int(float(form_data_raw.get("2_totalTrx_KK"))),
        "total_trx_kk_rata": int(float(form_data_raw.get("2_totalTrx_KK_rata"))),
        "trx_dompel": int(float(form_data_raw.get("2_trxDompel"))),
        "trx_dompel_rata": int(float(form_data_raw.get("2_trxDompel_rata"))),
        "trx_trf_dana_ln_inc": int(float(form_data_raw.get("2_trxTrfDanaLN_inc"))),
        "trx_trf_dana_ln_inc_rata": int(float(form_data_raw.get("2_trxTrfDanaLN_inc_rata"))),
        "trx_trf_dana_ln_out": int(float(form_data_raw.get("2_trxTrfDanaLN_out"))),
        "trx_trf_dana_ln_out_rata": int(float(form_data_raw.get("2_trxTrfDanaLN_out_rata"))),
        "trx_trf_dana_dom": int(float(form_data_raw.get("2_trxTrfDana_dom"))),
        "trx_trf_dana_dom_rata": int(float(form_data_raw.get("2_trxTrfDana_dom_rata"))),
        "trx_ue": int(float(form_data_raw.get("2_trxUE"))),
        "trx_ue_rata": int(float(form_data_raw.get("2_trxUE_rata"))),
        "trx_pias_fasil": int(float(form_data_raw.get("2_trxPIAS_fasil"))),
        "trx_pias_fasil_rata": int(float(form_data_raw.get("2_trxPIAS_fasil_rata"))),
        "trx_pias_merch_agg": int(float(form_data_raw.get("2_trxPIAS_merchAgg"))),
        "trx_pias_merch_agg_rata": int(float(form_data_raw.get("2_trxPIAS_merchAgg_rata"))),
        "trx_lainnya": int(float(form_data_raw.get("2_trxLainnya"))),
        "trx_lainnya_rata": int(float(form_data_raw.get("2_trxLainnya_rata"))),
        "total_nilai_trx": int(float(form_data_raw.get("2_totalNilaiTrx"))),
        "total_nilai_trx_rata": int(float(form_data_raw.get("2_totalNilaiTrx_rata"))),
        "beban_trx": int(float(form_data_raw.get("2_bebanTrx"))),
        "dana_float": int(float(form_data_raw.get("2_danaFloat"))),
        "dana_float_rata": int(float(form_data_raw.get("2_danaFloat_rata"))),
        "perc_beban_trx_dana_float": float(form_data_raw.get("2_percBebanTrxDanaFloat")),
        "beban_trx_dana_float": int(float(form_data_raw.get("2_bebanTrxDanaFloat"))),
        "total_beban": int(float(form_data_raw.get("2_totalBeban"))),
        "konstanta_ttmr": float(form_data_raw.get("2_konstantaTTMR")),
        "ttmr": int(float(form_data_raw.get("2_TTMR"))),

        # Komponen Perhitungan Ongoing Capital
        "modal_saham": int(float(form_data_raw.get("3_modalSaham"))),
        "uang_muka_setoran_modal": int(float(form_data_raw.get("3_uangMukaSetoranModal"))),
        "agio_disagio_saham": int(float(form_data_raw.get("3_agioDisagioSaham"))),
        "saldo_lr_berjalan": int(float(form_data_raw.get("3_saldoLRberjalan"))),
        "saldo_penghasilan_kompr": int(float(form_data_raw.get("3_saldoPenghasilanKompr"))),
        "modal_inti_utama": int(float(form_data_raw.get("3_modalIntiUtama"))),
        "aset_pajak_tangguhan": int(float(form_data_raw.get("3_asetPajakTangguhan"))),
        "goodwill": int(float(form_data_raw.get("3_goodWill"))),
        "aset_tidak_berwujud": int(float(form_data_raw.get("3_asetTidakBerwujud"))),
        "seluruh_penyertaan": int(float(form_data_raw.get("3_seluruhPenyertaan"))),
        "pembelian_kembali_inst_modal": int(float(form_data_raw.get("3_pembelianKembaliInstModal"))),
        "penempatan_dana_inst_utang": int(float(form_data_raw.get("3_penempatanDanaInstUtang"))),
        "faktor_pengurang_modal_inti": int(float(form_data_raw.get("3_faktorPengurangModalInti"))),
        "modal_inti_utama_setelah_fpr": int(float(form_data_raw.get("3_modalIntiUtama_setelahFPR"))),
        "instrumen_utang": int(float(form_data_raw.get("3_instrumenUtang"))),
        "instrumen_hybrid": int(float(form_data_raw.get("3_instrumenHybrid"))),
        "saham_preferen_non_kumulatif": int(float(form_data_raw.get("3_sahamPreferenNonKumulatif"))),
        "premium_diskonto": int(float(form_data_raw.get("3_premiumDiskonto"))),
        "modal_inti_tambahan": int(float(form_data_raw.get("3_modalIntiTambahan"))),
        "instrumen_modal_inti_tambahan": int(float(form_data_raw.get("3_instrumenModalIntiTambahan"))),
        "kepemilikan_modal_inti_tambahan": int(float(form_data_raw.get("3_kepemilikanModalIntiTambahan"))),
        "faktor_pengurang_modal_inti_tambahan": int(float(form_data_raw.get("3_faktorPengurangModalIntiTambahan"))),
        "modal_inti_tambahan_setelah_fpr": int(float(form_data_raw.get("3_modalIntiTambahan_setelahFPR"))),
        "modal_inti_tambahan_ongoing_capital": int(float(form_data_raw.get("3_modalIntiTambahan_ongoingCapital"))),
        "instrumen_utang_jangka_pjg": int(float(form_data_raw.get("3_instrumenUtangJangkaPjg"))),
        "premium_diskonto_modal_pelengkap": int(float(form_data_raw.get("3_premiumDiskontoModalPelengkap"))),
        "modal_pelengkap": int(float(form_data_raw.get("3_modalPelengkap"))),
        "instrumen_modal_pelengkap": int(float(form_data_raw.get("3_instrumenModalPelengkap"))),
        "kepemilikan_modal_pelengkap": int(float(form_data_raw.get("3_kepemilikanModalPelengkap"))),
        "faktor_pengurang_modal_pelengkap": int(float(form_data_raw.get("3_faktorPengurangModalPelengkap"))),
        "modal_pelengkap_setelah_fpr": int(float(form_data_raw.get("3_modalPelengkap_setelahFPR"))),
        "modal_pelengkap_ongoing_capital": int(float(form_data_raw.get("3_modalPelengkap_ongoingCapital"))),
        "total_ongoing_capital": int(float(form_data_raw.get("3_totalOngoingCapital"))),
        "rasio_kpsp": float(form_data_raw.get("3_rasioKPSP")),

        # Kewajiban Ongoing Capital
        "kpsp_dasar": float(form_data_raw.get("4_KPSPdasar")),
        "surcharge": float(form_data_raw.get("4_surcharge")),
        "total_kpsp": float(form_data_raw.get("4_totalKPSP")),
        "jumlah_kewajiban_ongoing_capital": int(float(form_data_raw.get("4_jumlahKewajibanOngoingCapital"))),
        "status_pemenuhan_ongoing_capital": form_data_raw.get("4_statusPemenuhanOngoingCapital"),
        "total_kebutuhan_tambahan_ongoing_capital": int(float(form_data_raw.get("4_totalKebutuhanTambahanOngoingCapital"))),
    }

    file_laporan = request.files.get("file_laporan") # Asumsi ada input file dengan name="file_laporan"

    # Menggunakan fungsi send_report_to_backend dengan json_payload
    success, message, status_code = send_report_to_backend("laporan/kpsp/submit", json_payload=payload, file_obj=file_laporan, method="POST")

    return jsonify({"success": success, "message": message}), status_code


@app.route("/form/laporan-manajemen")
def form_laporan_manajemen():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    # 1. Dapatkan tahun saat ini
    current_year = datetime.now().year
        
    # 2. Lewatkan 'current_year' ke template
    return render_template("user/forms/laporan_manajemen.html", current_year=current_year)

@app.route("/submit/laporan-manajemen", methods=["POST"])
def submit_laporan_manajemen():
    """
    Menangani pengiriman Laporan Manajemen dan Hasil Pengawasan Dewan Komisaris.
    """
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    # Untuk one-to-many relationships (Jajaran Komisaris, Jajaran Direksi),
    # Anda perlu mengadaptasi cara data ini dikirim dari frontend.
    # Jika dikirim sebagai JSON string dalam satu field form, Anda harus meng-parse-nya.
    # Jika dikirim sebagai multiple inputs dengan nama berulang, Anda perlu mengumpulkannya.
    # Untuk contoh ini, saya akan menyederhanakan dengan hanya mengirimkan jumlahnya jika data tidak terstruktur.
    # Idealnya, frontend harus mengirimkan ini sebagai array JSON.

    # Dummy lists for now, assuming frontend sends structured data or counts
    jajaran_komisaris_list = []
    jajaran_direksi_list = []

    # Example for parsing multiple inputs like:
    # <input type="text" name="nama_komisaris[]" value="Komisaris A">
    # <input type="text" name="keterangan_komisaris[]" value="Ket. A">
    # This requires more complex parsing of request.form.getlist.
    # For simplicity, if the frontend doesn't send structured JSON,
    # consider sending just counts or a single string summary.

    # If your frontend sends structured JSON for lists:
    # try:
    #     komisaris_json = request.form.get("jajaran_komisaris_json")
    #     if komisaris_json:
    #         jajaran_komisaris_list = json.loads(komisaris_json)
    # except json.JSONDecodeError:
    #     pass # Handle error

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun")),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Jumlah Komisaris"): int(request.form.get("jumlah_komisaris")), # Assuming count is sent
        # Removed duplicate "Jajaran Direksi" key, assuming it was a typo and should be "Jajaran Komisaris"
        # If both "Jajaran Komisaris" and "Jajaran Direksi" are lists, they need distinct keys.
        # For now, keeping only one for "Jajaran Direksi" as per the original structure.
        to_snake_case("Jajaran Direksi"): jajaran_direksi_list, # Placeholder for structured data
        to_snake_case("Jumlah Direksi"): int(request.form.get("jumlah_direksi")), # Assuming count is sent
        to_snake_case("Persentase kepemilikan domestik (%)"): int(request.form.get("persentase_kepemilikan_domestik")),
        to_snake_case("Persentase kepemilikan asing (%)"): int(request.form.get("persentase_kepemilikan_asing")),
        to_snake_case("Ringkasan Laporan Manajemen"): request.form.get("ringkasan_laporan_manajemen"),
        to_snake_case("Keterangan"): request.form.get("keterangan"),
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/manajemen-dan-pengawasan/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code


@app.route("/form/laporan-p2p")
def form_laporan_p2p():
    """Merender formulir untuk Laporan Kerjasama P2P."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    # Mendapatkan tahun saat ini untuk dropdown tahun laporan
    current_year = datetime.now().year
    return render_template("user/forms/laporan_p2p.html", current_year=current_year)

@app.route("/submit/laporan-p2p", methods=["POST"])
def submit_laporan_p2p():
    """
    Menangani pengiriman Laporan Kerjasama P2P.
    Ini adalah proses 2 tahap:
    1. Kirim Header Laporan (multipart/form-data dengan file)
    2. Jika Header berhasil, kirim Detail Perusahaan (application/json)
    """
    if "username" not in session or session.get("role") != "user":
        return jsonify({"success": False, "message": "Anda tidak memiliki otorisasi untuk mengakses fungsi ini."}), 401

    try:
        # Tahap 1: Persiapan data Header Laporan
        tanggal_surat_raw = request.form.get("tanggal_surat")
        # Format tanggal_surat ke DD/MM/YYYY untuk API header
        formatted_tanggal_surat_header = datetime.strptime(tanggal_surat_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    header_form_data = {
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat_header,
        "jumlah_perusahaan_kerjasama_p2p": int(request.form.get("jumlah_perusahaan_kerjasama_p2p")),
    }
    file_laporan = request.files.get("file")

    # Panggil send_report_to_backend untuk Header Laporan
    success_header, message_header, status_code_header = send_report_to_backend(
        "laporan/kerjasama-p2p/submit",
        form_data=header_form_data,
        file_obj=file_laporan,
        method="POST"
    )

    if not success_header:
        return jsonify({"success": False, "message": f"Gagal mengirim header laporan: {message_header}"}), status_code_header

    # Tahap 2: Persiapan data Detail Perusahaan
    # Mengambil data perusahaan sebagai string JSON dari FormData
    perusahaan_json_str = request.form.get("perusahaan_data_json") 
    daftar_perusahaan_kerjasama_p2p_list = []
    if perusahaan_json_str:
        try:
            daftar_perusahaan_kerjasama_p2p_list = json.loads(perusahaan_json_str)
        except json.JSONDecodeError:
            return jsonify({"success": False, "message": "Format data perusahaan tidak valid (bukan JSON)"}), 400

    # Pastikan data perusahaan memiliki format tanggal '%Y-%m-%d' jika ada
    for perusahaan in daftar_perusahaan_kerjasama_p2p_list:
        if 'tanggal_mulai_kerjasama' in perusahaan and perusahaan['tanggal_mulai_kerjasama']:
            try:
                # Pastikan format yang dikirim dari frontend sudah '%Y-%m-%d'
                datetime.strptime(perusahaan['tanggal_mulai_kerjasama'], '%Y-%m-%d')
            except ValueError:
                return jsonify({"success": False, "message": f"Format tanggal mulai kerjasama tidak valid untuk {perusahaan.get('nama_perusahaan_kerjasama', '')}. Harap gunakan '%Y-%m-%d'."}), 400
        
        if 'tanggal_akhir_kerjasama' in perusahaan and perusahaan['tanggal_akhir_kerjasama']:
            try:
                # Pastikan format yang dikirim dari frontend sudah '%Y-%m-%d'
                datetime.strptime(perusahaan['tanggal_akhir_kerjasama'], '%Y-%m-%d')
            except ValueError:
                return jsonify({"success": False, "message": f"Format tanggal akhir kerjasama tidak valid untuk {perusahaan.get('nama_perusahaan_kerjasama', '')}. Harap gunakan '%Y-%m-%d'."}), 400

    detail_payload = {
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        "perusahaan": daftar_perusahaan_kerjasama_p2p_list,
    }

    # Panggil send_report_to_backend untuk Detail Perusahaan (menggunakan json_payload)
    success_detail, message_detail, status_code_detail = send_report_to_backend(
        "laporan/kerjasama-p2p/perusahaan/submit",
        json_payload=detail_payload,
        method="POST"
    )

    if not success_detail:
        return jsonify({"success": False, "message": f"Gagal mengirim detail perusahaan: {message_detail}"}), status_code_detail

    return jsonify({"success": True, "message": "Laporan Kerjasama P2P berhasil dikirim!"}), 201


@app.route("/form/laporan-pelaksanaan-edukasi-publik")
def form_laporan_pelaksanaan_edukasi_publik():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_pelaksanaan_edukasi_publik.html")

@app.route("/submit/laporan-pelaksanaan-edukasi-publik", methods=["POST"])
def submit_laporan_pelaksanaan_edukasi_publik():
    """
    Menangani pengiriman Laporan Pelaksanaan Edukasi Publik.
    """
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun")),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Provinsi"): request.form.get("provinsi"),
        to_snake_case("Bentuk Aktivitas"): request.form.get("bentuk_aktivitas"),
        to_snake_case("Sasaran Edukasi"): request.form.get("sasaran_edukasi"),
        to_snake_case("Jumlah Peserta"): int(request.form.get("jumlah_peserta")),
        to_snake_case("Materi Edukasi"): request.form.get("materi_edukasi"),
        to_snake_case("Frekuensi"): int(request.form.get("frekuensi")),
        to_snake_case("Kanal Edukasi"): request.form.get("kanal_edukasi"),
        to_snake_case("Evaluasi"): request.form.get("evaluasi"),
        to_snake_case("Kendala"): request.form.get("kendala"),
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/pelaksanaan-edukasi-publik/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

@app.route("/form/laporan-pelaksanaan-pengujian-keamanan")
def form_laporan_pelaksanaan_pengujian_keamanan():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    current_year = datetime.now().year # Get current year
    return render_template("user/forms/laporan_pelaksanaan_pengujian_keamanan.html", current_year=current_year)

@app.route("/submit/laporan-pelaksanaan-pengujian-keamanan", methods=["POST"])
def submit_laporan_pelaksanaan_pengujian_keamanan():
    """
    Menangani pengiriman Laporan Pelaksanaan Pengujian Keamanan (Penetration Test).
    """
    try:
        # Menggunakan nilai langsung dari request.form.get() karena sudah dalam formatYYYY-MM-DD
        formatted_tanggal_surat = request.form.get("tanggal_surat")
        formatted_tanggal_selesai_audit = request.form.get("tanggal_selesai_audit")
        
        # Opsional: Tambahkan validasi format jika diperlukan, meskipun input type="date"
        # cenderung sudah memastikan format yang benar.
        if not formatted_tanggal_surat or not formatted_tanggal_selesai_audit:
            raise ValueError("Tanggal surat atau tanggal selesai audit tidak boleh kosong.")
        
        # Coba konversi untuk memastikan formatnya benar sebelum dikirim
        datetime.strptime(formatted_tanggal_surat, '%Y-%m-%d')
        datetime.strptime(formatted_tanggal_selesai_audit, '%Y-%m-%d')

    except ValueError as e:
        return jsonify({"success": False, "message": f"Format tanggal tidak valid: {e}. Harap gunakan formatYYYY-MM-DD."}), 400

    form_data = {
        "tahun_laporan": int(request.form.get("tahun_laporan")), # Menggunakan "tahun_laporan" sesuai HTML
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat, # Dikirim dalam formatYYYY-MM-DD
        "tanggal_selesai_audit": formatted_tanggal_selesai_audit, # Dikirim dalam formatYYYY-MM-DD
        "nama_auditor": request.form.get("nama_auditor"), # Menambahkan nama_auditor
        "temuan_low": int(request.form.get("temuan_low") or 0), # Added or 0 to handle None
        "keterangan_temuan_low": request.form.get("keterangan_temuan_low"), # Menambahkan keterangan
        "temuan_medium": int(request.form.get("temuan_medium") or 0), # Added or 0 to handle None
        "keterangan_temuan_medium": request.form.get("keterangan_temuan_medium"), # Menambahkan keterangan
        "temuan_high": int(request.form.get("temuan_high") or 0), # Added or 0 to handle None
        "keterangan_temuan_high": request.form.get("keterangan_temuan_high"), # Menambahkan keterangan
        "temuan_critical": int(request.form.get("temuan_critical") or 0), # Added or 0 to handle None
        "keterangan_temuan_critical": request.form.get("keterangan_temuan_critical"), # Menambahkan keterangan
        "jumlah_temuan": int(request.form.get("jumlah_temuan") or 0), # Added or 0 to handle None
        "jumlah_temuan_diselesaikan": int(request.form.get("jumlah_temuan_diselesaikan") or 0), # Added or 0 to handle None
        "keterangan_temuan_diselesaikan": request.form.get("keterangan_temuan_diselesaikan"), # Menambahkan keterangan
        # Corrected field name to match HTML and added or 0 for safety
        "jumlah_temuan_belum_diselesaikan": int(request.form.get("jumlah_temuan_belum_diselesaikan") or 0), 
        "keterangan_temuan_belum_diselesaikan": request.form.get("keterangan_temuan_belum_diselesaikan"), # Menambahkan keterangan
        "kesimpulan_auditor": request.form.get("kesimpulan_auditor"),
    }
    file_laporan = request.files.get("file") # Menggunakan "file" sesuai HTML dan API

    success, message, status_code = send_report_to_backend("laporan/pelaksanaan-pengujian-keamanan/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

@app.route("/form/laporan-pppk")
def form_laporan_pppk():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_pppk.html")

@app.route("/submit/laporan-pppk", methods=["POST"])
def submit_laporan_pppk():
    """
    Menangani pengiriman Laporan Penanganan dan Penyelesaian Pengaduan Konsumen.
    """
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun")),
        to_snake_case("Periode Laporan"): request.form.get("triwulan"),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Jumlah Pengaduan Konsumen"): int(request.form.get("jumlah_pengaduan_konsumen")),
        to_snake_case("Jumlah Pengaduan Diselesaikan"): int(request.form.get("jumlah_pengaduan_diselesaikan")),
        to_snake_case("Jumlah Pengaduan Belum Diselesaikan"): int(request.form.get("jumlah_pengaduan_belum_diselesaikan")),
        to_snake_case("Jumlah Pengaduan Diteruskan ke BI"): int(request.form.get("jumlah_pengaduan_diteruskan_bi")),
        to_snake_case("Jumlah Pengaduan Diteruskan ke OJK"): int(request.form.get("jumlah_pengaduan_diteruskan_ojk")),
        to_snake_case("Jumlah Pengaduan Diteruskan ke LAPS SJK"): int(request.form.get("jumlah_pengaduan_diteruskan_laps_sjk")),
        to_snake_case("Jumlah Pengaduan Diteruskan ke Pengadilan"): int(request.form.get("jumlah_pengaduan_diteruskan_pengadilan")),
        to_snake_case("Jumlah Pengaduan Diteruskan ke Arbitrase"): int(request.form.get("jumlah_pengaduan_diteruskan_arbitrase")),
        to_snake_case("Jumlah Pengaduan Diselesaikan Cara Lainnya"): int(request.form.get("jumlah_pengaduan_diselesaikan_lainnya")),
        to_snake_case("Persentase Pengaduan per Total Transaksi Berhasil"): int(request.form.get("persentase_pengaduan_transaksi_berhasil")),
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/penanganan-pengaduan-konsumen/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code


@app.route("/form/laporan-rencana-edukasi-publik")
def form_laporan_rencana_edukasi_publik():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_rencana_edukasi_publik.html")

@app.route("/submit/laporan-rencana-edukasi-publik", methods=["POST"])
def submit_laporan_rencana_edukasi_publik():
    """
    Menangani pengiriman Laporan Rencana Edukasi Publik.
    """
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun")),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Provinsi"): request.form.get("provinsi"),
        to_snake_case("Total Aset Tahun Lalu"): int(request.form.get("total_aset_tahun_lalu").replace('.', '')),
        to_snake_case("Total Aset Tahun Ini"): int(request.form.get("total_aset_tahun_ini").replace('.', '')),
        to_snake_case("Total Aset Tahun Depan"): int(request.form.get("total_aset_tahun_depan").replace('.', '')),
        to_snake_case("Pendapatan Tahun Lalu"): int(request.form.get("pendapatan_tahun_lalu").replace('.', '')),
        to_snake_case("Pendapatan Tahun Ini"): int(request.form.get("pendapatan_tahun_ini").replace('.', '')),
        to_snake_case("Target Pendapatan Tahun Depan"): int(request.form.get("target_pendapatan_tahun_depan").replace('.', '')),
        to_snake_case("Biaya Tahun Lalu"): int(request.form.get("biaya_tahun_lalu").replace('.', '')),
        to_snake_case("Biaya Tahun Ini"): int(request.form.get("biaya_tahun_ini").replace('.', '')),
        to_snake_case("Target Biaya Tahun Depan"): int(request.form.get("target_biaya_tahun_depan").replace('.', '')),
        to_snake_case("Jumlah Konsumen Tahun Depan"): int(request.form.get("jumlah_konsumen_tahun_depan").replace('.', '')),
        to_snake_case("Faktor Operasional"): request.form.get("faktor_operasional"),
        to_snake_case("Sasaran Edukasi"): request.form.get("sasaran_edukasi"),
        to_snake_case("Target Jumlah Peserta"): int(request.form.get("target_jumlah_peserta")),
        to_snake_case("Materi Edukasi"): request.form.get("materi_edukasi"),
        to_snake_case("Kanal Edukasi"): request.form.get("kanal_edukasi"),
        to_snake_case("Media Edukasi"): request.form.get("media_edukasi"),
        to_snake_case("Jumlah Kegiatan"): int(request.form.get("jumlah_kegiatan")),
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/rencana-edukasi-publik/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

@app.route("/form/laporan-sksp-tahunan")
def form_laporan_sksp_tahunan():
    # Jalur 1: Jika pengguna belum login, arahkan ke halaman login.
    # Pernyataan 'return' ini sudah benar.
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    
    # Jalur 2: Jika pengguna sudah login.
    # Dapatkan objek datetime saat ini.
    now = datetime.now()
    
    # PASTIKAN Anda menggunakan kata kunci 'return' di sini.
    # Error 'TypeError' yang Anda alami terjadi jika 'return' dihilangkan dari baris di bawah ini.
    # Fungsi ini harus MENGEMBALIKAN hasil dari render_template.
    return render_template("user/forms/laporan_sksp_tahunan.html", now=now)

@app.route("/submit/laporan-sksp-tahunan", methods=["POST"])
def submit_laporan_sksp_tahunan():
    """
    Menangani pengiriman Laporan Standar Kompetensi Sistem Pembayaran (Tahunan).
    """
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun")),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Total Rencana Penyediaan Dana PBK SP"): int(request.form.get("total_dana_pbk_sp").replace('.', '')),
        to_snake_case("Total Rencana Penyediaan Dana Pemeliharaan PBK SP"): int(request.form.get("total_dana_pemeliharaan_pbk_sp").replace('.', '')),
        to_snake_case("Total Rencana Penyediaan Dana Sertifikasi Kompetensi SP"): int(request.form.get("total_dana_sertifikasi_sp").replace('.', '')),
        to_snake_case("Total Rencana Penyediaan Dana Pemeliharaan Sertifikasi"): int(request.form.get("total_dana_pemeliharaan_sertifikasi").replace('.', '')),
        to_snake_case("Jenis Pelaku SPPUR"): request.form.get("jenis_pelaku_sppur"),
        to_snake_case("Tahap"): request.form.get("tahap"),
        to_snake_case("Sub Bidang SKKNI"): request.form.get("sub_bidang_skkni"),
        to_snake_case("PIC"): request.form.get("pic"),
        to_snake_case("Total Pegawai PBK Lv4"): int(request.form.get("total_pegawai_pbk_lv4")),
        to_snake_case("Total Pegawai PBK Lv5"): int(request.form.get("total_pegawai_pbk_lv5")),
        to_snake_case("Total Pegawai PBK Lv6"): int(request.form.get("total_pegawai_pbk_lv6")),
        to_snake_case("Total Pegawai SK Lv Direksi"): int(request.form.get("total_pegawai_sk_direksi")),
        to_snake_case("Rencana PBK Pelaksana Tw1"): int(request.form.get("rencana_pbk_pelaksana_tw1")),
        to_snake_case("Rencana PBK Pelaksana Tw2"): int(request.form.get("rencana_pbk_pelaksana_tw2")),
        to_snake_case("Rencana PBK Pelaksana Tw3"): int(request.form.get("rencana_pbk_pelaksana_tw3")),
        to_snake_case("Rencana PBK Pelaksana Tw4"): int(request.form.get("rencana_pbk_pelaksana_tw4")),
        to_snake_case("Rencana PBK Penyelia Tw1"): int(request.form.get("rencana_pbk_penyelia_tw1")),
        to_snake_case("Rencana PBK Penyelia Tw2"): int(request.form.get("rencana_pbk_penyelia_tw2")),
        to_snake_case("Rencana PBK Penyelia Tw3"): int(request.form.get("rencana_pbk_penyelia_tw3")),
        to_snake_case("Rencana PBK Penyelia Tw4"): int(request.form.get("rencana_pbk_penyelia_tw4")),
        to_snake_case("Rencana PBK Pejabat Eksekutif Tw1"): int(request.form.get("rencana_pbk_pejabat_eksekutif_tw1")),
        to_snake_case("Rencana PBK Pejabat Eksekutif Tw2"): int(request.form.get("rencana_pbk_pejabat_eksekutif_tw2")),
        to_snake_case("Rencana PBK Pejabat Eksekutif Tw3"): int(request.form.get("rencana_pbk_pejabat_eksekutif_tw3")),
        to_snake_case("Rencana PBK Pejabat Eksekutif Tw4"): int(request.form.get("rencana_pbk_pejabat_eksekutif_tw4")),
        to_snake_case("Pemeliharaan PBK Lv4 Tw1"): int(request.form.get("pemeliharaan_pbk_lv4_tw1")),
        to_snake_case("Pemeliharaan PBK Lv4 Tw2"): int(request.form.get("pemeliharaan_pbk_lv4_tw2")),
        to_snake_case("Pemeliharaan PBK Lv4 Tw3"): int(request.form.get("pemeliharaan_pbk_lv4_tw3")),
        to_snake_case("Pemeliharaan PBK Lv4 Tw4"): int(request.form.get("pemeliharaan_pbk_lv4_tw4")),
        to_snake_case("Pemeliharaan PBK Lv5 Tw1"): int(request.form.get("pemeliharaan_pbk_lv5_tw1")),
        to_snake_case("Pemeliharaan PBK Lv5 Tw2"): int(request.form.get("pemeliharaan_pbk_lv5_tw2")),
        to_snake_case("Pemeliharaan PBK Lv5 Tw3"): int(request.form.get("pemeliharaan_pbk_lv5_tw3")),
        to_snake_case("Pemeliharaan PBK Lv5 Tw4"): int(request.form.get("pemeliharaan_pbk_lv5_tw4")),
        to_snake_case("Pemeliharaan PBK Lv6 Tw1"): int(request.form.get("pemeliharaan_pbk_lv6_tw1")),
        to_snake_case("Pemeliharaan PBK Lv6 Tw2"): int(request.form.get("pemeliharaan_pbk_lv6_tw2")),
        to_snake_case("Pemeliharaan PBK Lv6 Tw3"): int(request.form.get("pemeliharaan_pbk_lv6_tw3")),
        to_snake_case("Pemeliharaan PBK Lv6 Tw4"): int(request.form.get("pemeliharaan_pbk_lv6_tw4")),
        to_snake_case("Rencana SK Pejabat Direksi Tw1"): int(request.form.get("rencana_sk_direksi_tw1")),
        to_snake_case("Rencana SK Pejabat Direksi Tw2"): int(request.form.get("rencana_sk_direksi_tw2")),
        to_snake_case("Rencana SK Pejabat Direksi Tw3"): int(request.form.get("rencana_sk_direksi_tw3")),
        to_snake_case("Rencana SK Pejabat Direksi Tw4"): int(request.form.get("rencana_sk_direksi_tw4")),
        to_snake_case("Pemeliharaan SK Lv Direksi Tw1"): int(request.form.get("pemeliharaan_sk_direksi_tw1")),
        to_snake_case("Pemeliharaan SK Lv Direksi Tw2"): int(request.form.get("pemeliharaan_sk_direksi_tw2")),
        to_snake_case("Pemeliharaan SK Lv Direksi Tw3"): int(request.form.get("pemeliharaan_sk_direksi_tw3")),
        to_snake_case("Pemeliharaan SK Lv Direksi Tw4"): int(request.form.get("pemeliharaan_sk_direksi_tw4")),
        to_snake_case("Periode Laporan"): "Tahunan" # Explicitly set for annual report
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/standar-kompetensi-sp/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

@app.route("/form/laporan-sksp-triwulan")
def form_laporan_sksp_triwulan():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_sksp_triwulan.html")

@app.route("/submit/laporan-sksp-triwulan", methods=["POST"])
def submit_laporan_sksp_triwulan():
    """
    Menangani pengiriman Laporan Standar Kompetensi Sistem Pembayaran (Triwulan).
    """
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun")),
        to_snake_case("Periode Laporan"): request.form.get("triwulan"),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Total Rencana Penyediaan Dana PBK SP"): int(request.form.get("total_dana_pbk_sp").replace('.', '')),
        to_snake_case("Total Rencana Penyediaan Dana Pemeliharaan PBK SP"): int(request.form.get("total_dana_pemeliharaan_pbk_sp").replace('.', '')),
        to_snake_case("Total Rencana Penyediaan Dana Sertifikasi Kompetensi SP"): int(request.form.get("total_dana_sertifikasi_sp").replace('.', '')),
        to_snake_case("Total Rencana Penyediaan Dana Pemeliharaan Sertifikasi"): int(request.form.get("total_dana_pemeliharaan_sertifikasi").replace('.', '')),
        to_snake_case("Jenis Pelaku SPPUR"): request.form.get("jenis_pelaku_sppur"),
        to_snake_case("Tahap"): request.form.get("tahap"),
        to_snake_case("Sub Bidang SKKNI"): request.form.get("sub_bidang_skkni"),
        to_snake_case("PIC"): request.form.get("pic"),
        to_snake_case("Total Pegawai PBK Lv4"): int(request.form.get("total_pegawai_pbk_lv4")),
        to_snake_case("Total Pegawai PBK Lv5"): int(request.form.get("total_pegawai_pbk_lv5")),
        to_snake_case("Total Pegawai PBK Lv6"): int(request.form.get("total_pegawai_pbk_lv6")),
        to_snake_case("Total Pegawai SK Lv Direksi"): int(request.form.get("total_pegawai_sk_direksi")),
        to_snake_case("Rencana PBK Pelaksana Tw1"): int(request.form.get("rencana_pbk_pelaksana_tw1")),
        to_snake_case("Rencana PBK Pelaksana Tw2"): int(request.form.get("rencana_pbk_pelaksana_tw2")),
        to_snake_case("Rencana PBK Pelaksana Tw3"): int(request.form.get("rencana_pbk_pelaksana_tw3")),
        to_snake_case("Rencana PBK Pelaksana Tw4"): int(request.form.get("rencana_pbk_pelaksana_tw4")),
        to_snake_case("Rencana PBK Penyelia Tw1"): int(request.form.get("rencana_pbk_penyelia_tw1")),
        to_snake_case("Rencana PBK Penyelia Tw2"): int(request.form.get("rencana_pbk_penyelia_tw2")),
        to_snake_case("Rencana PBK Penyelia Tw3"): int(request.form.get("rencana_pbk_penyelia_tw3")),
        to_snake_case("Rencana PBK Penyelia Tw4"): int(request.form.get("rencana_pbk_penyelia_tw4")),
        to_snake_case("Rencana PBK Pejabat Eksekutif Tw1"): int(request.form.get("rencana_pbk_pejabat_eksekutif_tw1")),
        to_snake_case("Rencana PBK Pejabat Eksekutif Tw2"): int(request.form.get("rencana_pbk_pejabat_eksekutif_tw2")),
        to_snake_case("Rencana PBK Pejabat Eksekutif Tw3"): int(request.form.get("rencana_pbk_pejabat_eksekutif_tw3")),
        to_snake_case("Rencana PBK Pejabat Eksekutif Tw4"): int(request.form.get("rencana_pbk_pejabat_eksekutif_tw4")),
        to_snake_case("Pemeliharaan PBK Lv4 Tw1"): int(request.form.get("pemeliharaan_pbk_lv4_tw1")),
        to_snake_case("Pemeliharaan PBK Lv4 Tw2"): int(request.form.get("pemeliharaan_pbk_lv4_tw2")),
        to_snake_case("Pemeliharaan PBK Lv4 Tw3"): int(request.form.get("pemeliharaan_pbk_lv4_tw3")),
        to_snake_case("Pemeliharaan PBK Lv4 Tw4"): int(request.form.get("pemeliharaan_pbk_lv4_tw4")),
        to_snake_case("Pemeliharaan PBK Lv5 Tw1"): int(request.form.get("pemeliharaan_pbk_lv5_tw1")),
        to_snake_case("Pemeliharaan PBK Lv5 Tw2"): int(request.form.get("pemeliharaan_pbk_lv5_tw2")),
        to_snake_case("Pemeliharaan PBK Lv5 Tw3"): int(request.form.get("pemeliharaan_pbk_lv5_tw3")),
        to_snake_case("Pemeliharaan PBK Lv5 Tw4"): int(request.form.get("pemeliharaan_pbk_lv5_tw4")),
        to_snake_case("Pemeliharaan PBK Lv6 Tw1"): int(request.form.get("pemeliharaan_pbk_lv6_tw1")),
        to_snake_case("Pemeliharaan PBK Lv6 Tw2"): int(request.form.get("pemeliharaan_pbk_lv6_tw2")),
        to_snake_case("Pemeliharaan PBK Lv6 Tw3"): int(request.form.get("pemeliharaan_pbk_lv6_tw3")),
        to_snake_case("Pemeliharaan PBK Lv6 Tw4"): int(request.form.get("pemeliharaan_pbk_lv6_tw4")),
        to_snake_case("Rencana SK Pejabat Direksi Tw1"): int(request.form.get("rencana_sk_direksi_tw1")),
        to_snake_case("Rencana SK Pejabat Direksi Tw2"): int(request.form.get("rencana_sk_direksi_tw2")),
        to_snake_case("Rencana SK Pejabat Direksi Tw3"): int(request.form.get("rencana_sk_direksi_tw3")),
        to_snake_case("Rencana SK Pejabat Direksi Tw4"): int(request.form.get("rencana_sk_direksi_tw4")),
        to_snake_case("Pemeliharaan SK Lv Direksi Tw1"): int(request.form.get("pemeliharaan_sk_direksi_tw1")),
        to_snake_case("Pemeliharaan SK Lv Direksi Tw2"): int(request.form.get("pemeliharaan_sk_direksi_tw2")),
        to_snake_case("Pemeliharaan SK Lv Direksi Tw3"): int(request.form.get("pemeliharaan_sk_direksi_tw3")),
        to_snake_case("Pemeliharaan SK Lv Direksi Tw4"): int(request.form.get("pemeliharaan_sk_direksi_tw4")),
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/standar-kompetensi-sp/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code


@app.route("/form/laporan-tahunan-sp")
def form_laporan_tahunan_sp():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_tahunan_sp.html")

@app.route("/submit/laporan-tahunan-sp", methods=["POST"])
def submit_laporan_tahunan_sp():
    """
    Menangani pengiriman Laporan Tahunan Sistem Pembayaran.
    """
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        to_snake_case("Tahun Laporan"): int(request.form.get("tahun")),
        to_snake_case("Nomor Surat"): request.form.get("nomor_surat"),
        to_snake_case("Tanggal Surat"): formatted_tanggal_surat,
        to_snake_case("Total Aset"): int(request.form.get("total_aset").replace('.', '')),
        to_snake_case("Kas dan Setara Kas"): int(request.form.get("kas_setara_kas").replace('.', '')),
        to_snake_case("Hutang"): int(request.form.get("hutang").replace('.', '')),
        to_snake_case("Total Pendapatan"): int(request.form.get("total_pendapatan").replace('.', '')),
        to_snake_case("Beban Pendapatan"): int(request.form.get("beban_pendapatan").replace('.', '')),
        to_snake_case("Total Beban"): int(request.form.get("total_beban").replace('.', '')),
        to_snake_case("Laba"): int(request.form.get("laba").replace('.', '')),
        to_snake_case("Rugi"): int(request.form.get("rugi").replace('.', '')),
        to_snake_case("Keterangan"): request.form.get("keterangan"),
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/tahunan-sp/submit", form_data=form_data, file_obj=file_laporan, method="POST")
    return jsonify({"success": success, "message": message}), status_code

# --- Rute Laporan RBA APU PPT (Baru Ditambahkan) ---
@app.route('/user/forms/laporan_rba_apu_ppt')
def laporan_rba_apu_ppt():
    """Merender formulir untuk Laporan RBA APU PPT."""
    if 'username' not in session or session['role'] != 'user':
        # Removed flash import, so replacing flash with direct return
        return redirect(url_for('login'))
    return render_template('user/forms/laporan_rba_apu_ppt.html')

@app.route('/submit/laporan_rba_apu_ppt', methods=['POST'])
def submit_laporan_rba_apu_ppt():
    """Menangani pengiriman formulir Laporan RBA APU PPT."""
    if 'username' not in session or session['role'] != 'user':
        # Removed flash import, so replacing flash with direct return
        return redirect(url_for('login'))

    try:
        # Informasi Umum Penginput
        nama_penginput = request.form['nama_penginput']
        email_penginput = request.form['email_penginput']
        email_perusahaan = request.form['email_perusahaan']
        nomor_hp_penginput = request.form['nomor_hp_penginput']

        # Data Frekuensi Transaksi
        frekuensi_incoming = int(request.form['frekuensi_incoming'])
        frekuensi_outgoing = int(request.form['frekuensi_outgoing'])
        frekuensi_domestik = int(request.form['frekuensi_domestik'])

        # Data Nilai/Nominal Transaksi
        nilai_incoming_cash_to_account = int(request.form['nilai_incoming_cash_to_account'])
        nilai_incoming_account_to_cash = int(request.form['nilai_incoming_account_to_cash'])
        nilai_incoming_account_to_account = int(request.form['nilai_incoming_account_to_account'])
        nilai_incoming_cash_to_cash = int(request.form['nilai_incoming_cash_to_cash'])
        nilai_outgoing_cash_to_account = int(request.form['nilai_outgoing_cash_to_account'])
        nilai_outgoing_account_to_cash = int(request.form['nilai_outgoing_account_to_cash'])
        nilai_outgoing_account_to_account = int(request.form['nilai_outgoing_account_to_account'])
        nilai_outgoing_cash_to_cash = int(request.form['nilai_outgoing_cash_to_cash'])
        nilai_domestik_cash_to_account = int(request.form['nilai_domestik_cash_to_account'])
        nilai_domestik_account_to_cash = int(request.form['nilai_domestik_account_to_cash'])
        nilai_domestik_account_to_account = int(request.form['nilai_domestik_account_to_account'])
        nilai_domestik_cash_to_cash = int(request.form['nilai_domestik_cash_to_cash'])

        # Data Nilai/Nominal Transaksi dari Negara High Risk Countries
        high_risk_countries = [
            "KOREA UTARA", "IRAN", "SURIAH", "MYANMAR", "AFGHANISTAN", "SUDAN", "KUBA",
            "BRITISH VIRGIN ISLAND", "CAYMAN ISLAND", "NIGERIA", "MALAYSIA", "JEPANG",
            "SINGAPURA", "THAILAND", "ARAB SAUDI", "UNI EMIRAT ARAB", "AMERIKA SERIKAT",
            "FILIPINA", "AUSTRALIA"
        ]
        transaction_types = [
            "incoming_cash_to_cash", "outgoing_cash_to_cash", "incoming_cash_to_account",
            "outgoing_cash_to_account", "incoming_account_to_account", "outgoing_account_to_account"
        ]
        high_risk_data = {}
        for t_type_slug in transaction_types:
            for country in high_risk_countries:
                field_name = f"{t_type_slug}_{country.replace(' ', '_').lower()}"
                high_risk_data[field_name] = int(request.form[field_name])
            other_countries_field = f"{t_type_slug}_negara_lain"
            high_risk_data[other_countries_field] = int(request.form[other_countries_field])

        # Data Nasabah Berdasarkan Profesi
        professions = [
            "Pegawai BUMN/Politik", "Pegawai Swasta", "Pengusaha/Wiraswasta",
            "Ibu Rumah Tangga", "Profesional", "Konsultan", "Profil/Pekerjaan Lainnya"
        ]
        customer_prof_data = {}
        for prof in professions:
            field_name = f"nasabah_profesi_{prof.replace('/', '_').replace(' ', '_').lower()}"
            customer_prof_data[field_name] = int(request.form[field_name])
        customer_prof_data['nasabah_pep'] = int(request.form['nasabah_pep'])

        # Data Nasabah Berdasarkan Status WNA/WNI
        customer_nationality_data = {}
        customer_nationality_data['nasabah_wni'] = int(request.form['nasabah_wni'])
        wna_countries = [
            "KOREA UTARA", "IRAN", "SURIAH", "MYANMAR", "AFGHANISTAN", "SUDAN", "KUBA",
            "BRITISH VIRGIN ISLAND", "CAYMAN ISLAND", "NIGERIA", "MALAYSIA", "JEPANG",
            "SINGAPURA", "THAILAND", "ARAB SAUDI", "UNI EMIRAT ARAB", "AMERIKA SERIKAT",
            "FILIPINA", "AUSTRALIA"
        ]
        for country in wna_countries:
            field_name = f"nasabah_wna_{country.replace(' ', '_').lower()}"
            customer_nationality_data[field_name] = int(request.form[field_name])
        customer_nationality_data['nasabah_wna_lainnya'] = int(request.form['nasabah_wna_lainnya'])

        # Data Perusahaan
        lokasi_kantor_pusat = request.form['lokasi_kantor_pusat']
        jumlah_titik_layanan = request.form['jumlah_titik_layanan'] # String, contoh: "1000 titik-Jawa Barat"
        jumlah_mitra_kerjasama = request.form['jumlah_mitra_kerjasama'] # String, contoh: "10 Mitra kerja sama Dalam Negeri"
        memiliki_aplikasi_website_api = request.form['memiliki_aplikasi_website_api']
        nama_brand_layanan = request.form.get('nama_brand_layanan', '')
        jenis_sistem = request.form.getlist('jenis_sistem') # List of strings

        # Persentase Pemegang Saham
        shareholder_types = ["berbadan_hukum", "perseorangan", "domestik", "asing"]
        shareholder_data = {}
        for s_type_slug in shareholder_types:
            shareholder_data[s_type_slug] = []
            i = 1
            while True:
                name_field = f"pemegang_saham_{s_type_slug}_{i}_nama"
                if name_field in request.form:
                    shareholder_entry = {
                        "nama": request.form[name_field],
                        "nominal": request.form[f"pemegang_saham_{s_type_slug}_{i}_nominal"],
                        "lbr_saham": request.form[f"pemegang_saham_{s_type_slug}_{i}_lbr_saham"],
                        "persentase": request.form[f"pemegang_saham_{s_type_slug}_{i}_persentase"]
                    }
                    shareholder_data[s_type_slug].append(shareholder_entry)
                    i += 1
                else:
                    break

        # Data Keuangan Perusahaan
        total_aset = int(request.form['total_aset'])
        total_modal_dasar = int(request.form['total_modal_dasar'])
        total_modal_disetor = int(request.form['total_modal_disetor'])
        total_laba_bersih_setelah_pajak = int(request.form['total_laba_bersih_setelah_pajak'])
        jenis_bisnis_lainnya = request.form['jenis_bisnis_lainnya']

        # Self-Assessment Data
        self_assessment_data = {}
        assessment_fields = [
            "dir_kom_kebijakan", "dir_kom_laporan_efektif", "dir_kom_pelaporan_ppatk", "dir_kom_pengawasan",
            "kpt_cdd_edd", "kpt_data_info_dokumen", "kpt_pelaporan_transaksi", "kpt_efektivitas",
            "kpt_laporan_efektivitas", "kpt_pengkinian_profil",
            "manajemen_risiko_identifikasi", "manajemen_risiko_pengkinian", "manajemen_risiko_dokumentasi",
            "manajemen_risiko_informasi_otoritas", "manajemen_risiko_peningkatan_pengendalian",
            "manajemen_risiko_dokumentasi_dttot", "manajemen_risiko_pengecekan_dttot",
            "sdm_kelakuan_baik", "sdm_peningkatan_pemahaman",
            "spi_unit_kerja", "spi_pemisahan_wewenang", "spi_audit_internal"
        ]
        for field in assessment_fields:
            self_assessment_data[field] = int(request.form[field])

        # Pernyataan Persetujuan
        pernyataan_setuju = 'pernyataan_setuju' in request.form

        # Penanganan Upload File
        uploaded_files_paths = {}
        file_keys = {
            'dokumen_form_risiko': 'file_form_risiko',
            'dokumen_kertas_kerja_self_assesment': 'file_kertas_kerja_self_assesment',
            'dokumen_surat_pernyataan_keabsahan': 'file_surat_pernyataan_keabsahan'
        }
        
        # Siapkan dictionary untuk file yang akan diunggah
        files_to_upload = {}
        for form_key, api_key in file_keys.items():
            if form_key in request.files:
                file = request.files[form_key]
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    uploaded_files_paths[api_key] = file_path
                    # Tambahkan file ke dictionary files_to_upload untuk send_report_to_backend
                    # Note: send_report_to_backend currently only takes one file_obj.
                    # If API expects multiple, this needs modification.
                    # For now, we'll pick one 'main_file_to_send' below.
                else:
                    uploaded_files_paths[api_key] = None # Tandai jika tidak ada file diupload
            else:
                uploaded_files_paths[api_key] = None # Tandai jika field tidak ada di request

        # Gabungkan semua data ke dalam satu payload untuk dikirim ke backend
        # Perhatikan bahwa API Anda mungkin mengharapkan struktur yang berbeda
        # Ini adalah contoh payload yang digabungkan
        full_payload = {
            "informasi_penginput": {
                "nama_penginput": nama_penginput,
                "email_penginput": email_penginput,
                "email_perusahaan": email_perusahaan,
                "nomor_hp_penginput": nomor_hp_penginput
            },
            "frekuensi_transaksi": {
                "incoming": frekuensi_incoming,
                "outgoing": frekuensi_outgoing,
                "domestik": frekuensi_domestik
            },
            "nilai_nominal_transaksi": {
                "incoming_cash_to_account": nilai_incoming_cash_to_account,
                "incoming_account_to_cash": nilai_incoming_account_to_cash,
                "incoming_account_to_account": nilai_incoming_account_to_account,
                "incoming_cash_to_cash": nilai_incoming_cash_to_cash,
                "outgoing_cash_to_account": nilai_outgoing_cash_to_account,
                "outgoing_account_to_cash": nilai_outgoing_account_to_cash,
                "outgoing_account_to_account": nilai_outgoing_account_to_account,
                "outgoing_cash_to_cash": nilai_outgoing_cash_to_cash,
                "domestik_cash_to_account": nilai_domestik_cash_to_account,
                "domestik_account_to_cash": nilai_domestik_account_to_cash,
                "domestik_account_to_account": nilai_domestik_account_to_account,
                "domestik_cash_to_cash": nilai_domestik_cash_to_cash
            },
            "nilai_nominal_transaksi_high_risk": high_risk_data,
            "nasabah_profesi": customer_prof_data,
            "nasabah_kewarganegaraan": customer_nationality_data,
            "data_perusahaan": {
                "lokasi_kantor_pusat": lokasi_kantor_pusat,
                "jumlah_titik_layanan": jumlah_titik_layanan,
                "jumlah_mitra_kerjasama": jumlah_mitra_kerjasama,
                "memiliki_aplikasi_website_api": memiliki_aplikasi_website_api,
                "nama_brand_layanan": nama_brand_layanan,
                "jenis_sistem": jenis_sistem
            },
            "pemegang_saham": shareholder_data,
            "keuangan_perusahaan": {
                "total_aset": total_aset,
                "total_modal_dasar": total_modal_dasar,
                "total_modal_disetor": total_modal_disetor,
                "total_laba_bersih_setelah_pajak": total_laba_bersih_setelah_pajak,
                "jenis_bisnis_lainnya": jenis_bisnis_lainnya
            },
            "self_assessment": self_assessment_data,
            "pernyataan_setuju": pernyataan_setuju
            # File paths can be sent separately or handled by the backend after upload
            # "uploaded_files_paths": uploaded_files_paths # Mungkin tidak perlu dikirim langsung ke API jika API mengharapkan file terpisah
        }

        # Untuk API yang mengharapkan JSON payload dan file terpisah,
        # Anda perlu memisahkan data JSON dari file.
        # Jika API mengharapkan semua dalam multipart/form-data,
        # Anda perlu meratakan full_payload ke form_data sederhana.

        # Contoh pengiriman sebagai JSON payload (jika API mendukungnya)
        # Jika API mengharapkan file terpisah, Anda bisa mengirim JSON payload,
        # lalu mengirim file dalam permintaan terpisah atau sebagai bagian dari multipart data.
        # Karena Anda menyebutkan file_laporan di send_report_to_backend, kita akan coba kirim sebagai multipart.

        # Mengubah full_payload menjadi format yang cocok untuk form_data (flat dictionary)
        # Ini akan menjadi kompleks karena ada nested dictionaries dan lists.
        # Pendekatan yang lebih baik adalah mengirim JSON payload jika API memungkinkan,
        # atau merancang ulang frontend untuk mengirim flat data.
        # Untuk tujuan demonstrasi, saya akan membuat flat_form_data.
        flat_form_data = {}
        for key, value in full_payload.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, list): # Handle lists like jenis_sistem, shareholder_data
                        # Convert list of items to comma-separated string if the backend expects it flat
                        # Or, if the backend expects arrays, you might need to adjust send_report_to_backend
                        # to handle lists in form_data more gracefully (e.g., by sending multiple key-value pairs
                        # with the same key, like 'jenis_sistem[]').
                        # For now, converting to JSON string for complex nested lists/dicts.
                        flat_form_data[f"{key}_{sub_key}"] = json.dumps(sub_value)
                    else:
                        flat_form_data[f"{key}_{sub_key}"] = sub_value
            elif isinstance(value, list):
                flat_form_data[f"{key}"] = json.dumps(value) # For top-level lists
            else:
                flat_form_data[key] = value
        
        # Karena API Anda mengharapkan 'file' sebagai nama field untuk file,
        # kita perlu memilih salah satu file untuk dikirim sebagai 'file' utama
        # atau memodifikasi send_report_to_backend untuk menangani multiple files
        # jika API mendukungnya. Untuk saat ini, saya akan memilih 'dokumen_form_risiko'
        # sebagai 'file' utama jika ada, dan mengabaikan yang lain untuk kesederhanaan
        # sesuai dengan fungsi send_report_to_backend yang ada.
        
        main_file_to_send = None
        if 'dokumen_form_risiko' in request.files and request.files['dokumen_form_risiko'].filename != '':
            main_file_to_send = request.files['dokumen_form_risiko']
        elif 'dokumen_kertas_kerja_self_assesment' in request.files and request.files['dokumen_kertas_kerja_self_assesment'].filename != '':
            main_file_to_send = request.files['dokumen_kertas_kerja_self_assesment']
        elif 'dokumen_surat_pernyataan_keabsahan' in request.files and request.files['dokumen_surat_pernyataan_keabsahan'].filename != '':
            main_file_to_send = request.files['dokumen_surat_pernyataan_keabsahan']

        # Jika API Anda membutuhkan semua file, Anda perlu memodifikasi send_report_to_backend
        # untuk menerima dictionary files, bukan hanya satu file_obj.
        # Untuk saat ini, kita akan mengirimkan flat_form_data dan satu file utama.

        success, message, status_code = send_report_to_backend(
            "laporan/rba-apu-ppt/submit", # Ganti dengan endpoint API yang sesuai
            form_data=flat_form_data, # Menggunakan form_data untuk multipart
            file_obj=main_file_to_send,
            method="POST"
        )

        # Setelah berhasil mengirim data, hapus file yang diunggah dari server lokal
        for key, path in uploaded_files_paths.items():
            if path and os.path.exists(path):
                os.remove(path)
                print(f"DEBUG: File lokal dihapus: {path}")

        # Replaced flash with jsonify for API-like response or direct redirect for user experience
        if success:
            return jsonify({"success": True, "message": message}), status_code
        else:
            return jsonify({"success": False, "message": message}), status_code

    except ValueError as e:
        return jsonify({"success": False, "message": f'Kesalahan validasi data: {str(e)}'}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f'Terjadi kesalahan saat mengirim laporan: {str(e)}'}), 500


@app.route("/logout")
def logout():
    """Mencatat keluar pengguna dengan menghapus sesi."""
    session.pop("username", None)
    session.pop("access_token", None)
    session.pop("refresh_token", None) # Hapus refresh token juga
    session.pop("role", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
