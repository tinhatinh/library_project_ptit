from django.contrib import admin
from .models import Category, Book

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')
    # Tự động gen slug từ name khi Admin gõ chữ
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'sell_price', 'sell_stock', 'borrow_stock')
    search_fields = ('title', 'author')
    list_filter = ('category',)
    list_editable = ('sell_stock', 'borrow_stock') # Cho phép thủ thư điền chỉnh số lượng nhanh ngay ngoài bảng
