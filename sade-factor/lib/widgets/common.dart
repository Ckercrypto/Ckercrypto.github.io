import 'package:flutter/material.dart';

import '../format.dart';
import '../models.dart';

class EmptyState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 112,
              height: 112,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  colors: [cs.primaryContainer, cs.secondaryContainer],
                  begin: Alignment.topRight,
                  end: Alignment.bottomLeft,
                ),
              ),
              child: Icon(icon, size: 52, color: cs.onPrimaryContainer),
            ),
            const SizedBox(height: 20),
            Text(title,
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Text(message,
                textAlign: TextAlign.center,
                style: TextStyle(color: cs.onSurfaceVariant, height: 1.7)),
            if (actionLabel != null) ...[
              const SizedBox(height: 20),
              FilledButton.icon(
                onPressed: onAction,
                icon: const Icon(Icons.add_rounded),
                label: Text(actionLabel!),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class StatCard extends StatelessWidget {
  final String label;
  final String value;
  final String? hint;
  final IconData icon;
  final List<Color> gradient;
  final Color foreground;

  const StatCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    required this.gradient,
    this.foreground = Colors.white,
    this.hint,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: LinearGradient(
          colors: gradient,
          begin: Alignment.topRight,
          end: Alignment.bottomLeft,
        ),
        boxShadow: [
          BoxShadow(
            color: gradient.first.withValues(alpha: 0.25),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: foreground.withValues(alpha: 0.18),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: foreground, size: 20),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(label,
                  style: TextStyle(
                      color: foreground.withValues(alpha: 0.9), fontSize: 13)),
            ),
          ]),
          const SizedBox(height: 14),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: AlignmentDirectional.centerStart,
            child: Text(value,
                style: TextStyle(
                    color: foreground,
                    fontSize: 22,
                    fontWeight: FontWeight.w700)),
          ),
          if (hint != null) ...[
            const SizedBox(height: 4),
            Text(hint!,
                style: TextStyle(
                    color: foreground.withValues(alpha: 0.8), fontSize: 12)),
          ],
        ],
      ),
    );
  }
}

class StatusChip extends StatelessWidget {
  final Invoice invoice;
  const StatusChip({super.key, required this.invoice});

  @override
  Widget build(BuildContext context) {
    late Color c;
    late String t;
    late IconData i;
    switch (invoice.status) {
      case InvoiceStatus.draft:
        c = Colors.blueGrey;
        t = 'پیش‌نویس';
        i = Icons.edit_note_rounded;
      case InvoiceStatus.cancelled:
        c = Colors.red.shade400;
        t = 'ابطال‌شده';
        i = Icons.block_rounded;
      case InvoiceStatus.issued:
        if (invoice.paid) {
          c = Colors.green.shade600;
          t = 'پرداخت‌شده';
          i = Icons.check_circle_rounded;
        } else {
          c = Colors.orange.shade700;
          t = 'منتظر پرداخت';
          i = Icons.schedule_rounded;
        }
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(i, size: 14, color: c),
        const SizedBox(width: 4),
        Text(t,
            style: TextStyle(
                color: c, fontSize: 12, fontWeight: FontWeight.w700)),
      ]),
    );
  }
}

class InvoiceTile extends StatelessWidget {
  final Invoice invoice;
  final VoidCallback onTap;
  const InvoiceTile({super.key, required this.invoice, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final name =
        invoice.customerName.isEmpty ? 'مشتری عمومی' : invoice.customerName;
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(children: [
            CircleAvatar(
              radius: 22,
              backgroundColor: cs.primaryContainer,
              child: Text(
                name.characters.first,
                style: TextStyle(
                    color: cs.onPrimaryContainer, fontWeight: FontWeight.w700),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text(
                    'فاکتور ${faDigits(invoice.number)}  |  ${jDateLong(invoice.date)}',
                    style: TextStyle(color: cs.onSurfaceVariant, fontSize: 12),
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(toman(invoice.total),
                    style: const TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 6),
                StatusChip(invoice: invoice),
              ],
            ),
          ]),
        ),
      ),
    );
  }
}

class SectionTitle extends StatelessWidget {
  final String text;
  final Widget? trailing;
  const SectionTitle(this.text, {super.key, this.trailing});

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(4, 20, 4, 10),
        child: Row(children: [
          Expanded(
            child: Text(text,
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(fontWeight: FontWeight.w700)),
          ),
          if (trailing != null) trailing!,
        ]),
      );
}

void toast(BuildContext context, String msg) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(
      content: Text(msg, style: const TextStyle(fontFamily: 'Vazirmatn')),
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
    ));
}

Future<bool> confirm(BuildContext context, String title, String body,
    {String ok = 'بله', bool danger = false}) async {
  final r = await showDialog<bool>(
    context: context,
    builder: (c) => AlertDialog(
      title: Text(title),
      content: Text(body, style: const TextStyle(height: 1.7)),
      actions: [
        TextButton(
            onPressed: () => Navigator.pop(c, false), child: const Text('نه')),
        FilledButton(
          style: danger
              ? FilledButton.styleFrom(backgroundColor: Colors.red.shade400)
              : null,
          onPressed: () => Navigator.pop(c, true),
          child: Text(ok),
        ),
      ],
    ),
  );
  return r ?? false;
}

/// Max content width so wide Windows screens don't stretch everything.
class Constrained extends StatelessWidget {
  final Widget child;
  final double maxWidth;
  const Constrained({super.key, required this.child, this.maxWidth = 900});

  @override
  Widget build(BuildContext context) => Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: maxWidth),
          child: child,
        ),
      );
}
