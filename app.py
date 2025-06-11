# app.py
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import requests
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Kunci rahasia untuk pengelolaan sesi

# Base URL untuk API backend Anda
API_BASE_URL = "http://20.205.26.22:8000/api/"

# Dummy data bank (sesuaikan dengan kebutuhan produksi Anda jika diperlukan)
# Data ini digunakan untuk mengisi dropdown "Nama PJP" di form KPSP
banks = [
    {"id": 1, "nama": "PT Fliptech Lentera Inspirasi Pertiwi", "kategori": "Penyedia Jasa Pembayaran - Kategori Izin 3",
     "no_izin": "18/196/DKSP/68", "tgl_izin": "04 Oktober 2016"},
    {"id": 2, "nama": "PT Contoh Bank Digital", "kategori": "Bank Umum",
     "no_izin": "SK-001/OJK/2020", "tgl_izin": "15 Januari 2020"},
    {"id": 3, "nama": "PT Pembayaran Cepat", "kategori": "Penyedia Jasa Pembayaran - Kategori Izin 2",
     "no_izin": "19/200/DKSP/70", "tgl_izin": "10 Maret 2018"}
]

# --- Penyimpanan data KPSP di memori (untuk demonstrasi sederhana) ---
# CATATAN PENTING: Data ini akan HILANG setiap kali server Flask di-restart.
# Untuk persistensi data di aplikasi produksi, Anda harus mengimplementasikan
# penggunaan database (misalnya, SQLite, PostgreSQL, MySQL) dengan ORM (seperti SQLAlchemy).
kpsp_reports = []
report_id_counter = 1 # Penghitung untuk memberikan ID unik pada setiap laporan

# --- Fungsi utilitas untuk simulasi perhitungan KPSP ---
# Anda SANGAT PERLU mengganti logika ini dengan rumus perhitungan KPSP yang sebenarnya
# dari file JavaScript (core.js) atau dokumentasi rumus KPSP Anda.
# Perhatikan bahwa dalam skenario ini, perhitungan utama sudah ada di frontend JS.
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


@app.route("/", methods=["GET", "POST"])
def login():
    """
    Menangani login pengguna. Mengirim kredensial ke endpoint login API backend.
    Jika berhasil, menyimpan token akses dalam sesi dan mengarahkan ke dasbor berdasarkan peran.
    """
    if request.method == "POST":
        sandi_pjp = request.form["username"] # Mengasumsikan frontend mengirim 'username'
        password = request.form["password"]
        # Mengubah kunci dari 'username_or_email' menjadi 'sandi_pjp' sesuai error backend yang diterima
        login_data = {"sandi_pjp": sandi_pjp, "password": password}
        try:
            response = requests.post(f"{API_BASE_URL}auth/login/", json=login_data)
            response_data = response.json()
            if response.status_code == 200 and response_data.get("data") and response_data["data"].get("access"):
                session["username"] = sandi_pjp
                session["access_token"] = response_data["data"]["access"]
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
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("admin/dashboardadmin.html", banks=banks)

@app.route("/user/dashboard")
def user_dashboard():
    """Merender dasbor pengguna, memerlukan login pengguna."""
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/dashboarduser.html")

@app.route("/admin/profile", endpoint="admin_profile")
def profile_admin():
    """Merender halaman profil admin, memerlukan peran admin."""
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("admin/profile.html")

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

