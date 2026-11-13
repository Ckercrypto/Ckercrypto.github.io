import 'package:flutter/material.dart';

import '../format.dart';
import '../models.dart';
import '../store.dart';
import '../widgets/common.dart';

class CustomersScreen extends StatefulWidget {
  const CustomersScreen({super.key});

  @override
  State<CustomersScreen> createState() => _CustomersScreenState();
}

class _CustomersScreenState extends State<CustomersScreen> {
  String _q = '';

  @override
  Widget build(BuildContext context) {
    final store = StoreScope.of(context);
    final cs = Theme.of(context).colorScheme;
    final list = store.customers
        .where((c) => _q.isEmpty || c.name.contains(_q) || c.phone.contains(_q))
        .toList()
      ..sort((a, b) => a.name.compareTo(b.name));

    return Scaffold(
      backgroundColor: Colors.transparent,
      floatingActionButton: FloatingActionButton.extended(
        heroTag: 'addCustomer',
        onPressed: () => editCustomer(context),
        icon: const Icon(Icons.person_add_alt_1_rounded),
        label: const Text('مشتری جدید'),
      ),
      body: Constrained(
        child: CustomScrollView(slivers: [
          const SliverAppBar(title: Text('مشتری‌ها'), floating: true),
          if (store.customers.isNotEmpty)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                child: TextField(
                  onChanged: (v) => setState(() => _q = v.trim()),
                  decoration: const InputDecoration(
                      hintText: 'جستجوی اسم یا تلفن',
                      prefixIcon: Icon(Icons.search_rounded)),
                ),
              ),
            ),
          if (list.isEmpty)
            SliverFillRemaining(
              hasScrollBody: false,
              child: EmptyState(
                icon: Icons.people_alt_rounded,
                title: 'مشتری‌هات اینجا میان',
                message:
                    'مشتری‌های ثابت رو یک بار ثبت کن تا موقع فاکتور فقط انتخابشون کنی.',
                actionLabel: 'مشتری جدید',
                onAction: () => editCustomer(context),
              ),
            )
          else
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 120),
              sliver: SliverList.separated(
                itemCount: list.length,
                separatorBuilder: (_, __) => const SizedBox(height: 10),
                itemBuilder: (context, i) {
                  final c = list[i];
                  final bought = store.invoices
                      .where((x) =>
                          x.customerId == c.id &&
                          x.status == InvoiceStatus.issued)
                      .fold(0, (s, x) => s + x.total);
                  return Card(
                    child: ListTile(
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 6),
                      leading: CircleAvatar(
                        backgroundColor: c.kind == CustomerKind.company
                            ? cs.secondaryContainer
                            : cs.primaryContainer,
                        child: Icon(c.kind == CustomerKind.company
                            ? Icons.apartment_rounded
                            : Icons.person_rounded),
                      ),
                      title: Text(c.name,
                          style: const TextStyle(fontWeight: FontWeight.w700)),
                      subtitle: Text(c.phone.isEmpty
                          ? (c.kind == CustomerKind.company ? 'شرکت' : 'شخص')
                          : faDigits(c.phone)),
                      trailing: Text(toman(bought),
                          style: TextStyle(color: cs.onSurfaceVariant)),
                      onTap: () => editCustomer(context, c),
                    ),
                  );
                },
              ),
            ),
        ]),
      ),
    );
  }
}

/// Opens the customer form. Returns the saved customer, or null.
Future<Customer?> editCustomer(BuildContext context, [Customer? existing]) {
  return showModalBottomSheet<Customer>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    showDragHandle: true,
    constraints: const BoxConstraints(maxWidth: 640),
    builder: (_) => _CustomerForm(existing: existing),
  );
}

class _CustomerForm extends StatefulWidget {
  final Customer? existing;
  const _CustomerForm({this.existing});

  @override
  State<_CustomerForm> createState() => _CustomerFormState();
}

class _CustomerFormState extends State<_CustomerForm> {
  late final Customer c = widget.existing != null
      ? Customer.fromJson(widget.existing!.toJson())
      : Customer();
  late final _name = TextEditingController(text: c.name);
  late final _nid = TextEditingController(text: c.nationalId);
  late final _eco = TextEditingController(text: c.economicCode);
  late final _phone = TextEditingController(text: c.phone);
  late final _addr = TextEditingController(text: c.address);
  late final _postal = TextEditingController(text: c.postalCode);
  String? _nidError;

