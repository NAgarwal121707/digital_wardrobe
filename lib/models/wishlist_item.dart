class WishlistItem {
  const WishlistItem({required this.id, required this.title, required this.category, required this.color, this.imageUrl, required this.reason, required this.priority, required this.isPurchased});
  final int id; final String title, category, color, reason, priority; final String? imageUrl; final bool isPurchased;
  factory WishlistItem.fromJson(Map<String,dynamic> j)=>WishlistItem(id:(j['id'] as num).toInt(),title:'${j['title']??''}',category:'${j['category']??''}',color:'${j['color']??''}',imageUrl:j['image_url']?.toString(),reason:'${j['reason']??''}',priority:'${j['priority']??'medium'}',isPurchased:j['is_purchased']==true);
}
