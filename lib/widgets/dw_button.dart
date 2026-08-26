import 'package:flutter/material.dart';
import '../core/theme/app_colors.dart';

class DwButton extends StatelessWidget {
  const DwButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.loading = false,
    this.dark = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool loading;
  final bool dark;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 56,
      width: double.infinity,
      child: FilledButton(
        onPressed: loading ? null : onPressed,
        style: FilledButton.styleFrom(
          backgroundColor: dark ? AppColors.black : AppColors.yellow,
          foregroundColor: dark ? Colors.white : AppColors.black,
          disabledBackgroundColor: dark ? AppColors.black.withValues(alpha: .55) : AppColors.yellow.withValues(alpha: .55),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
        ),
        child: loading
            ? SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  strokeWidth: 2.2,
                  color: dark ? Colors.white : AppColors.black,
                ),
              )
            : Text(label),
      ),
    );
  }
}
