from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import requests
from datetime import datetime
import json

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
    """
    Handles user login. Sends credentials to the backend API's login endpoint.
    If successful, stores access token in session and redirects to dashboard based on role.
    """
    if request.method == "POST":
        sandi_pjp = request.form["username"] # Mengasumsikan frontend mengirim 'username'
        password = request.form["password"]
        # Mengubah kunci dari 'username_or_email' menjadi 'sandi_pjp' sesuai error backend
        login_data = {"sandi_pjp": sandi_pjp, "password": password} 
        try:
            response = requests.post(f"{API_BASE_URL}auth/login/", json=login_data)
            response_data = response.json()
            if response.status_code == 200 and response_data.get("data") and response_data["data"].get("access"):
                session["username"] = sandi_pjp
                session["access_token"] = response_data["data"]["access"]
                # Determine role based on username (assuming 'admin' for admin, others for user)
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
            # Handle network errors or server not reachable
            error_message = f"Gagal terhubung ke server API: {e}"
            return render_template("login.html", error=error_message)
    return render_template("login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    """Renders the admin dashboard, requires admin role."""
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("admin/dashboardadmin.html", banks=banks)

@app.route("/user/dashboard")
def user_dashboard():
    """Renders the user dashboard, requires user login."""
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/dashboarduser.html")

@app.route("/admin/profile", endpoint="admin_profile")
def profile_admin():
    """Renders the admin profile page, requires admin role."""
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("admin/profile.html")

@app.route("/admin/add_bank", methods=["POST"])
def add_bank():
    """
    Handles adding a new bank (dummy data for now).
    This function doesn't interact with the API based on the provided documentation.
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
    """Redirects to user dashboard (assuming reports are accessible from there)."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    # This route might be redundant if user_dashboard already lists reports.
    # Consider removing if dashboarduser.html is the main reports page.
    return render_template("user/dashboarduser.html")

@app.route("/admin/laporan")
def admin_laporan():
    """Placeholder for admin reports page."""
    if "username" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    return "Halaman Laporan Admin (Dalam Pengembangan)"

@app.route('/admin/history')
def admin_history():
    """Renders the admin history page, requires admin role."""
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template('admin/history.html')

@app.route('/admin/peraturan')
def admin_peraturan():
    """Renders the admin regulations page, requires admin role."""
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template('admin/peraturan.html')

@app.route("/base")
def base_page():
    """Renders the admin base template (for debugging/testing purposes)."""
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("admin/base.html")

def send_report_to_backend(endpoint_path, form_data, file_obj):
    """
    Generic function to send report data and file to the backend API.
    Args:
        endpoint_path (str): The specific API endpoint path (e.g., "laporan/fraud/submit").
        form_data (dict): Dictionary of form fields and their values.
        file_obj (werkzeug.datastructures.FileStorage): The uploaded file object.
    Returns:
        tuple: A tuple containing (success_boolean, message, status_code).
    """
    if "username" not in session:
        return False, "Sesi tidak valid, silakan login kembali.", 401

    headers = {"Authorization": f"Bearer {session.get('access_token')}"}
    files = {}
    if file_obj and file_obj.filename:
        files = {"file": (file_obj.filename, file_obj.stream, file_obj.mimetype)}

    try:
        response = requests.post(f"{API_BASE_URL}{endpoint_path}", headers=headers, data=form_data, files=files)
        response_data = response.json()
        if response.status_code == 201: # 201 Created for successful submissions
            return True, response_data.get("message", "Laporan berhasil dikirim!"), 201
        else:
            return False, response_data.get("message", "Gagal mengirim laporan."), response.status_code
    except requests.exceptions.RequestException as e:
        return False, f"Gagal terhubung ke server API: {e}", 500
    except json.JSONDecodeError:
        return False, "Respon API bukan JSON yang valid atau kosong.", 500

# --- Report Submission Routes ---

@app.route("/submit/laporan-fraud", methods=["POST"])
def submit_laporan_fraud():
    """Handles submission of Laporan Fraud."""
    try:
        # Backend expects DD/MM/YYYY for tanggal_surat
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
    """Renders the form for Laporan Fraud."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_fraud.html")

@app.route("/submit/laporan-dttot", methods=["POST"])
def submit_laporan_dttot():
    """
    Handles submission of Laporan DTTOT.
    NOTE: Endpoint for DTTOT is not explicitly listed in API documentation.
    This will currently return a simulated success.
    """
    try:
        # Assuming DD/MM/YYYY for consistency if not specified otherwise
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
        "keterangan": request.form.get("keterangan"),
        "nomor_surat_kepolisian": request.form.get("nomor_surat_kepolisian"),
        "organisasi_teroris": request.form.get("organisasi_teroris")
    }
    file_laporan = request.files.get("file_laporan")

    # Simulate success as DTTOT endpoint not found in API docs
    print("Simulating DTTOT submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan DTTOT (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-dttot")
