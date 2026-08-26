DIGITAL WARDROBE FLUTTER — FOUNDATION V2

WHAT THIS FIXES
1. Registration endpoint now matches Django API: POST /api/auth/register/
2. Login endpoint now matches Django API: POST /api/auth/login/
3. Register button says Create Account.
4. Successful registration redirects to Login instead of Dashboard.
5. Premium gradient background + reusable cards/buttons/fields.
6. Yellow remains an accent; readable black/#333/white surfaces are used.
7. Font weights are 400/500 only.
8. Default backend is https://digital-wardrobe-l8xe.onrender.com

RUN
flutter pub get
flutter run -d chrome

OR explicitly:
flutter run -d chrome --dart-define=API_BASE_URL=https://digital-wardrobe-l8xe.onrender.com

IMPORTANT FOR FLUTTER WEB
If Chrome reports a browser/CORS error even though the API URL is correct, Django must allow your Flutter web origin. Install django-cors-headers on the Django backend and enable CORS for development. Android/iOS apps do not use browser CORS in the same way, but enabling it is useful while developing in Chrome.

BACKEND API EXPECTED
POST /api/auth/register/  body: {email, password}
POST /api/auth/login/     body: {email, password}

NEXT MILESTONE
Dashboard data + wardrobe API + item grid + bottom navigation.
