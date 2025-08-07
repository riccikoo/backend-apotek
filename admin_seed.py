from werkzeug.security import generate_password_hash
from app import create_app
from models import db, User

app = create_app()

def seed_admin():
    with app.app_context():
        # Cek apakah admin sudah ada
        existing_admin = User.query.filter_by(username='admin').first()
        
        if existing_admin:
            print("Admin user already exists!")
            return
        
        # Buat admin baru
        admin = User(
            username='admin',
            role='admin'
        )
        admin.set_password('admin123')  # Password default
        
        try:
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
            print(f"Username: admin")
            print(f"Password: admin123")
            print("Please change the password immediately after login!")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating admin user: {str(e)}")

if __name__ == '__main__':
    seed_admin()