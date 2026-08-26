class ApiConfig {
  ApiConfig._();

  // Your live Django backend. You can still override this at runtime with:
  // --dart-define=API_BASE_URL=https://example.onrender.com
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://digital-wardrobe-l8xe.onrender.com',
  );

  static Uri uri(String path) {
    final normalizedBase = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    final normalizedPath = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$normalizedBase$normalizedPath');
  }
}
