import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../api.dart';
import '../models.dart';
import '../ui.dart';

/// 見積カート(/cart)→「見積を依頼する」(C-03/C-04)
class CartScreen extends StatefulWidget {
  const CartScreen({super.key});
  @override
  State<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends State<CartScreen> {
  List<CartItem>? data;
  Object? error;
  final note = TextEditingController();
  bool sending = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => error = null);
    try {
      final rows = await apiGet('/cart') as List;
      if (mounted) {
        setState(() => data = [for (final r in rows) CartItem.fromJson(r)]);
      }
    } catch (e) {
      if (mounted) setState(() => error = e);
    }
  }

  Future<void> _delete(String code) async {
    await apiSend('DELETE', '/cart/items/$code');
    await _load();
  }

  Future<void> _send() async {
    setState(() => sending = true);
    try {
      final q = await apiSend('POST', '/quotes',
          body: {'note': note.text.isEmpty ? null : note.text});
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('見積依頼 ${q['quote_no']} を送信しました')),
      );
      context.go('/quotes/${q['id']}');
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final items = data;
    return Scaffold(
      appBar: AppBar(title: const Text('見積カート')),
      body: error != null
          ? ErrorView(error!, onRetry: _load)
          : items == null
              ? const LoadingView()
              : items.isEmpty
                  ? const Center(child: Text('カートは空です'))
                  : ListView(
                      padding: const EdgeInsets.all(16),
                      children: [
                        for (final i in items)
                          Card(
                            child: ListTile(
                              title: Text('${i.name}(${i.code})'),
                              subtitle: Text([
                                '数量: ${i.quantity}',
                                if (i.specNote != null) '仕様: ${i.specNote}',
                                i.priceNote ?? '要見積',
                              ].join(' / ')),
                              trailing: IconButton(
                                icon: const Icon(Icons.delete_outline),
                                onPressed: () => _delete(i.code),
                              ),
                              onTap: () => context.go('/p/${i.code}'),
                            ),
                          ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: note,
                          maxLines: 3,
                          decoration: const InputDecoration(
                            labelText: '要望(用途・数量・希望納期など)',
                            border: OutlineInputBorder(),
                          ),
                        ),
                        const SizedBox(height: 12),
                        FilledButton.icon(
                          icon: const Icon(Icons.send),
                          label: const Text('見積を依頼する'),
                          onPressed: sending ? null : _send,
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          '送信後、担当者から回答をお送りします。正式な契約・支払いは従来どおりの商流で行います。',
                          style: TextStyle(fontSize: 12, color: Colors.grey),
                        ),
                      ],
                    ),
    );
  }
}
