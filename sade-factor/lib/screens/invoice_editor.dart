import 'package:flutter/material.dart';
import 'package:shamsi_date/shamsi_date.dart';

import '../format.dart';
import '../models.dart';
import '../store.dart';
import '../widgets/common.dart';
import 'customers.dart';
import 'invoice_view.dart';
import 'items.dart';

/// New invoice in three steps: who, what, check & issue.
class InvoiceEditor extends StatefulWidget {
  final String? invoiceId; // edit an existing draft
  final DocKind kind; // for a new document
  const InvoiceEditor({super.key, this.invoiceId, this.kind = DocKind.invoice});

  @override
  State<InvoiceEditor> createState() => _InvoiceEditorState();
}

class _InvoiceEditorState extends State<InvoiceEditor> {
  late AppStore store;
  late Invoice inv;
  bool _init = false;
  int _step = 0;
  String _q = '';
  final _note = TextEditingController();

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_init) return;
    _init = true;
    store = StoreScope.of(context);
    final existing = widget.invoiceId == null
        ? null
        : store.invoices.where((i) => i.id == widget.invoiceId).firstOrNull;
    inv = existing != null
        ? Invoice.fromJson(existing.toJson())
        : store.newInvoice(kind: widget.kind);
    _note.text = inv.note;
    if (existing != null) _step = 1;
  }

  Customer? get _customer => store.customerById(inv.customerId);

  void _pickCustomer(Customer? c) {
    setState(() {
      inv.customerId = c?.id;
      inv.customerName = c?.name ?? '';
      inv.type = (c != null && c.canReceiveType1)
          ? InvoiceType.withBuyer
          : InvoiceType.consumer;
      _step = 1;
      _q = '';
    });
  }

  void _addItem(Item it) {
    setState(() {
      final ex = inv.lines.where((l) => l.itemId == it.id).firstOrNull;
      if (ex != null) {
        ex.qty += 1;
      } else {
        inv.lines.add(
            InvoiceLine.fromItem(it, vatOn: store.business.vatRegistered));
      }
    });
  }

  void _finish({required bool issue}) {
    if (inv.lines.isEmpty) {
      toast(context, 'حداقل یک کالا اضافه کن');
      return;
    }
    if (issue && inv.lines.any((l) => l.unitPrice <= 0)) {
      toast(context, 'قیمت یکی از ردیف‌ها صفره');
      return;
    }
    inv.note = _note.text.trim();
    inv.status = issue ? InvoiceStatus.issued : InvoiceStatus.draft;
    store.saveInvoice(inv);
    final nav = Navigator.of(context);
    nav.pop();
    if (issue) {
      nav.push(MaterialPageRoute(
          builder: (_) => InvoiceView(invoiceId: inv.id, justIssued: true)));
    } else {
      toast(context, 'پیش‌نویس ذخیره شد');
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    const titles = ['برای کی؟', 'چی فروختی؟', 'بررسی و صدور'];
    return PopScope(
      canPop: _step == 0,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) setState(() => _step--);
      },
      child: Scaffold(
        appBar: AppBar(
          leading: IconButton(
            icon: Icon(_step == 0 ? Icons.close_rounded : Icons.arrow_forward_rounded),
            onPressed: () => _step == 0
                ? Navigator.pop(context)
                : setState(() => _step--),
          ),
          title: Text('${inv.kindLabel} ${faDigits(inv.number)}'),
          bottom: PreferredSize(
            preferredSize: const Size.fromHeight(56),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              child: Row(children: [
                for (var i = 0; i < 3; i++) ...[
                  if (i > 0)
                    Expanded(
                      child: Container(
                        height: 2,
                        color: i <= _step ? cs.primary : cs.outlineVariant,
                      ),
                    ),
                  _StepDot(
                    n: i + 1,
                    label: titles[i],
                    active: i == _step,
                    done: i < _step,
                    onTap: i < _step ? () => setState(() => _step = i) : null,
                  ),
                ]
              ]),
            ),
          ),
        ),
        body: Constrained(
          maxWidth: 760,
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 250),
            transitionBuilder: (child, a) => FadeTransition(
              opacity: a,
              child: SlideTransition(
                position: Tween(begin: const Offset(0.05, 0), end: Offset.zero)
                    .animate(a),
                child: child,
              ),
            ),
            child: KeyedSubtree(
              key: ValueKey(_step),
              child: [_stepCustomer, _stepItems, _stepReview][_step](),
            ),
          ),
        ),
        bottomNavigationBar: _step == 0 ? null : _bottomBar(),
      ),
    );
  }

  Widget _bottomBar() {
    final cs = Theme.of(context).colorScheme;
    return SafeArea(
      child: Container(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
        decoration: BoxDecoration(
          color: Theme.of(context).cardTheme.color,
          boxShadow: [
            BoxShadow(
                color: Colors.black.withValues(alpha: 0.06),
                blurRadius: 16,
                offset: const Offset(0, -4))
          ],
        ),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Row(children: [
            Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('جمع کل', style: TextStyle(color: cs.onSurfaceVariant)),
                  Text(toman(inv.total),
                      style: const TextStyle(
                          fontSize: 20, fontWeight: FontWeight.w700)),
                ],
              ),
            ),
            if (_step == 1)
              FilledButton.icon(
                onPressed: inv.lines.isEmpty
                    ? null
                    : () => setState(() => _step = 2),
                icon: const Icon(Icons.arrow_back_rounded),
                label: const Text('ادامه'),
              ),
          ]),
          if (_step == 2) ...[
            const SizedBox(height: 10),
            Row(children: [
              Expanded(
                flex: 2,
                child: OutlinedButton(
                  style:
                      OutlinedButton.styleFrom(minimumSize: const Size(48, 52)),
                  onPressed: () => _finish(issue: false),
                  child: const Text('پیش‌نویس'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                flex: 3,
                child: FilledButton.icon(
                  onPressed: () => _finish(issue: true),
                  icon: const Icon(Icons.check_rounded),
                  label: Text('صدور ${inv.kindLabel}'),
                ),
              ),
            ]),
          ],
        ]),
      ),
    );
  }

  // ---- step 1: customer ---------------------------------------------------

  Widget _stepCustomer() {
    final cs = Theme.of(context).colorScheme;
    final list = store.customers
        .where((c) => _q.isEmpty || c.name.contains(_q) || c.phone.contains(_q))
        .toList()
      ..sort((a, b) => a.name.compareTo(b.name));
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (widget.invoiceId == null) ...[
          SegmentedButton<DocKind>(
            segments: const [
              ButtonSegment(
                  value: DocKind.invoice,
                  label: Text('فاکتور'),
                  icon: Icon(Icons.receipt_long_rounded)),
              ButtonSegment(
                  value: DocKind.proforma,
                  label: Text('پیش‌فاکتور'),
                  icon: Icon(Icons.request_quote_rounded)),
            ],
            selected: {inv.kind},
            onSelectionChanged: (k) =>
                setState(() => store.setKind(inv, k.first)),
          ),
          const SizedBox(height: 14),
        ],
        TextField(
          autofocus: store.customers.length > 6,
          onChanged: (v) => setState(() => _q = v.trim()),
          decoration: const InputDecoration(
              hintText: 'جستجوی مشتری', prefixIcon: Icon(Icons.search_rounded)),
        ),
        const SizedBox(height: 14),
        Row(children: [
          Expanded(
            child: _BigChoice(
              icon: Icons.shopping_bag_rounded,
              title: 'مشتری عمومی',
              subtitle: 'مصرف‌کننده، بدون مشخصات',
              color: cs.secondaryContainer,
              onTap: () => _pickCustomer(null),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: _BigChoice(
              icon: Icons.person_add_alt_1_rounded,
              title: 'مشتری جدید',
              subtitle: 'ثبت و انتخاب',
              color: cs.primaryContainer,
              onTap: () async {
                final c = await editCustomer(context);
                if (c != null) _pickCustomer(c);
              },
            ),
          ),
        ]),
        if (list.isNotEmpty) const SectionTitle('مشتری‌های ثبت‌شده'),
        for (final c in list)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Card(
              child: ListTile(
                leading: CircleAvatar(
                  child: Icon(c.kind == CustomerKind.company
                      ? Icons.apartment_rounded
                      : Icons.person_rounded),
                ),
                title: Text(c.name,
                    style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text(c.canReceiveType1
                    ? 'فاکتور رسمی با اعتبار مالیاتی'
                    : 'فاکتور مصرف‌کننده'),
                trailing: inv.customerId == c.id
                    ? Icon(Icons.check_circle_rounded, color: cs.primary)
                    : const Icon(Icons.chevron_left_rounded),
                onTap: () => _pickCustomer(c),
              ),
            ),
          ),
      ],
    );
  }

  // ---- step 2: items ------------------------------------------------------

  Widget _stepItems() {
    final cs = Theme.of(context).colorScheme;
    final pool = [...store.items]..sort((a, b) => a.name.compareTo(b.name));
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('برای افزودن، روی کالا بزن',
            style: TextStyle(color: cs.onSurfaceVariant)),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final it in pool)
            ActionChip(
              avatar: const Icon(Icons.add_rounded, size: 18),
              label: Text('${it.name}  |  ${toman(it.price)}'),
              onPressed: () => _addItem(it),
            ),
          ActionChip(
            avatar: Icon(Icons.add_box_rounded, size: 18, color: cs.primary),
            label: Text('کالای جدید',
                style: TextStyle(color: cs.primary, fontWeight: FontWeight.w700)),
            onPressed: () async {
              final it = await editItem(context);
              if (it != null) _addItem(it);
            },
          ),
        ]),
        const SectionTitle('اقلام فاکتور'),
        if (inv.lines.isEmpty)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Text('هنوز چیزی اضافه نکردی',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: cs.onSurfaceVariant)),
            ),
          ),
        for (var i = 0; i < inv.lines.length; i++)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: _LineCard(
              key: ObjectKey(inv.lines[i]),
              line: inv.lines[i],
              onChanged: () => setState(() {}),
              onRemove: () => setState(() => inv.lines.removeAt(i)),
            ),
          ),
      ],
    );
  }

  // ---- step 3: review -----------------------------------------------------

  Widget _stepReview() {
    final cs = Theme.of(context).colorScheme;
    final c = _customer;
    final missingIds = inv.lines.where((l) => !isValidStuffId(l.stuffId)).length;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(children: [
              _row('مشتری', c?.name ?? 'مشتری عمومی'),
              _row('تاریخ', jDateLong(inv.date),
                  action: TextButton(
                      onPressed: _pickDate, child: const Text('تغییر'))),
              if (inv.isProforma)
                _row('نوع', 'پیش‌فاکتور (فقط اعلام قیمت)')
              else
                _row(
                    'نوع',
                    inv.type == InvoiceType.withBuyer
                        ? 'رسمی (نوع اول)، خریدار اعتبار می‌گیره'
                        : 'مصرف‌کننده (نوع دوم)'),
            ]),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(children: [
              for (final l in inv.lines)
                _row(
                    '${l.name} × ${num0(l.qty)}${l.discount > 0 ? '  (تخفیف ${l.discountIsPercent ? '${num0(l.discountPercent)}٪' : toman(l.discount)})' : ''}',
                    toman(l.net)),
              const Divider(height: 24),
              _row('جمع کل', toman(inv.gross)),
              if (inv.discount > 0) _row('جمع تخفیف‌ها', toman(inv.discount)),
              if (inv.discount > 0) _row('جمع بعد از تخفیف', toman(inv.net)),
              if (inv.vat > 0) _row('مالیات بر ارزش افزوده', toman(inv.vat)),
              const SizedBox(height: 6),
              _row('مبلغ قابل پرداخت', toman(inv.total), bold: true),
            ]),
          ),
        ),
        const SizedBox(height: 12),
        if (!inv.isProforma && inv.type == InvoiceType.withBuyer && missingIds > 0)
          _hint(Icons.info_rounded, Colors.orange,
              '${faDigits(missingIds)} کالا شناسه‌ی ۱۳ رقمی نداره. برای ارسال به سامانه‌ی مودیان لازمه.'),
        if (!inv.isProforma &&
            inv.type == InvoiceType.withBuyer &&
            c != null &&
            c.nationalId.isEmpty &&
            c.economicCode.isEmpty)
          _hint(Icons.info_rounded, Colors.orange,
              'کد ملی یا اقتصادی خریدار ثبت نشده. بعد از ارسال قابل اصلاح نیست.'),
        if (!inv.isProforma)
          _hint(Icons.schedule_rounded, cs.primary,
              'از تاریخ فاکتور ۱۲ روز وقت داری در سامانه‌ی مودیان ثبتش کنی.'),
        if (inv.isProforma)
          _hint(Icons.info_outline_rounded, cs.primary,
              'پیش‌فاکتور جزو فروش حساب نمی‌شه. هر وقت مشتری قبول کرد، با یک دکمه فاکتورش کن.'),
        const SizedBox(height: 8),
        TextField(
          controller: _note,
          maxLines: 2,
          decoration: const InputDecoration(labelText: 'یادداشت (اختیاری)'),
        ),
      ],
    );
  }

  Future<void> _pickDate() async {
    final d = await showJalaliDatePicker(context, inv.date);
    if (d != null) setState(() => inv.date = d);
  }

  Widget _row(String a, String b, {bool bold = false, Widget? action}) {
    final st = TextStyle(
        fontWeight: bold ? FontWeight.w700 : FontWeight.normal,
        fontSize: bold ? 17 : 14);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(children: [
        Expanded(
            child: Text(a,
                style: st.copyWith(
                    color: bold
                        ? null
                        : Theme.of(context).colorScheme.onSurfaceVariant))),
        Flexible(child: Text(b, style: st, textAlign: TextAlign.end)),
        if (action != null) action,
      ]),
    );
  }

  Widget _hint(IconData i, Color c, String t) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: c.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(i, color: c, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(t, style: const TextStyle(height: 1.6))),
        ]),
      );
}

