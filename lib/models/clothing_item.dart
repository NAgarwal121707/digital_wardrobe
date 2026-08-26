class ClothingItem {
  const ClothingItem({required this.id, required this.name, required this.category, required this.color, this.imageUrl, this.garmentType = '', this.occasion = '', this.season = '', this.stylingNotes = '', this.isCompleteOutfit = false});
  final int id;
  final String name;
  final String category;
  final String color;
  final String? imageUrl;
  final String garmentType;
  final String occasion;
  final String season;
  final String stylingNotes;
  final bool isCompleteOutfit;

  factory ClothingItem.fromJson(Map<String, dynamic> j) => ClothingItem(
    id: (j['id'] as num).toInt(), name: '${j['name'] ?? ''}', category: '${j['category'] ?? ''}', color: '${j['color'] ?? ''}',
    imageUrl: j['image_url']?.toString(), garmentType: '${j['garment_type'] ?? ''}', occasion: '${j['occasion'] ?? ''}', season: '${j['season'] ?? ''}',
    stylingNotes: '${j['styling_notes'] ?? ''}', isCompleteOutfit: j['is_complete_outfit'] == true,
  );
}
