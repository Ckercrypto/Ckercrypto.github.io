// Renders preview screenshots: flutter test --update-goldens test/screenshots_test.dart
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sade_factor/main.dart';
import 'package:sade_factor/import/price_import.dart';
import 'package:sade_factor/models.dart';
import 'package:sade_factor/screens/import_items.dart';
import 'package:sade_factor/store.dart';

Future<void> _loadFonts() async {
  final v = FontLoader('Vazirmatn')
    ..addFont(rootBundle.load('assets/fonts/Vazirmatn-Regular.ttf'))
    ..addFont(rootBundle.load('assets/fonts/Vazirmatn-Bold.ttf'));
  await v.load();
  final icons = File(
      '${Platform.environment['FLUTTER_ROOT']}/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf');
  if (icons.existsSync()) {
    final m = FontLoader('MaterialIcons')
      ..addFont(Future.value(ByteData.sublistView(icons.readAsBytesSync())));
    await m.load();
  }
}

AppStore _demo() {
  final s = AppStore()..persist = false;
  s.business.name = 'ترانس رضا';
  s.themeMode = ThemeMode.light;
  final c1 = Customer(name: 'شرکت پارس الکتریک', kind: CustomerKind.company, economicCode: '411111111111');
  final c2 = Customer(name: 'علی محمدی', phone: '09151234567');
  s.upsertCustomer(c1);
  s.upsertCustomer(c2);
  final i1 = Item(name: 'استابلایزر ۵ کیلووات', price: 185000000, stuffId: '2720000000013');
  final i2 = Item(name: 'ترانس ۱۰ آمپر', price: 42000000);
  s.upsertItem(i1);
  s.upsertItem(i2);
  final now = DateTime.now();
  final data = [
    (c1, 40, 3, true), (c2, 25, 1, false), (c1, 3, 2, false),
    (c2, 70, 1, true), (c1, 100, 4, true), (c1, 130, 2, true), (c2, 1, 1, false),
  ];
  for (final d in data) {
    final inv = Invoice(
      number: s.nextNumber,
      date: now.subtract(Duration(days: d.$2)),
      customerId: d.$1.id,
      customerName: d.$1.name,
      type: d.$1.canReceiveType1 ? InvoiceType.withBuyer : InvoiceType.consumer,
      lines: [InvoiceLine.fromItem(i1)..qty = d.$3.toDouble(), InvoiceLine.fromItem(i2)],
      status: InvoiceStatus.issued,
      paid: d.$4,
    );
    s.saveInvoice(inv);
  }
  s.saveInvoice(Invoice(number: s.nextNumber, customerName: 'مشتری عمومی', lines: [InvoiceLine.fromItem(i2)]));
  return s;
}

void main() {
  setUpAll(_loadFonts);

  Future<void> shot(WidgetTester t, Size size, double dpr, String name,
      Future<void> Function()? go) async {
    debugDisableShadows = false;
    t.view.physicalSize = size * dpr;
    t.view.devicePixelRatio = dpr;
    addTearDown(t.view.reset);
    await t.pumpWidget(SadeFactorApp(store: _demo()));
    await t.pumpAndSettle();
    if (go != null) await go();
    await t.pumpAndSettle(const Duration(seconds: 1));
    await expectLater(find.byType(MaterialApp), matchesGoldenFile('../shots/$name.png'));
    debugDisableShadows = true;
  }

  const phone = Size(390, 844);
  testWidgets('dashboard phone', (t) => shot(t, phone, 2, 'phone-dashboard', null));
  testWidgets('import phone', skip: !File('test/fixtures/pricelist.pdf').existsSync(), (t) => shot(t, phone, 2, 'phone-import', () async {
        final rows = importFile('pricelist.pdf', File('test/fixtures/pricelist.pdf').readAsBytesSync()).rows;
        t.state<NavigatorState>(find.byType(Navigator).first).push(MaterialPageRoute(
            builder: (_) => ImportReviewScreen(fileName: 'price list - ups_mehr.pdf', rows: rows)));
      }));
  testWidgets('invoices phone', (t) => shot(t, phone, 2, 'phone-invoices', () async {
        await t.tap(find.text('فاکتورها').last);
      }));
  testWidgets('editor phone', (t) => shot(t, phone, 2, 'phone-editor', () async {
        await t.tap(find.text('فاکتور جدید').first);
        await t.pumpAndSettle();
        await t.tap(find.text('شرکت پارس الکتریک'));
        await t.pumpAndSettle();
        await t.tap(find.textContaining('استابلایزر').first);
        await t.pumpAndSettle();
        await t.tap(find.textContaining('ترانس ۱۰').first);
      }));
  testWidgets('view phone', (t) => shot(t, phone, 2, 'phone-view', () async {
        await t.tap(find.text('فاکتورها').last);
        await t.pumpAndSettle();
        await t.tap(find.text('شرکت پارس الکتریک').first);
      }));
  testWidgets('desktop', (t) => shot(t, const Size(1366, 800), 1, 'desktop-dashboard', null));
}
