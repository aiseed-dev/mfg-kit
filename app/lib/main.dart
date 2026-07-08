import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'screens/cart.dart';
import 'screens/category.dart';
import 'screens/home.dart';
import 'screens/login.dart';
import 'screens/product.dart';
import 'screens/qno.dart';
import 'screens/quote_detail.dart';
import 'screens/quotes.dart';
import 'screens/register.dart';
import 'screens/scan.dart';
import 'session.dart';

void main() => runApp(const MfgApp());

/// 認証が要るパス(未ログインなら /login?next= へ)
const _authPaths = ['/cart', '/quotes', '/q/'];

final _router = GoRouter(
  redirect: (context, state) {
    final path = state.uri.path;
    final needsAuth = _authPaths.any((p) => path.startsWith(p));
    if (needsAuth && !Session.i.loggedIn) {
      return '/login?next=${Uri.encodeComponent(path)}';
    }
    return null;
  },
  routes: [
    GoRoute(path: '/', builder: (_, s) => const HomeScreen()),
    GoRoute(
      path: '/c/:slug',
      builder: (_, s) => CategoryScreen(s.pathParameters['slug']!),
    ),
    GoRoute(
      path: '/p/:code',
      builder: (_, s) => ProductScreen(s.pathParameters['code']!),
    ),
    GoRoute(path: '/cart', builder: (_, s) => const CartScreen()),
    GoRoute(path: '/quotes', builder: (_, s) => const QuotesScreen()),
    GoRoute(
      path: '/quotes/:id',
      builder: (_, s) => QuoteDetailScreen(s.pathParameters['id']!),
    ),
    GoRoute(
      path: '/q/:no',
      builder: (_, s) => QnoScreen(s.pathParameters['no']!),
    ),
    GoRoute(path: '/scan', builder: (_, s) => const ScanScreen()),
    GoRoute(
      path: '/login',
      builder: (_, s) => LoginScreen(next: s.uri.queryParameters['next']),
    ),
    GoRoute(path: '/register', builder: (_, s) => const RegisterScreen()),
  ],
);

class MfgApp extends StatelessWidget {
  const MfgApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: '製品カタログ・見積依頼',
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF14532D),
        useMaterial3: true,
      ),
      routerConfig: _router,
    );
  }
}