/// Simple Jalali date picker: year / month / day wheels as dropdowns.
Future<DateTime?> showJalaliDatePicker(BuildContext context, DateTime initial) {
  var j = Jalali.fromDateTime(initial);
  int y = j.year, m = j.month, d = j.day;
  const months = [
    'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
  ];
  return showDialog<DateTime>(
    context: context,
    builder: (c) => StatefulBuilder(builder: (c, set) {
      final maxDay = Jalali(y, m, 1).monthLength;
      if (d > maxDay) d = maxDay;
      Widget dd<T>(T v, List<T> vals, String Function(T) lbl, void Function(T) on) =>
          Expanded(
            child: DropdownButtonFormField<T>(
              value: v,
              isExpanded: true,
              items: [
                for (final x in vals)
                  DropdownMenuItem(value: x, child: Text(lbl(x)))
              ],
              onChanged: (x) => set(() => on(x as T)),
            ),
          );
      final now = Jalali.now();
      return AlertDialog(
        title: const Text('تاریخ فاکتور'),
        content: SizedBox(
          width: 360,
          child: Row(children: [
            dd<int>(d, [for (var i = 1; i <= maxDay; i++) i], faDigits, (x) => d = x),
            const SizedBox(width: 8),
            dd<int>(m, [for (var i = 1; i <= 12; i++) i], (x) => months[x - 1], (x) => m = x),
            const SizedBox(width: 8),
            dd<int>(y, [now.year - 1, now.year, now.year + 1], faDigits, (x) => y = x),
          ]),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(c), child: const Text('انصراف')),
          FilledButton(
              onPressed: () => Navigator.pop(c, Jalali(y, m, d).toDateTime()),
              child: const Text('تأیید')),
        ],
      );
    }),
  );
}

