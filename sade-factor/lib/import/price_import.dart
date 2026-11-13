// Price-list import: turns PDF / Excel / CSV / Word files into item rows
// the user reviews before saving.
import 'dart:convert';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:excel/excel.dart' as xl;
import 'package:syncfusion_flutter_pdf/pdf.dart';
import 'package:xml/xml.dart';

import 'arabic_forms.dart';

class ImportRow {
  String name;
  int? price; // as written in the file (unit chosen later)
  String stuffId;
  String unit;
  bool selected;
  bool suspicious; // price far off its neighbours
  ImportRow({
    required this.name,
    this.price,
    this.stuffId = '',
    this.unit = '',
    bool? selected,
    this.suspicious = false,
  }) : selected = selected ?? price != null;
}

class ImportResult {
  final List<ImportRow> rows;
  final String? error;
  final PriceUnit? unit; // unit the file names, when it names one
  const ImportResult(this.rows, [this.error, this.unit]);
}

/// The unit a file's text names most: "ریال" or "تومان" (with "هزار").
PriceUnit? unitHint(String text) {
  final t = text.replaceAll('ي', 'ی');
  final rial = RegExp('ریال').allMatches(t).length;
  final toman = RegExp('تومان').allMatches(t).length;
  if (rial == 0 && toman == 0) return null;
  final thousand = RegExp(r'هزار\s*(ریال|تومان)').hasMatch(t);
  if (rial > toman) return thousand ? PriceUnit.thousandRial : PriceUnit.rial;
  return thousand ? PriceUnit.thousandToman : PriceUnit.toman;
}

String _lastText = '';

/// What the numbers in the file mean, converted to rial.
enum PriceUnit {
  toman('تومان', 10),
  rial('ریال', 1),
  thousandToman('هزار تومان', 10000),
  thousandRial('هزار ریال', 1000);

  final String label;
  final int toRial;
  const PriceUnit(this.label, this.toRial);
}

ImportResult importFile(String fileName, Uint8List bytes) {
  final ext = fileName.toLowerCase().split('.').last;
  try {
    switch (ext) {
      case 'pdf':
        return _finish(rowsFromPdf(bytes));
      case 'xlsx':
        return _finish(rowsFromTable(tableFromXlsx(bytes)));
      case 'csv':
      case 'txt':
        return _finish(rowsFromTable(tableFromCsv(_decodeText(bytes))));
      case 'docx':
        return _finish(rowsFromTable(tableFromDocx(bytes)));
      case 'xls':
        return const ImportResult(
            [], 'فایل xls قدیمیه. توی اکسل با Save As به xlsx تبدیلش کن.');
      case 'doc':
        return const ImportResult(
            [], 'فایل doc قدیمیه. توی ورد با Save As به docx تبدیلش کن.');
      default:
        return const ImportResult([], 'این نوع فایل پشتیبانی نمی‌شه.');
    }
  } catch (e) {
    return ImportResult([], 'فایل خونده نشد: $e');
  }
}

ImportResult _finish(List<ImportRow> rows) {
  final hint = unitHint(_lastText);
  _lastText = '';
  markSuspicious(rows);
  if (rows.isEmpty) {
    return const ImportResult([],
        'کالایی پیدا نشد. اگه PDF اسکن‌شده (عکس) باشه، متنی برای خوندن نداره.');
  }
  return ImportResult(rows, null, hint);
}

// ---------------------------------------------------------------- text utils

const _faDigits = '۰۱۲۳۴۵۶۷۸۹';
const _arDigits = '٠١٢٣٤٥٦٧٨٩';

String latinDigits(String s) {
  final b = StringBuffer();
  for (final r in s.runes) {
    final c = String.fromCharCode(r);
    final i = _faDigits.indexOf(c);
    final j = _arDigits.indexOf(c);
    b.write(i >= 0
        ? '$i'
        : j >= 0
            ? '$j'
            : c);
  }
  return b.toString();
}

final _priceRe = RegExp(r'^\d{1,3}([.,٬]\d{3})+$|^\d+$');

/// Parses "1.500.000", "1,500,000", "۲۵۰۰۰" -> int. Null when not a price.
int? parsePrice(String token) {
  final t = latinDigits(token.trim());
  if (!_priceRe.hasMatch(t)) return null;
  return int.tryParse(t.replaceAll(RegExp(r'[.,٬]'), ''));
}

