from flask import Flask, render_template, request, redirect, url_for, session
import requests
app = Flask(__name__)
app.secret_key = "supersecretkey"  # Untuk session

# Dummy data untuk login
# USERS = {
#     "admin": {"password": "1234", "role": "admin"},
#     "user": {"password": "5678", "role": "user"}
# }
# API Configuration
API_BASE_URL = "https://silap-backend.vercel.app/api/"

# Dummy data bank
banks = [
    {"id": 1, "nama": "PT Fliptech Lentera Inspirasi Pertiwi", "kategori": "Penyedia Jasa Pembayaran - Kategori Izin 3",
     "no_izin": "18/196/DKSP/68", "tgl_izin": "04 Oktober 2016"}
]

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        # Prepare the request to the external API
        payload = {
            "username": username,
            "password": password
        }
        
        try:
            response = requests.post((f"{API_BASE_URL}auth/token/"), json=payload)
            response_data = response.json()
            
            if response.status_code == 200:
                # Successful login
                session["username"] = username
                session["access_token"] = response_data["data"]["access"]
                session["refresh_token"] = response_data["data"]["refresh"]
                
                # Note: Since the API doesn't return role information, we'll assume all users are regular users
                # If you need admin/user differentiation, you'll need to get this info from another endpoint
                session["role"] = "user"
                
                return redirect(url_for("user_dashboard"))
            else:
                # Failed login
                error_message = response_data.get("message", "Username atau password salah!")
                return render_template("login.html", error=error_message)
                
        except requests.exceptions.RequestException as e:
            return render_template("login.html", error=f"{e}")
    
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
    return render_template("admin/laporan.html")  # Tambahkan file ini jika belum ada

@app.route('/admin/history')
def admin_history():
    return render_template('admin/history.html')

@app.route('/admin/peraturan')
def admin_peraturan():
    return render_template('admin/peraturan.html')

# Halaman Base (Jika Diperlukan)
@app.route("/base")
def base_page():
    return render_template("admin/base.html")  # Jika ada base.html

@app.route("/submit/laporan-fraud", methods=["POST"])
def submit_laporan_fraud():
    if "username" not in session:
        return redirect(url_for("login"))
    
    headers = {
        "Authorization": f"Bearer {session['access_token']}"
    }

    try:
        formatted_date = datetime.strptime(request.form.get("tanggal_surat"), '%Y-%m-%d').strftime('%d/%m/%Y')
    except:
        return {"success": False, "message": "Format tanggal tidak valid"}

    form_data = {
        "tahun_laporan": request.form.get("tahun"),
        "periode_laporan": request.form.get("bulan"),
        "nomor_surat": request.form.get("nomor_surat"),
        "tanggal_surat": formatted_date,
        "jumlah_fraud": request.form.get("jumlah_fraud"),
        "jumlah_besar_kerugian": request.form.get("kerugian"),
        "keterangan_fraud": request.form.get("keterangan_fraud"),
        "keterangan_tindak_lanjut": request.form.get("tindak_lanjut")
    }
    
    
    files = {}
    file = request.files.get("file_laporan")
    if file:
        files = {"file": (file.filename, file.stream, file.mimetype)}
    
    try:
        response = requests.post(
            f"{API_BASE_URL}laporan/fraud/submit",
            data=form_data,
            files=files,
            headers=headers
        )
        
        if response.status_code == 201:
            # Ambil seluruh data dari respons
            response_data = response.json()
            return {
                "success": True,
                "message": "Laporan berhasil dikirim!",
                "data": response_data.get("data", {})  # Kembalikan data yang dikirim oleh backend
            }
        else:
            error_data = response.json()
            error_message = error_data.get("message", "Gagal mengirim laporan. Silakan coba lagi.")
            return {"success": False, "message": error_message}
    except Exception as e:
        return {"success": False, "message": f"Gagal terhubung ke server. Silakan coba lagi nanti. {e}"}    
    # except requests.exceptions.RequestException as e:
    #     return {"success": False, "message": f"Gagal terhubung ke server. Silakan coba lagi nanti. {e}"}

@app.route("/form/laporan-fraud")
def form_laporan_fraud():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/forms/laporan_fraud.html")

@app.route("/form/laporan-dttot")
def form_laporan_dttot():
    return render_template("user/forms/laporan_dttot.html")

@app.route("/form/laporan-keuangan-tahunan")
def form_laporan_keuangan_tahunan():
    return render_template("user/forms/laporan_keuangan_tahunan.html")

@app.route("/form/laporan-keuangan-triwulan")
def form_laporan_keuangan_triwulan():
    return render_template("user/forms/laporan_keuangan_triwulan.html")

from datetime import datetime

@app.route('/laporan-manajemen')
def form_laporan_manajemen():
    current_year = datetime.now().year
    return render_template("user/forms/laporan_manajemen.html", current_year=current_year)

@app.route('/laporan-sksp')
def form_laporan_sksp():
    return render_template("user/forms/laporan_sksp.html")

@app.route('/laporan-gangguanit')
def form_laporan_gangguanit():
    return render_template("user/forms/laporan_gangguanit.html")
@app.route('/laporan-dana-bukan-bank')
def form_laporan_dana_bukan_bank():
    return render_template("user/forms/laporan_dana_bukan_bank.html")
@app.route('/laporan-p2p')
def form_laporan_p2p():
    return render_template("user/forms/laporan_p2p.html")
@app.route('/laporan-ppppk')
def form_laporan_pppk():
    return render_template("user/forms/laporan_pppk.html")
@app.route('/laporan-apuppt')
def form_laporan_apuppt():
    return render_template("user/forms/laporan_apuppt.html")
@app.route('/laporan-rencana-edukasi-publik')
def form_laporan_rencana_edukasi_publik():
    return render_template("user/forms/laporan_rencana_edukasi_publik.html")
@app.route('/laporan-pelaksanaan-pengujian-keamanan')
def form_laporan_pelaksanaan_pengujian_keamanan():
    return render_template("user/forms/laporan_pelaksanaan_pengujian_keamanan.html")
@app.route('/laporan-pelaksanaan-edukasi-publik')
def form_laporan_pelaksanaan_edukasi_publik():
    return render_template("user/forms/laporan_pelaksanaan_edukasi_publik.html")
@app.route('/laporan-auditsi')
def form_laporan_auditsi():
    return render_template("user/forms/laporan_auditsi.html")
# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
