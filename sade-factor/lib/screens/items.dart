import 'package:flutter/material.dart';

import '../format.dart';
import '../models.dart';
import '../store.dart';
import '../widgets/common.dart';
import 'import_items.dart';

class ItemsScreen extends StatefulWidget {
  const ItemsScreen({super.key});

  @override
  State<ItemsScreen> createState() => _ItemsScreenState();
}

class _ItemsScreenState extends State<ItemsScreen> {
  String _q = '';

  @override
  Widget build(BuildContext context) {
    final store = StoreScope.of(context);
    final cs = Theme.of(context).colorScheme;
    final list = store.items
        .where((i) => _q.isEmpty || i.name.contains(_q))
        .toList()
      ..sort((a, b) => a.name.compareTo(b.name));

    return Scaffold(
      backgroundColor: Colors.transparent,
      floatingActionButton: FloatingActionButton.extended(
        heroTag: 'addItem',
        onPressed: () => editItem(context),
        icon: const Icon(Icons.add_box_rounded),
        label: const Text('کالا یا خدمت'),
      ),
      body: Constrained(
        child: CustomScrollView(slivers: [
          SliverAppBar(
            title: const Text('کالاها و خدمات'),
            floating: true,
            actions: [
              Padding(
                padding: const EdgeInsetsDirectional.only(end: 8),
                child: TextButton.icon(
                  onPressed: () => startImport(context),
                  icon: const Icon(Icons.upload_file_rounded),
                  label: const Text('ورود از فایل'),
                ),
              ),
            ],
          ),
          if (store.items.isNotEmpty)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                child: TextField(
                  onChanged: (v) => setState(() => _q = v.trim()),
                  decoration: const InputDecoration(
                      hintText: 'جستجو', prefixIcon: Icon(Icons.search_rounded)),
                ),
              ),
            ),
          if (list.isEmpty)
            SliverFillRemaining(
              hasScrollBody: false,
              child: EmptyState(
                icon: Icons.inventory_2_rounded,
                title: 'چی می‌فروشی؟',
                message: 'کالاها یا خدماتت رو با قیمت ثبت کن تا فاکتور زدن یک لمس بشه.',
                actionLabel: 'افزودن',
                onAction: () => editItem(context),
              ),
            )
          else
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 120),
              sliver: SliverList.separated(
                itemCount: list.length,
                separatorBuilder: (_, __) => const SizedBox(height: 10),
                itemBuilder: (context, i) {
                  final it = list[i];
                  final missingId = !isValidStuffId(it.stuffId);
                  return Card(
                    child: ListTile(
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 6),
                      leading: CircleAvatar(
                        backgroundColor: cs.secondaryContainer,
                        child: const Icon(Icons.sell_rounded),
                      ),
                      title: Text(it.name,
                          style: const TextStyle(fontWeight: FontWeight.w700)),
                      subtitle: Text(
                        missingId
                            ? 'شناسه‌ی کالا ثبت نشده'
                            : store.business.vatRegistered
                                ? 'مالیات ${num0(it.vatRate)}٪  |  هر ${it.unit}'
                                : 'هر ${it.unit}',
                        style: TextStyle(
                            color: missingId ? Colors.orange.shade800 : null),
                      ),
                      trailing: Text(toman(it.price),
                          style: const TextStyle(fontWeight: FontWeight.w700)),
                      onTap: () => editItem(context, it),
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

/// Opens the item form. Returns the saved item, or null.
Future<Item?> editItem(BuildContext context, [Item? existing]) {
  return showModalBottomSheet<Item>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    showDragHandle: true,
    constraints: const BoxConstraints(maxWidth: 640),
    builder: (_) => _ItemForm(existing: existing),
  );
}

class _ItemForm extends StatefulWidget {
  final Item? existing;
  const _ItemForm({this.existing});

  @override
  State<_ItemForm> createState() => _ItemFormState();
}

class _ItemFormState extends State<_ItemForm> {
  late final AppStore store = StoreScope.of(context);
  late final Item it = widget.existing != null
      ? Item.fromJson(widget.existing!.toJson())
      : Item(vatRate: store.business.effectiveVatRate);
  late final _name = TextEditingController(text: it.name);
  late final _price = TextEditingController(
      text: it.price == 0 ? '' : (it.price ~/ 10).toString());
  late final _sid = TextEditingController(text: it.stuffId);
  late final _unit = TextEditingController(text: it.unit);
  late final _vat = TextEditingController(text: num0(it.vatRate));
  String? _sidError;

  void _save() {
    if (_name.text.trim().isEmpty) {
      toast(context, 'اسم کالا رو بنویس');
      return;
    }
    final sid = toLatinDigits(_sid.text.trim());
    if (sid.isNotEmpty && !isValidStuffId(sid)) {
      setState(() => _sidError = 'شناسه‌ی کالا باید دقیقاً ۱۳ رقم باشه');
      return;
    }
    it
      ..name = _name.text.trim()
      ..price = (int.tryParse(toLatinDigits(_price.text.trim())) ?? 0) * 10
      ..stuffId = sid
      ..unit = _unit.text.trim().isEmpty ? 'عدد' : _unit.text.trim()
      ..vatRate = store.business.vatRegistered
          ? (double.tryParse(toLatinDigits(_vat.text.trim())) ?? 10)
          : 0;
    store.upsertItem(it);
    Navigator.pop(context, it);
  }

  Future<void> _delete() async {
    if (await confirm(context, 'حذف کالا', 'فاکتورهای قبلی دست نمی‌خورن. حذف بشه؟',
        ok: 'حذف', danger: true)) {
      store.deleteItem(it);
      if (mounted) Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
          bottom: MediaQuery.viewInsetsOf(context).bottom + 16,
          left: 20,
          right: 20),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(widget.existing == null ? 'کالا یا خدمت جدید' : 'ویرایش',
                style:
                    const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
            const SizedBox(height: 16),
            TextField(
                controller: _name,
                autofocus: widget.existing == null,
                decoration: const InputDecoration(labelText: 'اسم *')),
            const SizedBox(height: 10),
            Row(children: [
              Expanded(
                flex: 3,
                child: TextField(
                    controller: _price,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                        labelText: 'قیمت', suffixText: 'تومان')),
              ),
              const SizedBox(width: 10),
              Expanded(
                flex: 2,
                child: TextField(
                    controller: _unit,
                    decoration: const InputDecoration(labelText: 'واحد')),
              ),
            ]),
            const SizedBox(height: 10),
            TextField(
              controller: _sid,
              keyboardType: TextInputType.number,
              onChanged: (_) {
                if (_sidError != null) setState(() => _sidError = null);
              },
              decoration: InputDecoration(
                labelText: 'شناسه‌ی کالا یا خدمت (۱۳ رقم)',
                helperText: 'از سامانه‌ی stuffid.tax.gov.ir. برای فاکتور رسمی لازمه',
                errorText: _sidError,
              ),
            ),
            if (store.business.vatRegistered) ...[
            const SizedBox(height: 10),
            TextField(
                controller: _vat,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                    labelText: 'نرخ مالیات بر ارزش افزوده', suffixText: '٪')),
            ],
            const SizedBox(height: 20),
            Row(children: [
              if (widget.existing != null)
                IconButton(
                  onPressed: _delete,
                  icon: const Icon(Icons.delete_outline_rounded),
                  color: Colors.red.shade400,
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
