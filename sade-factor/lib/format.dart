import 'package:shamsi_date/shamsi_date.dart';

const _fa = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];

String faDigits(Object v) {
  final s = v.toString();
  final b = StringBuffer();
  for (final c in s.runes) {
    final ch = String.fromCharCode(c);
    final d = int.tryParse(ch);
    b.write(d != null && ch.length == 1 && c >= 48 && c <= 57 ? _fa[d] : ch);
  }
  return b.toString();
}

/// Converts Persian/Arabic digits typed by the user to Latin digits.
String toLatinDigits(String s) {
  const ar = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];
  var out = s;
  for (var i = 0; i < 10; i++) {
    out = out.replaceAll(_fa[i], '$i').replaceAll(ar[i], '$i');
  }
  return out.replaceAll('٬', '').replaceAll(',', '');
}

String groupThousands(int n) {
  final neg = n < 0;
  final s = n.abs().toString();
  final b = StringBuffer();
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) b.write('٬');
    b.write(s[i]);
  }
  return (neg ? '-' : '') + b.toString();
}

/// Amounts are stored in rial and shown in toman.
String toman(int rial) => '${faDigits(groupThousands((rial / 10).round()))} تومان';

String num0(num n) =>
    faDigits(n == n.roundToDouble() ? n.toInt().toString() : n.toString());

const _months = [
  'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
  'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
];

String jDate(DateTime d) {
  final j = Jalali.fromDateTime(d);
  return faDigits('${j.year}/${j.month.toString().padLeft(2, '0')}/${j.day.toString().padLeft(2, '0')}');
}

String jDateLong(DateTime d) {
  final j = Jalali.fromDateTime(d);
  return '${faDigits(j.day)} ${_months[j.month - 1]} ${faDigits(j.year)}';
}

String jMonthName(DateTime d) => _months[Jalali.fromDateTime(d).month - 1];

bool sameJalaliMonth(DateTime a, DateTime b) {
  final x = Jalali.fromDateTime(a), y = Jalali.fromDateTime(b);
  return x.year == y.year && x.month == y.month;
}

int jalaliQuarter(DateTime d) => (Jalali.fromDateTime(d).month - 1) ~/ 3 + 1;

bool sameJalaliQuarter(DateTime a, DateTime b) =>
    Jalali.fromDateTime(a).year == Jalali.fromDateTime(b).year &&
    jalaliQuarter(a) == jalaliQuarter(b);

const quarterNames = ['بهار', 'تابستان', 'پاییز', 'زمستان'];

// ---- validation -----------------------------------------------------------

/// Iranian 10-digit national code checksum.
bool isValidNationalCode(String raw) {
  final s = toLatinDigits(raw.trim());
  if (!RegExp(r'^\d{10}$').hasMatch(s)) return false;
  if (RegExp(r'^(\d)\1{9}$').hasMatch(s)) return false;
  final check = int.parse(s[9]);
  var sum = 0;
  for (var i = 0; i < 9; i++) {
    sum += int.parse(s[i]) * (10 - i);
  }
  final r = sum % 11;
  return r < 2 ? check == r : check == 11 - r;
}

/// Iranian 11-digit legal-entity national ID checksum.
bool isValidLegalId(String raw) {
  final s = toLatinDigits(raw.trim());
  if (!RegExp(r'^\d{11}$').hasMatch(s)) return false;
  final d = int.parse(s[9]) + 2;
  const coef = [29, 27, 23, 19, 17, 29, 27, 23, 19, 17];
  var sum = 0;
  for (var i = 0; i < 10; i++) {
    sum += (int.parse(s[i]) + d) * coef[i];
  }
  var r = sum % 11;
  if (r == 10) r = 0;
  return r == int.parse(s[10]);
}

bool isValidStuffId(String raw) =>
    RegExp(r'^\d{13}$').hasMatch(toLatinDigits(raw.trim()));