def send_report_to_backend(endpoint_path, form_data, file_obj):
    """
    Fungsi generik untuk mengirim data laporan dan file ke API backend.
    Args:
        endpoint_path (str): Jalur endpoint API tertentu (misalnya, "laporan/fraud/submit").
        form_data (dict): Kamus bidang formulir dan nilainya.
        file_obj (werkzeug.datastructures.FileStorage): Objek file yang diunggah.
    Returns:
        tuple: Sebuah tuple yang berisi (boolean_sukses, pesan, kode_status).
    """
    if "username" not in session:
        print("DEBUG: Sesi tidak valid, tidak ada username dalam sesi.")
        return False, "Sesi tidak valid, silakan login kembali.", 401

    access_token = session.get('access_token')
    if not access_token:
        print("DEBUG: Tidak ada access_token dalam sesi. Pengguna mungkin tidak login.")
        return False, "Autentikasi gagal, silakan login kembali.", 401

    headers = {"Authorization": f"Bearer {access_token}"}
    files = {}
    if file_obj and file_obj.filename:
        # Nama kunci untuk file harus cocok dengan yang diharapkan oleh API backend
        # Berdasarkan Postman, kuncinya adalah 'file'
        files = {"file": (file_obj.filename, file_obj.stream, file_obj.mimetype)}
        print(f"DEBUG: File akan dikirim: {file_obj.filename}, MimeType: {file_obj.mimetype}")
    else:
        print("DEBUG: Tidak ada file yang akan dikirim.")


    full_api_url = f"{API_BASE_URL}{endpoint_path}"
    print(f"\n--- DEBUG: Mengirim permintaan ke API Backend ---")
    print(f"URL: {full_api_url}")
    print(f"Headers: {headers}")
    print(f"Data Form: {form_data}")
    print(f"Files: {files.keys() if files else 'No files'}") # Hanya tampilkan nama file, bukan kontennya


    try:
        response = requests.post(full_api_url, headers=headers, data=form_data, files=files)
        
        print(f"--- DEBUG: Respons dari API Backend ---")
        print(f"Status Code: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"Response JSON: {json.dumps(response_data, indent=2)}")
        except json.JSONDecodeError:
            response_data = {"message": response.text} # Ambil teks jika bukan JSON
            print(f"Response Text (bukan JSON): {response.text}")
        
        if response.status_code == 201: # 201 Created for successful submissions
            return True, response_data.get("message", "Laporan berhasil dikirim!"), 201
        else:
            # Mengembalikan pesan kesalahan dari backend jika ada
            error_message = response_data.get("message", "Gagal mengirim laporan.")
            if isinstance(response_data, dict):
                # Tambahkan detail kesalahan dari backend jika disediakan (misal: validasi field)
                for key, value in response_data.items():
                    if key != "message": # Hindari duplikasi pesan utama
                        error_message += f"\n{key}: {value}"
            return False, error_message, response.status_code
    except requests.exceptions.ConnectionError as e:
        print(f"DEBUG: Kesalahan Koneksi: {e}")
        return False, f"Gagal terhubung ke server API (koneksi ditolak atau server tidak tersedia): {e}", 500
    except requests.exceptions.Timeout as e:
        print(f"DEBUG: Kesalahan Timeout: {e}")
        return False, f"Permintaan ke server API habis waktu: {e}", 500
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Kesalahan Permintaan Umum: {e}")
        return False, f"Terjadi kesalahan saat mengirim permintaan ke server API: {e}", 500
    except json.JSONDecodeError:
        print(f"DEBUG: Respon API bukan JSON yang valid atau kosong.")
        return False, "Respon API bukan JSON yang valid atau kosong.", 500


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
        "tahun_laporan": int(request.form.get("tahun")),
        "periode_laporan": request.form.get("bulan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "jumlah_fraud": int(request.form.get("jumlah_fraud")),
        "jumlah_besar_kerugian": int(request.form.get("kerugian").replace('.', '')),
        "keterangan_fraud": request.form.get("keterangan_fraud"),
        "keterangan_tindak_lanjut": request.form.get("tindak_lanjut")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/fraud/submit", form_data, file_laporan)
    return jsonify({"success": success, "message": message}), status_code

@app.route("/form/laporan-fraud")
def form_laporan_fraud():
    """Merender formulir untuk Laporan Fraud."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_fraud.html")

@app.route("/submit/laporan-dttot", methods=["POST"])
def submit_laporan_dttot():
    """
    Menangani pengiriman Laporan DTTOT.
    """
    try:
        # Asumsi DD/MM/YYYY untuk konsistensi jika tidak ditentukan lain
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "tahun_laporan": int(request.form.get("tahun")),
        "periode_laporan": request.form.get("periode"),
        "jumlah_terduga_teroris": int(request.form.get("jumlah_terduga")),
        "perihal": request.form.get("perihal"),
        "keterangan": request.form.get("keterangan")
    }
    file_laporan = request.files.get("file_laporan")

    # Menggunakan fungsi send_report_to_backend untuk mengirim data ke API
    success, message, status_code = send_report_to_backend("laporan/dttot/submit", form_data, file_laporan)
    return jsonify({"success": success, "message": message}), status_code


@app.route("/form/laporan-dttot")
def form_laporan_dttot():
    """Merender formulir untuk Laporan DTTOT."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_dttot.html")

@app.route("/form/laporan-keuangan-tahunan")
def form_laporan_keuangan_tahunan():
    """Merender formulir untuk Laporan Keuangan Tahunan."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_keuangan_tahunan.html")

@app.route("/submit/laporan-keuangan-tahunan", methods=["POST"])
def submit_laporan_keuangan_tahunan():
    """
    Menangani pengiriman Laporan Keuangan Tahunan.
    CATATAN: Endpoint untuk Laporan Keuangan Tahunan tidak secara eksplisit tercantum dalam dokumentasi API.
    Ini akan mengembalikan keberhasilan yang disimulasikan.
    """
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
        formatted_tanggal_opini = None
        if request.form.get("tanggal_opini"):
            formatted_tanggal_opini = datetime.strptime(request.form.get("tanggal_opini"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal tidak valid"}), 400

    form_data = {
        "tahun_laporan": int(request.form.get("tahun")), # Menggunakan 'tahun_laporan' untuk konsistensi
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "modal_disetor": int(request.form.get("modal_disetor").replace('.', '')),
        "jenis_audit": request.form.get("jenis_audit"),
        "kantor_akuntan": request.form.get("kantor_akuntan"),
        "tanggal_opini": formatted_tanggal_opini,
        "opini": request.form.get("opini"),
        "pendapatan": int(request.form.get("pendapatan").replace('.', '')),
        "beban_operasional": int(request.form.get("beban_operasional").replace('.', '')),
        "laba": int(request.form.get("laba").replace('.', '')),
        "rugi": int(request.form.get("rugi").replace('.', '')),
        "total_aset": int(request.form.get("total_aset").replace('.', '')),
        "total_liabilitas": int(request.form.get("total_liabilitas").replace('.', '')),
        "total_equitas": int(request.form.get("total_equitas").replace('.', ''))
    }
    file_laporan = request.files.get("file_laporan")

    # Menggunakan fungsi send_report_to_backend
    success, message, status_code = send_report_to_backend("laporan/keuangan-tahunan/submit", form_data, file_laporan)
    return jsonify({"success": success, "message": message}), status_code


@app.route("/form/laporan-keuangan-triwulan")
def form_laporan_keuangan_triwulan():
    """Merender formulir untuk Laporan Keuangan Triwulan."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_keuangan_triwulan.html")

