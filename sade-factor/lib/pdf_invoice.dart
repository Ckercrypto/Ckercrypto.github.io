import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/services.dart' show rootBundle;
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

import 'format.dart';
import 'models.dart';

/// Builds an A4 (or A5) RTL invoice PDF.
Future<Uint8List> buildInvoicePdf({
  required Invoice inv,
  required Business biz,
  Customer? customer,
  PdfPageFormat format = PdfPageFormat.a4,
  bool withSeal = false,
}) async {
  pw.MemoryImage? img(String b64) {
    if (b64.isEmpty) return null;
    try {
      return pw.MemoryImage(base64Decode(b64));
    } catch (_) {
      return null;
    }
  }

  final logo = img(biz.logo);
  final sign = withSeal ? img(biz.signature) : null;
  final stamp = withSeal ? img(biz.stamp) : null;
  final reg = pw.Font.ttf(await rootBundle.load('assets/fonts/Vazirmatn-Regular.ttf'));
  final bold = pw.Font.ttf(await rootBundle.load('assets/fonts/Vazirmatn-Bold.ttf'));
  final theme = pw.ThemeData.withFont(base: reg, bold: bold);
  const teal = PdfColor.fromInt(0xFF0FA3A3);
  const light = PdfColor.fromInt(0xFFEFF7F7);

  pw.Widget kv(String k, String v) => pw.Padding(
        padding: const pw.EdgeInsets.symmetric(vertical: 2),
        child: pw.Row(children: [
          pw.Text('$k: ', style: const pw.TextStyle(color: PdfColors.grey700, fontSize: 9)),
          pw.Expanded(child: pw.Text(v.isEmpty ? '-' : _z(v), style: const pw.TextStyle(fontSize: 9))),
        ]),
      );

  pw.Widget party(String title, List<pw.Widget> rows) => pw.Expanded(
        child: pw.Container(
          padding: const pw.EdgeInsets.all(10),
          decoration: pw.BoxDecoration(
              color: light, borderRadius: pw.BorderRadius.circular(8)),
          child: pw.Column(
              crossAxisAlignment: pw.CrossAxisAlignment.start,
              children: [
                pw.Text(title,
                    style: pw.TextStyle(fontWeight: pw.FontWeight.bold, color: teal)),
                pw.SizedBox(height: 4),
                ...rows,
              ]),
        ),
      );

  final hasDisc = inv.discount > 0;
  final hasVat = inv.vat > 0;
  // (header, flex, cell) — written in reading order (right to left).
  final cols = <(String, double, String Function(int i))>[
    ('ردیف', 0, (i) => faDigits(i + 1)),
    ('شرح کالا یا خدمت', 3, (i) => _z(inv.lines[i].name)),
    if (!inv.isProforma) ('شناسه کالا', 1.5, (i) => faDigits(inv.lines[i].stuffId)),
    ('تعداد', 1.1, (i) => '${num0(inv.lines[i].qty)} ${inv.lines[i].unit}'),
    ('فی (ریال)', 1.4, (i) => faDigits(groupThousands(inv.lines[i].unitPrice))),
    if (hasDisc)
      ('تخفیف (ریال)', 1.4, (i) {
        final l = inv.lines[i];
        if (l.discount == 0) return '-';
        final amt = faDigits(groupThousands(l.discount));
        return l.discountIsPercent ? '$amt\n(${num0(l.discountPercent)}٪)' : amt;
      }),
    if (hasVat) ('مالیات', 1.1, (i) => faDigits(groupThousands(inv.lines[i].vat))),
    ('جمع (ریال)', 1.6, (i) => faDigits(groupThousands(inv.lines[i].total))),
  ];
  final headers = [for (final c in cols) c.$1];
  final data = <List<String>>[
    for (var i = 0; i < inv.lines.length; i++) [for (final c in cols) c.$3(i)]
  ];
  final n = cols.length;
  final widths = <int, pw.TableColumnWidth>{
    for (var k = 0; k < n; k++)
      // reversed index: column k in reading order sits at n-1-k
      n - 1 - k: cols[k].$2 == 0
          ? const pw.FixedColumnWidth(34)
          : pw.FlexColumnWidth(cols[k].$2),
  };
  final title = inv.isProforma
      ? 'پیش فاکتور'
      : inv.type == InvoiceType.withBuyer
          ? 'صورتحساب فروش کالا و خدمات'
          : 'صورتحساب فروش (مصرف کننده)';

  final doc = pw.Document(theme: theme, title: '${_z(inv.kindLabel)} ${inv.number}');
  doc.addPage(pw.MultiPage(
    pageFormat: format,
    textDirection: pw.TextDirection.rtl,
    margin: const pw.EdgeInsets.all(28),
    build: (ctx) => [
      pw.Row(crossAxisAlignment: pw.CrossAxisAlignment.start, children: [
        if (logo != null) ...[
          pw.Container(
            width: 64,
            height: 64,
            child: pw.Image(logo, fit: pw.BoxFit.contain),
          ),
          pw.SizedBox(width: 10),
        ],
        pw.Expanded(
          child: pw.Column(crossAxisAlignment: pw.CrossAxisAlignment.start, children: [
            pw.Text(_z(biz.name),
                style: pw.TextStyle(fontSize: 18, fontWeight: pw.FontWeight.bold)),
            pw.Text(title,
                style: pw.TextStyle(
                    color: inv.isProforma ? teal : PdfColors.grey700,
                    fontWeight: inv.isProforma ? pw.FontWeight.bold : null,
                    fontSize: inv.isProforma ? 14 : null)),
          ]),
        ),
        pw.Column(crossAxisAlignment: pw.CrossAxisAlignment.end, children: [
          pw.Container(
            padding: const pw.EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: pw.BoxDecoration(color: teal, borderRadius: pw.BorderRadius.circular(6)),
            child: pw.Text('${inv.isProforma ? 'پیش فاکتور ' : ''}شماره ${faDigits(inv.number)}',
                style: pw.TextStyle(color: PdfColors.white, fontWeight: pw.FontWeight.bold)),
          ),
          pw.SizedBox(height: 4),
          pw.Text('تاریخ ${jDate(inv.date)}'),
          if (inv.status == InvoiceStatus.cancelled)
            pw.Text('ابطال شده', style: pw.TextStyle(color: PdfColors.red, fontWeight: pw.FontWeight.bold)),
          if (inv.status == InvoiceStatus.draft)
            pw.Text('پیش نویس', style: const pw.TextStyle(color: PdfColors.grey)),
        ]),
      ]),
      pw.SizedBox(height: 14),
      pw.Row(children: [
        party('فروشنده', [
          kv('نام', biz.name),
          kv('کد/شناسه ملی', faDigits(biz.nationalId)),
          kv('کد اقتصادی', faDigits(biz.economicCode)),
          kv('تلفن', faDigits(biz.phone)),
          kv('نشانی', biz.address),
        ]),
        pw.SizedBox(width: 10),
        party('خریدار', [
          kv('نام', customer?.name ?? (inv.customerName.isEmpty ? 'مشتری عمومی' : inv.customerName)),
          kv('کد/شناسه ملی', faDigits(customer?.nationalId ?? '')),
          kv('کد اقتصادی', faDigits(customer?.economicCode ?? '')),
          kv('تلفن', faDigits(customer?.phone ?? '')),
          kv('نشانی', customer?.address ?? ''),
        ]),
      ]),
      pw.SizedBox(height: 14),
      // pdf tables lay out left-to-right, so reverse columns for RTL reading.
      pw.TableHelper.fromTextArray(
        headers: headers.reversed.toList(),
        data: [for (final r in data) r.reversed.toList()],
        headerStyle: pw.TextStyle(color: PdfColors.white, fontWeight: pw.FontWeight.bold, fontSize: 9),
        headerDecoration: const pw.BoxDecoration(color: teal),
        cellStyle: const pw.TextStyle(fontSize: 9),
        cellAlignment: pw.Alignment.center,
        cellAlignments: {n - 2: pw.Alignment.centerRight},
        columnWidths: widths,
        oddRowDecoration: const pw.BoxDecoration(color: light),
        border: null,
      ),
      pw.SizedBox(height: 12),
      pw.Row(crossAxisAlignment: pw.CrossAxisAlignment.start, children: [
        pw.Expanded(
          child: inv.note.isEmpty
              ? pw.SizedBox()
              : pw.Text('توضیحات: ${_z(inv.note)}', style: const pw.TextStyle(fontSize: 9)),
        ),
        pw.SizedBox(width: 20),
        pw.Container(
          width: 220,
          padding: const pw.EdgeInsets.all(10),
          decoration: pw.BoxDecoration(color: light, borderRadius: pw.BorderRadius.circular(8)),
          child: pw.Column(children: [
            _sum('جمع کل', inv.gross),
            if (hasDisc) _sum('جمع تخفیف ها', inv.discount),
            if (hasDisc) _sum('جمع بعد از تخفیف', inv.net),
            if (hasVat) _sum('مالیات بر ارزش افزوده', inv.vat),
            pw.Divider(color: PdfColors.grey400),
            _sum('مبلغ قابل پرداخت', inv.total, bold: true),
            pw.SizedBox(height: 2),
            pw.Align(
              alignment: pw.Alignment.centerLeft,
              child: pw.Text('(${toman(inv.total)})',
                  style: const pw.TextStyle(fontSize: 8, color: PdfColors.grey700)),
            ),
          ]),
        ),
      ]),
      pw.SizedBox(height: 24),
      pw.Row(crossAxisAlignment: pw.CrossAxisAlignment.start, children: [
        pw.Expanded(
          child: pw.Column(children: [
            pw.Text('مهر و امضای فروشنده', style: const pw.TextStyle(color: PdfColors.grey700)),
            pw.SizedBox(height: 4),
            pw.SizedBox(
              height: 110,
              width: 200,
              child: pw.Stack(alignment: pw.Alignment.center, children: [
                if (stamp != null)
                  pw.Positioned.fill(
                      child: pw.Image(stamp, fit: pw.BoxFit.contain)),
                if (sign != null)
                  pw.Positioned(
                    left: 20,
                    right: 20,
                    top: 15,
                    bottom: 15,
                    child: pw.Image(sign, fit: pw.BoxFit.contain),
                  ),
              ]),
            ),
          ]),
        ),
        pw.Expanded(
          child: pw.Column(children: [
            pw.Text(inv.isProforma ? 'تأیید خریدار' : 'مهر و امضای خریدار',
                style: const pw.TextStyle(color: PdfColors.grey700)),
          ]),
        ),
      ]),
    ],
    footer: (ctx) => pw.Align(
      alignment: pw.Alignment.center,
      child: pw.Text('ساخته شده با ساده فاکتور',
          style: const pw.TextStyle(fontSize: 7, color: PdfColors.grey500)),
    ),
  ));
  return doc.save();
}

pw.Widget _sum(String k, int rial, {bool bold = false}) => pw.Padding(
      padding: const pw.EdgeInsets.symmetric(vertical: 2),
      child: pw.Row(children: [
        pw.Expanded(
            child: pw.Text(k,
                style: pw.TextStyle(fontWeight: bold ? pw.FontWeight.bold : null))),
        pw.Text('${faDigits(groupThousands(rial))} ریال',
            style: pw.TextStyle(fontWeight: bold ? pw.FontWeight.bold : null)),
      ]),
    );

/// The PDF text shaper does not handle zero-width non-joiners well.
String _z(String s) => s.replaceAll('\u200c', ' ');
