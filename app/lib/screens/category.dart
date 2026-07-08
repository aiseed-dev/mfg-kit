import 'package:flutter/material.dart';

import '../api.dart';
import '../models.dart';
import '../ui.dart';

/// 分類別製品一覧(/c/:slug)
class CategoryScreen extends StatefulWidget {
  final String slug;
  const CategoryScreen(this.slug, {super.key});
  @override
  State<CategoryScreen> createState() => _CategoryScreenState();
}

class _CategoryScreenState extends State<CategoryScreen> {
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
    final cat = data?.categories
        .where((c) => c.slug == widget.slug)
        .firstOrNull;
    final products = data?.products
            .where((p) => p.categorySlug == widget.slug)
            .toList() ??
        [];
    return Scaffold(
      appBar: AppBar(title: Text(cat?.name ?? '')),
      body: error != null
          ? ErrorView(error!, onRetry: _load)
          : data == null
              ? const LoadingView()
              : GridView.extent(
                  padding: const EdgeInsets.all(16),
                  maxCrossAxisExtent: 280,
                  mainAxisExtent: 230,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                  children: [for (final p in products) ProductCard(p)],
                ),
    );
  }
}