bool _hasLetter(String s) => RegExp(r'[A-Za-z\u0600-\u06FF]').hasMatch(s);
bool _isRtlChar(int r) =>
    ((r >= 0x0590 && r <= 0x08FF) ||
        (r >= 0xFB1D && r <= 0xFDFF) ||
        (r >= 0xFE70 && r <= 0xFEFF)) &&
    !(r >= 0x06F0 && r <= 0x06F9) &&
    !(r >= 0x0660 && r <= 0x066C);

/// PDF text often keeps Persian in visual order and as presentation forms.
/// Restores logical order and base letters; leaves Latin text alone.
String fixRtl(String s) {
  final runes = s.runes.toList();
  final rtl = runes.where(_isRtlChar).length;
  final hasForms = runes.any((r) => presentationForms.containsKey(r));
  if (rtl == 0) return s;
  List<int> seq = runes;
  if (hasForms) {
    // Visual order: reverse the whole line, then put LTR runs back.
    seq = runes.reversed.toList();
    final out = <int>[];
    var i = 0;
    while (i < seq.length) {
      if (_isLtrRunChar(seq[i])) {
        var j = i;
        while (j < seq.length &&
            (_isLtrRunChar(seq[j]) || _innerNeutral(seq, j))) {
          j++;
        }
        out.addAll(seq.sublist(i, j).reversed);
        i = j;
      } else {
        out.add(seq[i]);
        i++;
      }
    }
    seq = out;
  }
  final b = StringBuffer();
  for (final r in seq) {
    b.write(presentationForms[r] ?? String.fromCharCode(r));
  }
  return b.toString().replaceAll(RegExp(r'\s+'), ' ').trim();
}

bool _isLtrRunChar(int r) =>
    (r >= 0x30 && r <= 0x39) ||
    (r >= 0x41 && r <= 0x5A) ||
    (r >= 0x61 && r <= 0x7A) ||
    (r >= 0x06F0 && r <= 0x06F9);

bool _innerNeutral(List<int> s, int j) {
  // ".", ",", "/", "-", space between two LTR chars stay inside the run.
  const n = [0x2E, 0x2C, 0x2F, 0x2D, 0x20, 0x2A, 0x3A];
  if (!n.contains(s[j])) return false;
  var k = j + 1;
  while (k < s.length && n.contains(s[k])) {
    k++;
  }
  return k < s.length && _isLtrRunChar(s[k]);
}

/// Fonts with tt/ti/fi ligatures and no text map drop those letters
/// ("ba  ery", "interac ve"). Repairs common product words.
const _ligatureWords = [
  'battery',
  'batteries',
  'interactive',
  'interaction',
  'active',
  'protection',
  'connection',
  'function',
  'digital',
  'output',
  'option',
  'station',
  'automatic',
  'office',
  'efficiency',
  'filter',
  'profile',
  'watt',
  'watts',
  'kilowatt',
  'setting',
  'cutting',
  'split',
  'portable',
  'stabilizer',
  'stabilization',
  'regulation',
  'isolation',
  'insulation',
  'ventilation',
];

String fixLigatures(String s) {
  var out = s;
  for (final w in _ligatureWords) {
    for (final lig in ['tt', 'ti', 'fi', 'fl', 'ff', 'ft', 'ffi']) {
      final i = w.indexOf(lig);
      if (i < 0) continue;
      final a = RegExp.escape(w.substring(0, i));
      final z = RegExp.escape(w.substring(i + lig.length));
      if (a.isEmpty || z.isEmpty) continue;
      out = out.replaceAllMapped(
          RegExp(
              '($a)[\\s\\u0000-\\u001F\\u00A0\\u2000-\\u200B\\uFFFD]{1,2}($z)\\b',
              caseSensitive: false),
          (m) => '${m[1]}${_matchCase(lig, m[1]!)}${m[2]}');
    }
  }
  return out;
}

String _matchCase(String lig, String before) => before.isNotEmpty &&
        before[before.length - 1].toUpperCase() == before[before.length - 1] &&
        RegExp(r'[A-Z]').hasMatch(before[before.length - 1])
    ? lig.toUpperCase()
    : lig;

