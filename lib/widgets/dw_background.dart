import 'dart:ui';
import 'package:flutter/material.dart';
import '../core/theme/app_colors.dart';

class DwBackground extends StatelessWidget {
  const DwBackground({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        const DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Color(0xFFFFF1DD),
                Color(0xFFFFFBF5),
                Color(0xFFF7F1FA),
              ],
            ),
          ),
        ),
        Positioned(
          top: -90,
          left: -70,
          child: _BlurOrb(size: 270, color: AppColors.yellow.withValues(alpha: .23)),
        ),
        Positioned(
          bottom: -110,
          right: -70,
          child: _BlurOrb(size: 300, color: const Color(0xFFCDB5EF).withValues(alpha: .22)),
        ),
        child,
      ],
    );
  }
}

class _BlurOrb extends StatelessWidget {
  const _BlurOrb({required this.size, required this.color});
  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return ImageFiltered(
      imageFilter: ImageFilter.blur(sigmaX: 45, sigmaY: 45),
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(shape: BoxShape.circle, color: color),
      ),
    );
  }
}
