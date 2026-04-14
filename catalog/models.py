from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=255, verbose_name="Tên Thể Loại")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="Đường dẫn tĩnh (Slug)")

    class Meta:
        verbose_name = "Danh mục"
        verbose_name_plural = "1. Nhóm thẻ loại"

    def __str__(self):
        return self.name

class Book(models.Model):
    class Meta:
        verbose_name = "Đầu sách"
        verbose_name_plural = "2. Kho Đầu sách"

    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='books', verbose_name="Thuộc danh mục")
    title = models.CharField(max_length=255, verbose_name="Tựa sách")
    author = models.CharField(max_length=255, verbose_name="Tác giả")
    description = models.TextField(blank=True, null=True, verbose_name="Giới thiệu nội dung")
    cover_image = models.ImageField(upload_to='book_covers/', blank=True, null=True, verbose_name="Upload Ảnh bìa")
    sell_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Giá niêm yết (VNĐ)")
    sell_stock = models.PositiveIntegerField(default=0, help_text="Số lượng tồn kho để bán", verbose_name="Kho Bán")
    borrow_stock = models.PositiveIntegerField(default=0, help_text="Số lượng tồn kho để cho mượn", verbose_name="Kho Mượn")

    def __str__(self):
        return f"{self.title} - {self.author} (Bán: {self.sell_stock} | Mượn: {self.borrow_stock})"