String cleanName(String s) => fixLigatures(fixRtl(s))
    .replaceAll(RegExp(r'[\u0000-\u001F\uFFFD]'), '')
    .replaceAll(RegExp(r'\s+'), ' ')
    .trim();

final _capacityRe = RegExp(
    r'\d+(\.\d+)?\s*(kva|va|kw|w|ah|vdc|v|a|hp|kg|کیلووات|وات|آمپر|ولت|کاوا)\b',
    caseSensitive: false);

bool _looksLikeProduct(String name) =>
    name.length >= 3 &&
    _hasLetter(name) &&
    (_capacityRe.hasMatch(latinDigits(name)) ||
        RegExp(r'[A-Za-z\u0600-\u06FF].*\d|\d.*[A-Za-z\u0600-\u06FF]')
            .hasMatch(latinDigits(name)));

/// Flags a price more than 5x both its priced neighbours (likely a typo).
void markSuspicious(List<ImportRow> rows) {
  final priced = rows.where((r) => r.price != null && r.price! > 0).toList();
  for (var i = 0; i < priced.length; i++) {
    final p = priced[i].price!;
    final prev = i > 0 ? priced[i - 1].price! : null;
    final next = i + 1 < priced.length ? priced[i + 1].price! : null;
    if (prev == null && next == null) continue;
    final hiPrev = prev == null || p > prev * 5;
    final hiNext = next == null || p > next * 5;
    final loPrev = prev == null || p * 5 < prev;
    final loNext = next == null || p * 5 < next;
    if ((hiPrev && hiNext) || (loPrev && loNext)) priced[i].suspicious = true;
  }
}

// ---------------------------------------------------------------------- PDF

class _Frag {
  final int page;
  final double top, bottom, left, right;
  final String text;
  _Frag(this.page, this.top, this.bottom, this.left, this.right, this.text);
  double get h => bottom - top;
  bool get rtl =>
      text.runes.any(_isRtlChar) && !RegExp(r'^[A-Za-z]').hasMatch(text);
  double get start => rtl ? right : left;
}

List<ImportRow> rowsFromPdf(Uint8List bytes) {
  final doc = PdfDocument(inputBytes: bytes);
  final lines = PdfTextExtractor(doc).extractTextLines();
  final frags = <_Frag>[for (final l in lines) ..._lineFrags(l)];
  doc.dispose();
  _lastText = frags.map((f) => f.text).join('\n');
  return _rowsFromFragments(frags);
}

/// Rebuilds a text line from glyph positions and splits it into cells at
/// wide gaps. Persian runs are read right to left, digits and Latin left to
/// right, and presentation forms are mapped back to plain letters.
List<_Frag> _lineFrags(TextLine l) {
  final rtlLine = l.text.runes.any(_isRtlChar);
  // Latin lines: word boxes (keeps the PDF's own spacing). Persian lines:
  // glyph boxes, since word order there is unreliable.
  final gs = <_Box>[];
  for (final w in l.wordCollection) {
    if (rtlLine) {
      for (final g in w.glyphs) {
        if (g.text.trim().isEmpty || g.text == '\u200c') continue;
        gs.add(_Box(g.text, g.bounds.left, g.bounds.right));
      }
    } else if (w.text.isNotEmpty) {
      gs.add(_Box(w.text, w.bounds.left, w.bounds.right));
    }
  }
  if (gs.isEmpty) return [];
  // The extractor can report the same glyph in two words; keep one.
  final seen = <String>{};
  gs.retainWhere((g) => seen.add('${g.text}@${g.left.toStringAsFixed(1)}'));
  gs.sort((a, b) => a.left.compareTo(b.left));
  final h = l.bounds.height <= 0 ? 10.0 : l.bounds.height;
  final cellGap = h * 1.1 < 8 ? 8.0 : h * 1.1;
  final clusters = <List<_Box>>[
    [gs.first]
  ];
  for (final g in gs.skip(1)) {
    final prev = clusters.last.last;
    if (g.text.trim().isNotEmpty && g.left - prev.right > cellGap) {
      clusters.add([g]);
    } else {
      clusters.last.add(g);
    }
  }
  // Latin: take each cell's text from the line text, which has the right
  // spaces, by walking it character by character.
  List<String>? ltrTexts;
  if (!rtlLine) {
    final src = l.text;
    var pos = 0;
    ltrTexts = [];
    for (final c in clusters) {
      final need =
          c.map((b) => b.text.replaceAll(RegExp(r'\s'), '')).join().length;
      final b = StringBuffer();
      var got = 0;
      while (pos < src.length && got < need) {
        final ch = src[pos++];
        b.write(ch);
        if (ch.trim().isNotEmpty) got++;
      }
      ltrTexts.add(b.toString().trim());
    }
    if (pos < src.length && src.substring(pos).trim().isNotEmpty) {
      ltrTexts = null;
    }
  }
  final out = <_Frag>[];
  for (var ci = 0; ci < clusters.length; ci++) {
    final c = clusters[ci];
    var t = ltrTexts?[ci] ?? _glyphText(c, h);
    if (t.isEmpty) continue;
    out.add(_Frag(l.pageIndex, l.bounds.top, l.bounds.bottom, c.first.left,
        c.map((g) => g.right).reduce((a, b) => a > b ? a : b), t));
  }
  return out;
}

