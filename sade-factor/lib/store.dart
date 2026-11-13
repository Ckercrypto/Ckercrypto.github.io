import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shamsi_date/shamsi_date.dart';

import 'format.dart';
import 'models.dart';

/// Holds all app data and saves it to one JSON file on the device.
class AppStore extends ChangeNotifier {
  Business business = Business();
  final List<Customer> customers = [];
  final List<Item> items = [];
  final List<Invoice> invoices = [];
  ThemeMode themeMode = ThemeMode.system;
  int nextNumber = 1;

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
  }

  Map<String, dynamic> _toJson() => {
        'version': 1,
        'business': business.toJson(),
        'customers': customers.map((c) => c.toJson()).toList(),
        'items': items.map((c) => c.toJson()).toList(),
        'invoices': invoices.map((c) => c.toJson()).toList(),
        'themeMode': themeMode.name,
        'nextNumber': nextNumber,
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
      invoices.where((i) => i.status == InvoiceStatus.issued);

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

  void deleteItem(Item it) {
    items.removeWhere((x) => x.id == it.id);
    save();
  }

  Invoice newInvoice() => Invoice(number: nextNumber);

  void saveInvoice(Invoice inv) {
    final i = invoices.indexWhere((x) => x.id == inv.id);
    if (i >= 0) {
      invoices[i] = inv;
    } else {
      invoices.add(inv);
      if (inv.number >= nextNumber) nextNumber = inv.number + 1;
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
