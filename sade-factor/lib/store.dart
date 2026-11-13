import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shamsi_date/shamsi_date.dart';

import 'format.dart';
import 'import/price_import.dart';
import 'models.dart';

/// Holds all app data and saves it to one JSON file on the device.
class AppStore extends ChangeNotifier {
  Business business = Business();
  final List<Customer> customers = [];
  final List<Item> items = [];
  final List<Invoice> invoices = [];
  ThemeMode themeMode = ThemeMode.system;
  int nextNumber = 1;
  int nextProformaNumber = 1;

  File? _file;
  bool loaded = false;

  /// For tests: skip disk.
  bool persist = true;

  Future<void> load() async {
    try {
      final dir = await getApplicationSupportDirectory();
      await dir.create(recursive: true);
      _file = File('${dir.path}${Platform.pathSeparator}sade_factor.json');
      if (await _file!.exists()) {
        final j = jsonDecode(await _file!.readAsString()) as Map<String, dynamic>;
        _fromJson(j);
      }
    } catch (e) {
      debugPrint('load failed: $e');
    }
    loaded = true;
    notifyListeners();
  }

  void _fromJson(Map<String, dynamic> j) {
    business = Business.fromJson(Map<String, dynamic>.from(j['business'] ?? {}));
    customers
      ..clear()
      ..addAll(((j['customers'] ?? []) as List)
          .map((e) => Customer.fromJson(Map<String, dynamic>.from(e))));
    items
      ..clear()
      ..addAll(((j['items'] ?? []) as List)
          .map((e) => Item.fromJson(Map<String, dynamic>.from(e))));
    invoices
      ..clear()
      ..addAll(((j['invoices'] ?? []) as List)
          .map((e) => Invoice.fromJson(Map<String, dynamic>.from(e))));
    themeMode = ThemeMode.values.byName(j['themeMode'] ?? 'system');
    nextNumber = j['nextNumber'] ?? (invoices.length + 1);
    nextProformaNumber = j['nextProformaNumber'] ?? 1;
  }

  Map<String, dynamic> _toJson() => {
        'version': 1,
        'business': business.toJson(),
        'customers': customers.map((c) => c.toJson()).toList(),
        'items': items.map((c) => c.toJson()).toList(),
        'invoices': invoices.map((c) => c.toJson()).toList(),
        'themeMode': themeMode.name,
        'nextNumber': nextNumber,
        'nextProformaNumber': nextProformaNumber,
      };

  Future<void> save() async {
    notifyListeners();
    if (!persist || _file == null) return;
    try {
      final tmp = File('${_file!.path}.tmp');
      await tmp.writeAsString(jsonEncode(_toJson()), flush: true);
      await tmp.rename(_file!.path);
    } catch (e) {
      debugPrint('save failed: $e');
    }
  }

  String exportJson() => const JsonEncoder.withIndent('  ').convert(_toJson());

  // ---- lookups ----------------------------------------------------------

  Customer? customerById(String? id) {
    if (id == null) return null;
    for (final c in customers) {
      if (c.id == id) return c;
    }
    return null;
  }

  List<Invoice> get sortedInvoices =>
      [...invoices]..sort((a, b) => b.date.compareTo(a.date) != 0
          ? b.date.compareTo(a.date)
          : b.number.compareTo(a.number));

  Iterable<Invoice> get _live =>
      invoices.where((i) => i.status == InvoiceStatus.issued && !i.isProforma);

  int salesThisMonth([DateTime? now]) => _live
      .where((i) => sameJalaliMonth(i.date, now ?? DateTime.now()))
      .fold(0, (s, i) => s + i.total);

  int receivables() =>
      _live.where((i) => !i.paid).fold(0, (s, i) => s + i.total);

  int unpaidCount() => _live.where((i) => !i.paid).length;

  int vatThisQuarter([DateTime? now]) => _live
      .where((i) => sameJalaliQuarter(i.date, now ?? DateTime.now()))
      .fold(0, (s, i) => s + i.vat);

  /// Sales per Jalali month for the last [n] months, oldest first.
  List<int> monthlySales(int n, [DateTime? now]) {
    final j = Jalali.fromDateTime(now ?? DateTime.now());
    final out = <int>[];
    for (var k = n - 1; k >= 0; k--) {
      var y = j.year, m = j.month - k;
      while (m < 1) {
        m += 12;
        y -= 1;
      }
      final d = Jalali(y, m, 1).toDateTime();
      out.add(_live
          .where((i) => sameJalaliMonth(i.date, d))
          .fold(0, (s, i) => s + i.total));
    }
    return out;
  }