class _Box {
  final String text;
  final double left, right;
  _Box(this.text, this.left, this.right);
}

String _glyphText(List<_Box> c, double h) {
  final rtl = c.any((g) => g.text.runes.any(_isRtlChar));
  final seq = [...c];
  if (rtl) seq.sort((a, b) => b.left.compareTo(a.left));
  final units = <String>[];
  _Box? prev;
  for (final g in seq) {
    if (prev != null) {
      final gap = rtl ? prev.left - g.right : g.left - prev.right;
      if (gap > h * (rtl ? 0.22 : 0.45)) units.add(' ');
    }
    units.add(g.text);
    prev = g;
  }
  var out = units;
  if (rtl) {
    // Runs of digits / Latin came out backwards; flip each run back.
    const punctChars = '.,/-*:%٬()';
    bool ltr(String u) =>
        u.runes.any(_isLtrRunChar) &&
        u.runes.every((r) => _isLtrRunChar(r) || punctChars.runes.contains(r));
    bool punct(String u) => u.runes.every((r) => punctChars.runes.contains(r));
    out = <String>[];
    var i = 0;
    while (i < units.length) {
      if (ltr(units[i])) {
        var j = i + 1;
        while (j < units.length) {
          final u = units[j];
          if (ltr(u)) {
            j++;
          } else if ((u == ' ' || punct(u)) &&
              j + 1 < units.length &&
              ltr(units[j + 1])) {
            j++;
          } else {
            break;
          }
        }
        out.addAll(units.sublist(i, j).reversed);
        i = j;
      } else {
        out.add(units[i]);
        i++;
      }
    }
  }
  final b = StringBuffer();
  for (final u in out) {
    for (final r in u.runes) {
      b.write(presentationForms[r] ?? String.fromCharCode(r));
    }
  }
  return b.toString().replaceAll(RegExp(r'[ \t]+'), ' ').trim();
}

List<ImportRow> _rowsFromFragments(List<_Frag> frags) {
  final rows = <ImportRow>[];
  final pages = frags.map((f) => f.page).toSet().toList()..sort();
  for (final p in pages) {
    rows.addAll(_pageRows(frags.where((f) => f.page == p).toList()));
  }
  return rows;
}

