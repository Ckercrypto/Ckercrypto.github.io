// Data models for Sade Factor. Plain classes with JSON in/out.

enum CustomerKind { person, company }

/// Moadian invoice type: 1 = with buyer info (B2B), 2 = consumer.
enum InvoiceType { withBuyer, consumer }

enum InvoiceStatus { draft, issued, cancelled }

String newId() =>
    DateTime.now().microsecondsSinceEpoch.toRadixString(36) +
    (DateTime.now().hashCode & 0xfff).toRadixString(36);

class Business {
  String name;
  String ownerName;
  String nationalId; // کد ملی / شناسه ملی
  String economicCode; // کد اقتصادی
  String memoryId; // شناسه یکتای حافظه مالیاتی
  String phone;
  String address;
  String postalCode;
  double defaultVatRate; // percent

  Business({
    this.name = '',
    this.ownerName = '',
    this.nationalId = '',
    this.economicCode = '',
    this.memoryId = '',
    this.phone = '',
    this.address = '',
    this.postalCode = '',
    this.defaultVatRate = 10,
  });

  bool get isSetUp => name.trim().isNotEmpty;

  Map<String, dynamic> toJson() => {
        'name': name,
        'ownerName': ownerName,
        'nationalId': nationalId,
        'economicCode': economicCode,
        'memoryId': memoryId,
        'phone': phone,
        'address': address,
        'postalCode': postalCode,
        'defaultVatRate': defaultVatRate,
      };

  factory Business.fromJson(Map<String, dynamic> j) => Business(
        name: j['name'] ?? '',
        ownerName: j['ownerName'] ?? '',
        nationalId: j['nationalId'] ?? '',
        economicCode: j['economicCode'] ?? '',
        memoryId: j['memoryId'] ?? '',
        phone: j['phone'] ?? '',
        address: j['address'] ?? '',
        postalCode: j['postalCode'] ?? '',
        defaultVatRate: (j['defaultVatRate'] ?? 10).toDouble(),
      );
}

class Customer {
  final String id;
  CustomerKind kind;
  String name;
  String nationalId;
  String economicCode;
  String phone;
  String address;
  String postalCode;

  Customer({
    String? id,
    this.kind = CustomerKind.person,
    this.name = '',
    this.nationalId = '',
    this.economicCode = '',
    this.phone = '',
    this.address = '',
    this.postalCode = '',
  }) : id = id ?? newId();

  /// A buyer with a registered identity gets a type-1 invoice so they can
  /// claim VAT credit; everyone else gets type 2.
  bool get canReceiveType1 =>
      kind == CustomerKind.company ||
      economicCode.trim().isNotEmpty ||
      nationalId.trim().isNotEmpty;

  Map<String, dynamic> toJson() => {
        'id': id,
        'kind': kind.name,
        'name': name,
        'nationalId': nationalId,
        'economicCode': economicCode,
        'phone': phone,
        'address': address,
        'postalCode': postalCode,
      };

  factory Customer.fromJson(Map<String, dynamic> j) => Customer(
        id: j['id'],
        kind: CustomerKind.values.byName(j['kind'] ?? 'person'),
        name: j['name'] ?? '',
        nationalId: j['nationalId'] ?? '',
        economicCode: j['economicCode'] ?? '',
        phone: j['phone'] ?? '',
        address: j['address'] ?? '',
        postalCode: j['postalCode'] ?? '',
      );
}

class Item {
  final String id;
  String name;
  String stuffId; // شناسه ۱۳ رقمی کالا/خدمت
  String unit;
  int price; // rial
  double vatRate; // percent

  Item({
    String? id,
    this.name = '',
    this.stuffId = '',
    this.unit = 'عدد',
    this.price = 0,
    this.vatRate = 10,
  }) : id = id ?? newId();

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'stuffId': stuffId,
        'unit': unit,
        'price': price,
        'vatRate': vatRate,
      };

  factory Item.fromJson(Map<String, dynamic> j) => Item(
        id: j['id'],
        name: j['name'] ?? '',
        stuffId: j['stuffId'] ?? '',
        unit: j['unit'] ?? 'عدد',
        price: (j['price'] ?? 0) as int,
        vatRate: (j['vatRate'] ?? 10).toDouble(),
      );
}

