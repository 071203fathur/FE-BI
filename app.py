from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import requests
from datetime import datetime
import json # Import json untuk mengelola data JSON

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Untuk session

# Base URL untuk API Anda
API_BASE_URL = "http://20.205.26.22:8000/api/"

# Dummy data bank (sesuaikan dengan kebutuhan produksi Anda)
banks = [
    {"id": 1, "nama": "PT Fliptech Lentera Inspirasi Pertiwi", "kategori": "Penyedia Jasa Pembayaran - Kategori Izin 3",
     "no_izin": "18/196/DKSP/68", "tgl_izin": "04 Oktober 2016"}
]

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Mengambil sandi_pjp (username) dan password dari form
        sandi_pjp = request.form["username"] # Menggunakan "username" dari form sebagai sandi_pjp
        password = request.form["password"]
        
        login_data = {
            "sandi_pjp": sandi_pjp, # Menggunakan sandi_pjp sesuai dengan body API
            "password": password
        }

        try:
            # Melakukan panggilan API untuk login
            response = requests.post(f"{API_BASE_URL}auth/login/", json=login_data)
            response_data = response.json()

            # Memeriksa status code dan struktur response API
            if response.status_code == 200 and response_data.get("data") and response_data["data"].get("access"):
                session["username"] = sandi_pjp # Menyimpan sandi_pjp sebagai username di session
                session["access_token"] = response_data["data"]["access"] # Mengambil access token dari data
                
                # Penentuan role (sementara):
                # Idealnya, role harus didapatkan dari response API setelah login berhasil.
                # Jika API Anda mengembalikan role, silakan sesuaikan logika di bawah ini.
                if sandi_pjp == "admin": # Contoh dummy role assignment
                    session["role"] = "admin"
                    return redirect(url_for("admin_dashboard"))
                else:
                    session["role"] = "user" # Default role untuk user lain
                    return redirect(url_for("user_dashboard"))
            else:
                # Jika login gagal, ambil pesan error dari API atau berikan pesan default
                error_message = response_data.get("message", "Username atau password salah!")
                return render_template("login.html", error=error_message)
        except requests.exceptions.RequestException as e:
            # Menangani error koneksi ke API
            error_message = f"Gagal terhubung ke server API: {e}"
            return render_template("login.html", error=error_message)

    return render_template("login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("admin/dashboardadmin.html", banks=banks)

@app.route("/user/dashboard")
def user_dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/dashboarduser.html")

@app.route("/admin/profile", endpoint="admin_profile")
def profile_admin():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("admin/profile.html")

# Tambah Data Bank (Hanya untuk Admin)
@app.route("/admin/add_bank", methods=["POST"])
def add_bank():
    if "username" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    
    nama = request.form["nama"]
    kategori = request.form["kategori"]
    no_izin = request.form["no_izin"]
    tgl_izin = request.form["tgl_izin"]
    
    banks.append({"id": len(banks) + 1, "nama": nama, "kategori": kategori, "no_izin": no_izin, "tgl_izin": tgl_izin})
    
    return redirect(url_for("admin_dashboard"))

# Halaman Laporan User
@app.route("/user/laporan")
def user_laporan():
    if "username" not in session or session["role"] != "user":
        return redirect(url_for("login"))
    success = request.args.get("success", False)
    return render_template("user/dashboarduser.html")

# Halaman Laporan Admin
@app.route("/admin/laporan")
def admin_laporan():
    if "username" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    return render_template("admin/laporan.html")

@app.route('/admin/history')
def admin_history():
    return render_template('admin/history.html')

@app.route('/admin/peraturan')
def admin_peraturan():
    return render_template('admin/peraturan.html')

@app.route("/base")
def base_page():
    return render_template("admin/base.html")

@app.route("/submit/laporan-fraud", methods=["POST"])
def submit_laporan_fraud():
    if "username" not in session:
        return redirect(url_for("login"))
    
    headers = {
        "Authorization": f"Bearer {session.get('access_token')}"
    }

    try:
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
    
    files = {}
    file = request.files.get("file_laporan")
    if file and file.filename:
        files = {"file": (file.filename, file.stream, file.mimetype)}
    
    try:
        response = requests.post(
            f"{API_BASE_URL}laporan/fraud/submit",
            data=form_data,
            files=files,
            headers=headers
        )
        
        if response.status_code == 201:
            response_data = response.json()
            return jsonify({
                "success": True,
                "message": "Laporan berhasil dikirim!",
                "data": response_data.get("data", {})
            }), 201
        else:
            error_data = response.json()
            error_message = error_data.get("message", "Gagal mengirim laporan. Silakan coba lagi.")
            return jsonify({"success": False, "message": error_message}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Gagal terhubung ke server. Silakan coba lagi nanti. {e}"}), 500

@app.route("/form/laporan-fraud")
def form_laporan_fraud():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_fraud.html")

@app.route("/submit/laporan-dttot", methods=["POST"])
def submit_laporan_dttot():
    if "username" not in session:
        return redirect(url_for("login"))

    headers = {
        "Authorization": f"Bearer {session.get('access_token')}"
    }

    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d') # Format API
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "tahun_laporan": int(request.form.get("tahun")),
        "periode_laporan": request.form.get("periode"),
        "jumlah_terduga_teroris": int(request.form.get("jumlah_terduga")),
        "perihal": request.form.get("perihal"),
        "keterangan": request.form.get("keterangan"),
        # Field tambahan yang tidak ada di API spec, tapi ada di HTML
        "nomor_surat_kepolisian": request.form.get("nomor_surat_kepolisian"), 
        "organisasi_teroris": request.form.get("organisasi_teroris")
    }

    files = {}
    file = request.files.get("file_laporan")
    if file and file.filename:
        files = {"file": (file.filename, file.stream, file.mimetype)}

    try:
        response = requests.post(
            f"{API_BASE_URL}laporan/dttot/submit",
            data=form_data,
            files=files,
            headers=headers
        )

        if response.status_code == 201:
            response_data = response.json()
            return jsonify({
                "success": True,
                "message": "Laporan DTTOT berhasil dikirim!",
                "data": response_data.get("data", {})
            }), 201
        else:
            error_data = response.json()
            return jsonify({
                "success": False,
                "message": error_data.get("message", "Gagal mengirim laporan DTTOT.")
            }), response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({
            "success": False,
            "message": f"Gagal terhubung ke server. Silakan coba lagi nanti. {e}"
        }), 500

@app.route("/form/laporan-dttot")
def form_laporan_dttot():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_dttot.html")

@app.route("/form/laporan-keuangan-tahunan")
def form_laporan_keuangan_tahunan():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_keuangan_tahunan.html")

@app.route("/form/laporan-keuangan-triwulan")
def form_laporan_keuangan_triwulan():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_keuangan_triwulan.html")

@app.route('/laporan-manajemen')
def form_laporan_manajemen():
    if "username" not in session:
        return redirect(url_for("login"))
    current_year = datetime.now().year
    return render_template("user/forms/laporan_manajemen.html", current_year=current_year)

@app.route('/form/laporan-sksp-triwulan')
def form_laporan_sksp_triwulan():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_sksp_triwulan.html")

@app.route('/form/laporan-sksp-tahunan')
def form_laporan_sksp_tahunan():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_sksp_tahunan.html", now=datetime.now())

@app.route("/submit/laporan-gangguanit", methods=["POST"])
def submit_laporan_gangguanit():
    if "username" not in session:
        return redirect(url_for("login"))

    headers = {
        "Authorization": f"Bearer {session.get('access_token')}"
    }

    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d') # Format API
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    # Mengambil data hanya untuk gangguan IT pertama karena API spec yang diberikan
    # hanya mendukung satu entri gangguan dengan field flat.
    # Jika API backend Anda mendukung multiple entries, struktur ini perlu disesuaikan.
    form_data = {
        "tahun_laporan": int(request.form.get("tahun")),
        "periode_laporan": request.form.get("periode"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "waktu_kejadian": datetime.strptime(request.form.get("waktu_kejadian_1"), '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d'), # Format API
        "jenis_gangguan": request.form.get("jenis_gangguan_1"),
        "upaya_perbaikan": request.form.get("upaya_perbaikan_1"),
        "status_penyelesaian": request.form.get("status_penyelesaian_1"),
        # Field tambahan yang tidak ada di API spec, tapi ada di HTML
        "ringkasan": request.form.get("ringkasan_1"),
        "tanggal_penyelesaian": datetime.strptime(request.form.get("tanggal_penyelesaian_1"), '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d') if request.form.get("tanggal_penyelesaian_1") else None
    }

    files = {}
    file = request.files.get("lampiran")
    if file and file.filename:
        files = {"file": (file.filename, file.stream, file.mimetype)}

    try:
        response = requests.post(
            f"{API_BASE_URL}laporan/gangguan-it/submit",
            data=form_data,
            files=files,
            headers=headers
        )
        
        if response.status_code == 201:
            response_data = response.json()
            return jsonify({
                "success": True,
                "message": "Laporan Gangguan IT berhasil dikirim!",
                "data": response_data.get("data", {})
            }), 201
        else:
            error_data = response.json()
            error_message = error_data.get("message", "Gagal mengirim laporan Gangguan IT. Silakan coba lagi.")
            return jsonify({"success": False, "message": error_message}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Gagal terhubung ke server. Silakan coba lagi nanti. {e}"}), 500

@app.route('/laporan-gangguanit')
def form_laporan_gangguanit():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_gangguanit.html")

@app.route('/laporan-dana-bukan-bank')
def form_laporan_dana_bukan_bank():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_dana_bukan_bank.html")

@app.route("/submit/laporan-transaksi-dana", methods=["POST"])
def submit_laporan_dana_bukan_bank():
    if "username" not in session:
        return redirect(url_for("login"))
    
    headers = {
        "Authorization": f"Bearer {session.get('access_token')}"
    }

    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d') # Format API
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        "tahun_laporan": int(request.form.get("tahun")),
        "periode_laporan": request.form.get("periode"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "number_outgoing_transactions": int(request.form.get("jumlah_keluar")),
        "amount_outgoing_transactions": int(request.form.get("nilai_keluar").replace('.', '')),
        "number_incoming_transactions": int(request.form.get("jumlah_masuk")),
        "amount_incoming_transactions": int(request.form.get("nilai_masuk").replace('.', '')),
        "number_local_transactions": int(request.form.get("jumlah_dalam")),
        "amount_local_transactions": int(request.form.get("nilai_dalam").replace('.', '')),
        # Field tambahan yang tidak ada di API spec, tapi ada di HTML
        "keterangan": request.form.get("keterangan")
    }
    
    files = {}
    file = request.files.get("bukti_lkpbu")
    if file and file.filename:
        files = {"file": (file.filename, file.stream, file.mimetype)}
    
    try:
        response = requests.post(
            f"{API_BASE_URL}laporan/ltdbb/submit",
            data=form_data,
            files=files,
            headers=headers
        )
        
        if response.status_code == 201:
            response_data = response.json()
            return jsonify({
                "success": True,
                "message": "Laporan Transaksi Dana Bukan Bank berhasil dikirim!",
                "data": response_data.get("data", {})
            }), 201
        else:
            error_data = response.json()
            error_message = error_data.get("message", "Gagal mengirim laporan. Silakan coba lagi.")
            return jsonify({"success": False, "message": error_message}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Gagal terhubung ke server. Silakan coba lagi nanti. {e}"}), 500

@app.route('/laporan-p2p')
def form_laporan_p2p():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_p2p.html")

@app.route("/submit/laporan-p2p", methods=["POST"])
def submit_laporan_p2p():
    if "username" not in session:
        return redirect(url_for("login"))

    headers = {
        "Authorization": f"Bearer {session.get('access_token')}"
    }

    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d') # Format API
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "tahun_laporan": int(request.form.get("tahun")),
        "periode_laporan": request.form.get("periode"),
        # Tambahkan field lain dari form P2P jika ada dan sesuai API spec
    }

    files = {}
    file = request.files.get("file_laporan") # Asumsi ada file input dengan name="file_laporan"
    if file and file.filename:
        files = {"file": (file.filename, file.stream, file.mimetype)}

    try:
        response = requests.post(
            f"{API_BASE_URL}laporan/kerjasama-p2p/submit",
            data=form_data,
            files=files,
            headers=headers
        )

        if response.status_code == 201:
            response_data = response.json()
            return jsonify({
                "success": True,
                "message": "Laporan Kerjasama P2P berhasil dikirim!",
                "data": response_data.get("data", {})
            }), 201
        else:
            error_data = response.json()
            return jsonify({
                "success": False,
                "message": error_data.get("message", "Gagal mengirim laporan Kerjasama P2P.")
            }), response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({
            "success": False,
            "message": f"Gagal terhubung ke server. Silakan coba lagi nanti. {e}"
        }), 500

@app.route("/submit/laporan-pppk", methods=["POST"])
def submit_laporan_pppk():
    if "username" not in session:
        return redirect(url_for("login"))
    
    headers = {
        "Authorization": f"Bearer {session.get('access_token')}"
    }

    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d') # Format API
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        "tahun": int(request.form.get("tahun")),
        "triwulan": request.form.get("triwulan"),
        "penyelenggara": request.form.get("penyelenggara"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "jumlah_pengaduan": int(request.form.get("jumlah_pengaduan")),
        "pengaduan_diselesaikan": int(request.form.get("pengaduan_diselesaikan")),
        "pengaduan_belum_diselesaikan": int(request.form.get("pengaduan_belum_diselesaikan")),
        "total_nilai_pengaduan": int(request.form.get("total_nilai_pengaduan").replace('.', '')),
        "persentase_pengaduan": float(request.form.get("persentase_pengaduan")),
        "diteruskan_bi": int(request.form.get("diteruskan_bi")),
        "diteruskan_ojk": int(request.form.get("diteruskan_ojk")),
        "diteruskan_laps_sjk": int(request.form.get("diteruskan_laps_sjk")),
        "diteruskan_pengadilan": int(request.form.get("diteruskan_pengadilan")),
        "diteruskan_arbitrase": int(request.form.get("diteruskan_arbitrase")),
        "diselesaikan_lainnya": int(request.form.get("diselesaikan_lainnya")),
        "keterangan": request.form.get("keterangan")
    }
    
    files = {}
    file = request.files.get("bukti_upload")
    if file and file.filename:
        files = {"bukti_upload": (file.filename, file.stream, file.mimetype)}
    
    try:
        response = requests.post(
            f"{API_BASE_URL}laporan/pppk/submit", # Asumsi endpoint PPPK
            data=form_data,
            files=files,
            headers=headers
        )
        
        if response.status_code == 201:
            response_data = response.json()
            return jsonify({
                "success": True,
                "message": "Laporan Penanganan Pengaduan Konsumen berhasil dikirim!",
                "data": response_data.get("data", {})
            }), 201
        else:
            error_data = response.json()
            error_message = error_data.get("message", "Gagal mengirim laporan. Silakan coba lagi.")
            return jsonify({"success": False, "message": error_message}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Gagal terhubung ke server. Silakan coba lagi nanti. {e}"}), 500

@app.route('/laporan-pppk')
def form_laporan_pppk():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_pppk.html")

@app.route("/submit/laporan-keuangan-tahunan", methods=["POST"])
def submit_laporan_keuangan_tahunan():
    if "username" not in session:
        return redirect(url_for("login"))
    
    headers = {
        "Authorization": f"Bearer {session.get('access_token')}"
    }

    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d') # Format API
        formatted_tanggal_opini = None
        if request.form.get("tanggal_opini"):
            formatted_tanggal_opini = datetime.strptime(request.form.get("tanggal_opini"), '%Y-%m-%d').strftime('%Y-%m-%d') # Format API
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal tidak valid"}), 400

    form_data = {
        "tahun": int(request.form.get("tahun")),
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
    
    files = {}
    file = request.files.get("file_laporan")
    if file and file.filename:
        files = {"file_laporan": (file.filename, file.stream, file.mimetype)}
    
    try:
        response = requests.post(
            f"{API_BASE_URL}laporan/keuangan-tahunan/submit",
            data=form_data,
            files=files,
            headers=headers
        )
        
        if response.status_code == 201:
            response_data = response.json()
            return jsonify({
                "success": True,
                "message": "Laporan Keuangan Tahunan berhasil dikirim!",
                "data": response_data.get("data", {})
            }), 201
        else:
            error_data = response.json()
            error_message = error_data.get("message", "Gagal mengirim laporan. Silakan coba lagi.")
            return jsonify({"success": False, "message": error_message}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Gagal terhubung ke server. Silakan coba lagi nanti. {e}"}), 500

@app.route("/submit/laporan-keuangan-triwulan", methods=["POST"])
def submit_laporan_keuangan_triwulan():
    if "username" not in session:
        return redirect(url_for("login"))
    
    headers = {
        "Authorization": f"Bearer {session.get('access_token')}"
    }

    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d') # Format API
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        "tahun": int(request.form.get("tahun")),
        "triwulan": request.form.get("triwulan"),
        "penyelenggara": request.form.get("penyelenggara"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "modal_disetor": int(request.form.get("modal_disetor").replace('.', '')),
        "pendapatan": int(request.form.get("pendapatan").replace('.', '')),
        "beban_operasional": int(request.form.get("beban_operasional").replace('.', '')),
        "laba": int(request.form.get("laba").replace('.', '')),
        "rugi": int(request.form.get("rugi").replace('.', '')),
        "total_aset": int(request.form.get("total_aset").replace('.', '')),
        "total_liabilitas": int(request.form.get("total_liabilitas").replace('.', '')),
        "total_equitas": int(request.form.get("equity").replace('.', ''))
    }
    
    files = {}
    file = request.files.get("file_laporan")
    if file and file.filename:
        files = {"file_laporan": (file.filename, file.stream, file.mimetype)}
    
    try:
        response = requests.post(
            f"{API_BASE_URL}laporan/keuangan-triwulan/submit",
            data=form_data,
            files=files,
            headers=headers
        )
        
        if response.status_code == 201:
            response_data = response.json()
            return jsonify({
                "success": True,
                "message": "Laporan Keuangan Triwulan berhasil dikirim!",
                "data": response_data.get("data", {})
            }), 201
        else:
            error_data = response.json()
            error_message = error_data.get("message", "Gagal mengirim laporan. Silakan coba lagi.")
            return jsonify({"success": False, "message": error_message}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Gagal terhubung ke server. Silakan coba lagi nanti. {e}"}), 500

@app.route('/laporan-apuppt')
def form_laporan_apuppt():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_apuppt.html")

@app.route('/laporan-rencana-edukasi-publik')
def form_laporan_rencana_edukasi_publik():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_rencana_edukasi_publik.html")

@app.route('/laporan-pelaksanaan-pengujian-keamanan')
def form_laporan_pelaksanaan_pengujian_keamanan():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_pelaksanaan_pengujian_keamanan.html")

@app.route('/laporan-pelaksanaan-edukasi-publik')
def form_laporan_pelaksanaan_edukasi_publik():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_pelaksanaan_edukasi_publik.html")

@app.route('/laporan-auditsi')
def form_laporan_auditsi():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_auditsi.html")

@app.route("/submit/laporan-auditsi", methods=["POST"])
def submit_laporan_auditsi():
    if "username" not in session:
        return redirect(url_for("login"))

    headers = {
        "Authorization": f"Bearer {session.get('access_token')}"
    }

    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d') # Format API
        formatted_tanggal_selesai = datetime.strptime(request.form.get("tanggal_selesai"), '%Y-%m-%d').strftime('%Y-%m-%d') # Format API
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat atau tanggal selesai tidak valid"}), 400

    # Mengumpulkan data temuan belum terselesaikan yang dinamis
    unresolved_findings_details = []
    i = 1
    while True:
        deskripsi_temuan_key = f"deskripsi_temuan_{i}"
        if deskripsi_temuan_key not in request.form:
            break # Berhenti jika tidak ada lagi temuan

        finding_item = {
            "deskripsi_temuan": request.form.get(deskripsi_temuan_key),
            "tindak_lanjut": request.form.get(f"tindak_lanjut_{i}")
        }
        unresolved_findings_details.append(finding_item)
        i += 1

    form_data = {
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "nama_penyelenggara": request.form.get("nama_penyelenggara"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "tanggal_selesai": formatted_tanggal_selesai,
        "nama_auditor": request.form.get("nama_auditor"),
        "confidentiality": int(request.form.get("confidentiality")),
        "integrity": int(request.form.get("integrity")),
        "availability": int(request.form.get("availability")),
        "authenticity": int(request.form.get("authenticity")),
        "non_repudiation": int(request.form.get("non_repudiation")),
        "ruang_lingkup": request.form.get("ruang_lingkup"),
        "metodologi": request.form.get("metodologi"),
        "jumlah_temuan": int(request.form.get("jumlah_temuan")),
        "jumlah_rekomendasi": int(request.form.get("jumlah_rekomendasi")), # Ini dari HTML sebelumnya
        "temuan_diselesaikan": int(request.form.get("temuan_diselesaikan")),
        "kesimpulan": request.form.get("kesimpulan"),
        "jumlah_temuan_belum_terselesaikan": int(request.form.get("jumlah_temuan_belum_terselesaikan")),
        "unresolved_findings_details": json.dumps(unresolved_findings_details), # Kirim sebagai JSON string
        "keterangan": request.form.get("keterangan")
    }

    files = {}
    file_laporan_audit = request.files.get("dokumen_laporan")
    if file_laporan_audit and file_laporan_audit.filename:
        files["file_laporan_audit"] = (file_laporan_audit.filename, file_laporan_audit.stream, file_laporan_audit.mimetype)
    
    dokumen_pendukung = request.files.get("dokumen_pendukung")
    if dokumen_pendukung and dokumen_pendukung.filename:
        files["dokumen_pendukung"] = (dokumen_pendukung.filename, dokumen_pendukung.stream, dokumen_pendukung.mimetype)

    try:
        response = requests.post(
            f"{API_BASE_URL}laporan/auditsi/submit",
            data=form_data,
            files=files,
            headers=headers
        )
        
        if response.status_code == 201:
            response_data = response.json()
            return jsonify({
                "success": True,
                "message": "Laporan Audit Sistem Informasi berhasil dikirim!",
                "data": response_data.get("data", {})
            }), 201
        else:
            error_data = response.json()
            error_message = error_data.get("message", "Gagal mengirim laporan Audit Sistem Informasi. Silakan coba lagi.")
            return jsonify({"success": False, "message": error_message}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Gagal terhubung ke server. Silakan coba lagi nanti. {e}"}), 500

# Rute submit untuk SKSP Triwulan
@app.route("/submit/standar-kompetensi-triwulan", methods=["POST"])
def submit_standar_kompetensi_triwulan():
    if "username" not in session:
        return redirect(url_for("login"))

    headers = {
        "Authorization": f"Bearer {session.get('access_token')}"
    }

    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d') # Format API
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        "tahun": int(request.form.get("tahun")),
        "periode": request.form.get("periode"),
        "penyelenggara": request.form.get("penyelenggara"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "jenis_pelaku": request.form.get("jenis_pelaku"),
        "tahap": request.form.get("tahap"),
        "sub_bidang": request.form.get("sub_bidang"),
        "pic": request.form.get("pic"),
        "total_pbk_lv4": int(request.form.get("total_pbk_lv4")),
        "total_pbk_lv5": int(request.form.get("total_pbk_lv5")),
        "total_pbk_lv6": int(request.form.get("total_pbk_lv6")),
        "total_sk_direksi": int(request.form.get("total_sk_direksi")),
    }

    # Mengumpulkan data tabel rencana PBK Pelaksana, Penyelia, Eksekutif
    for i in range(1, 5):
        form_data[f"rencana_pbk_pelaksana_{i}"] = int(request.form.get(f"rencana_pbk_pelaksana_{i}"))
        form_data[f"rencana_pbk_penyelia_{i}"] = int(request.form.get(f"rencana_pbk_penyelia_{i}"))
        form_data[f"rencana_pbk_eksekutif_{i}"] = int(request.form.get(f"rencana_pbk_eksekutif_{i}"))
        form_data[f"rencana_sk_direksi_{i}"] = int(request.form.get(f"rencana_sk_direksi_{i}"))
        form_data[f"pemeliharaan_sk_direksi_{i}"] = int(request.form.get(f"pemeliharaan_sk_direksi_{i}"))
        for level in [4, 5, 6]:
            form_data[f"pemeliharaan_pbk_lv{level}_{i}"] = int(request.form.get(f"pemeliharaan_pbk_lv{level}_{i}"))

    form_data["keterangan"] = request.form.get("keterangan")

    files = {}
    file = request.files.get("file_sertifikat_skps")
    if file and file.filename:
        files = {"file_sertifikat_skps": (file.filename, file.stream, file.mimetype)}
    
    try:
        response = requests.post(
            f"{API_BASE_URL}laporan/sksp-triwulan/submit",
            data=form_data,
            files=files,
            headers=headers
        )
        
        if response.status_code == 201:
            response_data = response.json()
            return jsonify({
                "success": True,
                "message": "Laporan SKSP Triwulan berhasil dikirim!",
                "data": response_data.get("data", {})
            }), 201
        else:
            error_data = response.json()
            error_message = error_data.get("message", "Gagal mengirim laporan SKSP Triwulan. Silakan coba lagi.")
            return jsonify({"success": False, "message": error_message}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Gagal terhubung ke server. Silakan coba lagi nanti. {e}"}), 500

# Rute submit untuk SKSP Tahunan
@app.route("/submit/standar-kompetensi-tahunan", methods=["POST"])
def submit_standar_kompetensi_tahunan():
    if "username" not in session:
        return redirect(url_for("login"))

    headers = {
        "Authorization": f"Bearer {session.get('access_token')}"
    }

    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d') # Format API
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400

    form_data = {
        "tahun": int(request.form.get("tahun")),
        "periode": request.form.get("periode"),
        "penyelenggara": request.form.get("penyelenggara"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "jenis_pelaku": request.form.get("jenis_pelaku"),
        "tahap": request.form.get("tahap"),
        "sub_bidang": request.form.get("sub_bidang"),
        "pic": request.form.get("pic"),
        "dana_pbk": int(request.form.get("dana_pbk").replace('.', '')),
        "dana_pemeliharaan_pbk": int(request.form.get("dana_pemeliharaan_pbk").replace('.', '')),
        "dana_sertifikasi": int(request.form.get("dana_sertifikasi").replace('.', '')),
        "dana_pemeliharaan_sertifikasi": int(request.form.get("dana_pemeliharaan_sertifikasi").replace('.', '')),
        "total_pbk_lv4": int(request.form.get("total_pbk_lv4")),
        "total_pbk_lv5": int(request.form.get("total_pbk_lv5")),
        "total_pbk_lv6": int(request.form.get("total_pbk_lv6")),
        "total_sk_direksi": int(request.form.get("total_sk_direksi")),
    }

    # Mengumpulkan data tabel rencana PBK Pelaksana, Penyelia, Eksekutif
    for i in range(1, 5):
        form_data[f"rencana_pbk_pelaksana_{i}"] = int(request.form.get(f"rencana_pbk_pelaksana_{i}"))
        form_data[f"rencana_pbk_penyelia_{i}"] = int(request.form.get(f"rencana_pbk_penyelia_{i}"))
        form_data[f"rencana_pbk_eksekutif_{i}"] = int(request.form.get(f"rencana_pbk_eksekutif_{i}"))
        form_data[f"rencana_sk_direksi_{i}"] = int(request.form.get(f"rencana_sk_direksi_{i}"))
        form_data[f"pemeliharaan_sk_direksi_{i}"] = int(request.form.get(f"pemeliharaan_sk_direksi_{i}"))
        for level in [4, 5, 6]:
            form_data[f"pemeliharaan_pbk_lv{level}_{i}"] = int(request.form.get(f"pemeliharaan_pbk_lv{level}_{i}"))

    form_data["keterangan"] = request.form.get("keterangan")

    files = {} 
    # Jika ada file upload untuk SKSP Tahunan, tambahkan di sini
    
    try:
        response = requests.post(
            f"{API_BASE_URL}laporan/sksp-tahunan/submit",
            data=form_data,
            files=files,
            headers=headers
        )
        
        if response.status_code == 201:
            response_data = response.json()
            return jsonify({
                "success": True,
                "message": "Laporan SKSP Tahunan berhasil dikirim!",
                "data": response_data.get("data", {})
            }), 201
        else:
            error_data = response.json()
            error_message = error_data.get("message", "Gagal mengirim laporan SKSP Tahunan. Silakan coba lagi.")
            return jsonify({"success": False, "message": error_message}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Gagal terhubung ke server. Silakan coba lagi nanti. {e}"}), 500

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
