import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../session.dart';

/// ログイン(C-01。PocketBase)
class LoginScreen extends StatefulWidget {
  final String? next;
  const LoginScreen({this.next, super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final email = TextEditingController();
  final password = TextEditingController();
  String? error;
  bool busy = false;

  Future<void> _login() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await Session.i.login(email.text.trim(), password.text);
      if (mounted) context.go(widget.next ?? '/');
    } catch (e) {
      setState(() => error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('ログイン')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 360),
          child: ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.all(24),
            children: [
              TextField(
                controller: email,
                decoration: const InputDecoration(labelText: 'メールアドレス'),
                keyboardType: TextInputType.emailAddress,
              ),
              TextField(
                controller: password,
                decoration: const InputDecoration(labelText: 'パスワード'),
                obscureText: true,
                onSubmitted: (_) => _login(),
              ),
              if (error != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(error!, style: const TextStyle(color: Colors.red)),
                ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: busy ? null : _login,
                child: const Text('ログイン'),
              ),
              TextButton(
                onPressed: () => context.go('/register'),
                child: const Text('はじめての方(登録)'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
