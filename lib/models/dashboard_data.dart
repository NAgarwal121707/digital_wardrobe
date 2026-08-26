import 'clothing_item.dart';
class CategoryCount { const CategoryCount(this.name, this.count); final String name; final int count; factory CategoryCount.fromJson(Map<String,dynamic> j)=>CategoryCount('${j['category']??''}', (j['item_count'] as num?)?.toInt()??0); }
class DashboardData {
  const DashboardData({required this.totalItems,required this.totalCategories,required this.wishlistCount,required this.totalOutfits,required this.categories,required this.recentItems});
  final int totalItems,totalCategories,wishlistCount,totalOutfits; final List<CategoryCount> categories; final List<ClothingItem> recentItems;
  factory DashboardData.fromJson(Map<String,dynamic> j){ final s=(j['stats'] as Map?)?.cast<String,dynamic>()??{}; return DashboardData(totalItems:(s['total_items'] as num?)?.toInt()??0,totalCategories:(s['total_categories'] as num?)?.toInt()??0,wishlistCount:(s['wishlist_count'] as num?)?.toInt()??0,totalOutfits:(s['total_outfits'] as num?)?.toInt()??0,categories:((j['categories'] as List?)??[]).map((e)=>CategoryCount.fromJson(Map<String,dynamic>.from(e))).toList(),recentItems:((j['recent_items'] as List?)??[]).map((e)=>ClothingItem.fromJson(Map<String,dynamic>.from(e))).toList()); }
}
