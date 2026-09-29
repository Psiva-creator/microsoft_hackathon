import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:incident_brain_ui/main.dart';

void main() {
  testWidgets('IncidentBrainApp smoke test', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;

    await tester.pumpWidget(const IncidentBrainApp());
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byType(IncidentBrainApp), findsOneWidget);

    // Reset surface size after test
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });
  });
}
