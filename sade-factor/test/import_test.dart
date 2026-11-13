import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:excel/excel.dart' as xl;
import 'package:flutter_test/flutter_test.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:flutter/material.dart';
import 'package:sade_factor/import/price_import.dart';
import 'package:sade_factor/models.dart';
import 'package:sade_factor/screens/import_items.dart';
import 'package:sade_factor/store.dart';

final _hasFixture = File('test/fixtures/pricelist.pdf').existsSync();

void main() {
  test('real supplier pdf (UPS price list)', skip: !_hasFixture, () {
    final r = importFile(
        'pricelist.pdf', File('test/fixtures/pricelist.pdf').readAsBytesSync());
    expect(r.error, isNull);
    final b = StringBuffer();
    for (final x in r.rows) {
      b.writeln(
          '${x.selected ? "[x]" : "[ ]"} ${x.suspicious ? "!" : " "} ${x.price} | ${x.name}');
    }
    File('/tmp/import_out.txt').writeAsStringSync(b.toString());
    final byName = {for (final x in r.rows) x.name: x};
    expect(
        byName['APC UPS lineinteractive 650va 12vdc int battery 1*7ah']?.price,
        20000);
    expect(
        byName['UPS 500VA/300W, 12V, Line interactive, LCD Display, Pure Sine Wave, Ext. Battery']
            ?.price,
        20000);
    expect(
        byName['UPS Nexus T.L online 60KVA3/3 +-180vdc ext battery (30-50 bat)']
            ?.price,
        1500000);
    expect(
        byName['UPS Galaxy T.B online 120KVA3/3 +-192vdc ext battery (32 bat)']
            ?.price,
        3300000);
    expect(
        byName['UPS Zenix online 6 KVA 192vdc int battery 16*9ah']?.suspicious,
        isTrue);
    expect(
        byName['UPS lineinteractive 600va 12vdc int battery 1*9ah led']
            ?.selected,
        isFalse);
    expect(byName['Batery Cabinet B30']?.price, 100000);
    expect(r.rows.where((x) => x.price != null).length, 43);
  });

  test('persian rtl pdf', () async {
    final font = pw.Font.ttf(File('assets/fonts/Vazirmatn-Regular.ttf')
        .readAsBytesSync()
        .buffer
        .asByteData());
    final doc = pw.Document();
    final data = [
      ['۱', 'استابلایزر ۵ کیلووات تک فاز', 'عدد', '۱۸٬۵۰۰٬۰۰۰'],
      ['۲', 'ترانس ۱۰ آمپر', 'عدد', '4,200,000'],
      ['۳', 'محافظ یخچال برق‌یار', 'عدد', '950000'],
    ];
    doc.addPage(pw.Page(
      pageFormat: PdfPageFormat.a4,
      textDirection: pw.TextDirection.rtl,
      theme: pw.ThemeData.withFont(base: font),
      build: (_) => pw.TableHelper.fromTextArray(
          headers: ['ردیف', 'نام کالا', 'واحد', 'قیمت (تومان)'], data: data),
    ));
    final bytes = Uint8List.fromList(await doc.save());
    final r = importFile('fa.pdf', bytes);
    expect(r.error, isNull);
    final names = r.rows.map((e) => '${e.name}=${e.price}').toList();
    expect(names, contains('استابلایزر ۵ کیلووات تک فاز=18500000'));
    expect(names, contains('ترانس ۱۰ آمپر=4200000'));
  });

  test('xlsx with header row', () {
    final book = xl.Excel.createExcel();
    final s = book[book.getDefaultSheet()!];
    s.appendRow([
      xl.TextCellValue('کد'),
      xl.TextCellValue('شرح کالا'),
      xl.TextCellValue('واحد'),
      xl.TextCellValue('قیمت')
    ]);
    s.appendRow([
      xl.TextCellValue('2720000000013'),
      xl.TextCellValue('استابلایزر ۳ کیلووات'),
      xl.TextCellValue('دستگاه'),
      xl.IntCellValue(12500000)
    ]);
    s.appendRow([
      xl.TextCellValue(''),
      xl.TextCellValue('سیم افشان ۲.۵'),
      xl.TextCellValue('متر'),
      xl.DoubleCellValue(85000)
    ]);
    final r = importFile('list.xlsx', Uint8List.fromList(book.encode()!));
    expect(r.error, isNull);
    expect(r.rows.length, 2);
    expect(r.rows[0].name, 'استابلایزر ۳ کیلووات');
    expect(r.rows[0].price, 12500000);
    expect(r.rows[0].unit, 'دستگاه');
    expect(r.rows[0].stuffId, '2720000000013');
    expect(r.rows[1].price, 85000);
    expect(r.rows[1].unit, 'متر');
  });

  test('csv without header', () {
    const csv = 'محافظ ماشین لباسشویی;450.000\nترانس ۵ آمپر;"1,200,000"\n';
    final r = importFile('a.csv', Uint8List.fromList(utf8.encode(csv)));
    expect(r.rows.map((e) => e.price), [450000, 1200000]);
    expect(r.rows.first.name, 'محافظ ماشین لباسشویی');
  });

  test('docx table', () {
    String tc(String t) => '<w:tc><w:p><w:r><w:t>$t</w:t></w:r></w:p></w:tc>';
    final xml =
        '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:tbl>'
        '<w:tr>${tc('نام کالا')}${tc('قیمت')}</w:tr>'
        '<w:tr>${tc('یو پی اس ۱ کاوا')}${tc('۵۵٬۰۰۰٬۰۰۰')}</w:tr>'
        '<w:tr>${tc('باتری ۹ آمپر')}${tc('3000000')}</w:tr>'
        '</w:tbl></w:body></w:document>';
    final a = Archive()
      ..addFile(ArchiveFile(
          'word/document.xml', utf8.encode(xml).length, utf8.encode(xml)));
    final r = importFile('a.docx', Uint8List.fromList(ZipEncoder().encode(a)!));
    expect(r.rows.map((e) => '${e.name}=${e.price}'),
        ['یو پی اس ۱ کاوا=55000000', 'باتری ۹ آمپر=3000000']);
  });

  test('old formats get a clear message', () {
    expect(importFile('a.xls', Uint8List(4)).error, contains('xlsx'));
  });

  test('store import: unit, duplicates, unselected', () {
    final st = AppStore()..persist = false;
    st.business.vatRegistered = false;
    st.items.add(Item(name: 'ترانس ۵ آمپر', price: 10));
    final rows = [
      ImportRow(name: 'ترانس 5 آمپر', price: 1200),
      ImportRow(name: 'یو پی اس ۱ کاوا', price: 55000),
      ImportRow(name: 'بی‌قیمت ۱۰ آمپر'),
    ];
    final (a, u) = st.importItems(rows, PriceUnit.thousandToman.toRial);
    expect((a, u), (1, 1));
    expect(st.items.length, 2);
    expect(st.itemByName('ترانس ۵ آمپر')!.price, 12000000);
    expect(st.itemByName('یو پی اس ۱ کاوا')!.price, 550000000);
    expect(st.itemByName('یو پی اس ۱ کاوا')!.vatRate, 0);
  });

  testWidgets('review screen imports selected rows', skip: !_hasFixture, (t) async {
    final st = AppStore()..persist = false;
    final rows = importFile('pricelist.pdf',
            File('test/fixtures/pricelist.pdf').readAsBytesSync())
        .rows;
    await t.binding.setSurfaceSize(const Size(420, 900));
    await t.pumpWidget(StoreScope(
      store: st,
      child: MaterialApp(
        builder: (c, w) => Directionality(textDirection: TextDirection.rtl, child: w!),
        home: Builder(
          builder: (c) => Scaffold(
            body: Center(
              child: FilledButton(
                onPressed: () => Navigator.of(c).push(MaterialPageRoute(
                    builder: (_) => ImportReviewScreen(fileName: 'pricelist.pdf', rows: rows))),
                child: const Text('go'),
              ),
            ),
          ),
        ),
      ),
    ));
    await t.tap(find.text('go'));
    await t.pumpAndSettle();
    expect(find.text('بازبینی لیست قیمت'), findsOneWidget);
    expect(find.text('افزودن ۴۳ کالا'), findsOneWidget);
    await t.tap(find.text('هزار تومان'));
    await t.pump();
    await t.tap(find.text('افزودن ۴۳ کالا'));
    await t.pumpAndSettle();
    expect(st.items.length, 43);
    expect(st.itemByName('Batery Cabinet B30')!.price, 1000000000);
    await t.binding.setSurfaceSize(null);
  });
}
