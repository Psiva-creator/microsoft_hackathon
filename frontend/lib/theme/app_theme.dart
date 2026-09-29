import 'package:flutter/material.dart';

class AppTheme {
  // Brand & Background Colors
  static const Color background = Color(0xFF090D16);
  static const Color surface = Color(0xFF0F172A);
  static const Color surfaceLight = Color(0xFF1E293B);
  static const Color surfaceBorder = Color(0xFF334155);
  static const Color surfaceGlow = Color(0xFF1E293B);

  // Neon & Status Accent Colors
  static const Color cyan = Color(0xFF06B6D4);
  static const Color cyanGlow = Color(0x3306B6D4);
  static const Color emerald = Color(0xFF10B981);
  static const Color emeraldGlow = Color(0x3310B981);
  static const Color amber = Color(0xFFF59E0B);
  static const Color amberGlow = Color(0x33F59E0B);
  static const Color rose = Color(0xFFF43F5E);
  static const Color roseGlow = Color(0x33F43F5E);
  static const Color indigo = Color(0xFF6366F1);
  static const Color indigoGlow = Color(0x336366F1);
  static const Color purple = Color(0xFFA855F7);

  // Text Colors
  static const Color textPrimary = Color(0xFFF8FAFC);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF64748B);

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: background,
      primaryColor: cyan,
      colorScheme: const ColorScheme.dark(
        primary: cyan,
        secondary: indigo,
        surface: surface,
        error: rose,
        onPrimary: Colors.black,
        onSurface: textPrimary,
      ),
      fontFamily: 'Inter',
      cardTheme: CardTheme(
        color: surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: surfaceBorder, width: 1),
        ),
      ),
      dividerTheme: const DividerThemeData(
        color: surfaceBorder,
        thickness: 1,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: surface,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 18,
          fontWeight: FontWeight.bold,
          letterSpacing: -0.5,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFF06090F),
        hintStyle: const TextStyle(color: textMuted, fontSize: 13),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: surfaceBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: surfaceBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: cyan, width: 1.5),
        ),
      ),
    );
  }

  // Box Decorations
  static BoxDecoration glassCard({
    Color? borderColor,
    Color? glowColor,
    double radius = 16,
  }) {
    return BoxDecoration(
      color: surface.withOpacity(0.85),
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(
        color: borderColor ?? surfaceBorder.withOpacity(0.8),
        width: 1,
      ),
      boxShadow: [
        BoxShadow(
          color: glowColor ?? Colors.black.withOpacity(0.3),
          blurRadius: 16,
          spreadRadius: 0,
          offset: const Offset(0, 4),
        ),
      ],
    );
  }

  static BoxDecoration glowBorder({
    required Color color,
    double radius = 12,
  }) {
    return BoxDecoration(
      color: color.withOpacity(0.12),
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(color: color.withOpacity(0.4), width: 1),
    );
  }
}
