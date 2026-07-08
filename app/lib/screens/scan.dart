import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

/// QR読み取り(/scan。C-08)。銘板・紙カタログ・見積書のQRから直行
class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});
  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  bool handled = false;

  void _onDetect(BarcodeCapture capture) {
    if (handled) return;
    for (final barcode in capture.barcodes) {
      final raw = barcode.rawValue;
      if (raw == null) continue;
      // QRの中身はこのアプリのURL(/p/{code} か /q/{quote_no})
      final uri = Uri.tryParse(raw);
      if (uri == null) continue;
      final path = uri.path;
      if (path.startsWith('/p/') || path.startsWith('/q/')) {
        handled = true;
        context.go(path);
        return;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('QR読み取り')),
      body: Column(
        children: [
          Expanded(child: MobileScanner(onDetect: _onDetect)),
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text('銘板・カタログ・見積書のQRコードをかざしてください'),
          ),
        ],
      ),
    );
  }
}
