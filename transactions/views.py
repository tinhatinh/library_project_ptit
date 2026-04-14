import os
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
from django.shortcuts import get_object_or_404, redirect, render
from xhtml2pdf import pisa
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages

from catalog.models import Book
from .models import Order, OrderItem, BorrowRecord
from .cart import Cart

@login_required
@transaction.atomic
def checkout_buy(request):
    if request.method != 'POST':
        return redirect('cart_detail')
        
    selected_book_ids = request.POST.getlist('selected_books')
    if not selected_book_ids:
        messages.warning(request, "Vui lòng tick chọn ít nhất 1 cuốn sách để thanh toán.")
        return redirect('cart_detail')
        
    cart = Cart(request)

    try:
        with transaction.atomic():
            order = Order.objects.create(user=request.user, status='Pending', total_price=0)
            total_price = 0
            
            books = Book.objects.select_for_update().filter(id__in=selected_book_ids).order_by('id')
            book_dict = {str(book.id): book for book in books}

            for book_id in selected_book_ids:
                book = book_dict.get(book_id)
                if not book:
                    raise Exception(f"Sách ID {book_id} không tồn tại hoặc đã bị xóa.")
                
                # Fetch dynamically updated quantity typed exactly on frontend right before submission
                try:
                    quantity = int(request.POST.get(f'quantity_{book_id}', 1))
                except ValueError:
                    quantity = 1
                
                if quantity <= 0:
                    continue
                
                if book.sell_stock < quantity:
                    raise Exception(f"Sách {book.title} không đủ số lượng tồn (Chỉ còn {book.sell_stock} cuốn).")

                book.sell_stock -= quantity
                book.save()

                OrderItem.objects.create(
                    order=order,
                    book=book,
                    quantity=quantity,
                    price_at_time_of_purchase=book.sell_price
                )
                
                total_price += book.sell_price * quantity
                
                # Loại bỏ cuốn đã thanh toán thành công khỏi rổ hàng Session
                cart.remove_from_buy(book)
            
            if total_price == 0:
                raise Exception("Giỏ hàng của bạn lỗi: Trị giá tổng thanh toán bằng 0.")

            order.total_price = total_price
            order.save()

        messages.success(request, f"Thanh toán đơn trị giá {total_price} VNĐ thành công! Hệ thống tự động in hoá đơn PDF...")
        return redirect('mock_payment', order_id=order.id)
        
    except Exception as e:
        messages.error(request, str(e))
        return redirect('home')


@login_required
@transaction.atomic
def checkout_borrow(request):
    if request.method != 'POST':
        return redirect('cart_detail')
        
    selected_book_ids = request.POST.getlist('selected_borrow_books')
    if not selected_book_ids:
        messages.warning(request, "Bạn chưa tick chọn cuốn sách nào để mượn.")
        return redirect('cart_detail')
        
    cart = Cart(request)

    try:
        with transaction.atomic():
            books = Book.objects.select_for_update().filter(id__in=selected_book_ids).order_by('id')
            book_dict = {str(b.id): b for b in books}
            due_date = date.today() + timedelta(days=14)

            for book_id in selected_book_ids:
                book = book_dict.get(book_id)
                if not book:
                    raise Exception(f"Dữ liệu lỗi: Sách ID {book_id} không khớp.")

                if book.borrow_stock <= 0:
                    raise Exception(f"Sách '{book.title}' vừa có người mượn hết. Vui lòng bỏ chọn để tiếp tục.")

                book.borrow_stock -= 1
                book.save()

                BorrowRecord.objects.create(
                    user=request.user,
                    book=book,
                    status='Pending',
                    due_date=due_date
                )
                
                # Xóa cuốn sách vừa đăng ký mượn xong ra khỏi Session
                cart.remove_from_borrow(book)

        messages.success(request, "Gửi Yêu cầu đăng ký mượn sách thành công! Vui lòng chờ thủ thư check và duyệt.")

    except Exception as e:
        messages.error(request, str(e))

    return redirect('home')

def link_callback(uri, rel):
    """
    Hàm helper convert các URI dạng /static/ hoặc /media/ thành Absolute Path trên hệ điều hành.
    """
    import os
    from django.conf import settings
    
    if uri.startswith(settings.MEDIA_URL):
        # Trích xuất phần đuôi
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, "", 1))
    elif uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, "", 1))
    else:
        return uri

    # Trả về đường dẫn chuẩn của Windows
    return os.path.normpath(path)

