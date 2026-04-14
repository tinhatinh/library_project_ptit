from django.contrib import admin
from django.db import transaction
from django.db.models import F
from django.contrib import messages
from django.http import HttpResponse
import csv
from .models import Order, OrderItem, BorrowRecord

class OrderItemInline(admin.TabularInline):
    """
    Sử dụng TabularInline để lồng giao diện các Sách trong hóa đơn vào bên trong View Của Order
    """
    model = OrderItem
    extra = 0
    # Thông thường giá mua sẽ không được edit lại để giữ nguyên lịch sử thanh toán
    readonly_fields = ('price_at_time_of_purchase',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'id')
    inlines = [OrderItemInline]
    actions = ['mark_as_paid', 'export_as_csv']

    @admin.action(description="Xác nhận: Đã thanh toán thành công (Paid)")
    def mark_as_paid(self, request, queryset):
        updated = queryset.filter(status='Pending').update(status='Paid')
        self.message_user(request, f"Đã bóc bill và xác nhận {updated} hóa đơn thanh toán thành công.", messages.SUCCESS)

    @admin.action(description="Xuất danh sách hóa đơn ra file CSV")
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response.write('\ufeff'.encode('utf8'))  # BOM để hỗ trợ Excel tiếng Việt
        response['Content-Disposition'] = 'attachment; filename=danh_sach_hoa_don_chi_tiet.csv'
        writer = csv.writer(response)

        # Ghi Header tự định nghĩa để đẹp và đầy đủ hơn
        writer.writerow(['Mã Hóa Đơn', 'Người Mua', 'Email', 'Tổng Tiền', 'Trạng Thái', 'Thời Gian Giao Dịch', 'Chi Tiết Sách (Tên sách x SL)'])
        
        # Ghi Data
        for order in queryset:
            # Gom thông tin các sách trong hóa đơn
            items = order.items.all()
            items_str = " | ".join([f"{item.book.title} (x{item.quantity})" for item in items])
            
            writer.writerow([
                f"HD{order.id:04d}",
                order.user.username,
                order.user.email,
                f"{order.total_price:,.0f} VNĐ",
                order.get_status_display(),
                order.created_at.strftime('%H:%M %d/%m/%Y'),
                items_str
            ])
            
        return response

@admin.register(BorrowRecord)
class BorrowRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_book_title', 'get_available_stock', 'get_currently_borrowed', 'user', 'status', 'borrow_date', 'due_date')
    list_filter = ('status', 'borrow_date', 'due_date')
    search_fields = ('user__username', 'book__title')
    actions = ['mark_as_approved', 'mark_as_returned', 'export_as_csv']

    @admin.display(description="Tựa sách mượn")
    def get_book_title(self, obj):
        return obj.book.title

    @admin.display(description="Sách Còn Lại (Có thể mượn)")
    def get_available_stock(self, obj):
        return obj.book.borrow_stock
        
    @admin.display(description="Đang bị người khác mượn")
    def get_currently_borrowed(self, obj):
        return BorrowRecord.objects.filter(book=obj.book, status__in=['Pending', 'Approved', 'Overdue']).count()

    @admin.action(description="Xác nhận: Phê duyệt (Approved)")
    def mark_as_approved(self, request, queryset):
        # Chỉ những Record đang Pending thì mới chuyển thành Approved thành công
        updated = queryset.filter(status='Pending').update(status='Approved')
        self.message_user(request, f"Đã phê duyệt {updated} yêu cầu mượn sách thành công.", messages.SUCCESS)

    @admin.action(description="Xuất danh sách phiếu mượn ra file CSV")
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response.write('\ufeff'.encode('utf8'))  # BOM để hỗ trợ Excel tiếng Việt
        response['Content-Disposition'] = 'attachment; filename=danh_sach_phieu_muon_chi_tiet.csv'
        writer = csv.writer(response)

        # Ghi Header rõ ràng dễ đọc
        writer.writerow(['Mã Phiếu', 'Sinh Viên / Giáo Viên', 'Sách Mượn', 'Trạng Thái', 'Ngày Gửi Đơn', 'Hẹn Ngày Trả'])
        
        # Ghi Data
        for record in queryset:
            writer.writerow([
                f"PM{record.id:04d}",
                record.user.username,
                record.book.title,
                record.get_status_display(),
                record.borrow_date.strftime('%H:%M %d/%m/%Y'),
                record.due_date.strftime('%d/%m/%Y')
            ])
            
        return response

    @admin.action(description="Xác nhận: Khách Đã trả sách (Returned & Hoàn Kho)")
    def mark_as_returned(self, request, queryset):
        # LỌC CỰC KỲ QUAN TRỌNG: Loại bỏ những cuốn ĐÃ TRẢ RỒI để Thủ thư dù mỏi tay ấn nhầm action 2 lần 
        # Cùng vào 1 Record cũng sẽ không bị xảy ra lỗi nhân đôi số lượng tồn kho vô hạn.
        eligible_records = queryset.exclude(status='Returned')
        
        count = 0
        try:
            # Atomic Guard: Tránh trường hợp đang hoàn kho cuốn 2 thì sập nguồn, cuốn 1 đã cộng kho cuốn 2 thì chưa
            with transaction.atomic():
                for record in eligible_records:
                    # 1. Chuyển trạng thái
                    record.status = 'Returned'
                    record.save(update_fields=['status'])

                    # 2. Hoàn cộng 1 vào kho mượn của cuốn sách tương ứng 
                    book = record.book
                    # Bonus Trick Senior: Sử dụng biểu thức F() để push toán tử +1 xuống tầng Database tự lo.
                    # Ngăn chặn 100% Data Race Conditions thay vì cách code book.borrow_stock += 1 truyền thống!
                    book.borrow_stock = F('borrow_stock') + 1
                    book.save(update_fields=['borrow_stock'])
                    
                    count += 1
            
            if count > 0:
                self.message_user(request, f"Thành công! Đã ghi nhận khách trả {count} cuốn và hoàn kho đẩy lên ứng dụng.", messages.SUCCESS)
            else:
                self.message_user(request, f"Không có phiếu mượn nào hợp lệ được xử lý (Tất cả phiếu được select đã Trả rổi).", messages.WARNING)
                
        except Exception as e:
            self.message_user(request, f"Lỗi nghiêm trọng không thể ghi dữ liệu hoàn kho: {str(e)}", messages.ERROR)
