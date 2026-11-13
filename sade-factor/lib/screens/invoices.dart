import 'package:flutter/material.dart';

import '../format.dart';
import '../models.dart';
import '../store.dart';
import '../widgets/common.dart';
import 'invoice_view.dart';

class InvoicesScreen extends StatefulWidget {
  final VoidCallback onNewInvoice;
  const InvoicesScreen({super.key, required this.onNewInvoice});

  @override
  State<InvoicesScreen> createState() => _InvoicesScreenState();
}

class _InvoicesScreenState extends State<InvoicesScreen> {
  String _q = '';
  int _filter = 0;
  static const _filters = ['همه', 'پیش‌نویس', 'منتظر پرداخت', 'پرداخت‌شده', 'ابطال‌شده'];

  bool _match(Invoice i) {
    switch (_filter) {
      case 1:
        if (i.status != InvoiceStatus.draft) return false;
      case 2:
        if (i.status != InvoiceStatus.issued || i.paid) return false;
      case 3:
        if (i.status != InvoiceStatus.issued || !i.paid) return false;
      case 4:
        if (i.status != InvoiceStatus.cancelled) return false;
    }
    if (_q.isEmpty) return true;
    final q = toLatinDigits(_q);
    return i.customerName.contains(_q) ||
        i.number.toString().contains(q) ||
        i.lines.any((l) => l.name.contains(_q));
  }

  @override
  Widget build(BuildContext context) {
    final store = StoreScope.of(context);
    final list = store.sortedInvoices.where(_match).toList();
    return Constrained(
      child: CustomScrollView(slivers: [
        const SliverAppBar(title: Text('فاکتورها'), floating: true),
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: TextField(
              onChanged: (v) => setState(() => _q = v.trim()),
              decoration: const InputDecoration(
                hintText: 'جستجو در اسم مشتری، شماره یا کالا',
                prefixIcon: Icon(Icons.search_rounded),
              ),
            ),
          ),
        ),
        SliverToBoxAdapter(
          child: SizedBox(
            height: 56,
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              scrollDirection: Axis.horizontal,
              itemCount: _filters.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (_, i) => ChoiceChip(
                label: Text(_filters[i]),
                selected: _filter == i,
                onSelected: (_) => setState(() => _filter = i),
              ),
            ),
          ),
        ),
        if (list.isEmpty)
          SliverFillRemaining(
            hasScrollBody: false,
            child: store.invoices.isEmpty
                ? EmptyState(
                    icon: Icons.receipt_long_rounded,
                    title: 'هنوز فاکتوری نداری',
                    message: 'با دکمه‌ی «فاکتور جدید» اولی رو بساز.',
                    actionLabel: 'فاکتور جدید',
                    onAction: widget.onNewInvoice,
                  )
                : const EmptyState(
                    icon: Icons.search_off_rounded,
                    title: 'چیزی پیدا نشد',
                    message: 'فیلتر یا جستجو رو عوض کن.',
                  ),
          )
        else
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 120),
            sliver: SliverList.separated(
              itemCount: list.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, i) => InvoiceTile(
                invoice: list[i],
                onTap: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => InvoiceView(invoiceId: list[i].id))),
              ),
            ),
          ),
      ]),
    );
  }
}
