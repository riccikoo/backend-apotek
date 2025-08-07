from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_jwt, jwt_required, get_jwt_identity
from models import db, User, Obat, Transaksi, TransaksiDetail
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
from flask import current_app

load_dotenv()

def role_required(role):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            claims = get_jwt()
            user_role = claims.get('role')
            if user_role != role:
                current_app.logger.info(f"Unauthorized access attempt with role: {user_role}")
                return jsonify(msg="Unauthorized, role not allowed"), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

def create_app():
    app = Flask(__name__, static_folder='static')
    CORS(app)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/apotek_db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.environ['JWT_SECRET']
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

    db.init_app(app)
    jwt = JWTManager(app)

    with app.app_context():
        db.create_all()
    
    @app.route("/debug")
    @jwt_required()
    def debug_token():
        identity = get_jwt_identity()
        claims = get_jwt()
        return jsonify({
            "identity": identity,
            "claims": claims
    })

    @app.route('/api/login', methods=['POST'])
    def login():
        data = request.get_json()
        current_app.logger.info(f"Login attempt for username: {data.get('username')}")
        user = User.query.filter_by(username=data['username']).first()

        if not user or not user.check_password(data['password']):
            current_app.logger.info("Invalid login credentials")
            return jsonify({"msg": "Invalid credentials"}), 401

        current_app.logger.info(f"Login success for user ID: {user.id}")
        return jsonify({
            "token": user.generate_token(),
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role
            }
        })

    @app.route('/api/admin/obat', methods=['GET', 'POST'])
    @jwt_required()
    @role_required('admin')
    def obat_list():
        if request.method == 'GET':
            current_app.logger.info("Fetching all obat data")
            obat_list = Obat.query.all()
            return jsonify([{
                "id": o.id,
                "nama": o.nama,
                "gambar": o.gambar,
                "stok": o.stok,
                "harga_satuan": str(o.harga_satuan)
            } for o in obat_list])

        elif request.method == 'POST':
            nama = request.form.get('nama')
            stok = request.form.get('stok')
            harga_satuan = request.form.get('harga_satuan')
            gambar_file = request.files.get('gambar')
            current_app.logger.info(f"Tambah obat: {nama}, Stok: {stok}, Harga: {harga_satuan}")

            if not nama or not stok or not harga_satuan or not gambar_file:
                current_app.logger.info("Field tidak lengkap untuk tambah obat")
                return jsonify({"msg": "Semua field harus diisi"}), 400

            # 1. Tambahkan obat ke database tanpa gambar
            obat = Obat(
                nama=nama,
                stok=int(stok),
                harga_satuan=float(harga_satuan),
                gambar=""  # kosong dulu
            )
            db.session.add(obat)
            db.session.commit()  # supaya obat.id muncul

            # 2. Simpan file gambar dengan nama berdasarkan ID
            ext = os.path.splitext(secure_filename(gambar_file.filename))[1]  # .jpg, .png, etc
            filename = f"obat-{obat.id}{ext}"
            upload_dir = os.path.join('static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            upload_path = os.path.join(upload_dir, filename)
            gambar_file.save(upload_path)
            current_app.logger.info(f"Gambar disimpan di: {upload_path}")

            # 3. Update kolom gambar dan commit lagi
            obat.gambar = upload_path
            db.session.commit()

            current_app.logger.info(f"Obat berhasil ditambahkan: {obat.id}")
            return jsonify({"msg": "Obat created"}), 201

    @app.route('/api/admin/obat/<int:id>', methods=['GET', 'PUT', 'DELETE'])
    @jwt_required()
    @role_required('admin')
    def obat_detail(id):
        obat = Obat.query.get_or_404(id)

        if request.method == 'GET':
            current_app.logger.info(f"Get detail obat ID: {id}")
            return jsonify({
                "id": obat.id,
                "nama": obat.nama,
                "gambar": obat.gambar,
                "stok": obat.stok,
                "harga_satuan": obat.harga_satuan
            })

        elif request.method == 'PUT':
            if request.content_type and request.content_type.startswith('multipart/form-data'):
                nama = request.form.get('nama')
                stok = request.form.get('stok')
                harga_satuan = request.form.get('harga_satuan')
                gambar_file = request.files.get('gambar')

                current_app.logger.info(f"Update obat ID: {id} with form data: {nama}, {stok}, {harga_satuan}")

                obat.nama = nama
                obat.stok = int(stok)
                obat.harga_satuan = float(harga_satuan)
                if gambar_file:
                    ext = os.path.splitext(secure_filename(gambar_file.filename))[1]
                    filename = f"obat-{obat.id}{ext}"
                    upload_dir = os.path.join('static', 'uploads')
                    os.makedirs(upload_dir, exist_ok=True)
                    upload_path = os.path.join(upload_dir, filename)
                    gambar_file.save(upload_path)
                    obat.gambar = upload_path
                db.session.commit()
                return jsonify({"msg": "Obat updated"})
            else:
                return jsonify({"msg": "Content-Type must be multipart/form-data"}), 415

        elif request.method == 'DELETE':
            current_app.logger.info(f"Delete obat ID: {id}")
            db.session.delete(obat)
            db.session.commit()
            return jsonify({"msg": "Obat deleted"})

    @app.route('/api/admin/pegawai', methods=['GET', 'POST'])
    @jwt_required()
    @role_required('admin')
    def pegawai_list():
        if request.method == 'GET':
            pegawai_list = User.query.filter_by(role='kasir').all()
            current_app.logger.info(f"Fetch pegawai: {len(pegawai_list)} found")
            return jsonify([{
                "id": p.id,
                "username": p.username
            } for p in pegawai_list])

        elif request.method == 'POST':
            data = request.get_json()
            current_app.logger.info(f"Tambah pegawai baru: {data['username']}")
            user = User(username=data['username'], role='kasir')
            user.set_password(data['password'])
            db.session.add(user)
            db.session.commit()
            return jsonify({"msg": "Pegawai created"}), 201
        
    @app.route('/api/admin/pegawai/<int:id>', methods=['PUT', 'DELETE'])
    @jwt_required()
    @role_required('admin')
    def pegawai_detail(id):
        if request.method == 'PUT':
            data = request.get_json()
            user = User.query.get_or_404(id)
            
            if 'username' in data:
                user.username = data['username']
            if 'password' in data and data['password']:
                user.set_password(data['password'])
                
            db.session.commit()
            current_app.logger.info(f"Update pegawai: {user.username}")
            return jsonify({"msg": "Pegawai updated"})
            
        elif request.method == 'DELETE':
            user = User.query.get_or_404(id)
            db.session.delete(user)
            db.session.commit()
            current_app.logger.info(f"Delete pegawai: {user.username}")
            return jsonify({"msg": "Pegawai deleted"})

    @app.route('/api/kasir/transaksi', methods=['GET', 'POST'])
    @jwt_required()
    @role_required('kasir')
    def transaksi_list():
        current_user_id = get_jwt_identity()

        if request.method == 'GET':
            try:
                # Get today's transactions for the current cashier
                today = datetime.now().date()
                transaksi_list = Transaksi.query.filter(
                    Transaksi.user_id == current_user_id,
                    db.func.date(Transaksi.tanggal) == today
                ).order_by(Transaksi.tanggal.desc()).all()
                
                current_app.logger.info(f"Kasir {current_user_id} fetched {len(transaksi_list)} transactions")
                
                return jsonify([{
                    "id": t.id,
                    "tanggal": t.tanggal.strftime('%Y-%m-%d %H:%M:%S'),
                    "total_harga": str(t.total_harga),
                    "user_id": t.user_id,
                    "details": [{
                        "id": d.id,
                        "obat_id": d.obat_id,
                        "nama_obat": d.obat.nama,
                        "jumlah": d.jumlah,
                        "harga_satuan": str(d.harga_satuan),
                        "subtotal": str(d.subtotal)
                    } for d in t.details]
                } for t in transaksi_list])
                
            except Exception as e:
                current_app.logger.error(f"Error fetching transactions: {str(e)}")
                return jsonify({"error": "Gagal mengambil data transaksi"}), 500

        elif request.method == 'POST':
            try:
                data = request.get_json()
                
                # Validate request data
                if not data or 'items' not in data or not data['items']:
                    current_app.logger.warning("Invalid transaction data format")
                    return jsonify({"error": "Format data transaksi tidak valid"}), 400
                
                # Calculate total
                total_harga = 0
                items = []
                
                # Validate items and calculate total
                for item in data['items']:
                    if 'obat_id' not in item or 'jumlah' not in item:
                        return jsonify({"error": "Format item tidak valid"}), 400
                    
                    obat = Obat.query.get(item['obat_id'])
                    if not obat:
                        return jsonify({"error": f"Obat dengan ID {item['obat_id']} tidak ditemukan"}), 404
                    
                    if obat.stok < item['jumlah']:
                        return jsonify({"error": f"Stok {obat.nama} tidak mencukupi"}), 400
                    
                    harga_satuan = obat.harga_satuan
                    subtotal = harga_satuan * item['jumlah']
                    total_harga += subtotal
                    
                    items.append({
                        "obat": obat,
                        "obat_id": item['obat_id'],
                        "jumlah": item['jumlah'],
                        "harga_satuan": harga_satuan,
                        "subtotal": subtotal
                    })
                
                # Create transaction in a database transaction
                # db.session.begin()
                
                # Create main transaction record
                transaksi = Transaksi(
                    total_harga=total_harga,
                    user_id=int(current_user_id)
                )
                db.session.add(transaksi)
                db.session.flush()  # To get the transaksi.id
                
                # Create transaction details
                for item in items:
                    transaksi_detail = TransaksiDetail(
                        transaksi_id=transaksi.id,
                        obat_id=item['obat_id'],
                        jumlah=item['jumlah'],
                        harga_satuan=item['harga_satuan'],
                        subtotal=item['subtotal']
                    )
                    db.session.add(transaksi_detail)
                    
                    # Update stock
                    item['obat'].stok -= item['jumlah']
                
                db.session.commit()
                
                current_app.logger.info(f"Transaksi berhasil dibuat ID: {transaksi.id}")
                
                # Prepare response
                response_data = {
                    "id": transaksi.id,
                    "tanggal": transaksi.tanggal.strftime('%Y-%m-%d %H:%M:%S'),
                    "total_harga": str(transaksi.total_harga),
                    "details": [{
                        "obat_id": d.obat_id,
                        "nama_obat": d.obat.nama,
                        "jumlah": d.jumlah,
                        "harga_satuan": str(d.harga_satuan),
                        "subtotal": str(d.subtotal)
                    } for d in transaksi.details]
                }
                
                return jsonify(response_data), 201
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error processing transaction: {str(e)}")
                return jsonify({"error": "Gagal memproses transaksi"}), 500


    @app.route('/api/kasir/transaksi/<int:id>', methods=['GET'])
    @jwt_required()
    @role_required('kasir')
    def transaksi_detail(id):
        try:
            transaksi = Transaksi.query.filter_by(
                id=id,
                user_id=get_jwt_identity()
            ).first_or_404()
            
            current_app.logger.info(f"Fetching transaction details for ID: {id}")
            
            return jsonify({
                "id": transaksi.id,
                "tanggal": transaksi.tanggal.strftime('%Y-%m-%d %H:%M:%S'),
                "total_harga": str(transaksi.total_harga),
                "user_id": transaksi.user_id,
                "details": [{
                    "id": d.id,
                    "obat_id": d.obat_id,
                    "nama_obat": d.obat.nama,
                    "jumlah": d.jumlah,
                    "harga_satuan": str(d.harga_satuan),
                    "subtotal": str(d.subtotal)
                } for d in transaksi.details]
            })
            
        except Exception as e:
            current_app.logger.error(f"Error fetching transaction {id}: {str(e)}")
            return jsonify({"error": "Gagal mengambil detail transaksi"}), 500


    @app.route('/api/kasir/obat', methods=['GET'])
    @jwt_required()
    @role_required('kasir')
    def obat_available():
        try:
            # Get available medicines (stock > 0)
            obat_list = Obat.query.filter(Obat.stok > 0).all()
            
            current_app.logger.info(f"Fetched {len(obat_list)} available medicines")
            
            return jsonify([{
                "id": o.id,
                "nama": o.nama,
                "harga_satuan": str(o.harga_satuan),
                "stok": o.stok,
                "gambar": o.gambar
            } for o in obat_list])
            
        except Exception as e:
            current_app.logger.error(f"Error fetching available medicines: {str(e)}")
            return jsonify({"error": "Gagal mengambil data obat"}), 500

    @app.route('/api/admin/laporan/mingguan')
    @jwt_required()
    @role_required('admin')
    def laporan_mingguan():
        satu_minggu_lalu = datetime.now() - timedelta(days=7)
        transaksi = Transaksi.query.filter(Transaksi.tanggal >= satu_minggu_lalu).all()
        current_app.logger.info(f"Generate laporan mingguan. Jumlah transaksi: {len(transaksi)}")

        total_penjualan = sum(t.total_harga for t in transaksi)
        total_barang_terjual = sum(
            sum(d.jumlah for d in t.details)
            for t in transaksi
        )

        return jsonify({
            "total_penjualan": total_penjualan,
            "total_barang_terjual": total_barang_terjual,
            "transaksi": [{
                "id": t.id,
                "tanggal": t.tanggal.isoformat(),
                "total": t.total_harga,
                "kasir": t.user.username
            } for t in transaksi]
        })

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
