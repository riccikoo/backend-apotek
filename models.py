from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'kasir'
    
    def __init__(self, username, role):
        self.username = username
        self.role = role
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    def generate_token(self):
        return create_access_token(
            identity=str(self.id),  # Pakai string ID saja
            additional_claims={"role": self.role}  # Role taruh di claims
    )
    
    def __repr__(self):
        return f'<User {self.username}>'

class Obat(db.Model):
    __tablename__ = 'obat'
    
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False, index=True)
    gambar = db.Column(db.String(255))  # Path to image
    stok = db.Column(db.Integer, nullable=False, default=0)
    harga_satuan = db.Column(db.Numeric(10, 2), nullable=False)  # Menggunakan Numeric untuk presisi
    
    def __repr__(self):
        return f'<Obat {self.nama}>'

class Transaksi(db.Model):
    __tablename__ = 'transaksi'
    
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    total_harga = db.Column(db.Numeric(10, 2), nullable=False)  # Menggunakan Numeric untuk presisi
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))
    
    def __repr__(self):
        return f'<Transaksi {self.id}>'

class TransaksiDetail(db.Model):
    __tablename__ = 'transaksi_detail'
    
    id = db.Column(db.Integer, primary_key=True)
    transaksi_id = db.Column(db.Integer, db.ForeignKey('transaksi.id'), nullable=False)
    obat_id = db.Column(db.Integer, db.ForeignKey('obat.id'), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False)
    harga_satuan = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    
    transaksi = db.relationship('Transaksi', backref=db.backref('details', lazy=True))
    obat = db.relationship('Obat')
    
    def __repr__(self):
        return f'<TransaksiDetail {self.id}>'