/// 認証トークン等の最小限を持つ Session シングルトン(CLAUDE.md)。
/// 認証は PocketBase(C-01)。
/// TODO: トークン永続化は shared_preferences の採用を確認してから
/// (現状はメモリのみ=リロードで再ログイン)。
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'config.dart';

class Session {
  Session._();
  static final Session i = Session._();

  String? token;
  String? userId;
  String? displayName;

  bool get loggedIn => token != null;

  Map<String, String> get headers =>
      token == null ? {} : {'Authorization': 'Bearer $token'};

  Future<void> login(String email, String password) async {
    final r = await http.post(
      Uri.parse('${Config.pbBase}/api/collections/users/auth-with-password'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'identity': email, 'password': password}),
    );
    if (r.statusCode != 200) {
      throw Exception('メールアドレスまたはパスワードが違います');
    }
    final j = jsonDecode(utf8.decode(r.bodyBytes));
    token = j['token'];
    userId = j['record']['id'];
    final name = j['record']['name'] as String?;
    displayName = (name == null || name.isEmpty) ? email : name;
  }

  /// 登録(メール確認は PocketBase 側の設定で送られる)
  Future<void> register(String name, String email, String password) async {
    final r = await http.post(
      Uri.parse('${Config.pbBase}/api/collections/users/records'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'name': name,
        'email': email,
        'password': password,
        'passwordConfirm': password,
      }),
    );
    if (r.statusCode >= 400) {
      throw Exception('登録できませんでした(メールアドレスが使用済みの可能性)');
    }
    await login(email, password);
  }

  void logout() {
    token = null;
    userId = null;
    displayName = null;
  }
}
