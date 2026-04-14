from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

# Import các controller (views) đã viết
from catalog import views as catalog_views
from transactions import views as transaction_views

urlpatterns = [
    # Giao diện Admin (http://localhost:8000/admin)
    path('admin/', admin.site.urls),
    
    # ==== AUTH: ĐĂNG NHẬP / ĐĂNG XUẤT / ĐĂNG KÝ ====
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('accounts/register/', catalog_views.register, name='register'),
    
    # ==== CATALOG: TRANG CHỦ CATALOG SÁCH ====
    path('', catalog_views.book_list, name='home'),
    path('book/<int:pk>/', catalog_views.book_detail, name='book_detail'),
    
    # ==== CART: GIỎ HÀNG VÀ THÊM CART ====
    path('cart/', transaction_views.cart_detail, name='cart_detail'),
    path('cart/buy/<int:book_id>/', transaction_views.add_to_buy, name='add_to_buy'),
    path('cart/borrow/<int:book_id>/', transaction_views.add_to_borrow, name='add_to_borrow'),
    
    # ==== CHECKOUT: XỬ LÝ THANH TOÁN (POST) ====
    path('checkout/buy/', transaction_views.checkout_buy, name='checkout_buy'),
    path('checkout/borrow/', transaction_views.checkout_borrow, name='checkout_borrow'),
    
    # ==== ORDER & PDF: XUẤT HÓA ĐƠN ====
    path('payment/<int:order_id>/', transaction_views.mock_payment, name='mock_payment'),
    path('invoice/pdf/<int:order_id>/', transaction_views.download_invoice_pdf, name='download_invoice_pdf'),
]

# Hỗ trợ render ảnh tĩnh (cover_image) trên trình duyệt local trong quá trình Build
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
