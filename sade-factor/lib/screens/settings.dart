import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../format.dart';
import '../store.dart';
import '../widgets/common.dart';
import '../widgets/image_slot.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final AppStore store = StoreScope.of(context);
  late final b = store.business;
  late final _name = TextEditingController(text: b.name);
  late final _owner = TextEditingController(text: b.ownerName);
  late final _nid = TextEditingController(text: b.nationalId);
  late final _eco = TextEditingController(text: b.economicCode);
  late final _mem = TextEditingController(text: b.memoryId);
  late final _phone = TextEditingController(text: b.phone);
  late final _addr = TextEditingController(text: b.address);
  late final _postal = TextEditingController(text: b.postalCode);
  late final _vat = TextEditingController(text: num0(b.defaultVatRate));

  void _save() {
    if (_name.text.trim().isEmpty) {
      toast(context, 'اسم کسب‌وکار خالی نمی‌تونه باشه');
      return;
    }
    b
      ..name = _name.text.trim()
      ..ownerName = _owner.text.trim()
      ..nationalId = toLatinDigits(_nid.text.trim())
      ..economicCode = toLatinDigits(_eco.text.trim())
      ..memoryId = _mem.text.trim()
      ..phone = toLatinDigits(_phone.text.trim())
      ..address = _addr.text.trim()
      ..postalCode = toLatinDigits(_postal.text.trim())
      ..defaultVatRate = double.tryParse(toLatinDigits(_vat.text.trim())) ?? 10;
    if (b.defaultVatRate == 0) b.defaultVatRate = 10;
    store.save();
    toast(context, 'ذخیره شد');
  }

  Widget _f(TextEditingController c, String label,
          {TextInputType? kb, int lines = 1, String? helper, String? suffix}) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: TextField(
          controller: c,
          keyboardType: kb,
          maxLines: lines,
          decoration: InputDecoration(
              labelText: label, helperText: helper, suffixText: suffix),
        ),
      );

  @override
  Widget build(BuildContext context) {
    return Constrained(
      maxWidth: 720,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 40),
        children: [
          const Text('تنظیمات',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
          const SectionTitle('ظاهر'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: SegmentedButton<ThemeMode>(
                segments: const [
                  ButtonSegment(
                      value: ThemeMode.light,
                      label: Text('روشن'),
                      icon: Icon(Icons.light_mode_rounded)),
                  ButtonSegment(
                      value: ThemeMode.system,
                      label: Text('خودکار'),
                      icon: Icon(Icons.brightness_auto_rounded)),
                  ButtonSegment(
                      value: ThemeMode.dark,
                      label: Text('تیره'),
                      icon: Icon(Icons.dark_mode_rounded)),
                ],
                selected: {store.themeMode},
                onSelectionChanged: (s) {
                  store.themeMode = s.first;
                  store.save();
                },
              ),
            ),
          ),
          const SectionTitle('کسب‌وکار'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(children: [
                _f(_name, 'اسم کسب‌وکار'),
                _f(_owner, 'اسم صاحب کسب‌وکار'),
                _f(_phone, 'تلفن', kb: TextInputType.phone),
                _f(_addr, 'آدرس', lines: 2),
                _f(_postal, 'کد پستی', kb: TextInputType.number),
              ]),
            ),
          ),
          const SectionTitle('مالیات'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(children: [
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  value: b.vatRegistered,
                  onChanged: (v) => setState(() => store.setVatRegistered(v)),
                  title: const Text('ثبت‌نام ارزش افزوده دارم',
                      style: TextStyle(fontWeight: FontWeight.w700)),
                  subtitle: Text(b.vatRegistered
                      ? 'مالیات ارزش افزوده روی فاکتورها حساب می‌شه'
                      : 'فاکتورها بدون مالیات ارزش افزوده صادر می‌شن'),
                ),
                const SizedBox(height: 8),
                _f(_nid, 'کد ملی یا شناسه ملی', kb: TextInputType.number),
                _f(_eco, 'کد اقتصادی', kb: TextInputType.number),
                _f(_mem, 'شناسه یکتای حافظه مالیاتی',
                    helper: 'از کارپوشه‌ی my.tax.gov.ir. برای ارسال خودکار در نسخه‌ی بعد'),
                if (b.vatRegistered)
                  _f(_vat, 'نرخ پیش‌فرض ارزش افزوده',
                      kb: const TextInputType.numberWithOptions(decimal: true),
                      suffix: '٪',
                      helper: 'نرخ کالاهای جدید. نرخ هر کالا جدا قابل تغییره'),
              ]),
            ),
          ),
          const SectionTitle('لوگو، مهر و امضا'),
          Card(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Column(children: [
                ImageSlot(
                  title: 'لوگو',
                  hint: 'بالای فاکتور و پیش‌فاکتور چاپ می‌شه',
                  value: b.logo,
                  onChanged: (v) => setState(() {
                    b.logo = v;
                    store.save();
                  }),
                ),
                const Divider(),
                ImageSlot(
                  title: 'امضا',
                  hint: 'PNG با پس‌زمینه‌ی شفاف',
                  value: b.signature,
                  pngOnly: true,
                  onChanged: (v) => setState(() {
                    b.signature = v;
                    store.save();
                  }),
                ),
                const Divider(),
                ImageSlot(
                  title: 'مهر',
                  hint: 'PNG با پس‌زمینه‌ی شفاف',
                  value: b.stamp,
                  pngOnly: true,
                  onChanged: (v) => setState(() {
                    b.stamp = v;
                    store.save();
                  }),
                ),
              ]),
            ),
          ),
          const SizedBox(height: 16),
          FilledButton(onPressed: _save, child: const Text('ذخیره‌ی تغییرات')),
          const SectionTitle('پشتیبان'),
          Card(
            child: ListTile(
              leading: const Icon(Icons.copy_all_rounded),
              title: const Text('کپی پشتیبان (JSON)'),
              subtitle: const Text('همه‌ی داده‌ها رو در کلیپ‌بورد کپی می‌کنه'),
              onTap: () async {
                await Clipboard.setData(ClipboardData(text: store.exportJson()));
                if (context.mounted) toast(context, 'کپی شد');
              },
            ),
          ),
          const SizedBox(height: 24),
          Center(
            child: Text('ساده‌فاکتور  |  نسخه‌ی ۰.۲',
                style: TextStyle(
                    color: Theme.of(context).colorScheme.onSurfaceVariant)),
          ),
        ],
      ),
    );
  }
}
