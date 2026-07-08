import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../api.dart';
import '../models.dart';
import '../session.dart';
import '../ui.dart';

/// 製品詳細(/p/:code)。QRの飛び先。カート追加(数量+個別仕様メモ)
class ProductScreen extends StatefulWidget {
  final String code;
  const ProductScreen(this.code, {super.key});
  @override
  State<ProductScreen> createState() => _ProductScreenState();
}

class _ProductScreenState extends State<ProductScreen> {
  Product? data;
  bool notFound = false;
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
      if (mounted) {
        setState(() {
          data = c.byCode(widget.code);
          notFound = data == null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = e);
    }
  }

  Future<void> _addToCart() async {
    if (!Session.i.loggedIn) {
      context.go('/login?next=/p/${widget.code}');
      return;
    }
    final qty = TextEditingController(text: '1');
    final note = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('${data!.name} を見積カートへ'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: qty,
              decoration: const InputDecoration(labelText: '数量'),
              keyboardType: TextInputType.number,
            ),
            TextField(
              controller: note,
              decoration:
                  const InputDecoration(labelText: '個別仕様(色・寸法など)'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('キャンセル')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('追加')),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    try {
      await apiSend('PUT', '/cart/items/${widget.code}', body: {
        'quantity': int.tryParse(qty.text) ?? 1,
        'spec_note': note.text.isEmpty ? null : note.text,
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: const Text('カートに追加しました'),
        action: SnackBarAction(label: 'カートへ', onPressed: () => context.go('/cart')),
      ));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = data;
    return Scaffold(
      appBar: AppBar(title: Text(p?.name ?? widget.code)),
      body: error != null
          ? ErrorView(error!, onRetry: _load)
          : notFound
              ? const Center(child: Text('製品が見つかりません'))
              : p == null
                  ? const LoadingView()
                  : ListView(
                      padding: const EdgeInsets.all(16),
                      children: [
                        for (final url in p.photos)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: CachedNetworkImage(imageUrl: url),
                          ),
                        Text(p.code, style: Theme.of(context).textTheme.labelLarge),
                        if (p.summary != null) Text(p.summary!),
                        if (p.description != null)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 8),
                            child: Text(p.description!),
                          ),
                        const SizedBox(height: 8),
                        Text('仕様', style: Theme.of(context).textTheme.titleMedium),
                        Table(
                          border: TableBorder.all(color: Colors.black12),
                          columnWidths: const {0: FlexColumnWidth(1), 1: FlexColumnWidth(2)},
                          children: [
                            for (final e in p.specs.entries)
                              TableRow(children: [
                                Padding(
                                  padding: const EdgeInsets.all(6),
                                  child: Text(e.key, style: const TextStyle(fontWeight: FontWeight.w600)),
                                ),
                                Padding(padding: const EdgeInsets.all(6), child: Text('${e.value}')),
                              ]),
                            TableRow(children: [
                              const Padding(
                                padding: EdgeInsets.all(6),
                                child: Text('価格', style: TextStyle(fontWeight: FontWeight.w600)),
                              ),
                              Padding(
                                padding: const EdgeInsets.all(6),
                                child: Text(p.priceNote ?? '要見積'),
                              ),
                            ]),
                          ],
                        ),
                        const SizedBox(height: 16),
                        FilledButton.icon(
                          icon: const Icon(Icons.add_shopping_cart),
                          label: const Text('見積カートに入れる'),
                          onPressed: _addToCart,
                        ),
                      ],
                    ),
    );
  }
}
