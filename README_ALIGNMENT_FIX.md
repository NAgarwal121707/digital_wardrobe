# Website / Flutter parity update

This build keeps one shared garment-analysis engine for both clients.

- Django website AI Add, Quick Gallery and Wardrobe Scanner use `accounts.ai_multigarment.analyse_and_store`.
- Flutter `/api/ai/analyze/` calls the same `analyse_and_store` service.
- The clothing detail website layout was cleaned up to match the Flutter detail layout: image + category badge, colour/season/occasion, Aesthetic, Fit & Silhouette, AI Tags, Suggested Accessories and AI Stylist Suggestions.
- Multi-garment outfit relationships are unchanged.

No new migration is introduced by this parity update.
