Digital Wardrobe - Functional Flutter Milestone

Implemented:
- Existing JWT register/login
- Dynamic dashboard and closet
- Manual clothing add with camera/gallery
- AI clothing analysis from camera/gallery with wrong-image rejection
- Save AI analyzed item to wardrobe
- Clothing detail and delete
- Real wishlist list/add/mark purchased/delete
- AI Stylist chat backed by the existing Django stylist logic
- Wardrobe image cards inside AI replies when backend selects relevant saved items
- Profile email + logout
- Bottom navigation actions connected

Backend API additions:
POST /api/wardrobe/
PATCH/DELETE /api/wardrobe/<id>/
GET/POST /api/wishlist/
PATCH/DELETE /api/wishlist/<id>/
POST /api/ai/analyze/
POST /api/ai/stylist/

Setup:
1. Copy backend files to your Django project and deploy to Render.
2. Run pip install -r requirements.txt if needed.
3. Copy Flutter files, then run flutter pub get (image_picker was added).
4. Local test:
   flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
5. Live test:
   flutter run -d chrome --dart-define=API_BASE_URL=https://digital-wardrobe-l8xe.onrender.com

Note: OPENAI_API_KEY must exist in the backend environment for AI Analyze and AI Stylist.