class InvoiceLine {
  String itemId;
  String name;
  String stuffId;
  String unit;
  double qty;
  int unitPrice; // rial
  int discount; // rial, for the whole line
  double vatRate;

  InvoiceLine({
    required this.itemId,
    required this.name,
    this.stuffId = '',
    this.unit = 'عدد',
    this.qty = 1,
    this.unitPrice = 0,
    this.discount = 0,
    this.vatRate = 10,
  });

  factory InvoiceLine.fromItem(Item it) => InvoiceLine(
        itemId: it.id,
        name: it.name,
        stuffId: it.stuffId,
        unit: it.unit,
        unitPrice: it.price,
        vatRate: it.vatRate,
      );

  int get gross => (qty * unitPrice).round();
  int get net => gross - discount;
  int get vat => (net * vatRate / 100).round();
  int get total => net + vat;

  Map<String, dynamic> toJson() => {
        'itemId': itemId,
        'name': name,
        'stuffId': stuffId,
        'unit': unit,
        'qty': qty,
        'unitPrice': unitPrice,
        'discount': discount,
        'vatRate': vatRate,
      };

  factory InvoiceLine.fromJson(Map<String, dynamic> j) => InvoiceLine(
        itemId: j['itemId'] ?? '',
        name: j['name'] ?? '',
        stuffId: j['stuffId'] ?? '',
        unit: j['unit'] ?? 'عدد',
        qty: (j['qty'] ?? 1).toDouble(),
        unitPrice: (j['unitPrice'] ?? 0) as int,
        discount: (j['discount'] ?? 0) as int,
        vatRate: (j['vatRate'] ?? 10).toDouble(),
      );
}

class Invoice {
  final String id;
  int number;
  DateTime date;
  String? customerId;
  String customerName; // snapshot for display / consumer invoices
  InvoiceType type;
  List<InvoiceLine> lines;
  InvoiceStatus status;
  bool paid;
  String note;

  Invoice({
    String? id,
    required this.number,
    DateTime? date,
    this.customerId,
    this.customerName = '',
    this.type = InvoiceType.consumer,
    List<InvoiceLine>? lines,
    this.status = InvoiceStatus.draft,
    this.paid = false,
    this.note = '',
  })  : id = id ?? newId(),
        date = date ?? DateTime.now(),
        lines = lines ?? [];

  int get net => lines.fold(0, (s, l) => s + l.net);
  int get vat => lines.fold(0, (s, l) => s + l.vat);
  int get discount => lines.fold(0, (s, l) => s + l.discount);
  int get total => net + vat;

  /// Days left to register this invoice in the Moadian system (12-day rule).
  int get daysLeftToRegister =>
      12 - DateTime.now().difference(date).inDays;

  Map<String, dynamic> toJson() => {
        'id': id,
        'number': number,
        'date': date.toIso8601String(),
        'customerId': customerId,
        'customerName': customerName,
        'type': type.name,
        'lines': lines.map((l) => l.toJson()).toList(),
        'status': status.name,
        'paid': paid,
        'note': note,
      };

  factory Invoice.fromJson(Map<String, dynamic> j) => Invoice(
        id: j['id'],
        number: j['number'] ?? 0,
        date: DateTime.tryParse(j['date'] ?? '') ?? DateTime.now(),
        customerId: j['customerId'],
        customerName: j['customerName'] ?? '',
        type: InvoiceType.values.byName(j['type'] ?? 'consumer'),
        lines: ((j['lines'] ?? []) as List)
            .map((e) => InvoiceLine.fromJson(Map<String, dynamic>.from(e)))
            .toList(),
        status: InvoiceStatus.values.byName(j['status'] ?? 'draft'),
        paid: j['paid'] ?? false,
        note: j['note'] ?? '',
      );
}
