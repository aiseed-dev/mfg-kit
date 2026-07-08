import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../api.dart';
import '../models.dart';
import '../session.dart';
import '../ui.dart';

/// カタログホーム: 分類グリッド+製品(静的JSONを読む。C-02)
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Catalog? data;
  Object? error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => error = null);
    try {
      final c = await fetchCatalog();
      if (mounted) setState(() => data = c);
    } catch (e) {
      if (mounted) setState(() => error = e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('製品カタログ'),
        actions: [
          IconButton(
            icon: const Icon(Icons.qr_code_scanner),
            tooltip: 'QR読み取り',
            onPressed: () => context.go('/scan'),
          ),
          IconButton(
            icon: const Icon(Icons.shopping_cart_outlined),
            tooltip: '見積カート',
            onPressed: () => context.go('/cart'),
          ),
          IconButton(
            icon: const Icon(Icons.receipt_long_outlined),
            tooltip: '依頼一覧',
            onPressed: () => context.go('/quotes'),
          ),
          if (!Session.i.loggedIn)
            TextButton(
              onPressed: () => context.go('/login'),
              child: const Text('ログイン'),
            ),
        ],
      ),
      body: error != null
          ? ErrorView(error!, onRetry: _load)
          : data == null
              ? const LoadingView()
              : _body(data!),
    );
  }

  Widget _body(Catalog c) => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final cat in c.categories)
                ActionChip(
                  label: Text(cat.name),
                  onPressed: () => context.go('/c/${cat.slug}'),
                ),
            ],
          ),
          const SizedBox(height: 16),
          GridView.extent(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            maxCrossAxisExtent: 280,
            mainAxisExtent: 230,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            children: [for (final p in c.products) ProductCard(p)],
          ),
        ],
      );
}
