import 'dart:async';
import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../services/auth_service.dart';
import '../../widgets/dw_background.dart';
import '../auth/login_screen.dart';
import '../dashboard/dashboard_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});
  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _start();
  }

  Future<void> _start() async {
    await Future<void>.delayed(const Duration(milliseconds: 1000));
    final loggedIn = await AuthService().hasSession();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => loggedIn ? const DashboardScreen() : const LoginScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: DwBackground(
        child: Center(
          child: TweenAnimationBuilder<double>(
            tween: Tween(begin: .88, end: 1),
            duration: const Duration(milliseconds: 700),
            curve: Curves.easeOutBack,
            builder: (_, scale, child) => Transform.scale(scale: scale, child: child),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 88,
                  height: 88,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(color: AppColors.black, borderRadius: BorderRadius.circular(28)),
                  child: const Text('DW', style: TextStyle(color: Colors.white, fontSize: 27, fontWeight: FontWeight.w500)),
                ),
                const SizedBox(height: 20),
                const Text('Digital Wardrobe', style: TextStyle(fontSize: 26, color: AppColors.black, fontWeight: FontWeight.w500)),
                const SizedBox(height: 8),
                const Text('Your closet. Smarter.', style: TextStyle(color: AppColors.muted, fontWeight: FontWeight.w400)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
