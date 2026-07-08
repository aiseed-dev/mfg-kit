/// 接続先。ビルド時に --dart-define で差し替える(導入先ごと)。
/// 例: flutter build web --dart-define=API_BASE=https://api.example.jp/api/v1
class Config {
  static const apiBase = String.fromEnvironment(
    'API_BASE',
    defaultValue: 'http://localhost:8000/api/v1',
  );
  static const pbBase = String.fromEnvironment(
    'PB_BASE',
    defaultValue: 'http://localhost:8090',
  );

  /// カタログ静的JSON(R2/Pages 配信。アプリ機停止中も読める)
  static const catalogUrl = String.fromEnvironment(
    'CATALOG_URL',
    defaultValue: 'http://localhost:5071/catalog.json',
  );
}
