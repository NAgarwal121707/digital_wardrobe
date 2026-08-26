import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../models/dashboard_data.dart';
import '../../services/api_service.dart';
import '../../services/auth_service.dart';
import '../../widgets/dw_background.dart';
import '../auth/login_screen.dart';
import '../wardrobe/wardrobe_screen.dart';
import '../wishlist/wishlist_screen.dart';
import '../ai/ai_stylist_screen.dart';
import '../ai/ai_add_screen.dart';
import '../profile/profile_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final ApiService _api = ApiService();
  late Future<DashboardData> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _future = _api.dashboard();
  }

  Future<void> _refresh() async {
    setState(_reload);
    await _future;
  }

  Future<void> _logout() async {
    await AuthService().logout();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (_) => false,
    );
  }

  void _closet([String? category]) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => WardrobeScreen(initialCategory: category),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: DwBackground(
        child: SafeArea(
          child: FutureBuilder<DashboardData>(
            future: _future,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }

              if (snapshot.hasError) {
                return Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '${snapshot.error}',
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 12),
                        FilledButton(
                          onPressed: () => setState(_reload),
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                );
              }

              final data = snapshot.data!;

              return RefreshIndicator(
                onRefresh: _refresh,
                child: ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.fromLTRB(20, 18, 20, 110),
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 46,
                          height: 46,
                          decoration: BoxDecoration(
                            color: AppColors.black,
                            borderRadius: BorderRadius.circular(15),
                          ),
                          alignment: Alignment.center,
                          child: const Text(
                            'DW',
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Your wardrobe',
                                style: TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                              Text(
                                'Live from your saved closet',
                                style: TextStyle(color: AppColors.muted),
                              ),
                            ],
                          ),
                        ),
                        IconButton(
                          onPressed: _logout,
                          icon: const Icon(Icons.logout_rounded),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    Row(
                      children: [
                        Expanded(
                          child: _Stat(
                            value: data.totalItems,
                            label: 'Items',
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: _Stat(
                            value: data.totalCategories,
                            label: 'Categories',
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: _Stat(
                            value: data.wishlistCount,
                            label: 'Wishlist',
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    _Hero(onTap: _closet),
                    const SizedBox(height: 14),
                    Row(children:[Expanded(child:FilledButton.icon(onPressed:() async {final r=await Navigator.push(context,MaterialPageRoute(builder:(_)=>const AiAddScreen()));if(r==true)setState(_reload);},icon:const Icon(Icons.camera_alt_outlined),label:const Text('AI Add'))),const SizedBox(width:10),Expanded(child:OutlinedButton.icon(onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const WishlistScreen())),icon:const Icon(Icons.favorite_border),label:const Text('Wishlist')))]),
                    const SizedBox(height: 24),
                    _Title(
                      text: 'Categories',
                      action: 'View closet',
                      onTap: _closet,
                    ),
                    const SizedBox(height: 12),
                    if (data.categories.isEmpty)
                      const Text(
                        'Your categories will appear after you add clothes.',
                        style: TextStyle(color: AppColors.muted),
                      )
                    else
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: data.categories
                            .map(
                              (category) => ActionChip(
                                label: Text(
                                  '${category.name}  ${category.count}',
                                ),
                                onPressed: () => _closet(category.name),
                              ),
                            )
                            .toList(),
                      ),
                    const SizedBox(height: 24),
                    const _Title(text: 'Recently added'),
                    const SizedBox(height: 12),
                    if (data.recentItems.isEmpty)
                      const Text(
                        'No saved clothes yet.',
                        style: TextStyle(color: AppColors.muted),
                      )
                    else
                      SizedBox(
                        height: 210,
                        child: ListView.separated(
                          scrollDirection: Axis.horizontal,
                          itemCount: data.recentItems.length,
                          separatorBuilder: (_, __) =>
                              const SizedBox(width: 12),
                          itemBuilder: (_, index) {
                            final item = data.recentItems[index];
                            final hasImage = item.imageUrl != null &&
                                item.imageUrl!.isNotEmpty;

                            return GestureDetector(
                              onTap: () => _closet(item.category),
                              child: Container(
                                width: 145,
                                decoration: BoxDecoration(
                                  color: Colors.white,
                                  borderRadius: BorderRadius.circular(20),
                                  border: Border.all(color: AppColors.border),
                                ),
                                clipBehavior: Clip.antiAlias,
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Expanded(
                                      child: hasImage
                                          ? Image.network(
                                              item.imageUrl!,
                                              width: 145,
                                              fit: BoxFit.cover,
                                              errorBuilder: (_, __, ___) =>
                                                  const Center(
                                                child: Icon(
                                                  Icons.checkroom_rounded,
                                                ),
                                              ),
                                            )
                                          : const Center(
                                              child: Icon(
                                                Icons.checkroom_rounded,
                                              ),
                                            ),
                                    ),
                                    Padding(
                                      padding: const EdgeInsets.all(10),
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            item.name,
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                            style: const TextStyle(
                                              fontWeight: FontWeight.w500,
                                            ),
                                          ),
                                          Text(
                                            item.category,
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                            style: const TextStyle(
                                              color: AppColors.muted,
                                              fontSize: 12,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                      ),
                  ],
                ),
              );
            },
          ),
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: 0,
        onDestinationSelected: (index) {
          if (index == 1) _closet();
          if (index == 2) Navigator.push(context, MaterialPageRoute(builder: (_) => const AiStylistScreen()));
          if (index == 3) Navigator.push(context, MaterialPageRoute(builder: (_) => const ProfileScreen()));
        },
        indicatorColor: AppColors.yellowSoft,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home_rounded),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.checkroom_outlined),
            label: 'Closet',
          ),
          NavigationDestination(
            icon: Icon(Icons.auto_awesome_outlined),
            label: 'AI',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline_rounded),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({required this.value, required this.label});

  final int value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          Text(
            '$value',
            style: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w500,
            ),
          ),
          Text(
            label,
            style: const TextStyle(
              fontSize: 11,
              color: AppColors.muted,
            ),
          ),
        ],
      ),
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(28),
      child: Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: AppColors.black,
          borderRadius: BorderRadius.circular(28),
        ),
        child: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              Icons.checkroom_rounded,
              color: AppColors.yellow,
              size: 30,
            ),
            SizedBox(height: 16),
            Text(
              'Open my wardrobe',
              style: TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.w500,
              ),
            ),
            SizedBox(height: 7),
            Text(
              'Your real saved clothes, categories and images are now connected to Django.',
              style: TextStyle(
                color: Color(0xFFD6D6D6),
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Title extends StatelessWidget {
  const _Title({required this.text, this.action, this.onTap});

  final String text;
  final String? action;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            text,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
        if (action != null)
          TextButton(
            onPressed: onTap,
            child: Text(action!),
          ),
      ],
    );
  }
}
