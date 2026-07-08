import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../api.dart';
import '../models.dart';
import '../ui.dart';

/// 依頼一覧(/quotes)。状態バッジ: 依頼中/回答済み/受注/完了(C-07)
class QuotesScreen extends StatefulWidget {
  const QuotesScreen({super.key});
  @override
  State<QuotesScreen> createState() => _QuotesScreenState();
}

class _QuotesScreenState extends State<QuotesScreen> {
  List<QuoteListItem>? data;
  Object? error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => error = null);
    try {
      final rows = await apiGet('/quotes') as List;
      if (mounted) {
        setState(
            () => data = [for (final r in rows) QuoteListItem.fromJson(r)]);
      }
    } catch (e) {
      if (mounted) setState(() => error = e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final rows = data;
    return Scaffold(
      appBar: AppBar(title: const Text('見積依頼')),
      body: error != null
          ? ErrorView(error!, onRetry: _load)
          : rows == null
              ? const LoadingView()
              : rows.isEmpty
                  ? const Center(child: Text('依頼はまだありません'))
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView(
                        children: [
                          for (final q in rows)
                            ListTile(
                              leading: StatusBadge(q.status),
                              title: Text(q.quoteNo),
                              subtitle: Text(
                                q.lastMessage ?? q.createdAt.substring(0, 10),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                              onTap: () => context.go('/quotes/${q.id}'),
                            ),
                        ],
                      ),
                    ),
    );
  }
}
