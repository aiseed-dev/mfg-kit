/// 画面共通の小物(3状態パターンの error/loading 表示・状態バッジ)。
library;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'models.dart';

const statusJa = {
  'requested': '依頼中',
  'answered': '回答済み',
  'ordered': '受注',
  'declined': '辞退',
  'cancelled': '取下げ',
  'closed': '完了',
  'expired': '期限切れ',
};

const _statusColor = {
  'requested': Colors.red,
  'answered': Colors.blue,
  'ordered': Colors.green,
};

class StatusBadge extends StatelessWidget {
  final String status;
  const StatusBadge(this.status, {super.key});

  @override
  Widget build(BuildContext context) => Chip(
        label: Text(
          statusJa[status] ?? status,
          style: const TextStyle(color: Colors.white, fontSize: 12),
        ),
        backgroundColor: _statusColor[status] ?? Colors.grey,
        visualDensity: VisualDensity.compact,
      );
}

/// 読込中(null)のスケルトン
class LoadingView extends StatelessWidget {
  const LoadingView({super.key});
  @override
  Widget build(BuildContext context) =>
      const Center(child: Padding(padding: EdgeInsets.all(48), child: CircularProgressIndicator()));
}

/// error 状態: リトライボタン。API 不応答時は「メンテナンス中」(CLAUDE.md)
class ErrorView extends StatelessWidget {
  final Object error;
  final VoidCallback onRetry;
  const ErrorView(this.error, {required this.onRetry, super.key});

  @override
  Widget build(BuildContext context) {
    final msg = error.toString().contains('SocketException') ||
            error.toString().contains('Failed to fetch') ||
            error.toString().contains('Connection')
        ? 'メンテナンス中です。しばらくしてからお試しください。'
        : error.toString().replaceFirst('Exception: ', '');
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(msg, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            OutlinedButton(onPressed: onRetry, child: const Text('再読み込み')),
          ],
        ),
      ),
    );
  }
}

/// 製品カード: 写真/一言/型番/仕様抜粋/価格表記 の順(03_apps)
class ProductCard extends StatelessWidget {
  final Product p;
  const ProductCard(this.p, {super.key});

  @override
  Widget build(BuildContext context) {
    final specs = p.specs.entries.take(2);
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => context.go('/p/${p.code}'),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (p.photos.isNotEmpty)
                AspectRatio(
                  aspectRatio: 4 / 3,
                  child: CachedNetworkImage(imageUrl: p.photos.first, fit: BoxFit.cover),
                ),
              Text(p.name, style: Theme.of(context).textTheme.titleMedium),
              if (p.summary != null)
                Text(p.summary!, maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall),
              Text(p.code, style: Theme.of(context).textTheme.labelSmall),
              for (final e in specs)
                Text('${e.key}: ${e.value}',
                    style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 4),
              Text(p.priceNote ?? '要見積',
                  style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.green)),
            ],
          ),
        ),
      ),
    );
  }
}
