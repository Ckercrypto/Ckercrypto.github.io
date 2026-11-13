import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../format.dart';
import '../import/price_import.dart';
import '../store.dart';
import '../widgets/common.dart';

ImportResult _parse((String, Uint8List) a) => importFile(a.$1, a.$2);

/// Picks a price-list file, reads it, and opens the review screen.
Future<void> startImport(BuildContext context) async {
  final res = await FilePicker.platform.pickFiles(
    type: FileType.custom,
    allowedExtensions: ['pdf', 'xlsx', 'xls', 'csv', 'docx', 'doc'],
    withData: true,
  );
  final f = res?.files.single;
  if (f == null || f.bytes == null || !context.mounted) return;
  showDialog(
    context: context,
    barrierDismissible: false,
    builder: (_) => const AlertDialog(
      content: Row(children: [
        CircularProgressIndicator(),
        SizedBox(width: 20),
        Expanded(child: Text('در حال خوندن فایل…')),
      ]),
    ),
  );
  ImportResult r;
  try {
    r = await compute(_parse, (f.name, f.bytes!));
  } catch (e) {
    r = ImportResult([], 'فایل خونده نشد: $e');
  }
  if (!context.mounted) return;
  Navigator.of(context).pop();
  if (r.error != null) {
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(r.error!)));
    return;
  }
  Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => ImportReviewScreen(fileName: f.name, rows: r.rows, unit: r.unit)));
}

class ImportReviewScreen extends StatefulWidget {
  final String fileName;
  final List<ImportRow> rows;
  final PriceUnit? unit;
  const ImportReviewScreen(
      {super.key, required this.fileName, required this.rows, this.unit});

  @override
  State<ImportReviewScreen> createState() => _ImportReviewScreenState();
}

class _ImportReviewScreenState extends State<ImportReviewScreen> {
  late PriceUnit _unit = widget.unit ?? PriceUnit.toman;
  bool _update = true;

  List<ImportRow> get rows => widget.rows;

