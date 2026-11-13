import 'package:flutter/material.dart';

import '../models.dart';
import '../store.dart';

/// First-run: three friendly steps, only the shop name is required.
class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _page = PageController();
  int _step = 0;
  final _name = TextEditingController();
  final _owner = TextEditingController();
  final _phone = TextEditingController();
  final _eco = TextEditingController();
  final _nid = TextEditingController();

  void _next() {
    if (_step == 1 && _name.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('اسم کسب‌وکارت رو بنویس')));
      return;
    }
    if (_step < 2) {
      _page.nextPage(
          duration: const Duration(milliseconds: 350), curve: Curves.easeOutCubic);
    } else {
      final store = StoreScope.of(context);
      store.business = Business(
        name: _name.text.trim(),
        ownerName: _owner.text.trim(),
        phone: _phone.text.trim(),
        economicCode: _eco.text.trim(),
        nationalId: _nid.text.trim(),
      );
      store.save();
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(children: [
                Row(children: [
                  for (var i = 0; i < 3; i++)
                    Expanded(
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 300),
                        margin: const EdgeInsets.symmetric(horizontal: 3),
                        height: 6,
                        decoration: BoxDecoration(
                          color: i <= _step
                              ? cs.primary
                              : cs.surfaceContainerHighest,
                          borderRadius: BorderRadius.circular(3),
                        ),
                      ),
                    ),
                ]),
                Expanded(
                  child: PageView(
                    controller: _page,
                    physics: const NeverScrollableScrollPhysics(),
                    onPageChanged: (i) => setState(() => _step = i),
                    children: [
                      _welcome(cs),
                      _form('کسب‌وکارت چیه؟', 'فقط اسم لازمه، بقیه رو بعداً هم می‌تونی کامل کنی.', [
                        TextField(
                            controller: _name,
                            autofocus: true,
                            decoration: const InputDecoration(
                                labelText: 'اسم فروشگاه یا شرکت *',
                                prefixIcon: Icon(Icons.storefront_rounded))),
                        const SizedBox(height: 12),
                        TextField(
                            controller: _owner,
                            decoration: const InputDecoration(
                                labelText: 'اسم خودت',
                                prefixIcon: Icon(Icons.person_rounded))),
                        const SizedBox(height: 12),
                        TextField(
                            controller: _phone,
                            keyboardType: TextInputType.phone,
                            decoration: const InputDecoration(
                                labelText: 'تلفن',
                                prefixIcon: Icon(Icons.call_rounded))),
                      ]),
                      _form('اطلاعات مالیاتی', 'برای فاکتور رسمی لازمه. اگه الان دم دستت نیست، رد شو.', [
                        TextField(
                            controller: _nid,
                            keyboardType: TextInputType.number,
                            decoration: const InputDecoration(
                                labelText: 'کد ملی یا شناسه ملی',
                                prefixIcon: Icon(Icons.badge_rounded))),
                        const SizedBox(height: 12),
                        TextField(
                            controller: _eco,
                            keyboardType: TextInputType.number,
                            decoration: const InputDecoration(
                                labelText: 'کد اقتصادی',
                                prefixIcon: Icon(Icons.numbers_rounded))),
                      ]),
                    ],
                  ),
                ),
                Row(children: [
                  if (_step > 0)
                    TextButton(
                      onPressed: () => _page.previousPage(
                          duration: const Duration(milliseconds: 300),
                          curve: Curves.easeOut),
                      child: const Text('قبلی'),
                    ),
                  const Spacer(),
                  FilledButton(
                    onPressed: _next,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 18),
                      child: Text(_step == 0
                          ? 'شروع کنیم'
                          : _step == 1
                              ? 'بعدی'
                              : 'تمام'),
                    ),
                  ),
                ]),
              ]),
            ),
          ),
        ),
      ),
    );
  }

  Widget _welcome(ColorScheme cs) => Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 140,
            height: 140,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(40),
              gradient: LinearGradient(
                colors: [cs.primary, cs.secondary],
                begin: Alignment.topRight,
                end: Alignment.bottomLeft,
              ),
            ),
            child: const Icon(Icons.receipt_long_rounded,
                size: 72, color: Colors.white),
          ),
          const SizedBox(height: 28),
          const Text('سلام! به ساده‌فاکتور خوش اومدی',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
          const SizedBox(height: 12),
          Text(
            'فاکتور بزن، طلب‌هات رو ببین و مالیاتت رو بدون دردسر حساب کن.\nزیر یک دقیقه.',
            textAlign: TextAlign.center,
            style: TextStyle(color: cs.onSurfaceVariant, height: 1.8),
          ),
        ],
      );

  Widget _form(String title, String sub, List<Widget> fields) => ListView(
        padding: const EdgeInsets.only(top: 40),
        children: [
          Text(title,
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Text(sub,
              style: TextStyle(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                  height: 1.7)),
          const SizedBox(height: 24),
          ...fields,
        ],
      );
}
