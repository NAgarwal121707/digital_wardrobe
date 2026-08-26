import 'package:flutter_test/flutter_test.dart';
import 'package:digital_wardrobe_flutter/main.dart';

void main() {
  testWidgets('Digital Wardrobe app starts', (tester) async {
    await tester.pumpWidget(const DigitalWardrobeApp());
    expect(find.text('Digital Wardrobe'), findsOneWidget);
  });
}