@app.route("/submit/laporan-keuangan-triwulan", methods=["POST"])
def submit_laporan_keuangan_triwulan():
    """
    Menangani pengiriman Laporan Keuangan Triwulan.
    Disambungkan ke endpoint laporan/keuangan-triwulanan/submit.
    """
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400
    
    # Memastikan semua nilai numerik dikonversi ke integer dan menghilangkan tanda titik
    try:
        modal_disetor = int(request.form.get("modal_disetor").replace('.', ''))
        total_revenue = int(request.form.get("pendapatan").replace('.', ''))
        cost_of_revenue = int(request.form.get("beban_operasional").replace('.', ''))
        profit = int(request.form.get("laba").replace('.', ''))
        loss = int(request.form.get("rugi").replace('.', ''))
        total_asset = int(request.form.get("total_aset").replace('.', ''))
        liabilities = int(request.form.get("total_liabilitas").replace('.', ''))
        equity = int(request.form.get("equity").replace('.', '')) # Menggunakan nama 'equity' dari HTML form
    except ValueError:
        return jsonify({"success": False, "message": "Format angka tidak valid. Pastikan hanya memasukkan angka."}), 400

    form_data = {
        "tahun_laporan": int(request.form.get("tahun")),
        "periode_laporan": request.form.get("triwulan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "modal_disetor": modal_disetor,
        "total_revenue": total_revenue, # Mengganti 'pendapatan' ke 'total_revenue'
        "cost_of_revenue": cost_of_revenue, # Mengganti 'beban_operasional' ke 'cost_of_revenue'
        "profit": profit, # Mengganti 'laba' ke 'profit'
        "loss": loss, # Mengganti 'rugi' ke 'loss'
        "total_asset": total_asset, # Mengganti 'total_aset' ke 'total_asset'
        "liabilities": liabilities, # Mengganti 'total_liabilitas' ke 'liabilities'
        "equity": equity, # Mengganti 'total_ekuitas' ke 'equity' (dari HTML 'equity')
        "keterangan": request.form.get("keterangan") # Menambahkan field keterangan
    }
    file_laporan = request.files.get("file_laporan")

    # Menggunakan fungsi send_report_to_backend dengan endpoint yang sesuai
    success, message, status_code = send_report_to_backend("laporan/keuangan-triwulanan/submit", form_data, file_laporan)
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
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
        
        # Ekstrak hanya bagian tanggal dari input datetime-local (YYYY-MM-DD) dan format ke DD/MM/YYYY
        waktu_kejadian_raw = request.form.get("waktu_kejadian")
        if waktu_kejadian_raw:
            formatted_waktu_kejadian = datetime.strptime(waktu_kejadian_raw.split('T')[0], '%Y-%m-%d').strftime('%d/%m/%Y')
        else:
            formatted_waktu_kejadian = None # Atau tangani sebagai error jika diperlukan dan tidak ada
    except ValueError as e:
        return jsonify({"success": False, "message": f"Format tanggal/waktu tidak valid: {e}"}), 400

    form_data = {
        "tahun_laporan": int(request.form.get("tahun")), # Dikoreksi dari tahun_laporan menjadi tahun
        "periode_laporan": request.form.get("periode"), # Dikoreksi dari periode_laporan menjadi periode
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "waktu_kejadian": formatted_waktu_kejadian, # Sekarang hanya bagian tanggal, sesuai docs API
        "jenis_gangguan": request.form.get("jenis_gangguan"),
        # 'ringkasan' dari HTML dipetakan ke 'keterangan_gangguan' untuk API backend.
        "keterangan_gangguan": request.form.get("ringkasan"), 
        "upaya_perbaikan": request.form.get("upaya_perbaikan"),
        "status_penyelesaian": request.form.get("status_penyelesaian")
    }

    # Tangani tanggal_penyelesaian opsional jika statusnya 'Terselesaikan'
    tanggal_penyelesaian_raw = request.form.get("tanggal_penyelesaian")
    if request.form.get("status_penyelesaian") == 'Terselesaikan' and tanggal_penyelesaian_raw:
        try:
            # Ekstrak hanya bagian tanggal dari input datetime-local dan format ke DD/MM/YYYY
            form_data["tanggal_penyelesaian"] = datetime.strptime(tanggal_penyelesaian_raw.split('T')[0], '%Y-%m-%d').strftime('%d/%m/%Y')
        except ValueError:
            return jsonify({"success": False, "message": "Format tanggal penyelesaian tidak valid"}), 400

    file_laporan = request.files.get("file_laporan") # Ini sesuai dengan name="file_laporan" di input HTML

    # Catatan: Fungsi Flask saat ini (dan kemungkinan endpoint API Django)
    # diatur untuk menerima *satu* data insiden per laporan.
    # Jika niat Anda adalah untuk mengirimkan beberapa insiden (dari tombol "Tambah Gangguan IT"),
    # API backend Anda harus diperbarui untuk menerima array objek insiden,
    # dan fungsi Flask ini perlu mengulang array tersebut.

    success, message, status_code = send_report_to_backend("laporan/gangguan-it/submit", form_data, file_laporan)
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Keamanan Siber ---
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
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "jenis_kejadian": request.form.get("jenis_kejadian"),
        "upaya_penanganan": request.form.get("upaya_penanganan"),
        "status_penyelesaian": request.form.get("status_penyelesaian")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/keamanan-siber/submit", form_data, file_laporan)
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Kepatuhan IT ---
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
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "jenis_audit": request.form.get("jenis_audit"),
        "hasil_audit": request.form.get("hasil_audit"),
        "tindak_lanjut": request.form.get("tindak_lanjut")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/kepatuhan-it/submit", form_data, file_laporan)
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Manajemen Risiko IT ---
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
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "jenis_risiko": request.form.get("jenis_risiko"),
        "dampak_risiko": request.form.get("dampak_risiko"),
        "langkah_mitigasi": request.form.get("langkah_mitigasi")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/manajemen-risiko-it/submit", form_data, file_laporan)
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Insiden Siber ---
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
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "jenis_insiden": request.form.get("jenis_insiden"),
        "dampak_insiden": request.form.get("dampak_insiden"),
        "status_penyelesaian": request.form.get("status_penyelesaian"),
        "upaya_penanganan": request.form.get("upaya_penanganan")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/insiden-siber/submit", form_data, file_laporan)
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Risiko IT (Kuartal) ---
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
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "jumlah_risiko_tinggi": int(request.form.get("jumlah_risiko_tinggi")),
        "jumlah_risiko_menengah": int(request.form.get("jumlah_risiko_menengah")),
        "jumlah_risiko_rendah": int(request.form.get("jumlah_risiko_rendah")),
        "keterangan_risiko": request.form.get("keterangan_risiko"),
        "rencana_mitigasi": request.form.get("rencana_mitigasi")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/risiko-it/submit", form_data, file_laporan)
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Tata Kelola IT (Semester) ---
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
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "aspek_tata_kelola": request.form.get("aspek_tata_kelola"),
        "hasil_evaluasi": request.form.get("hasil_evaluasi"),
        "rekomendasi_perbaikan": request.form.get("rekomendasi_perbaikan")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/tata-kelola-it/submit", form_data, file_laporan)
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Rencana Strategis IT (Tahunan) ---
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
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "strategi_utama": request.form.get("strategi_utama"),
        "target_pencapaian": request.form.get("target_pencapaian"),
        "realisasi_saat_ini": request.form.get("realisasi_saat_ini")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/rencana-strategis-it/submit", form_data, file_laporan)
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Pengelolaan Data Pribadi (Tahunan) ---
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
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "jenis_data": request.form.get("jenis_data"),
        "tujuan_penggunaan": request.form.get("tujuan_penggunaan"),
        "langkah_keamanan": request.form.get("langkah_keamanan")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/pengelolaan-data-pribadi/submit", form_data, file_laporan)
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Implementasi Kebijakan IT (Tahunan) ---
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
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "nama_kebijakan": request.form.get("nama_kebijakan"),
        "status_implementasi": request.form.get("status_implementasi"),
        "kendala_implementasi": request.form.get("kendala_implementasi"),
        "tindak_lanjut_kendala": request.form.get("tindak_lanjut_kendala")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/implementasi-kebijakan-it/submit", form_data, file_laporan)
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Ketersediaan Layanan IT (Tahunan) ---
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
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "nama_layanan": request.form.get("nama_layanan"),
        "persentase_ketersediaan": float(request.form.get("persentase_ketersediaan")),
        "penyebab_gangguan": request.form.get("penyebab_gangguan"),
        "dampak_gangguan": request.form.get("dampak_gangguan"),
        "upaya_pemulihan": request.form.get("upaya_pemulihan")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/ketersediaan-layanan-it/submit", form_data, file_laporan)
    return jsonify({"success": success, "message": message}), status_code

# --- Laporan Keamanan Informasi (Tahunan) ---
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
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "aspek_keamanan": request.form.get("aspek_keamanan"),
        "hasil_evaluasi": request.form.get("hasil_evaluasi"),
        "rekomendasi_perbaikan": request.form.get("rekomendasi_perbaikan")
    }
    file_laporan = request.files.get("file_laporan")

    success, message, status_code = send_report_to_backend("laporan/keamanan-informasi/submit", form_data, file_laporan)
    return jsonify({"success": success, "message": message}), status_code


