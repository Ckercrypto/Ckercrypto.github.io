import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import 'common.dart';

/// A card row that lets the user pick an image (logo, signature, stamp),
/// shows a preview on a checkerboard so transparency is visible, and
/// returns it as base64.
class ImageSlot extends StatelessWidget {
  final String title;
  final String hint;
  final String value; // base64, '' when empty
  final bool pngOnly;
  final ValueChanged<String> onChanged;

  const ImageSlot({
    super.key,
    required this.title,
    required this.hint,
    required this.value,
    required this.onChanged,
    this.pngOnly = false,
  });

  static const maxBytes = 1500 * 1024;

  Future<void> _pick(BuildContext context) async {
    final res = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: pngOnly ? ['png'] : ['png', 'jpg', 'jpeg'],
      withData: true,
    );
    final f = res?.files.firstOrNull;
    if (f == null || f.bytes == null) return;
    if (f.bytes!.length > maxBytes) {
      if (context.mounted) toast(context, 'عکس بزرگه؛ زیر ۱.۵ مگابایت انتخاب کن');
      return;
    }
    onChanged(base64Encode(f.bytes!));
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(children: [
        Container(
          width: 72,
          height: 72,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: cs.outlineVariant),
          ),
          clipBehavior: Clip.antiAlias,
          child: value.isEmpty
              ? Icon(Icons.add_photo_alternate_rounded,
                  color: cs.onSurfaceVariant)
              : CustomPaint(
                  painter: _Checker(cs.surfaceContainerHighest),
                  child: Padding(
                    padding: const EdgeInsets.all(4),
                    child: Image.memory(base64Decode(value),
                        fit: BoxFit.contain, gaplessPlayback: true),
                  ),
                ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 2),
            Text(hint,
                style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant)),
          ]),
        ),
        if (value.isNotEmpty)
          IconButton(
            tooltip: 'حذف',
            onPressed: () => onChanged(''),
            icon: Icon(Icons.delete_outline_rounded, color: Colors.red.shade400),
          ),
        FilledButton.tonal(
          onPressed: () => _pick(context),
          child: Text(value.isEmpty ? 'انتخاب' : 'تعویض'),
        ),
      ]),
    );
  }
}

class _Checker extends CustomPainter {
  final Color c;
  _Checker(this.c);
  @override
  void paint(Canvas canvas, Size size) {
    const s = 8.0;
    final p = Paint()..color = c;
    for (var y = 0.0; y < size.height; y += s) {
      for (var x = 0.0; x < size.width; x += s) {
        if (((x / s).floor() + (y / s).floor()).isEven) {
          canvas.drawRect(Rect.fromLTWH(x, y, s, s), p);
        }
      }
    }
  }

  @override
  bool shouldRepaint(_Checker old) => old.c != c;
}
