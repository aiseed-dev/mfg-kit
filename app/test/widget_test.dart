import 'package:flutter_test/flutter_test.dart';
import 'package:mfg_app/main.dart';

void main() {
  testWidgets('起動してカタログホームが出る(読込中でクラッシュしない)',
      (tester) async {
    await tester.pumpWidget(const MfgApp());
    expect(find.text('製品カタログ'), findsOneWidget);
  });
}
