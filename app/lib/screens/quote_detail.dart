import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../api.dart';
import '../models.dart';
import '../ui.dart';

/// 依頼詳細(/quotes/:id): 品目+状態+メッセージ(添付可)。
/// 回答受領後に「発注する」(C-05/C-06。正式契約は商流で)
class QuoteDetailScreen extends StatefulWidget {
  final String id;
  const QuoteDetailScreen(this.id, {super.key});
  @override
  State<QuoteDetailScreen> createState() => _QuoteDetailScreenState();
}

class _QuoteDetailScreenState extends State<QuoteDetailScreen> {
  QuoteDetail? quote;
  List<Message>? messages;
  Object? error;
  final input = TextEditingController();
  bool sending = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => error = null);
    try {
      final q = await apiGet('/quotes/${widget.id}');
      final m = await apiGet('/quotes/${widget.id}/messages') as List;
      if (mounted) {
        setState(() {
          quote = QuoteDetail.fromJson(q);
          messages = [for (final r in m) Message.fromJson(r)];
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = e);
    }
  }

  Future<void> _send({bool withPhoto = false}) async {
    List<int>? bytes;
    String? name;
    if (withPhoto) {
      final img = await ImagePicker().pickImage(source: ImageSource.gallery);
      if (img == null) return;
      bytes = await img.readAsBytes();
      name = img.name;
    }
    if (input.text.isEmpty && bytes == null) return;
    setState(() => sending = true);
    try {
      await apiPostMessage(
        widget.id,
        input.text.isEmpty ? '(添付)' : input.text,
        fileBytes: bytes,
        fileName: name,
      );
      input.clear();
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => sending = false);
    }
  }

  Future<void> _patch(String status, String confirmText) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        content: Text(confirmText),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('キャンセル')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('OK')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await apiSend('PATCH', '/quotes/${widget.id}', body: {'status': status});
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final q = quote;
    return Scaffold(
      appBar: AppBar(
        title: Text(q?.quoteNo ?? ''),
        actions: [if (q != null) Padding(padding: const EdgeInsets.only(right: 12), child: Center(child: StatusBadge(q.status)))],
      ),
      body: error != null
          ? ErrorView(error!, onRetry: _load)
          : q == null
              ? const LoadingView()
              : Column(
                  children: [
                    Expanded(
                      child: ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          Card(
                            child: Padding(
                              padding: const EdgeInsets.all(12),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  for (final i in q.items)
                                    Text(
                                      '・${i.name}(${i.code})× ${i.quantity}'
                                      '${i.specNote != null ? " / ${i.specNote}" : ""}',
                                    ),
                                  if (q.note != null)
                                    Padding(
                                      padding: const EdgeInsets.only(top: 8),
                                      child: Text('要望: ${q.note}'),
                                    ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: 8),
                          for (final m in messages ?? <Message>[])
                            Align(
                              alignment: m.isMine
                                  ? Alignment.centerRight
                                  : Alignment.centerLeft,
                              child: Card(
                                color: m.isMine
                                    ? Theme.of(context).colorScheme.primaryContainer
                                    : null,
                                child: Padding(
                                  padding: const EdgeInsets.all(10),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(m.body),
                                      if (m.hasFile)
                                        const Text('📎 添付あり',
                                            style: TextStyle(fontSize: 12)),
                                      Text(
                                        m.sentAt.substring(0, 16).replaceFirst('T', ' '),
                                        style: const TextStyle(
                                            fontSize: 11, color: Colors.grey),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          if (q.status == 'answered')
                            Padding(
                              padding: const EdgeInsets.symmetric(vertical: 8),
                              child: FilledButton.icon(
                                icon: const Icon(Icons.check_circle_outline),
                                label: const Text('発注する'),
                                onPressed: () => _patch(
                                  'ordered',
                                  'この内容で発注の意向を伝えます。正式な契約・支払いは従来どおりの商流で行います。',
                                ),
                              ),
                            ),
                          if (q.status == 'requested' || q.status == 'answered')
                            TextButton(
                              onPressed: () =>
                                  _patch('cancelled', 'この依頼を取り下げますか?'),
                              child: const Text('依頼を取り下げる'),
                            ),
                        ],
                      ),
                    ),
                    SafeArea(
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                        child: Row(
                          children: [
                            IconButton(
                              icon: const Icon(Icons.photo_outlined),
                              tooltip: '写真を添付',
                              onPressed: sending ? null : () => _send(withPhoto: true),
                            ),
                            Expanded(
                              child: TextField(
                                controller: input,
                                decoration: const InputDecoration(
                                  hintText: 'メッセージ(仕様の相談・質問など)',
                                  border: OutlineInputBorder(),
                                  isDense: true,
                                ),
                              ),
                            ),
                            IconButton(
                              icon: const Icon(Icons.send),
                              onPressed: sending ? null : _send,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
    );
  }
}
