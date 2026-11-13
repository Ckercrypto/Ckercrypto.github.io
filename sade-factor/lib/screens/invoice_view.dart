import 'package:flutter/material.dart';
import 'package:pdf/pdf.dart';
import 'package:printing/printing.dart';

import '../format.dart';
import '../models.dart';
import '../pdf_invoice.dart';
import '../store.dart';
import '../widgets/common.dart';
import 'invoice_editor.dart';

class InvoiceView extends StatefulWidget {
  final String invoiceId;
  final bool justIssued;
  const InvoiceView({super.key, required this.invoiceId, this.justIssued = false});

  @override
  State<InvoiceView> createState() => _InvoiceViewState();
}

class _InvoiceViewState extends State<InvoiceView> {
  bool _seal = false;

  String get invoiceId => widget.invoiceId;
  bool get justIssued => widget.justIssued;

  @override
  Widget build(BuildContext context) {
    final store = StoreScope.of(context);
    final inv = store.invoices.where((i) => i.id == invoiceId).firstOrNull;
    if (inv == null) {
      return const Scaffold(body: Center(child: Text('این فاکتور دیگه وجود نداره')));
    }
    final biz = store.business;
    final file = '${inv.isProforma ? 'pish-faktor' : 'faktor'}-${inv.number}.pdf';
    final cs = Theme.of(context).colorScheme;
    final customer = store.customerById(inv.customerId);

    Future<void> printIt() async {
      await Printing.layoutPdf(
        name: file,
        onLayout: (f) => buildInvoicePdf(
            inv: inv, biz: biz, customer: customer, format: f,
            withSeal: _seal),
      );
    }

    Future<void> shareIt() async {
      final bytes = await buildInvoicePdf(
          inv: inv, biz: biz, customer: customer, format: PdfPageFormat.a4,
          withSeal: _seal);
      await Printing.sharePdf(bytes: bytes, filename: file);
    }

    return Scaffold(
      appBar: AppBar(
        title: Text('${inv.kindLabel} ${faDigits(inv.number)}'),
        actions: [
          PopupMenuButton<String>(
            onSelected: (v) async {
              switch (v) {
                case 'dup':
                  final copy = Invoice.fromJson(inv.toJson());
                  final n = store.newInvoice(kind: inv.kind);
                  final dup = Invoice(
                    number: n.number,
                    kind: inv.kind,
                    customerId: copy.customerId,
                    customerName: copy.customerName,
                    type: copy.type,
                    lines: copy.lines,
                  );
                  store.saveInvoice(dup);
                  if (context.mounted) {
                    Navigator.of(context).pushReplacement(MaterialPageRoute(
                        builder: (_) => InvoiceEditor(invoiceId: dup.id)));
                  }
                case 'convert':
                  final made = store.invoiceFromProforma(inv);
                  if (context.mounted) {
                    Navigator.of(context).pushReplacement(MaterialPageRoute(
                        builder: (_) => InvoiceEditor(invoiceId: made.id)));
                  }
                case 'cancel':
                  if (await confirm(context, 'ابطال فاکتور',
                      'فاکتور ابطال‌شده از گزارش‌ها حذف می‌شه ولی شماره‌اش می‌مونه. اگه به سامانه فرستاده شده، اونجا هم باید ابطال بشه.',
                      ok: 'ابطال', danger: true)) {
                    inv.status = InvoiceStatus.cancelled;
                    store.saveInvoice(inv);
                  }
                case 'delete':
                  if (await confirm(context, 'حذف پیش‌نویس', 'این پیش‌نویس پاک بشه؟',
                      ok: 'حذف', danger: true)) {
                    store.deleteInvoice(inv);
                    if (context.mounted) Navigator.pop(context);
                  }
              }
            },
            itemBuilder: (_) => [
              if (inv.isProforma && inv.status != InvoiceStatus.cancelled)
                const PopupMenuItem(value: 'convert', child: Text('تبدیل به فاکتور')),
              PopupMenuItem(value: 'dup', child: Text('کپی به ${inv.kindLabel} جدید')),
              if (inv.status == InvoiceStatus.issued)
                const PopupMenuItem(value: 'cancel', child: Text('ابطال')),
              if (inv.status == InvoiceStatus.draft)
                const PopupMenuItem(value: 'delete', child: Text('حذف')),
            ],
          ),
        ],
      ),
      body: Constrained(
        maxWidth: 760,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
          children: [
            if (justIssued) const _SuccessBanner(),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(24),
                gradient: LinearGradient(
                  colors: const [Color(0xFF0FA3A3), Color(0xFF0B6E80)],
                  begin: Alignment.topRight,
                  end: Alignment.bottomLeft,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Expanded(
                      child: Text(
                          customer?.name ??
                              (inv.customerName.isEmpty ? 'مشتری عمومی' : inv.customerName),
                          style: const TextStyle(
                              color: Colors.white, fontSize: 18, fontWeight: FontWeight.w700)),
                    ),
                    Container(
                      decoration: BoxDecoration(
                          color: Colors.white, borderRadius: BorderRadius.circular(20)),
                      child: StatusChip(invoice: inv),
                    ),
                  ]),
                  const SizedBox(height: 4),
                  Text(jDateLong(inv.date),
                      style: const TextStyle(color: Colors.white70)),
                  const SizedBox(height: 18),
                  const Text('مبلغ کل', style: TextStyle(color: Colors.white70)),
                  Text(toman(inv.total),
                      style: const TextStyle(
                          color: Colors.white, fontSize: 28, fontWeight: FontWeight.w700)),
                ],
              ),
            ),
            const SizedBox(height: 14),
            if (inv.status == InvoiceStatus.draft)
              FilledButton.icon(
                onPressed: () => Navigator.of(context).pushReplacement(MaterialPageRoute(
                    builder: (_) => InvoiceEditor(invoiceId: inv.id))),
                icon: const Icon(Icons.edit_rounded),
                label: const Text('ادامه‌ی ویرایش و صدور'),
              )
            else
              Row(children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: printIt,
                    icon: const Icon(Icons.print_rounded),
                    label: const Text('چاپ'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: FilledButton.tonalIcon(
                    style: FilledButton.styleFrom(minimumSize: const Size(48, 52)),
                    onPressed: shareIt,
                    icon: const Icon(Icons.share_rounded),
                    label: const Text('ارسال PDF'),
                  ),
                ),
              ]),
            if (inv.status != InvoiceStatus.draft) ...[
              const SizedBox(height: 8),
              Card(
                child: CheckboxListTile(
                  key: const ValueKey('seal'),
                  value: _seal && biz.hasSeal,
                  onChanged: biz.hasSeal
                      ? (v) => setState(() => _seal = v ?? false)
                      : null,
                  title: const Text('مهر و امضا پای فاکتور',
                      style: TextStyle(fontWeight: FontWeight.w700)),
                  subtitle: Text(biz.hasSeal
                      ? 'مهر و امضای رنگی روی چاپ و PDF می‌خوره'
                      : 'اول از تنظیمات، مهر و امضا رو آپلود کن'),
                  secondary: Icon(Icons.approval_rounded, color: cs.primary),
                ),
              ),
            ],
            if (inv.isProforma && inv.status == InvoiceStatus.issued) ...[
              const SizedBox(height: 8),
              FilledButton.tonalIcon(
                onPressed: () {
                  final made = store.invoiceFromProforma(inv);
                  Navigator.of(context).pushReplacement(MaterialPageRoute(
                      builder: (_) => InvoiceEditor(invoiceId: made.id)));
                },
                icon: const Icon(Icons.transform_rounded),
                label: const Text('مشتری قبول کرد؛ تبدیل به فاکتور'),
              ),
            ],
            if (inv.status == InvoiceStatus.issued && !inv.isProforma) ...[
              const SizedBox(height: 12),
              Card(
                child: SwitchListTile(
                  value: inv.paid,
                  onChanged: (v) {
                    inv.paid = v;
                    store.saveInvoice(inv);
                  },
                  title: const Text('پولش رو گرفتم',
                      style: TextStyle(fontWeight: FontWeight.w700)),
                  subtitle: Text(inv.paid ? 'از طلب‌ها حذف شد' : 'هنوز جزو طلب‌هاست'),
                  secondary: Icon(Icons.payments_rounded, color: cs.primary),
                ),
              ),
              const SizedBox(height: 8),
              _moadianCard(context, inv),
            ],
            const SectionTitle('اقلام'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(children: [
                  for (final l in inv.lines)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Row(children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(l.name, style: const TextStyle(fontWeight: FontWeight.w700)),
                              Text('${num0(l.qty)} ${l.unit} × ${toman(l.unitPrice)}${l.discount > 0 ? '  |  تخفیف ${l.discountIsPercent ? '${num0(l.discountPercent)}٪' : toman(l.discount)}' : ''}',
                                  style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant)),
                            ],
                          ),
                        ),
                        Text(toman(l.net)),
                      ]),
                    ),
                  const Divider(height: 24),
                  _sum(context, 'جمع کل', inv.gross),
                  if (inv.discount > 0) _sum(context, 'جمع تخفیف‌ها', inv.discount),
                  if (inv.discount > 0) _sum(context, 'جمع بعد از تخفیف', inv.net),
                  if (inv.vat > 0) _sum(context, 'مالیات بر ارزش افزوده', inv.vat),
                  _sum(context, 'قابل پرداخت', inv.total, bold: true),
                ]),
              ),
            ),
            if (inv.note.isNotEmpty) ...[
              const SectionTitle('یادداشت'),
              Card(
                child: Padding(
                    padding: const EdgeInsets.all(16), child: Text(inv.note)),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _moadianCard(BuildContext context, Invoice inv) {
    final left = inv.daysLeftToRegister;
    final late = left < 0;
    final c = late ? Colors.red.shade400 : Colors.indigo;
    return Card(
      child: ListTile(
        leading: Icon(Icons.cloud_upload_rounded, color: c),
        title: const Text('سامانه‌ی مودیان',
            style: TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text(late
            ? 'مهلت ۱۲ روزه‌ی ثبت گذشته'
            : 'ارسال خودکار در نسخه‌ی بعد  |  ${faDigits(left)} روز تا پایان مهلت'),
      ),
    );
  }

  Widget _sum(BuildContext context, String k, int v, {bool bold = false}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(children: [
          Expanded(
              child: Text(k,
                  style: TextStyle(
                      fontWeight: bold ? FontWeight.w700 : null,
                      color: bold ? null : Theme.of(context).colorScheme.onSurfaceVariant))),
          Text(toman(v),
              style: TextStyle(
                  fontWeight: bold ? FontWeight.w700 : null, fontSize: bold ? 17 : 14)),
        ]),
      );
}

class _SuccessBanner extends StatelessWidget {
  const _SuccessBanner();

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: const Duration(milliseconds: 600),
      curve: Curves.elasticOut,
      builder: (context, t, child) => Transform.scale(scale: 0.6 + 0.4 * t, child: child),
      child: Container(
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.green.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Row(children: [
          Icon(Icons.celebration_rounded, color: Colors.green.shade700),
          const SizedBox(width: 10),
          const Expanded(
            child: Text('صادر شد! حالا چاپش کن یا برای مشتری بفرست.',
                style: TextStyle(fontWeight: FontWeight.w700)),
          ),
        ]),
      ),
    );
  }
}
