from django.db import models
from django.contrib.auth import get_user_model
from catalog.models import Book

User = get_user_model()

class Order(models.Model):
    class Meta:
        verbose_name = "Hoá đơn xuất"
        verbose_name_plural = "1. Quản lý Hoá Đơn Bán"

    STATUS_CHOICES = (
        ('Pending', 'Chờ xử lý thanh toán'),
        ('Paid', 'Đã thanh toán (Thành công)'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name="Người mua")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Tổng hóa đơn")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', verbose_name="Thực trạng")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Giao dịch lúc")

    def __str__(self):
        return f"Order #{self.id} | {self.user.username} | {self.status}"

class OrderItem(models.Model):
    class Meta:
        verbose_name = "Chi tiết mục"
        verbose_name_plural = "Chi tiết mục"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="Mã Hóa Đơn")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='order_items', verbose_name="Cuốn sách")
    quantity = models.PositiveIntegerField(default=1, verbose_name="SL Mua")
    price_at_time_of_purchase = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Giá thu")

    def __str__(self):
        return f"{self.quantity} x {self.book.title} (Order #{self.order.id})"

class BorrowRecord(models.Model):
    class Meta:
        verbose_name = "Phiếu mượn"
        verbose_name_plural = "2. Xét duyệt Phiếu Mượn"

    STATUS_CHOICES = (
        ('Pending', 'Đang đợi Phê Duyệt'),
        ('Approved', 'Đang mượn (Thủ thư đã duyệt)'),
        ('Returned', 'Khách đã trả (Hoàn tất)'),
        ('Overdue', 'Quá hạn'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrow_records', verbose_name="Sinh viên/Giáo viên")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrow_records', verbose_name="Sách mượn")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', verbose_name="Trạng thái hệ thống")
    borrow_date = models.DateTimeField(auto_now_add=True, verbose_name="Ngày làm đơn")
    due_date = models.DateField(verbose_name="Hẹn ngày trả")

    def __str__(self):
        return f"Borrow #{self.id} | {self.book.title} | {self.user.username} - {self.status}"
