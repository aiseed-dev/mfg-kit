import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../api.dart';
import '../ui.dart';

/// 見積番号ページ(/q/:no)。見積書・納品書のQRの飛び先。
/// 自分の依頼なら詳細へ、他人の番号は404(02_api)
class QnoScreen extends StatefulWidget {
  final String quoteNo;
  const QnoScreen(this.quoteNo, {super.key});
  @override
  State<QnoScreen> createState() => _QnoScreenState();
}

class _QnoScreenState extends State<QnoScreen> {
  Object? error;
  bool notFound = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      error = null;
      notFound = false;
    });
    try {
      final q = await apiGet('/quotes/by-no/${widget.quoteNo}');
      if (mounted) context.go('/quotes/${q['id']}');
    } catch (e) {
      if (!mounted) return;
      if (e is ApiException && e.status == 404) {
        setState(() => notFound = true);
      } else {
        setState(() => error = e);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.quoteNo)),
      body: error != null
          ? ErrorView(error!, onRetry: _load)
          : notFound
              ? const Center(
                  child: Text('この見積番号の依頼が見つかりません。\nご依頼時のアカウントでログインしていますか?',
                      textAlign: TextAlign.center),
                )
              : const LoadingView(),
    );
  }
}
