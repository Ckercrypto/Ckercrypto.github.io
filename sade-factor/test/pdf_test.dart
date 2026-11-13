import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:sade_factor/models.dart';
import 'package:sade_factor/pdf_invoice.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('pdf builds', () async {
    final c = Customer(name: 'شرکت پارس الکتریک', kind: CustomerKind.company, nationalId: '10101234567', economicCode: '411111111111');
    final inv = Invoice(number: 12, customerId: c.id, type: InvoiceType.withBuyer, status: InvoiceStatus.issued, note: 'تحویل در محل', lines: [
      InvoiceLine(itemId: 'a', name: 'استابلایزر ۵ کیلووات', stuffId: '2720000000013', qty: 2, unitPrice: 185000000, vatRate: 10),
      InvoiceLine(itemId: 'b', name: 'ترانس ۱۰ آمپر', qty: 1, unitPrice: 42000000, discount: 2000000, vatRate: 10),
    ]);
    final bytes = await buildInvoicePdf(inv: inv, biz: Business(name: 'ترانس رضا', phone: '05138000000', address: 'مشهد'), customer: c);
    File('shots/sample-invoice.pdf').writeAsBytesSync(bytes);
    expect(bytes.length, greaterThan(1000));
  });
}
