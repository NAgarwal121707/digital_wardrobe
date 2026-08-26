import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../models/clothing_item.dart';
import '../../services/api_service.dart';
import '../../widgets/dw_background.dart';
import '../add_item/add_item_screen.dart';
import '../ai/ai_add_screen.dart';
import 'item_detail_screen.dart';

class WardrobeScreen extends StatefulWidget {
  const WardrobeScreen({super.key, this.initialCategory});

  final String? initialCategory;

  @override
  State<WardrobeScreen> createState() => _WardrobeScreenState();
}

class _WardrobeScreenState extends State<WardrobeScreen> {
  final ApiService _api = ApiService();
  late Future<List<ClothingItem>> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _future = _api.wardrobe(category: widget.initialCategory);
  }

  Future<void> _refresh() async {
    setState(_reload);
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton(onPressed: () async { final changed = await showModalBottomSheet<bool>(context: context, builder: (c) => SafeArea(child: Wrap(children: [ListTile(leading: const Icon(Icons.edit_outlined), title: const Text('Add manually'), onTap: () async { Navigator.pop(c); final r=await Navigator.push(context,MaterialPageRoute(builder:(_)=>const AddItemScreen())); if(r==true){setState(_reload);} }),ListTile(leading: const Icon(Icons.auto_awesome), title: const Text('AI camera / gallery'), onTap: () async { Navigator.pop(c); final r=await Navigator.push(context,MaterialPageRoute(builder:(_)=>const AiAddScreen())); if(r==true){setState(_reload);} })]))); if(changed==true)setState(_reload); }, child: const Icon(Icons.add)),
      appBar: AppBar(
        title: Text(widget.initialCategory ?? 'My Closet'),
      ),
      body: DwBackground(
        child: SafeArea(
          child: FutureBuilder<List<ClothingItem>>(
            future: _future,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }

              if (snapshot.hasError) {
                return _Error(
                  message: '${snapshot.error}',
                  retry: () => setState(_reload),
                );
              }

              final items = snapshot.data ?? [];

              if (items.isEmpty) {
                return RefreshIndicator(
                  onRefresh: _refresh,
                  child: ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    children: const [
                      SizedBox(height: 180),
                      Padding(
                        padding: EdgeInsets.all(24),
                        child: Text(
                          'No clothes here yet. Add items from your wardrobe builder.',
                          textAlign: TextAlign.center,
                        ),
                      ),
                    ],
                  ),
                );
              }

              return RefreshIndicator(
                onRefresh: _refresh,
                child: GridView.builder(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(18),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    crossAxisSpacing: 12,
                    mainAxisSpacing: 12,
                    childAspectRatio: .72,
                  ),
                  itemCount: items.length,
                  itemBuilder: (_, index) => _ItemCard(item: items[index], onTap: () async { final r=await Navigator.push(context,MaterialPageRoute(builder:(_)=>ItemDetailScreen(item:items[index]))); if(r==true)setState(_reload); }),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

class _ItemCard extends StatelessWidget {
  const _ItemCard({required this.item, required this.onTap});

  final ClothingItem item; final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final hasImage = item.imageUrl != null && item.imageUrl!.isNotEmpty;
    final subtitle = item.color.isEmpty
        ? item.category
        : '${item.category} • ${item.color}';

    return InkWell(onTap: onTap, borderRadius: BorderRadius.circular(20), child: Container(
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
                    width: double.infinity,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => const _Placeholder(),
                  )
                : const _Placeholder(),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontWeight: FontWeight.w500,
                    fontSize: 15,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
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
    ));
  }
}

class _Placeholder extends StatelessWidget {
  const _Placeholder();

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFFF2F2F2),
      alignment: Alignment.center,
      child: const Icon(
        Icons.checkroom_rounded,
        size: 42,
        color: AppColors.muted,
      ),
    );
  }
}

class _Error extends StatelessWidget {
  const _Error({required this.message, required this.retry});

  final String message;
  final VoidCallback retry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: retry,
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}
