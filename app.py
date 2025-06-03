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
        sandi_pjp = request.form["username"] 
        password = request.form["password"]
        login_data = {"sandi_pjp": sandi_pjp, "password": password}
        try:
            response = requests.post(f"{API_BASE_URL}auth/login/", json=login_data)
            response_data = response.json()
            if response.status_code == 200 and response_data.get("data") and response_data["data"].get("access"):
                session["username"] = sandi_pjp 
                session["access_token"] = response_data["data"]["access"] 
                if sandi_pjp == "admin": 
                    session["role"] = "admin"
                    return redirect(url_for("admin_dashboard"))
                else:
                    session["role"] = "user" 
                    return redirect(url_for("user_dashboard"))
            else:
                error_message = response_data.get("message", "Username atau password salah!")
                return render_template("login.html", error=error_message)
        except requests.exceptions.RequestException as e:
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

@app.route("/user/laporan")
def user_laporan():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/dashboarduser.html") 

@app.route("/admin/laporan")
def admin_laporan():
    if "username" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    return "Halaman Laporan Admin (Dalam Pengembangan)"

@app.route('/admin/history')
def admin_history():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template('admin/history.html')

@app.route('/admin/peraturan')
def admin_peraturan():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template('admin/peraturan.html')

@app.route("/base") 
def base_page():
    if session.get("role") != "admin": 
        return redirect(url_for("login"))
    return render_template("admin/base.html")

