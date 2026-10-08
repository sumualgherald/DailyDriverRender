# DailyDriver 🚀

Aplikasi web untuk mencatat dan memantau kebiasaan harian.

## Tech Stack
- **Backend**: Python Flask
- **Database**: SQLite (otomatis dibuat saat pertama dijalankan)
- **Frontend**: HTML + CSS + JavaScript (Vanilla)

## Cara Menjalankan

### 1. Pastikan Python sudah terinstal
```bash
python --version
# atau
python3 --version
```

### 2. Install Flask
```bash
pip install flask
```

### 3. Jalankan server
```bash
python app.py
```

### 4. Buka browser
```
http://localhost:5000
```

## Struktur Project
```
dailydriver/
├── app.py              ← Backend Flask (API + server)
├── dailydriver.db      ← Database SQLite (auto-generated)
├── requirements.txt    ← Daftar dependencies
└── public/
    └── index.html      ← Frontend (semua halaman)
```

## Fitur
- ✅ Register & Login akun
- ✅ Dashboard habit harian
- ✅ Tambah habit baru (nama + target per hari)
- ✅ Tandai habit selesai / belum (toggle)
- ✅ Progress bar harian
- ✅ Riwayat aktivitas per tanggal
- ✅ Filter riwayat: Semua / Done / Not Done
- ✅ Hapus habit

## Struktur Database
- **users**: userId, userName, userEmail, userPassword
- **habits**: habitId, userId, habitName, habitTarget, habitStartDate
- **habit_log**: logId, habitId, logDate, status
