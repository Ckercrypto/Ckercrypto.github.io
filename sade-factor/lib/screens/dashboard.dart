import 'package:flutter/material.dart';

import '../format.dart';
import '../models.dart';
import '../store.dart';
import '../widgets/common.dart';
import 'invoice_view.dart';

class DashboardScreen extends StatelessWidget {
  final VoidCallback onNewInvoice;
  final VoidCallback onSeeAll;
  const DashboardScreen(
      {super.key, required this.onNewInvoice, required this.onSeeAll});

  String _greeting() {
    final h = DateTime.now().hour;
    if (h < 12) return 'صبح بخیر';
    if (h < 17) return 'روز بخیر';
    return 'عصر بخیر';
  }

  @override
  Widget build(BuildContext context) {
    final store = StoreScope.of(context);
    final cs = Theme.of(context).colorScheme;
    final now = DateTime.now();
    final recent = store.sortedInvoices.take(5).toList();
    final drafts =
        store.invoices.where((i) => i.status == InvoiceStatus.draft).length;
    final q = jalaliQuarter(now);

    final cards = [
      StatCard(
        label: 'فروش ${jMonthName(now)}',
        value: toman(store.salesThisMonth()),
        icon: Icons.trending_up_rounded,
        gradient: const [Color(0xFF0FA3A3), Color(0xFF0B7A8F)],
      ),
      StatCard(
        label: 'طلب‌ها',
        value: toman(store.receivables()),
        hint: '${faDigits(store.unpaidCount())} فاکتور پرداخت‌نشده',
        icon: Icons.account_balance_wallet_rounded,
        gradient: const [Color(0xFFFF9A62), Color(0xFFF2675B)],
      ),
      if (!store.business.vatRegistered)
        StatCard(
          label: 'پیش‌فاکتورهای باز',
          value: faDigits(store.invoices
              .where((i) => i.isProforma && i.status == InvoiceStatus.issued)
              .length),
          hint: 'منتظر تأیید مشتری',
          icon: Icons.request_quote_rounded,
          gradient: const [Color(0xFF7C6CF2), Color(0xFF5546C9)],
        )
      else
      StatCard(
        label: 'ارزش افزوده‌ی ${quarterNames[q - 1]}',
        value: toman(store.vatThisQuarter()),
        hint: 'مهلت اظهار: یک ماه بعد از فصل',
        icon: Icons.account_balance_rounded,
        gradient: const [Color(0xFF7C6CF2), Color(0xFF5546C9)],
      ),
    ];

    return Constrained(
      maxWidth: 1000,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 120),
        children: [
          Row(children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_greeting(),
                      style: TextStyle(color: cs.onSurfaceVariant)),
                  const SizedBox(height: 2),
                  Text(store.business.name,
                      style: const TextStyle(
                          fontSize: 24, fontWeight: FontWeight.w700)),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: cs.primaryContainer,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Text(jDateLong(now),
                  style: TextStyle(
                      color: cs.onPrimaryContainer,
                      fontWeight: FontWeight.w700,
                      fontSize: 13)),
            ),
          ]),
          const SizedBox(height: 20),
          LayoutBuilder(builder: (context, c) {
            if (c.maxWidth >= 700) {
              return IntrinsicHeight(
                child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  for (var i = 0; i < cards.length; i++) ...[
                    if (i > 0) const SizedBox(width: 12),
                    Expanded(child: cards[i]),
                  ]
                ]),
              );
            }
            return Column(children: [
              cards[0],
              const SizedBox(height: 12),
              IntrinsicHeight(
                child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  Expanded(child: cards[1]),
                  const SizedBox(width: 12),
                  Expanded(child: cards[2]),
                ]),
              ),
            ]);
          }),
          if (drafts > 0) ...[
            const SizedBox(height: 16),
            Card(
              color: cs.tertiaryContainer,
              child: ListTile(
                leading: Icon(Icons.edit_note_rounded,
                    color: cs.onTertiaryContainer),
                title: Text('${faDigits(drafts)} فاکتور پیش‌نویس داری',
                    style: TextStyle(
                        color: cs.onTertiaryContainer,
                        fontWeight: FontWeight.w700)),
                subtitle: Text('قبل از گذشتن مهلت ۱۲ روزه نهایی‌شون کن',
                    style: TextStyle(color: cs.onTertiaryContainer)),
                trailing: Icon(Icons.chevron_left_rounded,
                    color: cs.onTertiaryContainer),
                onTap: onSeeAll,
              ),
            ),
          ],
          const SectionTitle('روند فروش'),
          Card(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 20, 16, 12),
              child: _SalesChart(
                values: store.monthlySales(6),
                labels: store.monthLabels(6),
              ),
            ),
          ),
          SectionTitle('آخرین فاکتورها',
              trailing: recent.isEmpty
                  ? null
                  : TextButton(
                      onPressed: onSeeAll, child: const Text('همه'))),
          if (recent.isEmpty)
            Card(
              child: EmptyState(
                icon: Icons.receipt_long_rounded,
                title: 'هنوز فاکتوری نزدی',
                message: 'اولین فاکتورت رو بساز، کمتر از یک دقیقه طول می‌کشه.',
                actionLabel: 'فاکتور جدید',
                onAction: onNewInvoice,
              ),
            )
          else
            for (final inv in recent)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: InvoiceTile(
                  invoice: inv,
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => InvoiceView(invoiceId: inv.id))),
                ),
              ),
        ],
      ),
    );
  }
}

class _SalesChart extends StatelessWidget {
  final List<int> values;
  final List<String> labels;
  const _SalesChart({required this.values, required this.labels});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final maxV = values.fold<int>(0, (m, v) => v > m ? v : m);
    return SizedBox(
      height: 160,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          for (var i = 0; i < values.length; i++)
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 6),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Expanded(
                      child: Align(
                        alignment: Alignment.bottomCenter,
                        child: TweenAnimationBuilder<double>(
                          tween: Tween(
                              begin: 0,
                              end: maxV == 0 ? 0.04 : (values[i] / maxV).clamp(0.04, 1.0)),
                          duration: Duration(milliseconds: 500 + i * 80),
                          curve: Curves.easeOutCubic,
                          builder: (context, f, _) => FractionallySizedBox(
                            heightFactor: f,
                            child: Container(
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(10),
                                gradient: LinearGradient(
                                  begin: Alignment.bottomCenter,
                                  end: Alignment.topCenter,
                                  colors: i == values.length - 1
                                      ? [cs.primary, cs.secondary]
                                      : [
                                          cs.primary.withValues(alpha: 0.25),
                                          cs.primary.withValues(alpha: 0.45)
                                        ],
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(labels[i],
                        style:
                            TextStyle(fontSize: 11, color: cs.onSurfaceVariant)),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
