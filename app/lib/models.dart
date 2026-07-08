/// API・カタログJSONのモデル。app/lib 内で自己完結(共有パッケージは作らない)。
library;

class Category {
  final String slug;
  final String name;
  Category(this.slug, this.name);
  factory Category.fromJson(Map<String, dynamic> j) =>
      Category(j['slug'], j['name']);
}

class Product {
  final String code;
  final String name;
  final String categorySlug;
  final String? summary;
  final String? description;
  final Map<String, dynamic> specs;
  final String? priceNote;
  final List<String> photos;
  Product.fromJson(Map<String, dynamic> j)
      : code = j['code'],
        name = j['name'],
        categorySlug = j['category_slug'],
        summary = j['summary'],
        description = j['description'],
        specs = Map<String, dynamic>.from(j['specs'] ?? {}),
        priceNote = j['price_note'],
        photos = List<String>.from(j['photos'] ?? []);
}

class Catalog {
  final List<Category> categories;
  final List<Product> products;
  Catalog.fromJson(Map<String, dynamic> j)
      : categories = [for (final c in j['categories']) Category.fromJson(c)],
        products = [for (final p in j['products']) Product.fromJson(p)];

  Product? byCode(String code) {
    for (final p in products) {
      if (p.code == code) return p;
    }
    return null;
  }
}

class CartItem {
  final String code;
  final String name;
  final int quantity;
  final String? specNote;
  final String? priceNote;
  CartItem.fromJson(Map<String, dynamic> j)
      : code = j['code'],
        name = j['name'],
        quantity = j['quantity'],
        specNote = j['spec_note'],
        priceNote = j['price_note'];
}

class QuoteListItem {
  final String id;
  final String quoteNo;
  final String status;
  final String createdAt;
  final String? lastMessage;
  QuoteListItem.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        quoteNo = j['quote_no'],
        status = j['status'],
        createdAt = j['created_at'],
        lastMessage = j['last_message'];
}

class QuoteItem {
  final String code;
  final String name;
  final int quantity;
  final String? specNote;
  QuoteItem.fromJson(Map<String, dynamic> j)
      : code = j['code'],
        name = j['name'],
        quantity = j['quantity'],
        specNote = j['spec_note'];
}

class QuoteDetail {
  final String id;
  final String quoteNo;
  final String status;
  final String? note;
  final String createdAt;
  final List<QuoteItem> items;
  QuoteDetail.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        quoteNo = j['quote_no'],
        status = j['status'],
        note = j['note'],
        createdAt = j['created_at'],
        items = [for (final i in j['items']) QuoteItem.fromJson(i)];
}

class Message {
  final String id;
  final String body;
  final bool hasFile;
  final String sentAt;
  final bool isMine;
  Message.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        body = j['body'],
        hasFile = j['has_file'],
        sentAt = j['sent_at'],
        isMine = j['is_mine'];
}