@login_required
@transaction.atomic
def mock_payment(request, order_id):
    """
    Mock gateway thanh toán: Set Paid và điều hướng đi rút hóa đơn PDF.
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status != 'Paid':
        order.status = 'Paid'
        order.save()
        messages.success(request, f"Giao dịch cho đơn hàng #{order.id} đã hoàn tất.")
        
    # Redirect sang xuất Hóa đơn PDF
    return redirect('download_invoice_pdf', order_id=order.id)

@login_required
def download_invoice_pdf(request, order_id):
    """
    Phát sinh PDF hoá đơn mua thư viện trường bằng reportlab Canvas.
    Hỗ trợ font tiếng Việt + watermark logo PTIT.
    """
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm, mm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import Table, TableStyle
    from reportlab.pdfgen import canvas as pdf_canvas
    from django.utils import timezone

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status != 'Paid':
        messages.warning(request, "Đơn hàng phải được thanh toán trước khi lấy hoá đơn đỏ.")
        return redirect('home')

    # --- Đường dẫn tuyệt đối ---
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    font_regular = os.path.join(project_dir, 'media', 'fonts', 'arial.ttf')
    font_bold = os.path.join(project_dir, 'media', 'fonts', 'arialbd.ttf')
    logo_path = os.path.join(project_dir, 'media', 'images', 'ptit_logo.png')

    # --- Đăng ký font (chỉ 1 lần) ---
    try:
        pdfmetrics.getFont('ArialVN')
    except KeyError:
        pdfmetrics.registerFont(TTFont('ArialVN', font_regular))
        pdfmetrics.registerFont(TTFont('ArialVN-Bold', font_bold))
        pdfmetrics.registerFontFamily('ArialVN', normal='ArialVN', bold='ArialVN-Bold')

    # --- Tạo PDF trong bộ nhớ ---
    buf = BytesIO()
    width, height = A4  # 595.27 x 841.89 pt
    margin = 2 * cm
    content_w = width - 2 * margin
    c = pdf_canvas.Canvas(buf, pagesize=A4)
    now_str = timezone.localtime().strftime('%d/%m/%Y %H:%M')

    # ══════════════════════════════════════════
    # WATERMARK (vẽ đầu tiên → nằm dưới cùng)
    # ══════════════════════════════════════════
    if os.path.isfile(logo_path):
        c.saveState()
        c.setFillAlpha(0.06)
        wm_size = 320
        c.drawImage(logo_path,
                     (width - wm_size) / 2,
                     (height - wm_size) / 2 - 20,
                     width=wm_size, height=wm_size,
                     preserveAspectRatio=True, mask='auto')
        c.restoreState()

    y = height - margin

    # ══════════════════════════════════════════
    # HEADER: Logo nhỏ + Tên trường + Biên lai
    # ══════════════════════════════════════════

    # --- Logo nhỏ góc trái (nếu có) ---
    logo_size = 50
    if os.path.isfile(logo_path):
        c.drawImage(logo_path, margin, y - logo_size + 5,
                     width=logo_size, height=logo_size,
                     preserveAspectRatio=True, mask='auto')

    # --- Tên trường (cạnh logo) ---
    text_x = margin + logo_size + 10
    c.setFont('ArialVN-Bold', 13)
    c.setFillColor(HexColor('#d32f2f'))
    c.drawString(text_x, y - 12, "HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG")
    c.setFont('ArialVN', 10)
    c.setFillColor(HexColor('#555555'))
    c.drawString(text_x, y - 28, "Trung Tâm Thư Viện — Cơ Sở Đa Phương Tiện")

    y -= logo_size + 15

    # --- Đường kẻ trên ---
    c.setStrokeColor(HexColor('#2980b9'))
    c.setLineWidth(2)
    c.line(margin, y, width - margin, y)

    # ══════════════════════════════════════════
    # TIÊU ĐỀ BIÊN LAI (căn giữa trang)
    # ══════════════════════════════════════════
    y -= 35
    c.setFont('ArialVN-Bold', 22)
    c.setFillColor(HexColor('#c0392b'))
    c.drawCentredString(width / 2, y, "BIÊN LAI ĐIỆN TỬ")
    y -= 18
    c.setFont('ArialVN', 10)
    c.setFillColor(HexColor('#7f8c8d'))
    c.drawCentredString(width / 2, y, f"Ngày xuất: {now_str}")

    # --- Đường kẻ mỏng dưới tiêu đề ---
    y -= 15
    c.setStrokeColor(HexColor('#bdc3c7'))
    c.setLineWidth(0.5)
    c.line(margin + 3 * cm, y, width - margin - 3 * cm, y)

    # ══════════════════════════════════════════
    # THÔNG TIN ĐƠN HÀNG (bảng 2 cột gọn gàng)
    # ══════════════════════════════════════════
    y -= 28
    full_name = order.user.get_full_name() or order.user.username
    if order.created_at:
        time_str = timezone.localtime(order.created_at).strftime('%H:%M — %d/%m/%Y')
    else:
        time_str = now_str

    info_data = [
        ['Mã phiếu thu:', f'#HD-{order.id:05d}',    'Tình trạng:', 'ĐÃ THANH TOÁN'],
        ['Người nộp tiền:', full_name,                 'Ghi nhận lúc:', time_str],
    ]
    info_col_w = [3.5 * cm, 5.5 * cm, 3.5 * cm, 5.2 * cm]
    info_table = Table(info_data, colWidths=info_col_w)
    info_style = [
        ('FONTNAME', (0, 0), (0, -1), 'ArialVN-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'ArialVN-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'ArialVN'),
        ('FONTNAME', (3, 0), (3, -1), 'ArialVN'),
        ('FONTNAME', (3, 0), (3, 0), 'ArialVN-Bold'),  # "ĐÃ THANH TOÁN" in đậm
        ('TEXTCOLOR', (3, 0), (3, 0), HexColor('#27ae60')),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    info_table.setStyle(TableStyle(info_style))
    iw, ih = info_table.wrap(content_w, 0)
    info_table.drawOn(c, margin, y - ih)
    y -= ih + 10

    # ══════════════════════════════════════════
    # TIÊU ĐỀ BẢNG CHI TIẾT
    # ══════════════════════════════════════════
    y -= 10
    c.setFont('ArialVN-Bold', 12)
    c.setFillColor(HexColor('#2c3e50'))
    c.drawString(margin, y, "CHI TIẾT MỤC LỤC SÁCH:")

    # ══════════════════════════════════════════
    # BẢNG SẢN PHẨM
    # ══════════════════════════════════════════
    y -= 20

    items = order.items.all()
    table_data = [['STT', 'Tựa Sách / Tài Liệu', 'Đơn giá (VNĐ)', 'SL', 'Thành tiền (VNĐ)']]
    for idx, item in enumerate(items, 1):
        line_total = item.price_at_time_of_purchase * item.quantity
        table_data.append([
            str(idx),
            item.book.title,
            f"{item.price_at_time_of_purchase:,.0f}",
            str(item.quantity),
            f"{line_total:,.0f}",
        ])
    table_data.append(['', '', '', 'TỔNG CỘNG:', f"{order.total_price:,.0f} VNĐ"])

    col_widths = [1.2 * cm, 7.3 * cm, 3 * cm, 1.5 * cm, 4.7 * cm]
    t = Table(table_data, colWidths=col_widths)

    header_bg = HexColor('#2c3e50')
    header_fg = HexColor('#ffffff')
    row_alt = HexColor('#f8f9fa')
    total_bg = HexColor('#fce4ec')
    total_fg = HexColor('#c0392b')
    border_c = HexColor('#dee2e6')

    style_cmds = [
        # Font
        ('FONTNAME', (0, 0), (-1, 0), 'ArialVN-Bold'),
        ('FONTNAME', (0, 1), (-1, -2), 'ArialVN'),
        ('FONTNAME', (0, -1), (-1, -1), 'ArialVN-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), header_fg),
        # Total row
        ('BACKGROUND', (0, -1), (-1, -1), total_bg),
        ('TEXTCOLOR', (0, -1), (-1, -1), total_fg),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        # Alignment
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),   # STT
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),    # Đơn giá
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),   # SL
        ('ALIGN', (4, 0), (4, -1), 'RIGHT'),    # Thành tiền
        # Grid & padding
        ('GRID', (0, 0), (-1, -1), 0.5, border_c),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]
    # Zebra stripe cho data rows
    for i in range(1, len(table_data) - 1):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), row_alt))

    t.setStyle(TableStyle(style_cmds))
    t_w, t_h = t.wrap(content_w, 0)
    t.drawOn(c, margin, y - t_h)

    # ══════════════════════════════════════════
    # VÙNG CHỮ KÝ
    # ══════════════════════════════════════════
    sig_y = y - t_h - 50

    # Đường kẻ mỏng ngăn cách
    c.setStrokeColor(HexColor('#bdc3c7'))
    c.setLineWidth(0.5)
    c.line(margin, sig_y + 15, width - margin, sig_y + 15)

    c.setFont('ArialVN-Bold', 11)
    c.setFillColor(HexColor('#2c3e50'))
    c.drawCentredString(width * 0.28, sig_y, "CÁN BỘ THƯ VIỆN")
    c.setFont('ArialVN', 8)
    c.setFillColor(HexColor('#95a5a6'))
    c.drawCentredString(width * 0.28, sig_y - 14, "(Đã lưu hồ sơ trên hệ thống)")

    c.setFont('ArialVN-Bold', 11)
    c.setFillColor(HexColor('#2c3e50'))
    c.drawCentredString(width * 0.72, sig_y, "NGƯỜI NỘP NHẬN SÁCH")
    c.setFont('ArialVN', 8)
    c.setFillColor(HexColor('#95a5a6'))
    c.drawCentredString(width * 0.72, sig_y - 14, "(Chữ ký điện toán bằng Email xác thực)")

    # ══════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════
    c.setFont('ArialVN', 7)
    c.setFillColor(HexColor('#bdc3c7'))
    c.drawCentredString(width / 2, margin - 10,
                         "Biên lai được tạo tự động bởi Hệ thống Thư viện PTIT — Không cần đóng dấu.")

    # === HOÀN TẤT ===
    c.showPage()
    c.save()

    # Trả response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Hoa_Don_Thu_Vien_{order.id}.pdf"'
    response.write(buf.getvalue())
    buf.close()
    return response

@login_required
def cart_detail(request):
    """
    Render giao diện Giỏ hàng 2 Cột (Mua/Mượn).
    """
    cart = Cart(request)
    
    # Tổ hợp Data cho Giỏ Mua
    buy_items = []
    for book_id, quantity in cart.buy_cart.items():
        try:
            book = Book.objects.get(id=book_id)
            buy_items.append({
                'book': book,
                'quantity': quantity,
                'total_price': book.sell_price * quantity
            })
        except Book.DoesNotExist:
            pass
            
    # Tổ hợp Data cho Giỏ Mượn
    borrow_items = []
    for book_id in cart.borrow_cart.keys():
        try:
            book = Book.objects.get(id=book_id)
            borrow_items.append({'book': book})
        except Book.DoesNotExist:
            pass
            
    context = {
        'buy_items': buy_items,
        'buy_total': cart.get_buy_total_price(),
        'borrow_items': borrow_items,
    }
    return render(request, 'transactions/cart.html', context)

from django.urls import reverse

@login_required
def add_to_buy(request, book_id):
    if request.method == 'POST':
        book = get_object_or_404(Book, id=book_id)
        cart = Cart(request)
        cart.add_to_buy(book, 1)
        messages.success(request, f"Đã thả thành công sách '{book.title}' vào Giỏ mua.")
    return redirect(f"{reverse('home')}?open_cart=1")

@login_required
def add_to_borrow(request, book_id):
    if request.method == 'POST':
        book = get_object_or_404(Book, id=book_id)
        
        # Kiểm tra logic nghiệp vụ: Cùng 1 user không được phép mượn đúp 1 loại sách 
        # (Nếu đang Pending, Approved hoặc Overdue thì tự động chặn)
        is_borrowing = BorrowRecord.objects.filter(
            user=request.user,
            book=book,
            status__in=['Pending', 'Approved', 'Overdue']
        ).exists()
        
        if is_borrowing:
            messages.error(request, f"Lỗi: Bạn đang mượn hoặc đang chờ duyệt cuốn '{book.title}' này rồi. Không thể mượn trùng hai phiên bản!")
        else:
            cart = Cart(request)
            cart.add_to_borrow(book)
            messages.success(request, f"Đã đăng ký giữ chỗ vào Giỏ mượn '{book.title}'.")
            
    return redirect(f"{reverse('home')}?open_cart=1")
