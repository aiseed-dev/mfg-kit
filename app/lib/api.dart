/// API 呼び出しの薄いヘルパー。カタログ静的JSONの取得もここ。
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'config.dart';
import 'models.dart';
import 'session.dart';

class ApiException implements Exception {
  final int status;
  final String message;
  ApiException(this.status, this.message);
  @override
  String toString() => message;
}

dynamic _decode(http.Response r) {
  if (r.statusCode >= 400) {
    String msg = 'エラーが発生しました($r.statusCode)';
    try {
      msg = jsonDecode(utf8.decode(r.bodyBytes))['detail'].toString();
    } catch (_) {}
    throw ApiException(r.statusCode, msg);
  }
  if (r.bodyBytes.isEmpty) return null;
  return jsonDecode(utf8.decode(r.bodyBytes));
}

Future<dynamic> apiGet(String path) async {
  final r = await http.get(
    Uri.parse('${Config.apiBase}$path'),
    headers: Session.i.headers,
  );
  return _decode(r);
}

Future<dynamic> apiSend(String method, String path, {Object? body}) async {
  final req = http.Request(method, Uri.parse('${Config.apiBase}$path'))
    ..headers.addAll({...Session.i.headers, 'Content-Type': 'application/json'});
  if (body != null) req.body = jsonEncode(body);
  final r = await http.Response.fromStream(await req.send());
  return _decode(r);
}

/// メッセージ送信(添付は multipart)
Future<dynamic> apiPostMessage(
  String quoteId,
  String body, {
  List<int>? fileBytes,
  String? fileName,
}) async {
  final req = http.MultipartRequest(
    'POST',
    Uri.parse('${Config.apiBase}/quotes/$quoteId/messages'),
  )
    ..headers.addAll(Session.i.headers)
    ..fields['body'] = body;
  if (fileBytes != null) {
    req.files.add(
      http.MultipartFile.fromBytes('file', fileBytes, filename: fileName),
    );
  }
  final r = await http.Response.fromStream(await req.send());
  return _decode(r);
}

/// カタログ(静的JSON。アプリ機停止中も読める)。メモリキャッシュ付き
Catalog? _catalog;

Future<Catalog> fetchCatalog() async {
  if (_catalog != null) return _catalog!;
  final r = await http.get(Uri.parse(Config.catalogUrl));
  if (r.statusCode != 200) {
    throw ApiException(r.statusCode, 'カタログを読み込めませんでした');
  }
  _catalog = Catalog.fromJson(jsonDecode(utf8.decode(r.bodyBytes)));
  return _catalog!;
}
