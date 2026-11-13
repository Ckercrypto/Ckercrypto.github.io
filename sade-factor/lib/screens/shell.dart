import 'package:flutter/material.dart';

import '../store.dart';
import 'customers.dart';
import 'dashboard.dart';
import 'invoice_editor.dart';
import 'invoices.dart';
import 'items.dart';
import 'onboarding.dart';
import 'settings.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _index = 0;

  static const _dest = [
    (Icons.space_dashboard_outlined, Icons.space_dashboard_rounded, 'خانه'),
    (Icons.receipt_long_outlined, Icons.receipt_long_rounded, 'فاکتورها'),
    (Icons.people_alt_outlined, Icons.people_alt_rounded, 'مشتری‌ها'),
    (Icons.inventory_2_outlined, Icons.inventory_2_rounded, 'کالاها'),
    (Icons.tune_outlined, Icons.tune_rounded, 'تنظیمات'),
  ];

  void go(int i) => setState(() => _index = i);

  Future<void> newInvoice() async {
    await Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => const InvoiceEditor(),
      fullscreenDialog: true,
    ));
  }

  @override
  Widget build(BuildContext context) {
    final store = StoreScope.of(context);
    if (!store.business.isSetUp) return const OnboardingScreen();

    final pages = [
      DashboardScreen(onNewInvoice: newInvoice, onSeeAll: () => go(1)),
      InvoicesScreen(onNewInvoice: newInvoice),
      const CustomersScreen(),
      const ItemsScreen(),
      const SettingsScreen(),
    ];

    final wide = MediaQuery.sizeOf(context).width >= 840;
    final body = AnimatedSwitcher(
      duration: const Duration(milliseconds: 220),
      child: KeyedSubtree(key: ValueKey(_index), child: pages[_index]),
    );

    final fab = _index <= 1
        ? FloatingActionButton.extended(
            onPressed: newInvoice,
            icon: const Icon(Icons.add_rounded),
            label: const Text('فاکتور جدید',
                style: TextStyle(fontWeight: FontWeight.w700)),
          )
        : null;

    if (wide) {
      final cs = Theme.of(context).colorScheme;
      return Scaffold(
        floatingActionButton: fab,
        body: Row(children: [
          NavigationRail(
            selectedIndex: _index,
            onDestinationSelected: go,
            extended: MediaQuery.sizeOf(context).width >= 1100,
            minExtendedWidth: 200,
            labelType: MediaQuery.sizeOf(context).width >= 1100
                ? NavigationRailLabelType.none
                : NavigationRailLabelType.all,
            leading: Padding(
              padding: const EdgeInsets.symmetric(vertical: 20),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: cs.primary,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(Icons.bolt_rounded, color: cs.onPrimary),
                ),
                if (MediaQuery.sizeOf(context).width >= 1100) ...[
                  const SizedBox(width: 10),
                  const Text('ساده‌فاکتور',
                      style:
                          TextStyle(fontWeight: FontWeight.w700, fontSize: 18)),
                ],
              ]),
            ),
            destinations: [
              for (final d in _dest)
                NavigationRailDestination(
                  icon: Icon(d.$1),
                  selectedIcon: Icon(d.$2),
                  label: Text(d.$3),
                ),
            ],
          ),
          const VerticalDivider(width: 1),
          Expanded(child: body),
        ]),
      );
    }

    return Scaffold(
      body: SafeArea(bottom: false, child: body),
      floatingActionButton: fab,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: go,
        destinations: [
          for (final d in _dest)
            NavigationDestination(
              icon: Icon(d.$1),
              selectedIcon: Icon(d.$2),
              label: d.$3,
            ),
        ],
      ),
    );
  }
}