  String? _checkNid(String v) {
    final s = toLatinDigits(v.trim());
    if (s.isEmpty) return null;
    if (c.kind == CustomerKind.person && !isValidNationalCode(s)) {
      return 'این کد ملی معتبر نیست. یک بار دیگه چک کن';
    }
    if (c.kind == CustomerKind.company && !isValidLegalId(s)) {
      return 'شناسه ملی شرکت ۱۱ رقمه و این یکی معتبر نیست';
    }
    return null;
  }

  void _save() {
    if (_name.text.trim().isEmpty) {
      toast(context, 'اسم مشتری رو بنویس');
      return;
    }
    _nidError = _checkNid(_nid.text);
    if (_nidError != null) {
      setState(() {});
      return;
    }
    c
      ..name = _name.text.trim()
      ..nationalId = toLatinDigits(_nid.text.trim())
      ..economicCode = toLatinDigits(_eco.text.trim())
      ..phone = toLatinDigits(_phone.text.trim())
      ..address = _addr.text.trim()
      ..postalCode = toLatinDigits(_postal.text.trim());
    StoreScope.of(context).upsertCustomer(c);
    Navigator.pop(context, c);
  }

  Future<void> _delete() async {
    final store = StoreScope.of(context);
    final used = store.invoices.any((i) => i.customerId == c.id);
    if (used) {
      toast(context, 'این مشتری فاکتور داره و نمی‌شه حذفش کرد');
      return;
    }
    if (await confirm(context, 'حذف مشتری', 'مطمئنی؟', ok: 'حذف', danger: true)) {
      store.deleteCustomer(c);
      if (mounted) Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isCo = c.kind == CustomerKind.company;
    return Padding(
      padding: EdgeInsets.only(
          bottom: MediaQuery.viewInsetsOf(context).bottom + 16,
          left: 20,
          right: 20),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(widget.existing == null ? 'مشتری جدید' : 'ویرایش مشتری',
                style:
                    const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
            const SizedBox(height: 16),
            SegmentedButton<CustomerKind>(
              segments: const [
                ButtonSegment(
                    value: CustomerKind.person,
                    label: Text('شخص'),
                    icon: Icon(Icons.person_rounded)),
                ButtonSegment(
                    value: CustomerKind.company,
                    label: Text('شرکت / مغازه'),
                    icon: Icon(Icons.apartment_rounded)),
              ],
              selected: {c.kind},
              onSelectionChanged: (s) => setState(() {
                c.kind = s.first;
                _nidError = null;
              }),
            ),
            const SizedBox(height: 14),
            TextField(
                controller: _name,
                autofocus: widget.existing == null,
                decoration: InputDecoration(
                    labelText: isCo ? 'اسم شرکت یا مغازه *' : 'اسم و فامیل *')),
            const SizedBox(height: 10),
            TextField(
                controller: _phone,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(labelText: 'تلفن')),
            const SizedBox(height: 18),
            Row(children: [
              Icon(Icons.verified_user_rounded,
                  size: 18, color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 6),
              const Expanded(
                child: Text(
                    'برای فاکتور رسمی (تا خریدار اعتبار مالیاتی بگیره)',
                    style: TextStyle(fontWeight: FontWeight.w700)),
              ),
            ]),
            const SizedBox(height: 10),
            TextField(
              controller: _nid,
              keyboardType: TextInputType.number,
              onChanged: (_) {
                if (_nidError != null) setState(() => _nidError = null);
              },
              decoration: InputDecoration(
                labelText: isCo ? 'شناسه ملی (۱۱ رقم)' : 'کد ملی (۱۰ رقم)',
                errorText: _nidError,
              ),
            ),
            const SizedBox(height: 10),
            TextField(
                controller: _eco,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'کد اقتصادی')),
            const SizedBox(height: 10),
            TextField(
                controller: _postal,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'کد پستی')),
            const SizedBox(height: 10),
            TextField(
                controller: _addr,
                maxLines: 2,
                decoration: const InputDecoration(labelText: 'آدرس')),
            const SizedBox(height: 20),
            Row(children: [
              if (widget.existing != null)
                IconButton(
                  onPressed: _delete,
                  icon: const Icon(Icons.delete_outline_rounded),
                  color: Colors.red.shade400,
                  tooltip: 'حذف',
                ),
              const SizedBox(width: 8),
              Expanded(
                  child: FilledButton(
                      onPressed: _save, child: const Text('ذخیره'))),
            ]),
          ],
        ),
      ),
    );
  }
}