List<ImportRow> _pageRows(List<_Frag> fs) {
  if (fs.isEmpty) return [];
  // 1) The name column: the left edge most text starts at.
  final weight = <int, int>{};
  for (final f in fs) {
    if (!_hasLetter(f.text)) continue;
    if (f.text.length > 60) continue;
    final w = 3 + (f.text.length > 12 ? 12 : f.text.length);
    final kl = (f.left / 6).round();
    final kr = 100000 + (f.right / 6).round();
    weight[kl] = (weight[kl] ?? 0) + w;
    weight[kr] = (weight[kr] ?? 0) + w;
  }
  if (weight.isEmpty) return [];
  final nameKey =
      weight.entries.reduce((a, b) => a.value >= b.value ? a : b).key;
  final nameRtl = nameKey >= 100000;
  final nameX = (nameKey % 100000) * 6.0;
  // A header row naming the columns wins when it puts the names elsewhere
  // (e.g. a dimensions column that the left-edge guess picked instead).
  final guessed = [
    for (final f in fs)
      if (_hasLetter(f.text) &&
          ((nameRtl ? f.right : f.left) - nameX).abs() <= 9)
        (f.left + f.right) / 2
  ]..sort();
  final byHead = _headerRows(fs, guessed[guessed.length ~/ 2]);
  if (byHead != null) return byHead;
  bool inNameCol(_Frag f) =>
      (nameRtl ? f.right : f.left) - nameX <= 9 &&
      nameX - (nameRtl ? f.right : f.left) <= 9;

  // 2) Drop the group/category column outside the name column (merged
  //    cells there span several rows), then group fragments into visual
  //    rows by vertical overlap.
  fs = fs
      .where((f) => nameRtl ? f.left < nameX + 9 : f.right > nameX - 9)
      .toList();
  fs.sort((a, b) => a.top.compareTo(b.top));
  final groups = <List<_Frag>>[];
  for (final f in fs) {
    List<_Frag>? hit;
    for (final g in groups.reversed.take(4)) {
      if (g.any((o) {
        final ov = (f.bottom < o.bottom ? f.bottom : o.bottom) -
            (f.top > o.top ? f.top : o.top);
        final mh = f.h < o.h ? f.h : o.h;
        return ov > mh * 0.2;
      })) {
        hit = g;
        break;
      }
    }
    hit == null ? groups.add([f]) : hit.add(f);
  }

  // 3) Each row: name = fragments starting at the name column; price = a
  //    number at the end of the fragment farthest from the name column
  //    (works for left-to-right and right-to-left tables).
  final out = <_PdfRow>[];
  for (final g in groups) {
    g.sort((a, b) => a.left.compareTo(b.left));
    final nameFrags = g.where(inNameCol).toList()
      ..sort((a, b) => (a.top - b.top).abs() > a.h / 2
          ? a.top.compareTo(b.top)
          : a.left.compareTo(b.left));
    if (nameFrags.isEmpty) continue;
    final byDist = [...g]..sort((a, b) => ((b.left + b.right) / 2 - nameX)
        .abs()
        .compareTo(((a.left + a.right) / 2 - nameX).abs()));
    _Frag? pf;
    int? price;
    var dash = false;
    var rest = <String>[];
    for (final strict in [true, false]) {
      for (final f in byDist) {
        final tokens = f.text.split(RegExp(r'\s+'));
        final rtl = f.text.runes.any(_isRtlChar);
        for (final atEnd in rtl ? [true, false] : [true]) {
          final tok = atEnd ? tokens.last : tokens.first;
          final v = parsePrice(tok);
          final d = tok == '-' || tok == '—';
          if ((v != null && (!strict || v >= 100)) || d) {
            pf = f;
            price = v;
            dash = d;
            rest = atEnd
                ? tokens.sublist(0, tokens.length - 1)
                : tokens.sublist(1);
            break;
          }
        }
        if (pf != null) break;
      }
      if (pf != null) break;
    }
    var name = '';
    if (pf != null && nameFrags.contains(pf)) {
      name = [
        for (final f in nameFrags) identical(f, pf) ? rest.join(' ') : f.text
      ].join(' ');
    } else {
      name = nameFrags.map((f) => f.text).join(' ');
      if (pf != null && rest.isNotEmpty) {
        final extra = rest.join(' ');
        // Spec columns of pure numbers are dropped; words (a brand) are kept.
        if (_hasLetter(extra)) name = '$name $extra';
      }
    }
    name = cleanName(name);
    if (name.isEmpty) continue;
    out.add(_PdfRow(
        name,
        dash ? null : price,
        g.first.top,
        g.map((f) => f.bottom).reduce((a, b) => a > b ? a : b),
        nameFrags.first.h));
  }

  // 4) A priced line with no size in it, right under an unpriced line, is the
  //    second line of a wrapped cell.
  final merged = <_PdfRow>[];
  for (final r in out) {
    if (merged.isNotEmpty) {
      final a = merged.last;
      if (a.price == null &&
          r.price != null &&
          r.top - a.bottom < a.h * 0.8 &&
          !_capacityRe.hasMatch(r.name) &&
          _capacityRe.hasMatch(a.name)) {
        merged[merged.length - 1] =
            _PdfRow('${a.name} ${r.name}', r.price, a.top, r.bottom, a.h);
        continue;
      }
    }
    merged.add(r);
  }

  // Bare codes like "B1": prefix the column header above them.
  final priced = merged.where((r) => r.price != null).toList();
  var prefix = '';
  if (priced.isNotEmpty &&
      priced.where((r) => r.name.length <= 4).length * 2 > priced.length) {
    final i = merged.indexOf(priced.first);
    final heads = merged.sublist(0, i).where((r) => r.price == null);
    if (heads.isNotEmpty) prefix = heads.map((r) => r.name).join(' ');
    if (prefix.length > 30) prefix = '';
  }
  return [
    for (final r in merged)
      if (r.price != null || _looksLikeProduct(r.name))
        ImportRow(
            name: prefix.isNotEmpty && r.name.length <= 4
                ? '$prefix ${r.name}'
                : r.name,
            price: r.price),
  ];
}

