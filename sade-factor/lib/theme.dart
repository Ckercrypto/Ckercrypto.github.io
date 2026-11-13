import 'package:flutter/material.dart';

const brandSeed = Color(0xFF0FA3A3); // warm teal
const accentCoral = Color(0xFFFF8A5B);

ThemeData buildTheme(Brightness b) {
  final scheme = ColorScheme.fromSeed(
    seedColor: brandSeed,
    brightness: b,
    secondary: accentCoral,
  );
  final base = ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    fontFamily: 'Vazirmatn',
    brightness: b,
  );
  final radius = BorderRadius.circular(20);
  return base.copyWith(
    scaffoldBackgroundColor: b == Brightness.light
        ? const Color(0xFFF5F7F8)
        : scheme.surface,
    cardTheme: CardTheme(
      elevation: 0,
      color: b == Brightness.light ? Colors.white : scheme.surfaceContainerHigh,
      shape: RoundedRectangleBorder(borderRadius: radius),
      margin: EdgeInsets.zero,
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: Colors.transparent,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: base.textTheme.titleLarge?.copyWith(
          fontFamily: 'Vazirmatn',
          fontWeight: FontWeight.w700,
          color: scheme.onSurface),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: b == Brightness.light
          ? const Color(0xFFF0F3F4)
          : scheme.surfaceContainerHighest,
      border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(48, 52),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        textStyle: const TextStyle(
            fontFamily: 'Vazirmatn', fontWeight: FontWeight.w700, fontSize: 16),
      ),
    ),
    floatingActionButtonTheme: FloatingActionButtonThemeData(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    ),
    navigationBarTheme: NavigationBarThemeData(
      height: 68,
      labelTextStyle: WidgetStateProperty.all(
          const TextStyle(fontFamily: 'Vazirmatn', fontSize: 12)),
    ),
    chipTheme: base.chipTheme.copyWith(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    ),
  );
}
