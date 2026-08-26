import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import '../core/config/api_config.dart';

class AuthException implements Exception {
  const AuthException(this.message);
  final String message;
  @override
  String toString() => message;
}

class AuthService {
  AuthService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;
  static const _storage = FlutterSecureStorage();
  static const _accessKey = 'dw_access_token';
  static const _refreshKey = 'dw_refresh_token';
  static const _emailKey = 'dw_user_email';

  Future<bool> hasSession() async {
    final token = await _storage.read(key: _accessKey);
    return token != null && token.isNotEmpty;
  }

  Future<String?> get email => _storage.read(key: _emailKey);
  Future<String?> get accessToken => _storage.read(key: _accessKey);

  Future<void> register({required String email, required String password}) async {
    http.Response response;
    try {
      response = await _client
          .post(
            ApiConfig.uri('/api/auth/register/'),
            headers: const {'Content-Type': 'application/json', 'Accept': 'application/json'},
            body: jsonEncode({'email': email.trim().toLowerCase(), 'password': password}),
          )
          .timeout(const Duration(seconds: 35));
    } catch (_) {
      throw const AuthException(
        'Could not reach the server. Check internet access, Render status, and CORS settings.',
      );
    }

    final decoded = _decode(response.body);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw AuthException(_extractError(decoded, response.statusCode));
    }
  }

  Future<void> login({required String email, required String password}) async {
    http.Response response;
    try {
      response = await _client
          .post(
            ApiConfig.uri('/api/auth/login/'),
            headers: const {'Content-Type': 'application/json', 'Accept': 'application/json'},
            body: jsonEncode({'email': email.trim().toLowerCase(), 'password': password}),
          )
          .timeout(const Duration(seconds: 35));
    } catch (_) {
      throw const AuthException(
        'Could not reach the server. Check internet access, Render status, and CORS settings.',
      );
    }

    final decoded = _decode(response.body);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw AuthException(_extractError(decoded, response.statusCode));
    }

    final access = decoded['access']?.toString();
    final refresh = decoded['refresh']?.toString();
    if (access == null || access.isEmpty) {
      throw const AuthException('Login succeeded but the API did not return an access token.');
    }

    await _storage.write(key: _accessKey, value: access);
    if (refresh != null && refresh.isNotEmpty) {
      await _storage.write(key: _refreshKey, value: refresh);
    }
    await _storage.write(key: _emailKey, value: email.trim().toLowerCase());
  }

  Future<void> logout() => _storage.deleteAll();

  Map<String, dynamic> _decode(String body) {
    if (body.trim().isEmpty) return <String, dynamic>{};
    try {
      final decoded = jsonDecode(body);
      return decoded is Map<String, dynamic> ? decoded : {'detail': decoded.toString()};
    } catch (_) {
      return {'detail': body};
    }
  }

  String _extractError(Map<String, dynamic> data, int code) {
    for (final key in ['detail', 'message', 'error', 'email', 'password', 'non_field_errors']) {
      final value = data[key];
      if (value is List && value.isNotEmpty) return value.first.toString();
      if (value is String && value.trim().isNotEmpty) return value;
    }
    return 'Request failed (HTTP $code).';
  }
}
