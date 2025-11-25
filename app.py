from flask import Flask, request, render_template, redirect, url_for, jsonify, Response
import boto3
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Konfigurasi AWS
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
API_URL = os.getenv("API_GATEWAY_URL")

# EC2 menggunakan IAM Role-nya sendiri, jadi tidak perlu hardcode key jika sudah attach role
# Tapi kalau masih pakai env vars, boto3 akan otomatis pakai itu.
s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
)

@app.route("/")
def index():
    response = requests.get(API_URL)
    # Parsing body jika perlu (seperti kasus sebelumnya)
    api_data = response.json()
    
    users = []
    if 'body' in api_data and isinstance(api_data['body'], str):
        import json
        users = json.loads(api_data['body'])
    elif 'body' in api_data:
        users = api_data['body']
    else:
        users = api_data

    # Kita tidak butuh variabel s3_bucket di sini lagi karena URL gambar sudah lengkap di database
    return render_template("index.html", users=users)

# --- ROUTE BARU: PROXY GAMBAR ---
@app.route("/images/<path:filename>")
def serve_s3_image(filename):
    """
    Fungsi ini dipanggil browser. 
    Dia akan mendownload stream dari S3 dan langsung melemparnya ke browser.
    """
    try:
        # 'users/' adalah folder di dalam bucket kamu
        s3_key = f"users/{filename}"
        
        # Minta object ke S3 (EC2 punya izin)
        file_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        
        # Ambil tipe konten (misal: image/png, image/jpeg) dari S3
        content_type = file_obj['ContentType']
        
        # Baca isi file dan kembalikan sebagai Response Flask
        return Response(
            file_obj['Body'].read(),
            mimetype=content_type
        )
    except Exception as e:
        return f"Error mengambil gambar: {e}", 404

@app.route("/users", methods=["POST"])
def add_user():
    name = request.form["name"]
    email = request.form["email"]
    institution = request.form["institution"]
    position = request.form["position"]
    phone = request.form["phone"]
    image = request.files["image"]

    # 1. Cek Email
    check_response = requests.get(f"{API_URL}?email={email}")
    if check_response.status_code == 409:
        return jsonify({"error": "Email already exists"}), 409

    # 2. Upload Gambar & Generate URL Lokal
    image_url = "" # Default kalau ga ada gambar
    
    if image:
        # Nama file di S3
        image_filename = f"users/{image.filename}"
        
        try:
            # Upload ke S3
            # ExtraArgs ContentType penting agar browser tahu ini gambar
            s3_client.upload_fileobj(
                image, 
                S3_BUCKET, 
                image_filename,
                ExtraArgs={'ContentType': image.content_type} 
            )
            
            # --- BAGIAN PENTING ---
            # Kita simpan URL yang mengarah ke Route Flask kita sendiri, bukan ke AWS S3 langsung.
            # Contoh hasil: /images/foto_profil.png
            image_url = url_for('serve_s3_image', filename=image.filename)
            
            # Kalau mau URL lengkap (http://ip-address/images/...) bisa pakai:
            # image_url = url_for('serve_s3_image', filename=image.filename, _external=True)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # 3. Simpan user ke database
    user_data = {
        "name": name,
        "email": email,
        "institution": institution,
        "position": position,
        "phone": phone,
        "image_url": image_url, # Ini sekarang isinya "/images/namafile.png"
    }

    response = requests.post(API_URL, json=user_data)

    if response.status_code == 409:
        return jsonify({"error": "Email already exists"}), 409

    return redirect(url_for("index"))

# ... (Sisa kode delete/update/get sama saja) ...
@app.route("/users/<int:user_id>/delete", methods=["DELETE"])
def delete_user(user_id):
    response = requests.delete(f"{API_URL}/{user_id}")
    if response.status_code == 204:
        return jsonify({"message": "User deleted successfully"}), 200
    try:
        return jsonify(response.json()), response.status_code
    except:
        return jsonify({"error": "Unexpected empty response"}), response.status_code

@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    response = requests.get(f"{API_URL}/{user_id}")
    return jsonify(response.json()), response.status_code

@app.route("/users/<int:user_id>", methods=["PUT", "PATCH"])
def update_user(user_id):
    data = request.json
    response = requests.put(f"{API_URL}/{user_id}", json=data)
    if response.status_code == 200:
        return jsonify({"message": "Used sudah diupdate", "data": response.json()})
    else:
        return jsonify({"error": "Failed to update user"}), response.status_code

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')