  @override
  Widget build(BuildContext context) {
    final store = StoreScope.of(context);
    final cs = Theme.of(context).colorScheme;
    final sel = rows.where((r) => r.selected).length;
    final noPrice = rows.where((r) => r.price == null).length;
    final odd = rows.where((r) => r.suspicious).length;

    return Scaffold(
      appBar: AppBar(
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('بازبینی لیست قیمت'),
          Text(widget.fileName,
              style: Theme.of(context).textTheme.bodySmall,
              overflow: TextOverflow.ellipsis),
        ]),
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
          child: FilledButton.icon(
            style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(52)),
            onPressed: sel == 0
                ? null
                : () {
                    final (a, u) = store.importItems(rows, _unit.toRial,
                        updateExisting: _update);
                    Navigator.of(context).pop();
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                        content: Text(u > 0
                            ? '${faDigits(a)} کالا اضافه و ${faDigits(u)} کالا به‌روز شد'
                            : '${faDigits(a)} کالا اضافه شد')));
                  },
            icon: const Icon(Icons.download_done_rounded),
            label: Text('افزودن ${faDigits(sel)} کالا'),
          ),
        ),
      ),
      body: Constrained(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                          '${faDigits(rows.length)} ردیف پیدا شد'
                          '${noPrice > 0 ? '، ${faDigits(noPrice)} بی‌قیمت' : ''}'
                          '${odd > 0 ? '، ${faDigits(odd)} قیمت مشکوک' : ''}',
                          style: const TextStyle(fontWeight: FontWeight.w700)),
                      const SizedBox(height: 4),
                      Text(
                          'ردیف‌های بی‌قیمت تیک ندارن. روی هر ردیف بزن تا نام یا قیمتش رو درست کنی.',
                          style: TextStyle(color: cs.onSurfaceVariant)),
                      const SizedBox(height: 14),
                      const Text('قیمت‌های فایل به چه واحدی‌اند؟'),
                      const SizedBox(height: 8),
                      Wrap(spacing: 8, runSpacing: 8, children: [
                        for (final u in PriceUnit.values)
                          ChoiceChip(
                            label: Text(u.label),
                            selected: _unit == u,
                            onSelected: (_) => setState(() => _unit = u),
                          ),
                      ]),
                      const SizedBox(height: 6),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        value: _update,
                        onChanged: (v) => setState(() => _update = v),
                        title: const Text('کالاهای هم‌نام قیمتشون به‌روز بشه'),
                        subtitle: const Text('خاموش باشه، تکراری‌ها رد می‌شن'),
                      ),
                      Row(children: [
                        TextButton(
                            onPressed: () => setState(() {
                                  for (final r in rows) {
                                    r.selected = true;
                                  }
                                }),
                            child: const Text('انتخاب همه')),
                        TextButton(
                            onPressed: () => setState(() {
                                  for (final r in rows) {
                                    r.selected = false;
                                  }
                                }),
                            child: const Text('هیچ‌کدوم')),
                      ]),
                    ]),
              ),
            ),
            const SizedBox(height: 8),
            for (var i = 0; i < rows.length; i++) _rowTile(context, store, i),
          ],
        ),
      ),
    );
  }

  Widget _rowTile(BuildContext context, AppStore store, int i) {
    final r = rows[i];
    final cs = Theme.of(context).colorScheme;
    final exists = store.itemByName(r.name) != null;
    final chips = <Widget>[
      if (r.price == null) _tag('بی‌قیمت', Colors.orange.shade800),
      if (r.suspicious) _tag('قیمت مشکوک', cs.error),
      if (exists) _tag(_update ? 'به‌روز می‌شه' : 'تکراری', cs.primary),
    ];
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _edit(context, i),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(4, 8, 12, 8),
          child: Row(children: [
            Checkbox(
              value: r.selected,
              onChanged: (v) => setState(() => r.selected = v ?? false),
            ),
            Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(r.name,
                        textDirection: _dir(r.name),
                        style: const TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 4),
                    Wrap(
                        spacing: 6,
                        runSpacing: 4,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          if (r.price != null)
                            Text(toman(r.price! * _unit.toRial),
                                style: TextStyle(color: cs.onSurfaceVariant)),
                          ...chips,
                        ]),
                  ]),
            ),
            const Icon(Icons.edit_rounded, size: 18),
          ]),
        ),
      ),
    );
  }

  TextDirection _dir(String s) =>
      RegExp(r'^[^\u0600-\u06FF]*[A-Za-z]').hasMatch(s)
          ? TextDirection.ltr
          : TextDirection.rtl;

  Widget _tag(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          color: c.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(t,
            style: TextStyle(
                color: c, fontSize: 12, fontWeight: FontWeight.w600)),
      );

  Future<void> _edit(BuildContext context, int i) async {
    final r = rows[i];
    final name = TextEditingController(text: r.name);
    final price =
        TextEditingController(text: r.price == null ? '' : '${r.price}');
    final unit = TextEditingController(text: r.unit);
    final res = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('ویرایش ردیف'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(
                controller: name,
                maxLines: null,
                decoration: const InputDecoration(labelText: 'نام کالا')),
            const SizedBox(height: 12),
            TextField(
                controller: price,
                keyboardType: TextInputType.number,
                inputFormatters: [
                  FilteringTextInputFormatter.allow(RegExp(r'[0-9۰-۹]'))
                ],
                decoration: InputDecoration(
                    labelText: 'قیمت (${_unit.label})')),
            const SizedBox(height: 12),
            TextField(
                controller: unit,
                decoration: const InputDecoration(
                    labelText: 'واحد', hintText: 'عدد')),
          ]),
        ),
        actions: [
          if (i > 0)
            TextButton(
                onPressed: () => Navigator.pop(ctx, 'merge'),
                child: const Text('ادغام با ردیف بالا')),
          TextButton(
              onPressed: () => Navigator.pop(ctx, 'delete'),
              child: const Text('حذف')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, 'save'),
              child: const Text('ذخیره')),
        ],
      ),
    );
    if (res == null) return;
    setState(() {
      if (res == 'delete') {
        rows.removeAt(i);
      } else if (res == 'merge') {
        final up = rows[i - 1];
        up.name = '${up.name} ${r.name}'.trim();
        up.price ??= r.price;
        up.selected = up.price != null;
        rows.removeAt(i);
      } else {
        r.name = name.text.trim();
        r.price = int.tryParse(toLatinDigits(price.text));
        r.unit = unit.text.trim();
        r.suspicious = false;
        if (r.price != null && r.name.isNotEmpty) r.selected = true;
      }
    });
  }
}