String _headNorm(String t) => t
    .replaceAll('ي', 'ی')
    .replaceAll('ك', 'ک')
    .replaceAll('\u200c', ' ')
    .toLowerCase()
    .trim();

final _nameHeadRe = RegExp(
    r'^(نام|شرح|مدل|کالا|عنوان|محصول|model|item|product|name)( .*)?$');
final _priceHeadRe = RegExp(r'^(قیمت|مبلغ|فی|price)( .*)?$');
final _dimRe = RegExp(r'\d\s*[*×xX]\s*\d');

/// Table with a header row ("مدل" … "قیمت"): names come from the column
/// under the name header, prices from the number column nearest the price
/// header, each price paired with the closest name vertically.
List<ImportRow>? _headerRows(List<_Frag> fs, double guessedNameX) {
  _Frag? nh, ph;
  for (final f in fs) {
    final t = _headNorm(f.text);
    if (t.length > 20 || RegExp(r'\d').hasMatch(t)) continue;
    if (ph == null && _priceHeadRe.hasMatch(t)) ph = f;
  }
  if (ph == null) return null;
  for (final f in fs) {
    final t = _headNorm(f.text);
    if (t.length > 20 || RegExp(r'\d').hasMatch(t)) continue;
    if ((f.top - ph.top).abs() > ph.h * 3) continue;
    if (_nameHeadRe.hasMatch(t)) {
      nh = f;
      break;
    }
  }
  if (nh == null) return null;
  final headBottom = [nh.bottom, ph.bottom].reduce((a, b) => a > b ? a : b);
  final heads = fs
      .where((f) =>
          (f.top - nh!.top).abs() <= nh.h * 3 &&
          f.top <= headBottom + 1 &&
          !RegExp(r'\d').hasMatch(f.text))
      .toList()
    ..sort((a, b) => a.left.compareTo(b.left));
  double cx(_Frag f) => (f.left + f.right) / 2;
  final i = heads.indexOf(nh);
  final lo = i > 0 ? (cx(heads[i - 1]) + cx(nh)) / 2 : -1e9;
  final hi = i + 1 < heads.length ? (cx(heads[i + 1]) + cx(nh)) / 2 : 1e9;
  if (guessedNameX >= lo && guessedNameX <= hi) return null; // guess agrees

  final body = fs.where((f) => f.top > headBottom).toList();
  final names = body
      .where((f) =>
          cx(f) >= lo &&
          cx(f) <= hi &&
          _hasLetter(f.text) &&
          !_dimRe.hasMatch(f.text))
      .toList()
    ..sort((a, b) => a.top.compareTo(b.top));
  if (names.isEmpty) return null;
  // A price cell can run into the next cell ("2,700,000,000 65*35*84cm").
  String tok(_Frag f) => f.text.trim().split(RegExp(r'\s+')).first;
  bool isPrice(_Frag f) {
    final t = tok(f);
    if (t == '-' || t == '—') return true;
    if (_dimRe.hasMatch(t) || t.contains('/')) return false;
    final v = parsePrice(t);
    return v != null && v >= 100;
  }

  final nums = body.where(isPrice).toList();
  if (nums.isEmpty) return null;
  // The price column: right edge of the number nearest the price header.
  nums.sort((a, b) => (cx(a) - cx(ph!)).abs().compareTo((cx(b) - cx(ph)).abs()));
  final ref = nums.first;
  final prices = nums
      .where((f) =>
          (f.right - ref.right).abs() < 15 || (f.left - ref.left).abs() < 15)
      .where((f) => !names.contains(f))
      .toList();

  // Pair each price with the nearest free name (ties go to the name above).
  final pairs = <(double, _Frag, _Frag)>[];
  for (final p in prices) {
    final pc = (p.top + p.bottom) / 2;
    for (final n in names) {
      final d = ((n.top + n.bottom) / 2 - pc);
      if (d.abs() > n.h * 6) continue;
      pairs.add((d.abs() + (d > 0 ? 0.01 : 0), p, n));
    }
  }
  pairs.sort((a, b) => a.$1.compareTo(b.$1));
  final priceOf = <_Frag, _Frag>{};
  final usedP = <_Frag>{};
  for (final (_, p, n) in pairs) {
    if (usedP.contains(p) || priceOf.containsKey(n)) continue;
    priceOf[n] = p;
    usedP.add(p);
  }
  return [
    for (final n in names)
      if (cleanName(n.text).isNotEmpty)
        ImportRow(
            name: cleanName(n.text),
            price: priceOf[n] == null ? null : parsePrice(tok(priceOf[n]!))),
  ];
}

