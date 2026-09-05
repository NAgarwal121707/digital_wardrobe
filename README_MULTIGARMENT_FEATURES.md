# Digital Wardrobe — Multi-Garment Backend + Website

This build keeps the existing Django website and REST API, and adds one shared
multi-garment AI engine for both the website and Flutter app.

## Core multi-garment rule

A photograph is not automatically a wardrobe item. If one photo contains a
burgundy top and black jeans, AI returns two independently reusable pieces.
The original photo is remembered as an `OutfitGroup`, so the app can also show
that those pieces were originally worn together.

True one-piece garments such as a dress or jumpsuit stay as one item.

Save modes:

- `separate` (recommended): save selected garment pieces.
- `outfit`: save the original full look only.
- `both`: save selected pieces plus the full-look card.

AI returns approximate bounding boxes. The backend creates a crop for each
piece when possible; the original photo remains available as the outfit source.

## Website features

- Login, register, password reset
- Dynamic dashboard, categories and wardrobe cards
- Manual add/edit/delete with full styling metadata
- AI single-photo add with multi-garment review
- Sequential multi-photo wardrobe scanner
- Quick gallery add with keep/skip review
- Original-look / paired-piece relationship on item detail
- Wishlist / future purchase workflow
- AI stylist with wardrobe visuals

## REST API used by Flutter

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/token/refresh/`
- `GET /api/dashboard/`
- `GET|POST /api/wardrobe/`
- `GET|PATCH|DELETE /api/wardrobe/<id>/`
- `GET|POST /api/wishlist/`
- `PATCH|DELETE /api/wishlist/<id>/`
- `POST /api/ai/analyze/`
- `POST /api/ai/save/`
- `POST /api/ai/stylist/`
- `GET /api/profile/`

## Required migration

This build adds `OutfitGroup` and links wardrobe pieces to it.

```powershell
python manage.py check
python manage.py migrate
```

The migration is:

`wardrobe/migrations/0006_outfitgroup_clothingitem_outfit_group_and_more.py`

## Environment variables

Keep real secrets only in local `.env` (ignored by Git) and Render Environment.
Never commit secrets.

Required/commonly used variables:

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_VISION_MODEL` (optional; defaults to `gpt-4o-mini`)
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `CSRF_TRUSTED_ORIGINS`

## Safer Git update for the backend repository

Because Flutter files were previously mixed into the backend working folder,
do not blindly use `git add .` unless you have cleaned that repository.
A safer command for this milestone is:

```powershell
git add accounts backend wardrobe templates static requirements.txt .gitignore .env.example README_MULTIGARMENT_FEATURES.md
git commit -m "Add full multi garment wardrobe intelligence"
git push origin main
```

Render should run migrations during deploy, or run `python manage.py migrate`
before starting the new application version.
