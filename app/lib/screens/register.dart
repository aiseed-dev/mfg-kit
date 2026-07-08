import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../session.dart';

/// 登録(C-01。メール確認は PocketBase 側の設定)
class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});
  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final name = TextEditingController();
  final email = TextEditingController();
  final password = TextEditingController();
  String? error;
  bool busy = false;

  Future<void> _register() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await Session.i
          .register(name.text.trim(), email.text.trim(), password.text);
      if (mounted) context.go('/');
    } catch (e) {
      setState(() => error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('登録')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 360),
          child: ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.all(24),
            children: [
              TextField(
                controller: name,
                decoration: const InputDecoration(labelText: 'お名前'),
              ),
              TextField(
                controller: email,
                decoration: const InputDecoration(labelText: 'メールアドレス'),
                keyboardType: TextInputType.emailAddress,
              ),
              TextField(
                controller: password,
                decoration: const InputDecoration(labelText: 'パスワード(8文字以上)'),
                obscureText: true,
              ),
              if (error != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(error!, style: const TextStyle(color: Colors.red)),
                ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: busy ? null : _register,
                child: const Text('登録する'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