class _PdfRow {
  final String name;
  final int? price;
  final double top, bottom, h;
  _PdfRow(this.name, this.price, this.top, this.bottom, this.h);
}

// ------------------------------------------------------ tables (xlsx/csv/docx)

List<List<String>> tableFromXlsx(Uint8List bytes) {
  final book = xl.Excel.decodeBytes(bytes);
  final out = <List<String>>[];
  for (final name in book.tables.keys) {
    final sheet = book.tables[name]!;
    for (final row in sheet.rows) {
      out.add([for (final c in row) _cellText(c?.value)]);
    }
    out.add(const []); // sheet break
  }
  return out;
}

String _cellText(xl.CellValue? v) {
  if (v == null) return '';
  if (v is xl.IntCellValue) return '${v.value}';
  if (v is xl.DoubleCellValue) {
    final d = v.value;
    return d == d.roundToDouble() ? '${d.round()}' : '$d';
  }
  if (v is xl.TextCellValue) return v.value.toString();
  return v.toString();
}

String _decodeText(Uint8List bytes) {
  var b = bytes;
  if (b.length >= 3 && b[0] == 0xEF && b[1] == 0xBB && b[2] == 0xBF) {
    b = b.sublist(3);
  }
  try {
    return utf8.decode(b);
  } catch (_) {
    return latin1.decode(b);
  }
}

List<List<String>> tableFromCsv(String text) {
  final first = text.split('\n').first;
  final sep = [';', '\t', ',']
      .reduce((a, b) => first.split(a).length >= first.split(b).length ? a : b);
  final rows = <List<String>>[];
  var row = <String>[];
  final cell = StringBuffer();
  var q = false;
  for (var i = 0; i < text.length; i++) {
    final c = text[i];
    if (q) {
      if (c == '"') {
        if (i + 1 < text.length && text[i + 1] == '"') {
          cell.write('"');
          i++;
        } else {
          q = false;
        }
      } else {
        cell.write(c);
      }
    } else if (c == '"') {
      q = true;
    } else if (c == sep) {
      row.add(cell.toString());
      cell.clear();
    } else if (c == '\n' || c == '\r') {
      if (c == '\r' && i + 1 < text.length && text[i + 1] == '\n') i++;
      row.add(cell.toString());
      cell.clear();
      rows.add(row);
      row = <String>[];
    } else {
      cell.write(c);
    }
  }
  if (cell.isNotEmpty || row.isNotEmpty) {
    row.add(cell.toString());
    rows.add(row);
  }
  return rows;
}

List<List<String>> tableFromDocx(Uint8List bytes) {
  final zip = ZipDecoder().decodeBytes(bytes);
  final f = zip.findFile('word/document.xml');
  if (f == null) return [];
  final doc = XmlDocument.parse(utf8.decode(f.content as List<int>));
  String text(XmlElement e) =>
      e.findAllElements('w:t').map((t) => t.innerText).join();
  final out = <List<String>>[];
  final tables = doc.findAllElements('w:tbl').toList();
  if (tables.isNotEmpty) {
    for (final t in tables) {
      for (final tr in t.findAllElements('w:tr')) {
        out.add([for (final tc in tr.findElements('w:tc')) text(tc).trim()]);
      }
      out.add(const []);
    }
  } else {
    // No table: one paragraph per line, split on tabs / runs of spaces.
    for (final p in doc.findAllElements('w:p')) {
      final s = p.descendants
          .map((n) => n is XmlElement && n.name.qualified == 'w:tab'
              ? '\t'
              : n is XmlElement && n.name.qualified == 'w:t'
                  ? n.innerText
                  : '')
          .join();
      if (s.trim().isEmpty) continue;
      out.add(s.split(RegExp(r'\t+| {3,}')).map((x) => x.trim()).toList());
    }
  }
  return out;
}