class _StepDot extends StatelessWidget {
  final int n;
  final String label;
  final bool active, done;
  final VoidCallback? onTap;
  const _StepDot(
      {required this.n,
      required this.label,
      required this.active,
      required this.done,
      this.onTap});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final on = active || done;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 250),
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: on ? cs.primary : cs.surfaceContainerHighest,
            ),
            alignment: Alignment.center,
            child: done
                ? Icon(Icons.check_rounded, size: 16, color: cs.onPrimary)
                : Text(faDigits(n),
                    style: TextStyle(
                        color: on ? cs.onPrimary : cs.onSurfaceVariant,
                        fontWeight: FontWeight.w700)),
          ),
          if (active) ...[
            const SizedBox(width: 6),
            Text(label, style: const TextStyle(fontWeight: FontWeight.w700)),
          ],
        ]),
      ),
    );
  }
}

class _BigChoice extends StatelessWidget {
  final IconData icon;
  final String title, subtitle;
  final Color color;
  final VoidCallback onTap;
  const _BigChoice(
      {required this.icon,
      required this.title,
      required this.subtitle,
      required this.color,
      required this.onTap});

  @override
  Widget build(BuildContext context) => Material(
        color: color,
        borderRadius: BorderRadius.circular(20),
        child: InkWell(
          borderRadius: BorderRadius.circular(20),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(icon, size: 30),
                const SizedBox(height: 12),
                Text(title,
                    style: const TextStyle(
                        fontWeight: FontWeight.w700, fontSize: 15)),
                const SizedBox(height: 2),
                Text(subtitle, style: const TextStyle(fontSize: 12)),
              ],
            ),
          ),
        ),
      );
}

