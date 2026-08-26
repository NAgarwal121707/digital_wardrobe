import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import '../core/config/api_config.dart';
import '../models/clothing_item.dart';
import '../models/dashboard_data.dart';
import '../models/wishlist_item.dart';
import 'auth_service.dart';

class ApiException implements Exception { const ApiException(this.message); final String message; @override String toString()=>message; }
class ApiService {
  ApiService({http.Client? client}):_client=client??http.Client(); final http.Client _client; final AuthService _auth=AuthService();
  Future<Map<String,String>> _headers({bool json=false}) async { final t=await _auth.accessToken; if(t==null||t.isEmpty) throw const ApiException('Your session has expired. Please login again.'); return {'Accept':'application/json','Authorization':'Bearer $t',if(json)'Content-Type':'application/json'}; }
  dynamic _decode(http.Response r){ if(r.body.trim().isEmpty)return <String,dynamic>{}; try{return jsonDecode(r.body);}catch(_){return {'detail':r.body};}}
  String _error(dynamic d,int code){if(d is Map){for(final k in ['detail','error','message','name','title']){final v=d[k];if(v is List&&v.isNotEmpty)return '${v.first}';if(v is String&&v.isNotEmpty)return v;}}return 'Server request failed (HTTP $code).';}
  Future<dynamic> _get(String path) async { try { final r=await _client.get(ApiConfig.uri(path),headers:await _headers()).timeout(const Duration(seconds:35)); final d=_decode(r); if(r.statusCode<200||r.statusCode>=300)throw ApiException(_error(d,r.statusCode)); return d;}on ApiException{rethrow;}catch(_){throw const ApiException('Could not load data from the server.');}}
  Future<dynamic> _json(String method,String path,Map<String,dynamic> body) async {final h=await _headers(json:true); late http.Response r; final u=ApiConfig.uri(path); if(method=='POST')r=await _client.post(u,headers:h,body:jsonEncode(body));else if(method=='PATCH')r=await _client.patch(u,headers:h,body:jsonEncode(body));else r=await _client.delete(u,headers:h); final d=_decode(r);if(r.statusCode<200||r.statusCode>=300)throw ApiException(_error(d,r.statusCode));return d;}
  Future<dynamic> _multipart(String method,String path,Map<String,String> fields,{XFile? image}) async {final req=http.MultipartRequest(method,ApiConfig.uri(path));req.headers.addAll(await _headers());req.fields.addAll(fields);if(image!=null){final bytes=await image.readAsBytes();req.files.add(http.MultipartFile.fromBytes('image',bytes,filename:image.name));}final streamed=await req.send();final r=await http.Response.fromStream(streamed);final d=_decode(r);if(r.statusCode<200||r.statusCode>=300)throw ApiException(_error(d,r.statusCode));return d;}
  Future<DashboardData> dashboard() async=>DashboardData.fromJson(Map<String,dynamic>.from(await _get('/api/dashboard/')));
  Future<List<ClothingItem>> wardrobe({String? category}) async {final q=(category==null||category.isEmpty)?'':'?category=${Uri.encodeQueryComponent(category)}';final d=Map<String,dynamic>.from(await _get('/api/wardrobe/$q'));return ((d['items'] as List?)??[]).map((e)=>ClothingItem.fromJson(Map<String,dynamic>.from(e))).toList();}
  Future<ClothingItem> clothing(int id) async=>ClothingItem.fromJson(Map<String,dynamic>.from(await _get('/api/wardrobe/$id/')));
  Future<ClothingItem> saveClothing(Map<String,String> fields,{int? id,XFile? image}) async=>ClothingItem.fromJson(Map<String,dynamic>.from(await _multipart(id==null?'POST':'PATCH',id==null?'/api/wardrobe/':'/api/wardrobe/$id/',fields,image:image)));
  Future<void> deleteClothing(int id) async=>_json('DELETE','/api/wardrobe/$id/',{});
  Future<List<WishlistItem>> wishlist() async {final d=Map<String,dynamic>.from(await _get('/api/wishlist/'));return ((d['items'] as List?)??[]).map((e)=>WishlistItem.fromJson(Map<String,dynamic>.from(e))).toList();}
  Future<void> addWishlist(Map<String,dynamic> body) async=>_json('POST','/api/wishlist/',body);
  Future<void> toggleWishlist(WishlistItem x) async=>_json('PATCH','/api/wishlist/${x.id}/',{'is_purchased':!x.isPurchased});
  Future<void> deleteWishlist(int id) async=>_json('DELETE','/api/wishlist/$id/',{});
  Future<Map<String,dynamic>> analyze(XFile image) async=>Map<String,dynamic>.from(await _multipart('POST','/api/ai/analyze/',{},image:image));
  Future<Map<String,dynamic>> stylist(String question) async=>Map<String,dynamic>.from(await _json('POST','/api/ai/stylist/',{'question':question}));
}