# --- Rute placeholder untuk formulir tanpa endpoint API pengiriman eksplisit ---
# Rute ini akan merender formulir, tetapi pengirimannya akan disimulasikan karena
# dokumentasi API tidak menyediakan endpoint khusus untuk mereka.

@app.route("/form/laporan-apuppt")
def form_laporan_apuppt():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_apuppt.html")

@app.route("/submit/laporan-apuppt", methods=["POST"])
def submit_laporan_apuppt():
    # Simulasi keberhasilan karena endpoint tidak ditemukan di docs API
    print("Simulating Laporan APUPPT submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan APUPPT (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-auditsi")
def form_laporan_auditsi():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_auditsi.html")

@app.route("/submit/laporan-auditsi", methods=["POST"])
def submit_laporan_auditsi():
    # Simulasi keberhasilan karena endpoint tidak ditemukan di docs API
    print("Simulating Laporan Auditsi submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan Auditsi (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-dana-bukan-bank")
def form_laporan_dana_bukan_bank():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_dana_bukan_bank.html")

@app.route("/submit/laporan-dana-bukan-bank", methods=["POST"])
def submit_laporan_dana_bukan_bank():
    """
    Menangani pengiriman Laporan Transaksi Dana Bukan Bank (LTDBB).
    """
    try:
        # Tanggal surat bisa dalam format DD/MM/YYYY atau YYYY-MM-DD
        tanggal_surat_raw = request.form.get("tanggal_surat")
        
        # Coba parse sebagai YYYY-MM-DD dulu (dari input type="date")
        try:
            formatted_tanggal_surat = datetime.strptime(tanggal_surat_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
        except ValueError:
            # Jika gagal, coba parse sebagai DD/MM/YYYY
            formatted_tanggal_surat = datetime.strptime(tanggal_surat_raw, '%d/%m/%Y').strftime('%d/%m/%Y')

    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid. Gunakan YYYY-MM-DD atau DD/MM/YYYY."}), 400

    form_data = {
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "tahun_laporan": int(request.form.get("tahun")),
        "periode_laporan": request.form.get("periode"),
        "number_outgoing_transactions": int(request.form.get("jumlah_keluar")),
        "amount_outgoing_transactions": int(request.form.get("nilai_keluar")),
        "number_incoming_transactions": int(request.form.get("jumlah_masuk")),
        "amount_incoming_transactions": int(request.form.get("nilai_masuk")),
        "number_local_transactions": int(request.form.get("jumlah_dalam")),
        "amount_local_transactions": int(request.form.get("nilai_dalam")),
    }
    
    # Keterangan tambahan (opsional)
    keterangan = request.form.get("keterangan")
    if keterangan:
        form_data["keterangan"] = keterangan

    # Nama file dari form HTML adalah 'bukti_lkpbu' tapi API menginginkan 'file'
    file_laporan = request.files.get("bukti_lkpbu") 

    # Menggunakan fungsi send_report_to_backend untuk mengirim data ke API
    # Endpoint untuk LTDBB adalah "laporan/ltdbb/submit"
    success, message, status_code = send_report_to_backend("laporan/ltdbb/submit", form_data, file_laporan)
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
    # Melewatkan data banks ke template
    return render_template("user/forms/laporan_kpsp.html", banks=banks)

@app.route("/submit/laporan-kpsp", methods=["POST"])
def submit_laporan_kpsp():
    """
    Menerima data form KPSP dari frontend (termasuk hasil perhitungan dari JS),
    dan menyimpan laporan secara in-memory.
    """
    global report_id_counter # Menggunakan variabel global untuk ID laporan

    # Memastikan pengguna sudah login dan memiliki peran 'user'
    if "username" not in session or session.get("role") != "user":
        return jsonify({"success": False, "message": "Anda tidak memiliki otorisasi untuk mengakses fungsi ini."}), 401

    # Mengambil semua data form yang dikirim dari frontend sebagai dictionary
    form_data = request.form.to_dict()
    print("Menerima data form KPSP:", form_data)

    # Anda bisa melakukan validasi tambahan atau pemrosesan di sini jika perlu.
    # Misalnya, panggil fungsi calculate_kpsp_backend untuk validasi.
    backend_validation_results = calculate_kpsp_backend(form_data)
    if "error" in backend_validation_results:
        return jsonify({"success": False, "message": f"Validasi backend gagal: {backend_validation_results['error']}"}), 400

    # Ambil hasil perhitungan yang dikirim dari frontend (misalnya, sebagai string)
    frontend_calculated_results = {
        "total_ongoing_capital": form_data.get('totalOngoingCapitalDisplay'),
        "rasio_kpsp": form_data.get('rasioKPSPDisplay'),
        "status_initial_capital": form_data.get('statusPemenuhanInitialCapitalDisplay'),
        "status_ongoing_capital": form_data.get('statusPemenuhanOngoingCapitalDisplay')
        # Tambahkan hasil perhitungan lain yang Anda ingin simpan dari frontend
    }

    # Membuat entri laporan baru untuk disimpan
    report_entry = {
        "id": report_id_counter,
        "submitted_by": session["username"],
        "timestamp": datetime.now().isoformat(), # Waktu pengiriman laporan
        "form_data_raw": form_data, # Menyimpan semua data form mentah
        "frontend_calculations": frontend_calculated_results, # Menyimpan hasil dari frontend
        "backend_validation": backend_validation_results # Hasil validasi/pemrosesan backend
    }
    kpsp_reports.append(report_entry) # Menambahkan laporan ke daftar in-memory
    report_id_counter += 1 # Meningkatkan counter ID untuk laporan berikutnya

    print("Laporan KPSP tersimpan (in-memory):", report_entry)

    # Mengembalikan respons JSON ke frontend
    return jsonify({
        "success": True,
        "message": "Laporan KPSP berhasil diterima dan dihitung!",
        "report_id": report_entry["id"],
        "calculation_results_from_frontend": frontend_calculated_results,
        "backend_validation_status": backend_validation_results
    }), 201


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
    # Simulasi keberhasilan karena endpoint tidak ditemukan di docs API
    print("Simulating Laporan Manajemen submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan Manajemen (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-p2p")
def form_laporan_p2p():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_p2p.html")

@app.route("/submit/laporan-p2p", methods=["POST"])
def submit_laporan_p2p():
    # Simulasi keberhasilan karena endpoint tidak ditemukan di docs API
    print("Simulating Laporan P2P submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan P2P (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-pelaksanaan-edukasi-publik")
def form_laporan_pelaksanaan_edukasi_publik():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_pelaksanaan_edukasi_publik.html")

@app.route("/submit/laporan-pelaksanaan-edukasi-publik", methods=["POST"])
def submit_laporan_pelaksanaan_edukasi_publik():
    # Simulasi keberhasilan karena endpoint tidak ditemukan di docs API
    print("Simulating Laporan Pelaksanaan Edukasi Publik submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan Pelaksanaan Edukasi Publik (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-pelaksanaan-pengujian-keamanan")
def form_laporan_pelaksanaan_pengujian_keamanan():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_pelaksanaan_pengujian_keamanan.html")

@app.route("/submit/laporan-pelaksanaan-pengujian-keamanan", methods=["POST"])
def submit_laporan_pelaksanaan_pengujian_keamanan():
    # Simulasi keberhasilan karena endpoint tidak ditemukan di docs API
    print("Simulating Laporan Pelaksanaan Pengujian Keamanan submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan Pelaksanaan Pengujian Keamanan (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-pppk")
def form_laporan_pppk():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_pppk.html")

@app.route("/submit/laporan-pppk", methods=["POST"])
def submit_laporan_pppk():
    # Simulasi keberhasilan karena endpoint tidak ditemukan di docs API
    print("Simulating Laporan PPPK submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan PPPK (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-rencana-edukasi-publik")
def form_laporan_rencana_edukasi_publik():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_rencana_edukasi_publik.html")

@app.route("/submit/laporan-rencana-edukasi-publik", methods=["POST"])
def submit_laporan_rencana_edukasi_publik():
    # Simulasi keberhasilan karena endpoint tidak ditemukan di docs API
    print("Simulating Laporan Rencana Edukasi Publik submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan Rencana Edukasi Publik (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

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
    # Simulasi keberhasilan karena endpoint tidak ditemukan di docs API
    print("Simulating Laporan SKSP Tahunan submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan SKSP Tahunan (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-sksp-triwulan")
def form_laporan_sksp_triwulan():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_sksp_triwulan.html")

@app.route("/submit/laporan-sksp-triwulan", methods=["POST"])
def submit_laporan_sksp_triwulan():
    # Simulasi keberhasilan karena endpoint tidak ditemukan di docs API
    print("Simulating Laporan SKSP Triwulan submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan SKSP Triwulan (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-tahunan-sp")
def form_laporan_tahunan_sp():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_tahunan_sp.html")

@app.route("/submit/laporan-tahunan-sp", methods=["POST"])
def submit_laporan_tahunan_sp():
    # Simulasi keberhasilan karena endpoint tidak ditemukan di docs API
    print("Simulating Laporan Tahunan SP submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan Tahunan SP (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201


@app.route("/logout")
def logout():
    """Mencatat keluar pengguna dengan menghapus sesi."""
    session.pop("username", None)
    session.pop("access_token", None)
    session.pop("role", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
