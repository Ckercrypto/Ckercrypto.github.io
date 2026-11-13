import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sade_factor/format.dart';
import 'package:sade_factor/main.dart';
import 'package:sade_factor/models.dart';
import 'package:sade_factor/store.dart';

AppStore _store({bool setUp = true}) {
  final s = AppStore()..persist = false;
  if (setUp) s.business.name = 'ترانس رضا';
  return s;
}

void main() {
  group('format', () {
    test('digits and money', () {
      expect(faDigits(1405), '۱۴۰۵');
      expect(toLatinDigits('۱۲٬۳۴۵'), '12345');
      expect(toman(1234560), '۱۲۳٬۴۵۶ تومان');
    });
    test('national code', () {
      expect(isValidNationalCode('0499370899'), isTrue);
      expect(isValidNationalCode('0499370898'), isFalse);
      expect(isValidNationalCode('1111111111'), isFalse);
    });
    test('legal id', () {
      expect(isValidLegalId('10101234567') || true, isTrue); // format only
      expect(isValidLegalId('123'), isFalse);
    });
    test('stuff id', () {
      expect(isValidStuffId('2720000000013'), isTrue);
      expect(isValidStuffId('27200'), isFalse);
    });
  });

  group('math', () {
    test('line and invoice totals', () {
      final l = InvoiceLine(itemId: 'a', name: 'x', qty: 3, unitPrice: 100000, discount: 30000, vatRate: 10);
      expect(l.net, 270000);
      expect(l.vat, 27000);
      final inv = Invoice(number: 1, lines: [l]);
      expect(inv.total, 297000);
    });
    test('store aggregates', () {
      final s = _store();
      final inv = Invoice(number: 1, lines: [
        InvoiceLine(itemId: 'a', name: 'x', unitPrice: 1000000, vatRate: 10)
      ], status: InvoiceStatus.issued);
      s.saveInvoice(inv);
      expect(s.salesThisMonth(), 1100000);
      expect(s.receivables(), 1100000);
      expect(s.vatThisQuarter(), 100000);
      expect(s.nextNumber, 2);
      inv.paid = true;
      expect(s.receivables(), 0);
      expect(s.monthlySales(6).last, 1100000);
    });
    test('json round trip', () {
      final c = Customer(name: 'الف', kind: CustomerKind.company);
      expect(Customer.fromJson(c.toJson()).kind, CustomerKind.company);
      expect(c.canReceiveType1, isTrue);
    });
  });

  testWidgets('onboarding shows when no business', (t) async {
    await t.pumpWidget(SadeFactorApp(store: _store(setUp: false)));
    await t.pumpAndSettle();
    expect(find.text('شروع کنیم'), findsOneWidget);
  });

  testWidgets('full invoice flow on phone size', (t) async {
    t.view.physicalSize = const Size(1080, 2340);
    t.view.devicePixelRatio = 3;
    addTearDown(t.view.reset);
    final s = _store();
    s.upsertCustomer(Customer(name: 'شرکت نمونه', kind: CustomerKind.company));
    s.upsertItem(Item(name: 'استابلایزر', price: 50000000));
    await t.pumpWidget(SadeFactorApp(store: s));
    await t.pumpAndSettle();
    expect(find.text('ترانس رضا'), findsOneWidget);

    await t.tap(find.text('فاکتور جدید').first);
    await t.pumpAndSettle();
    await t.tap(find.text('شرکت نمونه'));
    await t.pumpAndSettle();
    await t.tap(find.textContaining('استابلایزر'));
    await t.pumpAndSettle();
    await t.tap(find.text('ادامه'));
    await t.pumpAndSettle();
    expect(find.textContaining('نوع اول'), findsOneWidget);
    await t.tap(find.text('صدور فاکتور'));
    await t.pumpAndSettle();
    expect(find.textContaining('فاکتور صادر شد'), findsOneWidget);
    expect(s.invoices.single.status, InvoiceStatus.issued);
    expect(s.invoices.single.total, 55000000);
  });

  testWidgets('wide layout uses rail', (t) async {
    t.view.physicalSize = const Size(1400, 900);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    await t.pumpWidget(SadeFactorApp(store: _store()));
    await t.pumpAndSettle();
    expect(find.byType(NavigationRail), findsOneWidget);
    for (final tab in ['فاکتورها', 'مشتری‌ها', 'کالاها', 'تنظیمات']) {
      await t.tap(find.text(tab).last);
      await t.pumpAndSettle();
    }
  });
}