@app.route("/submit/laporan-fraud", methods=["POST"])
def submit_laporan_fraud():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
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
        print("Data Laporan Fraud Diterima:", form_data)
        if files:
            print("File Laporan Fraud Diterima:", files["file"][0])
        return jsonify({"success": True, "message": "Laporan Fraud (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500

@app.route("/form/laporan-fraud")
def form_laporan_fraud():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_fraud.html")

@app.route("/submit/laporan-dttot", methods=["POST"])
def submit_laporan_dttot():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d')
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
        "nomor_surat_kepolisian": request.form.get("nomor_surat_kepolisian"), 
        "organisasi_teroris": request.form.get("organisasi_teroris")
    }
    files = {}
    file = request.files.get("file_laporan")
    if file and file.filename:
        files = {"file": (file.filename, file.stream, file.mimetype)}
    try:
        print("Data Laporan DTTOT Diterima:", form_data)
        if files:
            print("File Laporan DTTOT Diterima:", files["file"][0])
        return jsonify({"success": True, "message": "Laporan DTTOT (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500
        
@app.route("/form/laporan-dttot")
def form_laporan_dttot():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_dttot.html")

@app.route("/form/laporan-keuangan-tahunan")
def form_laporan_keuangan_tahunan():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_keuangan_tahunan.html")

@app.route("/submit/laporan-keuangan-tahunan", methods=["POST"])
def submit_laporan_keuangan_tahunan():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d')
        formatted_tanggal_opini = None
        if request.form.get("tanggal_opini"):
            formatted_tanggal_opini = datetime.strptime(request.form.get("tanggal_opini"), '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal tidak valid"}), 400
    form_data = {
        "tahun": int(request.form.get("tahun")), "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat, "modal_disetor": int(request.form.get("modal_disetor").replace('.', '')),
        "jenis_audit": request.form.get("jenis_audit"), "kantor_akuntan": request.form.get("kantor_akuntan"),
        "tanggal_opini": formatted_tanggal_opini, "opini": request.form.get("opini"),
        "pendapatan": int(request.form.get("pendapatan").replace('.', '')), "beban_operasional": int(request.form.get("beban_operasional").replace('.', '')),
        "laba": int(request.form.get("laba").replace('.', '')), "rugi": int(request.form.get("rugi").replace('.', '')),
        "total_aset": int(request.form.get("total_aset").replace('.', '')), "total_liabilitas": int(request.form.get("total_liabilitas").replace('.', '')),
        "total_equitas": int(request.form.get("total_equitas").replace('.', ''))
    }
    files = {}
    file_laporan = request.files.get("file_laporan") 
    if file_laporan and file_laporan.filename:
        files["file_laporan"] = (file_laporan.filename, file_laporan.stream, file_laporan.mimetype)
    try:
        print("Data Laporan Keuangan Tahunan Diterima:", form_data)
        if files:
            print("File Laporan Keuangan Tahunan Diterima:", files["file_laporan"][0])
        return jsonify({"success": True, "message": "Laporan Keuangan Tahunan (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500

@app.route("/form/laporan-keuangan-triwulan")
def form_laporan_keuangan_triwulan():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_keuangan_triwulan.html")

@app.route("/submit/laporan-keuangan-triwulan", methods=["POST"])
def submit_laporan_keuangan_triwulan():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400
    form_data = {
        "tahun": int(request.form.get("tahun")), "triwulan": request.form.get("triwulan"),
        "penyelenggara": request.form.get("penyelenggara"), "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat, "modal_disetor": int(request.form.get("modal_disetor").replace('.', '')),
        "pendapatan": int(request.form.get("pendapatan").replace('.', '')), "beban_operasional": int(request.form.get("beban_operasional").replace('.', '')),
        "laba": int(request.form.get("laba").replace('.', '')), "rugi": int(request.form.get("rugi").replace('.', '')),
        "total_aset": int(request.form.get("total_aset").replace('.', '')), "total_liabilitas": int(request.form.get("total_liabilitas").replace('.', '')),
        "total_equitas": int(request.form.get("equity").replace('.', '')) 
    }
    files = {}
    file_laporan = request.files.get("file_laporan") 
    if file_laporan and file_laporan.filename:
        files["file_laporan"] = (file_laporan.filename, file_laporan.stream, file_laporan.mimetype)
    try:
        print("Data Laporan Keuangan Triwulan Diterima:", form_data)
        if files:
            print("File Laporan Keuangan Triwulan Diterima:", files["file_laporan"][0])
        return jsonify({"success": True, "message": "Laporan Keuangan Triwulan (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500

@app.route('/form/laporan-manajemen') 
def form_laporan_manajemen():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    current_year = datetime.now().year
    return render_template("user/forms/laporan_manajemen.html", current_year=current_year)

@app.route("/submit/laporan-manajemen", methods=["POST"])
def submit_laporan_manajemen():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d') 
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid."}), 400
    nama_komisaris_list = request.form.getlist("nama_komisaris[]")
    keterangan_komisaris_list = request.form.getlist("keterangan_komisaris[]")
    komisaris_data = []
    for i in range(len(nama_komisaris_list)):
        komisaris_data.append({"nama": nama_komisaris_list[i], "keterangan": keterangan_komisaris_list[i]})
    nama_direksi_list = request.form.getlist("nama_direksi[]")
    keterangan_direksi_list = request.form.getlist("keterangan_direksi[]")
    direksi_data = []
    for i in range(len(nama_direksi_list)):
        direksi_data.append({"nama": nama_direksi_list[i], "keterangan": keterangan_direksi_list[i]})
    form_data = {
        "tahun_laporan": request.form.get("tahun"), "nama_penyelenggara": request.form.get("penyelenggara"),
        "nomor_surat": request.form.get("nomor_surat"), "tanggal_surat": formatted_tanggal_surat,
        "jumlah_komisaris": int(request.form.get("jumlah_komisaris", 0)), "detail_komisaris": json.dumps(komisaris_data), 
        "jumlah_direksi": int(request.form.get("jumlah_direksi", 0)), "detail_direksi": json.dumps(direksi_data), 
        "persentase_kepemilikan_domestik": float(request.form.get("kepemilikan_domestik", 0)),
        "persentase_kepemilikan_asing": float(request.form.get("kepemilikan_asing", 0)),
        "ringkasan_laporan_manajemen": request.form.get("ringkasan"), "keterangan_tambahan": request.form.get("keterangan"),
    }
    files = {}
    file_laporan_manajemen = request.files.get("file_laporan")
    if file_laporan_manajemen and file_laporan_manajemen.filename:
        files["file_laporan_manajemen"] = (file_laporan_manajemen.filename, file_laporan_manajemen.stream, file_laporan_manajemen.mimetype)
    try:
        print("Data Laporan Manajemen Diterima:", form_data)
        if files:
            print("File Laporan Manajemen Diterima:", files["file_laporan_manajemen"][0])
        return jsonify({"success": True, "message": "Laporan Manajemen (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500

@app.route('/form/laporan-sksp-triwulan')
def form_laporan_sksp_triwulan():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_sksp_triwulan.html")

@app.route('/form/laporan-sksp-tahunan')
def form_laporan_sksp_tahunan():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_sksp_tahunan.html", now=datetime.now())

@app.route("/submit/laporan-gangguanit", methods=["POST"]) 
def submit_laporan_gangguanit():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400
    gangguan_details = []
    i = 1
    while True:
        waktu_kejadian_key = f"waktu_kejadian_{i}"
        if waktu_kejadian_key not in request.form:
            break
        try:
            waktu_kejadian_dt = datetime.strptime(request.form.get(waktu_kejadian_key), '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d %H:%M:%S')
            tanggal_penyelesaian_dt = None
            if request.form.get(f"tanggal_penyelesaian_{i}"):
                tanggal_penyelesaian_dt = datetime.strptime(request.form.get(f"tanggal_penyelesaian_{i}"), '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            return jsonify({"success": False, "message": f"Format waktu kejadian atau tanggal penyelesaian tidak valid untuk gangguan ke-{i}"}), 400
        gangguan_item = {
            "waktu_kejadian": waktu_kejadian_dt, "jenis_gangguan": request.form.get(f"jenis_gangguan_{i}"),
            "ringkasan_gangguan": request.form.get(f"ringkasan_{i}"), "upaya_perbaikan": request.form.get(f"upaya_perbaikan_{i}"),
            "status_penyelesaian": request.form.get(f"status_penyelesaian_{i}"), "tanggal_penyelesaian": tanggal_penyelesaian_dt
        }
        gangguan_details.append(gangguan_item)
        i += 1
    form_data = {
        "tahun_laporan": int(request.form.get("tahun")), "periode_laporan": request.form.get("periode"), 
        "nomor_surat": request.form.get("nomor_surat"), "tanggal_surat": formatted_tanggal_surat,
        "detail_gangguan": json.dumps(gangguan_details) 
    }
    files = {}
    file = request.files.get("lampiran")
    if file and file.filename:
        files = {"file_lampiran": (file.filename, file.stream, file.mimetype)} 
    try:
        print("Data Laporan Gangguan IT Diterima:", form_data)
        if files:
            print("File Lampiran Gangguan IT Diterima:", files["file_lampiran"][0])
        return jsonify({"success": True, "message": "Laporan Gangguan IT (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500

@app.route('/form/laporan-gangguanit') 
def form_laporan_gangguanit():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_gangguanit.html")

@app.route('/form/laporan-dana-bukan-bank') 
def form_laporan_dana_bukan_bank():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_dana_bukan_bank.html")

@app.route("/submit/laporan-transaksi-dana", methods=["POST"]) 
def submit_laporan_dana_bukan_bank():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400
    form_data = {
        "tahun_laporan": int(request.form.get("tahun")), "periode_laporan": request.form.get("periode"), 
        "nomor_surat": request.form.get("nomor_surat"), "tanggal_surat": formatted_tanggal_surat,
        "number_outgoing_transactions": int(request.form.get("jumlah_keluar")),
        "amount_outgoing_transactions": int(request.form.get("nilai_keluar").replace('.', '')),
        "number_incoming_transactions": int(request.form.get("jumlah_masuk")),
        "amount_incoming_transactions": int(request.form.get("nilai_masuk").replace('.', '')),
        "number_local_transactions": int(request.form.get("jumlah_dalam")),
        "amount_local_transactions": int(request.form.get("nilai_dalam").replace('.', '')),
        "keterangan": request.form.get("keterangan")
    }
    files = {}
    file_bukti = request.files.get("bukti_lkpbu") 
    if file_bukti and file_bukti.filename:
        files = {"file_bukti_penyampaian_ltdbb": (file_bukti.filename, file_bukti.stream, file_bukti.mimetype)} 
    try:
        print("Data Laporan LTDBB Diterima:", form_data)
        if files:
            print("File Bukti LTDBB Diterima:", files["file_bukti_penyampaian_ltdbb"][0])
        return jsonify({"success": True, "message": "Laporan LTDBB (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500

@app.route('/form/laporan-p2p') 
def form_laporan_p2p():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_p2p.html")

@app.route("/submit/laporan-p2p", methods=["POST"]) 
def submit_laporan_p2p():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400
    companies = []
    nama_perusahaan_list = request.form.getlist("nama_perusahaan[]")
    peran_pjp_list = request.form.getlist("peran_pjp[]")
    tanggal_kerjasama_list = request.form.getlist("tanggal_kerjasama[]")
    keterangan_list = request.form.getlist("keterangan[]")
    for i in range(len(nama_perusahaan_list)):
        try:
            formatted_tgl_kerjasama = datetime.strptime(tanggal_kerjasama_list[i], '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
             return jsonify({"success": False, "message": f"Format tanggal kerjasama tidak valid untuk perusahaan ke-{i+1}"}), 400
        companies.append({
            "nama_perusahaan": nama_perusahaan_list[i], "peran_pjp": peran_pjp_list[i],
            "tanggal_kerjasama": formatted_tgl_kerjasama, "keterangan": keterangan_list[i] if i < len(keterangan_list) else "" 
        })
    form_data = {
        "nomor_surat": request.form.get("nomor_surat"), "tanggal_surat": formatted_tanggal_surat,
        "tahun_laporan": int(request.form.get("tahun")), "periode_laporan": request.form.get("periode"), 
        "jumlah_perusahaan_kerjasama": int(request.form.get("jumlah_perusahaan")), 
        "detail_kerjasama": json.dumps(companies), 
        "keterangan_umum": request.form.get("keterangan_umum")
    }
    files = {}
    file_dokumen = request.files.get("dokumen_kerjasama") 
    if file_dokumen and file_dokumen.filename:
        files = {"file_dokumen_kerjasama": (file_dokumen.filename, file_dokumen.stream, file_dokumen.mimetype)} 
    try:
        print("Data Laporan P2P Diterima:", form_data)
        if files:
            print("File Dokumen Kerjasama P2P Diterima:", files["file_dokumen_kerjasama"][0])
        return jsonify({"success": True, "message": "Laporan Kerjasama P2P (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500

@app.route("/submit/laporan-pppk", methods=["POST"]) 
def submit_laporan_pppk():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400
    form_data = {
        "tahun": int(request.form.get("tahun")), "triwulan": request.form.get("triwulan"), 
        "penyelenggara": request.form.get("penyelenggara"), "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat, "jumlah_pengaduan": int(request.form.get("jumlah_pengaduan").replace('.', '')),
        "pengaduan_diselesaikan": int(request.form.get("pengaduan_diselesaikan").replace('.', '')),
        "pengaduan_belum_diselesaikan": int(request.form.get("pengaduan_belum_diselesaikan").replace('.', '')),
        "total_nilai_pengaduan": int(request.form.get("total_nilai_pengaduan").replace('.', '')),
        "persentase_pengaduan": float(request.form.get("persentase_pengaduan")),
        "diteruskan_bi": int(request.form.get("diteruskan_bi").replace('.', '')), 
        "diteruskan_ojk": int(request.form.get("diteruskan_ojk").replace('.', '')),
        "diteruskan_laps_sjk": int(request.form.get("diteruskan_laps_sjk").replace('.', '')), 
        "diteruskan_pengadilan": int(request.form.get("diteruskan_pengadilan").replace('.', '')),
        "diteruskan_arbitrase": int(request.form.get("diteruskan_arbitrase").replace('.', '')), 
        "diselesaikan_lainnya": int(request.form.get("diselesaikan_lainnya").replace('.', '')),
        "keterangan": request.form.get("keterangan")
    }
    files = {}
    file_bukti = request.files.get("bukti_upload") 
    if file_bukti and file_bukti.filename:
        files = {"file_bukti_upload": (file_bukti.filename, file_bukti.stream, file_bukti.mimetype)} 
    try:
        print("Data Laporan PPPK Diterima:", form_data)
        if files:
            print("File Bukti PPPK Diterima:", files["file_bukti_upload"][0])
        return jsonify({"success": True, "message": "Laporan PPPK (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500

@app.route('/form/laporan-pppk') 
def form_laporan_pppk():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_pppk.html")

@app.route('/form/laporan-apuppt') 
def form_laporan_apuppt():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    current_year = datetime.now().year
    years = range(current_year - 5, current_year + 2) 
    return render_template("user/forms/laporan_apuppt.html", years=years)

@app.route("/submit/laporan-apuppt", methods=["POST"])
def submit_laporan_apuppt():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d') 
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400
    triwulan_1 = True if request.form.get("triwulan_1") == "true" else False
    triwulan_2 = True if request.form.get("triwulan_2") == "true" else False
    triwulan_3 = True if request.form.get("triwulan_3") == "true" else False
    triwulan_4 = True if request.form.get("triwulan_4") == "true" else False
    dttot_reported = True if request.form.get("dttot_reported") == "true" else False
    dppspm_reported = True if request.form.get("dppspm_reported") == "true" else False
    form_data = {
        "tahun_laporan": int(request.form.get("tahun_laporan")), "nama_penyelenggara": request.form.get("nama_penyelenggara"),
        "nomor_surat": request.form.get("nomor_surat"), "tanggal_surat": formatted_tanggal_surat,
        "nama_petugas_apu_ppt": request.form.get("nama_petugas"), "sk_penunjukkan_apu_ppt": request.form.get("sk_penunjukkan"), 
        "user_id_goaml": request.form.get("user_id_goaml"), "user_id_sipesat": request.form.get("user_id_sipesat"),
        "user_id_pep": request.form.get("user_id_pep"), "user_id_sipendar": request.form.get("user_id_sipendar"),
        "jumlah_ltkt": int(request.form.get("jumlah_ltkt")), "jumlah_ltkm": int(request.form.get("jumlah_ltkm")),
        "jumlah_ltkl": int(request.form.get("jumlah_ltkl")), "laporan_sipesat_q1": triwulan_1, 
        "laporan_sipesat_q2": triwulan_2, "laporan_sipesat_q3": triwulan_3, "laporan_sipesat_q4": triwulan_4,
        "dttot_dilaporkan": dttot_reported, "dppspm_dilaporkan": dppspm_reported, 
        "tanggung_jawab_direksi_dewan_komisaris": request.form.get("tanggung_jawab_direksi"),
        "kebijakan_prosedur_tertulis": request.form.get("kebijakan_prosedur"), "metode_pelaksanaan_pmpj": request.form.get("metode_pmpj"),
        "proses_manajemen_risiko": request.form.get("manajemen_risiko"), "manajemen_sdm_apu_ppt": request.form.get("manajemen_sdm"), 
        "sistem_pengendalian_intern_apu_ppt": request.form.get("sistem_pengendalian"), 
        "nama_penginput_data": request.form.get("nama_penginput"), "email_penginput_data": request.form.get("email_penginput"),
        "email_perusahaan_apu_ppt": request.form.get("email_perusahaan"), "nomor_hp_penginput": request.form.get("nomor_hp"),
    }
    files = {}
    dokumen_laporan_apu_ppt = request.files.get("dokumen_laporan")
    if dokumen_laporan_apu_ppt and dokumen_laporan_apu_ppt.filename:
        files["file_laporan_tahunan_apu_ppt"] = (dokumen_laporan_apu_ppt.filename, dokumen_laporan_apu_ppt.stream, dokumen_laporan_apu_ppt.mimetype)
    api_endpoint_apu_ppt = f"{API_BASE_URL}laporan/apu-ppt/submit" 
    try:
        print("Data Laporan APU PPT Diterima:", form_data)
        if files:
            print("File Laporan APU PPT Diterima:", files["file_laporan_tahunan_apu_ppt"][0])
        return jsonify({"success": True, "message": "Laporan APU PPT (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500

@app.route('/form/laporan-rencana-edukasi-publik') 
def form_laporan_rencana_edukasi_publik():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_rencana_edukasi_publik.html")

# +++++ AWAL PENAMBAHAN ROUTE SUBMIT UNTUK LAPORAN RENCANA EDUKASI PUBLIK (SIMULASI) +++++
@app.route("/submit/laporan-rencana-edukasi-publik", methods=["POST"])
def submit_laporan_rencana_edukasi_publik():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid."}), 400

    form_data = {
        "tahun_laporan": request.form.get("tahun_laporan"),
        "nama_penyelenggara": request.form.get("nama_penyelenggara"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "provinsi": request.form.get("provinsi"),
        "total_aset_tahun_lalu": request.form.get("total_aset_tahun_lalu"),
        "total_aset_tahun_ini": request.form.get("total_aset_tahun_ini"),
        "total_aset_tahun_depan": request.form.get("total_aset_tahun_depan"),
        "pendapatan_tahun_lalu": request.form.get("pendapatan_tahun_lalu"),
        "pendapatan_tahun_ini": request.form.get("pendapatan_tahun_ini"),
        "target_pendapatan_tahun_depan": request.form.get("target_pendapatan_tahun_depan"),
        "biaya_tahun_lalu": request.form.get("biaya_tahun_lalu"),
        "biaya_tahun_ini": request.form.get("biaya_tahun_ini"),
        "target_biaya_tahun_depan": request.form.get("target_biaya_tahun_depan"),
        "jumlah_konsumen_tahun_depan": request.form.get("jumlah_konsumen_tahun_depan"),
        "faktor_operasional": request.form.get("faktor_operasional"),
        "sasaran_edukasi": request.form.get("sasaran_edukasi"),
        "target_jumlah_peserta": request.form.get("target_jumlah_peserta"),
        "materi_edukasi": request.form.get("materi_edukasi"),
        "kanal_edukasi": request.form.get("kanal_edukasi"),
        "media_edukasi": request.form.get("media_edukasi"),
        "jumlah_kegiatan": request.form.get("jumlah_kegiatan"),
        "catatan_tambahan": request.form.get("catatan_tambahan"),
    }
    files = {}
    dokumen_rencana = request.files.get("dokumen_rencana")
    if dokumen_rencana and dokumen_rencana.filename:
        files["dokumen_rencana_edukasi"] = (dokumen_rencana.filename, dokumen_rencana.stream, dokumen_rencana.mimetype)

    try:
        print("Data Laporan Rencana Edukasi Publik Diterima:", form_data)
        if files:
            print("File Dokumen Rencana Edukasi Publik Diterima:", files["dokumen_rencana_edukasi"][0])
        return jsonify({"success": True, "message": "Laporan Rencana Edukasi Publik (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500
# +++++ AKHIR PENAMBAHAN ROUTE SUBMIT UNTUK LAPORAN RENCANA EDUKASI PUBLIK (SIMULASI) +++++


@app.route('/form/laporan-pelaksanaan-pengujian-keamanan') 
def form_laporan_pelaksanaan_pengujian_keamanan():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_pelaksanaan_pengujian_keamanan.html")

# +++++ AWAL PENAMBAHAN ROUTE SUBMIT UNTUK LAPORAN PELAKSANAAN PENGUJIAN KEAMANAN (SIMULASI) +++++
@app.route("/submit/laporan-pelaksanaan-pengujian-keamanan", methods=["POST"])
def submit_laporan_pelaksanaan_pengujian_keamanan():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d')
        formatted_tanggal_selesai_audit = datetime.strptime(request.form.get("tanggal_selesai_audit"), '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal tidak valid."}), 400

    form_data = {
        "tahun_laporan": request.form.get("tahun_laporan"),
        "triwulan_laporan": request.form.get("triwulan_laporan"),
        "nama_penyelenggara": request.form.get("nama_penyelenggara"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "tanggal_selesai_audit": formatted_tanggal_selesai_audit,
        "temuan_low": int(request.form.get("temuan_low", 0)),
        "temuan_medium": int(request.form.get("temuan_medium", 0)),
        "temuan_high": int(request.form.get("temuan_high", 0)),
        "temuan_critical": int(request.form.get("temuan_critical", 0)),
        "jumlah_temuan": int(request.form.get("jumlah_temuan", 0)), # Ini dihitung otomatis di frontend
        "jumlah_temuan_diselesaikan": int(request.form.get("jumlah_temuan_diselesaikan", 0)),
        "kesimpulan_auditor": request.form.get("kesimpulan_auditor"),
    }
    files = {}
    dokumen_laporan = request.files.get("dokumen_laporan")
    if dokumen_laporan and dokumen_laporan.filename:
        files["dokumen_laporan_pengujian"] = (dokumen_laporan.filename, dokumen_laporan.stream, dokumen_laporan.mimetype)

    try:
        print("Data Laporan Pelaksanaan Pengujian Keamanan Diterima:", form_data)
        if files:
            print("File Dokumen Laporan Pengujian Keamanan Diterima:", files["dokumen_laporan_pengujian"][0])
        return jsonify({"success": True, "message": "Laporan Pelaksanaan Pengujian Keamanan (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500
# +++++ AKHIR PENAMBAHAN ROUTE SUBMIT UNTUK LAPORAN PELAKSANAAN PENGUJIAN KEAMANAN (SIMULASI) +++++


@app.route('/form/laporan-pelaksanaan-edukasi-publik') 
def form_laporan_pelaksanaan_edukasi_publik():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_pelaksanaan_edukasi_publik.html")

# +++++ AWAL PENAMBAHAN ROUTE SUBMIT UNTUK LAPORAN PELAKSANAAN EDUKASI PUBLIK (SIMULASI) +++++
@app.route("/submit/laporan-pelaksanaan-edukasi-publik", methods=["POST"]) # Nama route disesuaikan dengan HTML
def submit_laporan_pelaksanaan_edukasi_publik():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid."}), 400

    form_data = {
        "tahun_laporan": request.form.get("tahun_laporan"),
        "nama_penyelenggara": request.form.get("nama_penyelenggara"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "bentuk_aktivitas": request.form.get("bentuk_aktivitas"),
        "provinsi": request.form.get("provinsi"),
        "sasaran_edukasi": request.form.get("sasaran_edukasi"),
        "jumlah_peserta": int(request.form.get("jumlah_peserta", 0)),
        "materi_edukasi": request.form.get("materi_edukasi"),
        "frekuensi": int(request.form.get("frekuensi", 0)),
        "kanal_edukasi": request.form.get("kanal_edukasi"),
        "evaluasi": request.form.get("evaluasi"),
        "kendala": request.form.get("kendala"),
    }
    files = {}
    dokumen_laporan = request.files.get("dokumen_laporan")
    if dokumen_laporan and dokumen_laporan.filename:
        files["dokumen_laporan_kegiatan"] = (dokumen_laporan.filename, dokumen_laporan.stream, dokumen_laporan.mimetype)
    
    dokumen_pendukung = request.files.get("dokumen_pendukung")
    if dokumen_pendukung and dokumen_pendukung.filename:
        files["dokumen_pendukung_edukasi"] = (dokumen_pendukung.filename, dokumen_pendukung.stream, dokumen_pendukung.mimetype)

    try:
        print("Data Laporan Pelaksanaan Edukasi Publik Diterima:", form_data)
        if files:
            print("File-file Laporan Pelaksanaan Edukasi Publik Diterima:", files)
        return jsonify({"success": True, "message": "Laporan Pelaksanaan Edukasi Publik (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500
# +++++ AKHIR PENAMBAHAN ROUTE SUBMIT UNTUK LAPORAN PELAKSANAAN EDUKASI PUBLIK (SIMULASI) +++++


@app.route('/form/laporan-auditsi') 
def form_laporan_auditsi():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_auditsi.html")

@app.route("/submit/laporan-auditsi", methods=["POST"]) 
def submit_laporan_auditsi():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d')
        formatted_tanggal_selesai = datetime.strptime(request.form.get("tanggal_selesai"), '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat atau tanggal selesai tidak valid"}), 400
    unresolved_findings_details = []
    i = 0 
    while True:
        deskripsi_temuan_key = f"deskripsi_temuan_{i}" 
        tindak_lanjut_key = f"tindak_lanjut_{i}"
        if deskripsi_temuan_key not in request.form and tindak_lanjut_key not in request.form : 
            break 
        finding_item = {
            "deskripsi_temuan": request.form.get(deskripsi_temuan_key, ""), 
            "tindak_lanjut": request.form.get(tindak_lanjut_key, "")
        }
        if finding_item["deskripsi_temuan"] or finding_item["tindak_lanjut"]:
             unresolved_findings_details.append(finding_item)
        i += 1
    jumlah_temuan_belum_val = request.form.get("jumlah_temuan_belum_terselesaikan")
    try:
        jumlah_temuan_belum_int = int(jumlah_temuan_belum_val) if jumlah_temuan_belum_val is not None and jumlah_temuan_belum_val.strip() != "" else 0
    except ValueError:
        jumlah_temuan_belum_int = 0 
    form_data = {
        "tahun_laporan": int(request.form.get("tahun_laporan")), "nama_penyelenggara": request.form.get("nama_penyelenggara"),
        "nomor_surat": request.form.get("nomor_surat"), "tanggal_surat": formatted_tanggal_surat,
        "tanggal_selesai": formatted_tanggal_selesai, "nama_auditor": request.form.get("nama_auditor"),
        "confidentiality": int(request.form.get("confidentiality")), "integrity": int(request.form.get("integrity")),
        "availability": int(request.form.get("availability")), "authenticity": int(request.form.get("authenticity")),
        "non_repudiation": int(request.form.get("non_repudiation")), "jumlah_temuan": int(request.form.get("jumlah_temuan")),
        "temuan_diselesaikan": int(request.form.get("temuan_diselesaikan")), "kesimpulan": request.form.get("kesimpulan"),
        "jumlah_temuan_belum_terselesaikan": jumlah_temuan_belum_int, 
        "unresolved_findings_details": json.dumps(unresolved_findings_details), 
    }
    files = {}
    file_laporan_audit = request.files.get("dokumen_laporan") 
    if file_laporan_audit and file_laporan_audit.filename:
        files["file_laporan_audit"] = (file_laporan_audit.filename, file_laporan_audit.stream, file_laporan_audit.mimetype) 
    dokumen_pendukung = request.files.get("dokumen_pendukung") 
    if dokumen_pendukung and dokumen_pendukung.filename:
        files["dokumen_pendukung"] = (dokumen_pendukung.filename, dokumen_pendukung.stream, dokumen_pendukung.mimetype)
    try:
        print("Data Laporan Audit SI Diterima:", form_data)
        if files:
            print("File Laporan Audit SI Diterima:", files)
        return jsonify({"success": True, "message": "Laporan Audit SI (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500

@app.route("/submit/standar-kompetensi-triwulan", methods=["POST"]) 
def submit_standar_kompetensi_triwulan():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400
    form_data = {
        "tahun": int(request.form.get("tahun")), "periode": request.form.get("periode"), 
        "penyelenggara": request.form.get("penyelenggara"), "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat, "jenis_pelaku": request.form.get("jenis_pelaku"), 
        "tahap": request.form.get("tahap"), "sub_bidang": request.form.get("sub_bidang"), 
        "pic": request.form.get("pic"), "total_pbk_lv4": int(request.form.get("total_pbk_lv4")),
        "total_pbk_lv5": int(request.form.get("total_pbk_lv5")), "total_pbk_lv6": int(request.form.get("total_pbk_lv6")),
        "total_sk_direksi": int(request.form.get("total_sk_direksi")),
    }
    for i in range(1, 5): 
        form_data[f"rencana_pbk_pelaksana_q{i}"] = int(request.form.get(f"rencana_pbk_pelaksana_{i}"))
        form_data[f"rencana_pbk_penyelia_q{i}"] = int(request.form.get(f"rencana_pbk_penyelia_{i}"))
        form_data[f"rencana_pbk_eksekutif_q{i}"] = int(request.form.get(f"rencana_pbk_eksekutif_{i}"))
        form_data[f"rencana_sk_direksi_q{i}"] = int(request.form.get(f"rencana_sk_direksi_{i}"))
        form_data[f"pemeliharaan_sk_direksi_q{i}"] = int(request.form.get(f"pemeliharaan_sk_direksi_{i}"))
        for level in [4, 5, 6]:
            form_data[f"pemeliharaan_pbk_lv{level}_q{i}"] = int(request.form.get(f"pemeliharaan_pbk_lv{level}_{i}"))
    form_data["keterangan"] = request.form.get("keterangan")
    files = {}
    file_sertifikat = request.files.get("file_sertifikat_skps") 
    if file_sertifikat and file_sertifikat.filename:
        files["file_sertifikat_skps"] = (file_sertifikat.filename, file_sertifikat.stream, file_sertifikat.mimetype) 
    try:
        print("Data Laporan SKSP Triwulan Diterima:", form_data)
        if files:
            print("File Sertifikat SKSP Diterima:", files["file_sertifikat_skps"][0])
        return jsonify({"success": True, "message": "Laporan SKSP Triwulan (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500

@app.route("/submit/standar-kompetensi-tahunan", methods=["POST"]) 
def submit_standar_kompetensi_tahunan():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400
    form_data = {
        "tahun": int(request.form.get("tahun")), "periode": request.form.get("periode"), 
        "penyelenggara": request.form.get("penyelenggara"), "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat, "jenis_pelaku": request.form.get("jenis_pelaku"),
        "tahap": request.form.get("tahap"), "sub_bidang": request.form.get("sub_bidang"),
        "pic": request.form.get("pic"), "dana_pbk": int(request.form.get("dana_pbk").replace('.', '')),
        "dana_pemeliharaan_pbk": int(request.form.get("dana_pemeliharaan_pbk").replace('.', '')),
        "dana_sertifikasi": int(request.form.get("dana_sertifikasi").replace('.', '')),
        "dana_pemeliharaan_sertifikasi": int(request.form.get("dana_pemeliharaan_sertifikasi").replace('.', '')),
        "total_pbk_lv4": int(request.form.get("total_pbk_lv4")), "total_pbk_lv5": int(request.form.get("total_pbk_lv5")),
        "total_pbk_lv6": int(request.form.get("total_pbk_lv6")), "total_sk_direksi": int(request.form.get("total_sk_direksi")),
    }
    for i in range(1, 5): 
        form_data[f"rencana_pbk_pelaksana_q{i}"] = int(request.form.get(f"rencana_pbk_pelaksana_{i}"))
        form_data[f"rencana_pbk_penyelia_q{i}"] = int(request.form.get(f"rencana_pbk_penyelia_{i}"))
        form_data[f"rencana_pbk_eksekutif_q{i}"] = int(request.form.get(f"rencana_pbk_eksekutif_{i}"))
        form_data[f"rencana_sk_direksi_q{i}"] = int(request.form.get(f"rencana_sk_direksi_{i}"))
        form_data[f"pemeliharaan_sk_direksi_q{i}"] = int(request.form.get(f"pemeliharaan_sk_direksi_{i}"))
        for level in [4, 5, 6]:
            form_data[f"pemeliharaan_pbk_lv{level}_q{i}"] = int(request.form.get(f"pemeliharaan_pbk_lv{level}_{i}"))
    form_data["keterangan"] = request.form.get("keterangan")
    files = {} 
    try:
        print("Data Laporan SKSP Tahunan Diterima:", form_data)
        return jsonify({"success": True, "message": "Laporan SKSP Tahunan (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500

@app.route("/form/laporan-kpsp")
def form_laporan_kpsp():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_kpsp.html")

@app.route("/submit/laporan-kpsp", methods=["POST"])
def submit_laporan_kpsp():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    form_data_kpsp = {}
    for key, value in request.form.items():
        # Membersihkan nilai numerik dari format maskMoney (Rp. xxx.xxx)
        if "maskMoney" in key or "jumlah" in key or "modal" in key or "trx" in key or "danaFloat" in key or "saldo" in key or "aset" in key or "penyertaan" in key or "pembelian" in key or "penempatan" in key or "instrumen" in key or "premium" in key:
            cleaned_value = value.replace('Rp', '').replace('.', '').replace(',', '').strip()
            try:
                form_data_kpsp[key] = int(cleaned_value) if cleaned_value else 0
            except ValueError:
                form_data_kpsp[key] = cleaned_value # Simpan sebagai string jika tidak bisa di-parse
        else:
            form_data_kpsp[key] = value
    
    # Khusus untuk checkbox, pastikan nilainya boolean atau sesuai ekspektasi API
    form_data_kpsp["klp_aktivitasPIP"] = True if request.form.get("klp_aktivitasPIP") == "PIP" else False
    form_data_kpsp["klp_aktivitasAIS"] = True if request.form.get("klp_aktivitasAIS") == "AIS" else False
    form_data_kpsp["klp_aktivitasPIAS"] = True if request.form.get("klp_aktivitasPIAS") == "PIAS" else False
    form_data_kpsp["klp_aktivitasREM1"] = True if request.form.get("klp_aktivitasREM1") == "REM1" else False
    form_data_kpsp["klp_aktivitasREM2"] = True if request.form.get("klp_aktivitasREM2") == "REM2" else False
    form_data_kpsp["flag_gl_pip_asing"] = True if request.form.get("flag_gl_pip_asing") == "true" else False


    # Tidak ada file upload di form KPSP yang asli, jadi 'files' bisa dikosongkan
    files = {}
    print("Data Laporan KPSP (Simulasi) Diterima:", json.dumps(form_data_kpsp, indent=2))
    return jsonify({"success": True, "message": "Data KPSP (Simulasi) berhasil diterima!"}), 201

@app.route("/form/laporan-tahunan-sp")
def form_laporan_tahunan_sp():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_tahunan_sp.html")

@app.route("/submit/laporan-tahunan-sp", methods=["POST"])
def submit_laporan_tahunan_sp():
    if "username" not in session:
        return jsonify({"success": False, "message": "Sesi tidak valid, silakan login kembali."}), 401
    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    form_data = {
        "tahun_laporan": request.form.get("tahun_laporan"), "nama_pjp_pip_laporan": request.form.get("nama_pjp_pip_laporan"),
        "nomor_surat_pengantar": request.form.get("nomor_surat_pengantar"), "tanggal_surat_pengantar": request.form.get("tanggal_surat_pengantar"),
        "nama_pejabat_penandatangan": request.form.get("nama_pejabat_penandatangan"), "jabatan_pejabat_penandatangan": request.form.get("jabatan_pejabat_penandatangan"),
        "email_pic": request.form.get("email_pic"), "telepon_pic": request.form.get("telepon_pic"),
        "executive_summary": request.form.get("executive_summary"), "perizinan_penjelasan": request.form.get("perizinan_penjelasan"),
        "perizinan_kategori_izin": request.form.get("perizinan_kategori_izin"), "perizinan_klasifikasi": request.form.get("perizinan_klasifikasi"),
        "kepemilikan_penjelasan": request.form.get("kepemilikan_penjelasan"), "kepengurusan_penjelasan": request.form.get("kepengurusan_penjelasan"),
        "jaringan_usaha_penjelasan": request.form.get("jaringan_usaha_penjelasan"), "jaringan_jumlah_total": request.form.get("jaringan_jumlah_total"),
        "realisasi_produk_aktivitas_pengembangan_sp": request.form.get("realisasi_produk_aktivitas_pengembangan_sp"),
        "realisasi_kerjasama_sp": request.form.get("realisasi_kerjasama_sp"), "kinerja_keuangan_penjelasan": request.form.get("kinerja_keuangan_penjelasan"),
        "proyeksi_visi_misi_strategi": request.form.get("proyeksi_visi_misi_strategi"), "proyeksi_swot": request.form.get("proyeksi_swot"),
        "proyeksi_langkah_strategis": request.form.get("proyeksi_langkah_strategis"), "proyeksi_rencana_mrsi": request.form.get("proyeksi_rencana_mrsi"),
        "proyeksi_permodalan_kecukupan": request.form.get("proyeksi_permodalan_kecukupan"),
        "proyeksi_permodalan_aksi_korporasi": request.form.get("proyeksi_permodalan_aksi_korporasi"),
        "proyeksi_kinerja_keuangan_penjelasan": request.form.get("proyeksi_kinerja_keuangan_penjelasan"),
        "proyeksi_target_nasabah_pengguna": request.form.get("proyeksi_target_nasabah_pengguna"),
        "proyeksi_pengembangan_jaringan_kantor": request.form.get("proyeksi_pengembangan_jaringan_kantor"),
        "proyeksi_rencana_produk_aktivitas_pengembangan_sp": request.form.get("proyeksi_rencana_produk_aktivitas_pengembangan_sp"),
        "proyeksi_rencana_kerjasama_sp": request.form.get("proyeksi_rencana_kerjasama_sp"),
        "proyeksi_rencana_strategis_it": request.form.get("proyeksi_rencana_strategis_it"),
    }
    files = {}
    if 'kepemilikan_upload_bagan' in request.files:
        file = request.files['kepemilikan_upload_bagan']
        if file.filename != '': files['kepemilikan_upload_bagan'] = (file.filename, file.stream, file.mimetype)
    if 'upload_lapkeu_realisasi' in request.files:
        lapkeu_realisasi_files = request.files.getlist('upload_lapkeu_realisasi')
        for idx, file in enumerate(lapkeu_realisasi_files):
            if file.filename != '': files[f'upload_lapkeu_realisasi_{idx}'] = (file.filename, file.stream, file.mimetype)
    if 'upload_lapkeu_proyeksi' in request.files:
        lapkeu_proyeksi_files = request.files.getlist('upload_lapkeu_proyeksi')
        for idx, file in enumerate(lapkeu_proyeksi_files):
            if file.filename != '': files[f'upload_lapkeu_proyeksi_{idx}'] = (file.filename, file.stream, file.mimetype)
    if 'lampiran_profil_penyelenggara_sp' in request.files:
        file = request.files['lampiran_profil_penyelenggara_sp']
        if file.filename != '': files['lampiran_profil_penyelenggara_sp'] = (file.filename, file.stream, file.mimetype)
    if 'lampiran_profil_it' in request.files:
        file = request.files['lampiran_profil_it']
        if file.filename != '': files['lampiran_profil_it'] = (file.filename, file.stream, file.mimetype)
    if 'lampiran_tambahan' in request.files:
        lampiran_tambahan_files = request.files.getlist('lampiran_tambahan')
        for idx, file in enumerate(lampiran_tambahan_files):
            if file.filename != '': files[f'lampiran_tambahan_{idx}'] = (file.filename, file.stream, file.mimetype)
    api_endpoint = f"{API_BASE_URL}laporan/tahunan-sp/submit" 
    try:
        print("Data Laporan Tahunan SP Diterima:", form_data)
        if files:
            print("File Laporan Tahunan SP Diterima:", files)
        return jsonify({"success": True, "message": "Laporan Tahunan SP (Simulasi) berhasil diterima!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan internal: {str(e)}"}), 500

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
