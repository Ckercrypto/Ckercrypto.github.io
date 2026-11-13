import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:sade_factor/models.dart';
import 'package:sade_factor/pdf_invoice.dart';

String _b64(String f) => base64Encode(File('test/fixtures/$f').readAsBytesSync());

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final biz = Business(
    name: 'ترانس رضا',
    phone: '05138000000',
    address: 'مشهد',
    vatRegistered: false,
    logo: _b64('logo.png'),
    signature: _b64('signature.png'),
    stamp: _b64('stamp.png'),
  );
  final c = Customer(name: 'شرکت پارس الکتریک', kind: CustomerKind.company, nationalId: '10101234567', economicCode: '411111111111');
  List<InvoiceLine> lines() => [
        InvoiceLine(itemId: 'a', name: 'استابلایزر ۵ کیلووات', stuffId: '2720000000013', qty: 2, unitPrice: 185000000, vatRate: 0, discountIsPercent: true, discountPercent: 5),
        InvoiceLine(itemId: 'b', name: 'ترانس ۱۰ آمپر', qty: 1, unitPrice: 42000000, discountAmount: 2000000, vatRate: 0),
        InvoiceLine(itemId: 'c', name: 'محافظ یخچال', qty: 3, unitPrice: 9500000, vatRate: 0),
      ];

  test('invoice pdf with seal, no VAT', () async {
    final inv = Invoice(number: 12, customerId: c.id, type: InvoiceType.withBuyer, status: InvoiceStatus.issued, note: 'تحویل در محل', lines: lines());
    final bytes = await buildInvoicePdf(inv: inv, biz: biz, customer: c, withSeal: true);
    File('shots/sample-invoice.pdf').writeAsBytesSync(bytes);
    expect(bytes.length, greaterThan(1000));
  });

  test('proforma pdf without seal', () async {
    final inv = Invoice(number: 3, kind: DocKind.proforma, customerId: c.id, status: InvoiceStatus.issued, lines: lines());
    final bytes = await buildInvoicePdf(inv: inv, biz: biz, customer: c);
    File('shots/sample-proforma.pdf').writeAsBytesSync(bytes);
    expect(bytes.length, greaterThan(1000));
  });
}