  List<String> monthLabels(int n, [DateTime? now]) {
    final j = Jalali.fromDateTime(now ?? DateTime.now());
    final out = <String>[];
    for (var k = n - 1; k >= 0; k--) {
      var m = j.month - k;
      while (m < 1) {
        m += 12;
      }
      out.add(jMonthName(Jalali(1400, m, 1).toDateTime()));
    }
    return out;
  }

  // ---- mutations --------------------------------------------------------

  void upsertCustomer(Customer c) {
    final i = customers.indexWhere((x) => x.id == c.id);
    if (i >= 0) {
      customers[i] = c;
    } else {
      customers.add(c);
    }
    save();
  }

  void deleteCustomer(Customer c) {
    customers.removeWhere((x) => x.id == c.id);
    save();
  }

  void upsertItem(Item it) {
    final i = items.indexWhere((x) => x.id == it.id);
    if (i >= 0) {
      items[i] = it;
    } else {
      items.add(it);
    }
    save();
  }

  static String normName(String s) => toLatinDigits(s)
      .replaceAll('ي', 'ی')
      .replaceAll('ك', 'ک')
      .replaceAll('\u200c', ' ')
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim()
      .toLowerCase();

  Item? itemByName(String name) {
    final n = normName(name);
    for (final it in items) {
      if (normName(it.name) == n) return it;
    }
    return null;
  }

  /// Adds the selected rows as items. Prices are converted to rial with
  /// [toRial]. Returns (added, updated).
  (int, int) importItems(List<ImportRow> rows, int toRial,
      {bool updateExisting = true}) {
    var added = 0, updated = 0;
    for (final r in rows.where((r) => r.selected && r.name.trim().isNotEmpty)) {
      final price = (r.price ?? 0) * toRial;
      final old = itemByName(r.name);
      if (old != null) {
        if (!updateExisting) continue;
        if (r.price != null) old.price = price;
        if (r.unit.isNotEmpty) old.unit = r.unit;
        if (r.stuffId.isNotEmpty) old.stuffId = r.stuffId;
        updated++;
      } else {
        items.add(Item(
          name: r.name.trim(),
          price: price,
          unit: r.unit.isNotEmpty ? r.unit : 'عدد',
          stuffId: r.stuffId,
          vatRate: business.effectiveVatRate,
        ));
        added++;
      }
    }
    save();
    return (added, updated);
  }

  void deleteItem(Item it) {
    items.removeWhere((x) => x.id == it.id);
    save();
  }

  Invoice newInvoice({DocKind kind = DocKind.invoice}) => Invoice(
      number: kind == DocKind.proforma ? nextProformaNumber : nextNumber,
      kind: kind);

  /// Switch an unsaved/draft document between invoice and proforma,
  /// giving it the next number of its new series.
  void setKind(Invoice inv, DocKind kind) {
    if (inv.kind == kind) return;
    inv.kind = kind;
    inv.number = kind == DocKind.proforma ? nextProformaNumber : nextNumber;
  }

  /// Make a real invoice draft from a proforma.
  Invoice invoiceFromProforma(Invoice p) {
    final copy = Invoice.fromJson(p.toJson());
    final inv = Invoice(
      number: nextNumber,
      customerId: copy.customerId,
      customerName: copy.customerName,
      type: copy.type,
      lines: copy.lines,
      note: copy.note,
    );
    saveInvoice(inv);
    return inv;
  }

  /// Turn VAT on/off for the business; when off, zero every item and every
  /// draft line so nothing new carries VAT.
  void setVatRegistered(bool on) {
    business.vatRegistered = on;
    if (!on) {
      for (final it in items) {
        it.vatRate = 0;
      }
      for (final inv in invoices.where((i) => i.status == InvoiceStatus.draft)) {
        for (final l in inv.lines) {
          l.vatRate = 0;
        }
      }
    } else {
      for (final it in items.where((i) => i.vatRate == 0)) {
        it.vatRate = business.defaultVatRate;
      }
    }
    save();
  }

  void saveInvoice(Invoice inv) {
    final i = invoices.indexWhere((x) => x.id == inv.id);
    if (i >= 0) {
      invoices[i] = inv;
    } else {
      invoices.add(inv);
      if (inv.isProforma) {
        if (inv.number >= nextProformaNumber) nextProformaNumber = inv.number + 1;
      } else if (inv.number >= nextNumber) {
        nextNumber = inv.number + 1;
      }
    }
    save();
  }

  void deleteInvoice(Invoice inv) {
    invoices.removeWhere((x) => x.id == inv.id);
    save();
  }
}

/// Makes the store reachable from any widget.
class StoreScope extends InheritedNotifier<AppStore> {
  const StoreScope({super.key, required AppStore store, required super.child})
      : super(notifier: store);

  static AppStore of(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<StoreScope>()!.notifier!;
}