const _nameHeads = [
  'نام',
  'شرح',
  'کالا',
  'مدل',
  'محصول',
  'عنوان',
  'name',
  'item',
  'model',
  'product',
  'description'
];
const _priceHeads = ['قیمت', 'فی', 'مبلغ', 'price', 'cost'];
const _unitHeads = ['واحد', 'unit'];
const _idHeads = ['شناسه', 'کد', 'code', 'id', 'sku'];

int _findHead(List<String> row, List<String> keys, {Set<int> skip = const {}}) {
  for (var i = 0; i < row.length; i++) {
    if (skip.contains(i)) continue;
    final c = row[i].toLowerCase();
    if (keys.any((k) => c.contains(k))) return i;
  }
  return -1;
}

List<ImportRow> rowsFromTable(List<List<String>> table) {
  _lastText = table.map((r) => r.join(' ')).join('\n');
  final out = <ImportRow>[];
  // Split into blocks at empty rows (sheets / separate tables).
  var block = <List<String>>[];
  void flush() {
    if (block.isNotEmpty) out.addAll(_blockRows(block));
    block = [];
  }

  for (final r in table) {
    if (r.every((c) => c.trim().isEmpty)) {
      flush();
    } else {
      block.add(r.map((c) => c.trim()).toList());
    }
  }
  flush();
  return out;
}

List<ImportRow> _blockRows(List<List<String>> rows) {
  // Header row: first of the top 5 rows naming a price and a name column.
  var head = -1, nameCol = -1, priceCol = -1, unitCol = -1, idCol = -1;
  for (var i = 0; i < rows.length && i < 5; i++) {
    final p = _findHead(rows[i], _priceHeads);
    final n = _findHead(rows[i], _nameHeads, skip: {p});
    if (p >= 0 && n >= 0) {
      head = i;
      priceCol = p;
      nameCol = n;
      unitCol = _findHead(rows[i], _unitHeads, skip: {p, n});
      idCol = _findHead(rows[i], _idHeads, skip: {p, n, unitCol});
      break;
    }
  }
  final body = rows.sublist(head + 1);
  if (body.isEmpty) return [];
  final width = body.map((r) => r.length).reduce((a, b) => a > b ? a : b);
  if (nameCol < 0) {
    // Guess: name = column with most letters; price = rightmost mostly-price column.
    var best = -1, bestScore = 0;
    for (var c = 0; c < width; c++) {
      var s = 0;
      for (final r in body) {
        if (c < r.length && _hasLetter(r[c])) s += r[c].length;
      }
      if (s > bestScore) {
        bestScore = s;
        best = c;
      }
    }
    nameCol = best;
    var bestP = -1, bestCount = 0;
    for (var c = 0; c < width; c++) {
      if (c == nameCol) continue;
      var n = 0;
      for (final r in body) {
        final v = c < r.length ? parsePrice(r[c]) : null;
        if (v != null && v >= 100) n++;
      }
      if (n > 0 && n >= bestCount) {
        bestCount = n;
        bestP = c;
      }
    }
    priceCol = bestP;
  }
  if (nameCol < 0) return [];
  final res = <ImportRow>[];
  for (final r in body) {
    String at(int c) => c >= 0 && c < r.length ? r[c] : '';
    final name = cleanName(at(nameCol));
    if (name.isEmpty) continue;
    final price = parsePrice(at(priceCol));
    if (price == null && !_looksLikeProduct(name)) continue;
    final id = latinDigits(at(idCol)).replaceAll(RegExp(r'\D'), '');
    res.add(ImportRow(
      name: name,
      price: price,
      unit: at(unitCol),
      stuffId: id.length == 13 ? id : '',
    ));
  }
  return res;
}