def form_laporan_dttot():
    """Renders the form for Laporan DTTOT."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_dttot.html")

@app.route("/form/laporan-keuangan-tahunan")
def form_laporan_keuangan_tahunan():
    """Renders the form for Laporan Keuangan Tahunan."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_keuangan_tahunan.html")

@app.route("/submit/laporan-keuangan-tahunan", methods=["POST"])
def submit_laporan_keuangan_tahunan():
    """
    Handles submission of Laporan Keuangan Tahunan.
    NOTE: Endpoint for Laporan Keuangan Tahunan is not explicitly listed in API documentation.
    This will currently return a simulated success.
    """
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
        formatted_tanggal_opini = None
        if request.form.get("tanggal_opini"):
            formatted_tanggal_opini = datetime.strptime(request.form.get("tanggal_opini"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal tidak valid"}), 400

    form_data = {
        "tahun_laporan": int(request.form.get("tahun")), # Using 'tahun_laporan' for consistency
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

    # Simulate success as endpoint not found in API docs
    print("Simulating Laporan Keuangan Tahunan submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan Keuangan Tahunan (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201


@app.route("/form/laporan-keuangan-triwulan")
def form_laporan_keuangan_triwulan():
    """Renders the form for Laporan Keuangan Triwulan."""
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_keuangan_triwulan.html")

@app.route("/submit/laporan-keuangan-triwulan", methods=["POST"])
def submit_laporan_keuangan_triwulan():
    """
    Handles submission of Laporan Keuangan Triwulan.
    NOTE: Endpoint for Laporan Keuangan Triwulan is not explicitly listed in API documentation.
    This will currently return a simulated success.
    """
    try:
        formatted_tanggal_surat = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal surat tidak valid"}), 400
    form_data = {
        "tahun_laporan": int(request.form.get("tahun")), # Using 'tahun_laporan' for consistency
        "periode_laporan": request.form.get("triwulan"), # Mapped 'triwulan' to 'periode_laporan'
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "modal_disetor": int(request.form.get("modal_disetor").replace('.', '')),
        "pendapatan": int(request.form.get("pendapatan").replace('.', '')),
        "beban_operasional": int(request.form.get("beban_operasional").replace('.', '')),
        "laba": int(request.form.get("laba").replace('.', '')),
        "rugi": int(request.form.get("rugi").replace('.', '')),
        "total_aset": int(request.form.get("total_aset").replace('.', '')),
        "total_liabilitas": int(request.form.get("total_liabilitas").replace('.', '')),
        "total_ekuitas": int(request.form.get("total_ekuitas").replace('.', '')) # Mapped 'total_equitas' to 'total_ekuitas'
    }
    file_laporan = request.files.get("file_laporan")

    # Simulate success as endpoint not found in API docs
    print("Simulating Laporan Keuangan Triwulan submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan Keuangan Triwulan (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

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
        # waktu_kejadian can be DD/MM/YYYY or YYYY-MM-DD
        formatted_waktu_kejadian = datetime.strptime(request.form.get("waktu_kejadian"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal tidak valid"}), 400

    form_data = {
        "tahun_laporan": int(request.form.get("tahun_laporan")),
        "periode_laporan": request.form.get("periode_laporan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_tanggal_surat,
        "waktu_kejadian": formatted_waktu_kejadian,
        "jenis_gangguan": request.form.get("jenis_gangguan"),
        "upaya_perbaikan": request.form.get("upaya_perbaikan"),
        "status_penyelesaian": request.form.get("status_penyelesaian")
    }
    file_laporan = request.files.get("file_laporan")

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


# --- Placeholder routes for forms without explicit API submit endpoints ---
# These routes will render the forms, but their submission will be simulated as
# the API documentation does not provide specific endpoints for them.

@app.route("/form/laporan-apuppt")
def form_laporan_apuppt():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_apuppt.html")

@app.route("/submit/laporan-apuppt", methods=["POST"])
def submit_laporan_apuppt():
    # Simulate success as endpoint not found in API docs
    print("Simulating Laporan APUPPT submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan APUPPT (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-auditsi")
def form_laporan_auditsi():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_auditsi.html")

@app.route("/submit/laporan-auditsi", methods=["POST"])
def submit_laporan_auditsi():
    # Simulate success as endpoint not found in API docs
    print("Simulating Laporan Auditsi submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan Auditsi (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-dana-bukan-bank")
def form_laporan_dana_bukan_bank():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_dana_bukan_bank.html")

@app.route("/submit/laporan-dana-bukan-bank", methods=["POST"])
def submit_laporan_dana_bukan_bank():
    # Simulate success as endpoint not found in API docs
    print("Simulating Laporan Dana Bukan Bank submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan Dana Bukan Bank (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-kpsp")
def form_laporan_kpsp():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_kpsp.html")

@app.route("/submit/laporan-kpsp", methods=["POST"])
def submit_laporan_kpsp():
    # Simulate success as endpoint not found in API docs
    print("Simulating Laporan KPSP submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan KPSP (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-manajemen")
def form_laporan_manajemen():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_manajemen.html")

@app.route("/submit/laporan-manajemen", methods=["POST"])
def submit_laporan_manajemen():
    # Simulate success as endpoint not found in API docs
    print("Simulating Laporan Manajemen submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan Manajemen (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-p2p")
def form_laporan_p2p():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_p2p.html")

@app.route("/submit/laporan-p2p", methods=["POST"])
def submit_laporan_p2p():
    # Simulate success as endpoint not found in API docs
    print("Simulating Laporan P2P submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan P2P (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-pelaksanaan-edukasi-publik")
def form_laporan_pelaksanaan_edukasi_publik():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_pelaksanaan_edukasi_publik.html")

@app.route("/submit/laporan-pelaksanaan-edukasi-publik", methods=["POST"])
def submit_laporan_pelaksanaan_edukasi_publik():
    # Simulate success as endpoint not found in API docs
    print("Simulating Laporan Pelaksanaan Edukasi Publik submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan Pelaksanaan Edukasi Publik (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-pelaksanaan-pengujian-keamanan")
def form_laporan_pelaksanaan_pengujian_keamanan():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_pelaksanaan_pengujian_keamanan.html")

@app.route("/submit/laporan-pelaksanaan-pengujian-keamanan", methods=["POST"])
def submit_laporan_pelaksanaan_pengujian_keamanan():
    # Simulate success as endpoint not found in API docs
    print("Simulating Laporan Pelaksanaan Pengujian Keamanan submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan Pelaksanaan Pengujian Keamanan (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-pppk")
def form_laporan_pppk():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_pppk.html")

@app.route("/submit/laporan-pppk", methods=["POST"])
def submit_laporan_pppk():
    # Simulate success as endpoint not found in API docs
    print("Simulating Laporan PPPK submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan PPPK (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-rencana-edukasi-publik")
def form_laporan_rencana_edukasi_publik():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_rencana_edukasi_publik.html")

@app.route("/submit/laporan-rencana-edukasi-publik", methods=["POST"])
def submit_laporan_rencana_edukasi_publik():
    # Simulate success as endpoint not found in API docs
    print("Simulating Laporan Rencana Edukasi Publik submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan Rencana Edukasi Publik (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-sksp-tahunan")
def form_laporan_sksp_tahunan():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_sksp_tahunan.html")

@app.route("/submit/laporan-sksp-tahunan", methods=["POST"])
def submit_laporan_sksp_tahunan():
    # Simulate success as endpoint not found in API docs
    print("Simulating Laporan SKSP Tahunan submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan SKSP Tahunan (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-sksp-triwulan")
def form_laporan_sksp_triwulan():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_sksp_triwulan.html")

@app.route("/submit/laporan-sksp-triwulan", methods=["POST"])
def submit_laporan_sksp_triwulan():
    # Simulate success as endpoint not found in API docs
    print("Simulating Laporan SKSP Triwulan submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan SKSP Triwulan (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201

@app.route("/form/laporan-tahunan-sp")
def form_laporan_tahunan_sp():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_tahunan_sp.html")

@app.route("/submit/laporan-tahunan-sp", methods=["POST"])
def submit_laporan_tahunan_sp():
    # Simulate success as endpoint not found in API docs
    print("Simulating Laporan Tahunan SP submission (endpoint not found in docs)")
    return jsonify({"success": True, "message": "Laporan Tahunan SP (Simulasi) berhasil diterima! (Endpoint tidak ditemukan di Dokumentasi API)"}), 201


@app.route("/logout")
def logout():
    """Logs out the user by clearing the session."""
    session.pop("username", None)
    session.pop("access_token", None)
    session.pop("role", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
