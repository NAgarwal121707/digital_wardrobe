# Digital Wardrobe Flutter – Milestone 1

## Included
- Yellow/black mobile theme with normal font weights
- Splash screen
- Login and registration screens
- Password visibility toggle
- JWT storage using flutter_secure_storage
- Django API integration
- Dashboard shell

## 1. Install packages
```powershell
cd D:\digital_wardrobe_flutter
flutter pub get
```

## 2. Run against your Render backend
Replace the URL below with your actual Render URL:

```powershell
flutter run -d chrome --dart-define=API_BASE_URL=https://YOUR-SERVICE.onrender.com
```

Do not add `/api` at the end of API_BASE_URL.

## 3. Expected backend endpoints
The app tries:
- `POST /api/token/` first for login
- `POST /api/login/` as a fallback
- `POST /api/register/` for registration

JWT response should contain `access` and optionally `refresh`.

## 4. Android later
Before APK work, move Android SDK to a path without spaces (example `C:\Android\Sdk`) and update Flutter/Android Studio SDK paths.

## 5. Security
OPENAI_API_KEY and Cloudinary secrets stay in Django/Render only. Never put them in Flutter.