class _LineCard extends StatefulWidget {
  final InvoiceLine line;
  final VoidCallback onChanged, onRemove;
  const _LineCard(
      {super.key,
      required this.line,
      required this.onChanged,
      required this.onRemove});

  @override
  State<_LineCard> createState() => _LineCardState();
}

class _LineCardState extends State<_LineCard> {
  bool _open = false;
  late final _price =
      TextEditingController(text: (widget.line.unitPrice ~/ 10).toString());
  late final _disc = TextEditingController(text: _discText());

  String _discText() {
    final l = widget.line;
    if (l.discountIsPercent) {
      return l.discountPercent == 0 ? '' : num0(l.discountPercent);
    }
    return l.discountAmount == 0 ? '' : (l.discountAmount ~/ 10).toString();
  }

  void _applyDisc(String v) {
    final l = widget.line;
    final t = toLatinDigits(v.trim());
    if (l.discountIsPercent) {
      l.discountPercent = (double.tryParse(t) ?? 0).clamp(0, 100).toDouble();
    } else {
      l.discountAmount = (int.tryParse(t) ?? 0) * 10;
    }
    widget.onChanged();
  }

  void _qty(double d) {
    final l = widget.line;
    final q = l.qty + d;
    if (q <= 0) {
      widget.onRemove();
      return;
    }
    l.qty = q;
    widget.onChanged();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final l = widget.line;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(children: [
          Row(children: [
            Expanded(
              child: InkWell(
                onTap: () => setState(() => _open = !_open),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(l.name,
                        style: const TextStyle(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 2),
                    Text(
                        '${toman(l.unitPrice)}${l.discount > 0 ? '  |  تخفیف ${l.discountIsPercent ? '${num0(l.discountPercent)}٪' : toman(l.discount)}' : ''}  |  ${_open ? 'بستن' : 'قیمت و تخفیف'}',
                        style: TextStyle(
                            fontSize: 12, color: cs.onSurfaceVariant)),
                  ],
                ),
              ),
            ),
            Container(
              decoration: BoxDecoration(
                color: cs.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                IconButton(
                    visualDensity: VisualDensity.compact,
                    onPressed: () => _qty(1),
                    icon: const Icon(Icons.add_rounded)),
                Text(num0(l.qty),
                    style: const TextStyle(
                        fontWeight: FontWeight.w700, fontSize: 16)),
                IconButton(
                    visualDensity: VisualDensity.compact,
                    onPressed: () => _qty(-1),
                    icon: Icon(l.qty <= 1
                        ? Icons.delete_outline_rounded
                        : Icons.remove_rounded)),
              ]),
            ),
          ]),
          AnimatedSize(
            duration: const Duration(milliseconds: 200),
            child: !_open
                ? const SizedBox(width: double.infinity)
                : Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Column(children: [
                      TextField(
                        controller: _price,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(
                            labelText: 'قیمت واحد', suffixText: 'تومان'),
                        onChanged: (v) {
                          l.unitPrice =
                              (int.tryParse(toLatinDigits(v)) ?? 0) * 10;
                          widget.onChanged();
                        },
                      ),
                      const SizedBox(height: 10),
                      Row(children: [
                        Expanded(
                          child: TextField(
                            key: const ValueKey('disc'),
                            controller: _disc,
                            keyboardType:
                                const TextInputType.numberWithOptions(
                                    decimal: true),
                            decoration: InputDecoration(
                              labelText: 'تخفیف این ردیف',
                              suffixText:
                                  l.discountIsPercent ? 'درصد' : 'تومان',
                              helperText: l.discount > 0
                                  ? 'برابر ${toman(l.discount)}'
                                  : null,
                            ),
                            onChanged: _applyDisc,
                          ),
                        ),
                        const SizedBox(width: 8),
                        SegmentedButton<bool>(
                          showSelectedIcon: false,
                          segments: const [
                            ButtonSegment(value: false, label: Text('تومان')),
                            ButtonSegment(value: true, label: Text('٪')),
                          ],
                          selected: {l.discountIsPercent},
                          onSelectionChanged: (x) {
                            setState(() {
                              l.discountIsPercent = x.first;
                              _applyDisc(_disc.text);
                            });
                          },
                        ),
                      ]),
                    ]),
                  ),
          ),
        ]),
      ),
    );
  }
}
