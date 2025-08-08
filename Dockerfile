# Gunakan Python versi ringan
FROM python:3.11-slim

# Set direktori kerja
WORKDIR /app

# Copy file dependency
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua file ke container
COPY . .

# Jalankan aplikasi
CMD ["python", "app.py"]
