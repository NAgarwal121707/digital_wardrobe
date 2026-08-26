import 'package:flutter/material.dart';
import '../core/theme/app_colors.dart';

class DwCard extends StatelessWidget {
  const DwCard({super.key, required this.child, this.padding = const EdgeInsets.all(28)});
  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: .96),
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: Colors.white),
        boxShadow: [
          BoxShadow(
            color: AppColors.black.withValues(alpha: .09),
            blurRadius: 38,
            offset: const Offset(0, 18),
          ),
        ],
      ),
      child: child,
    );
  }
}
