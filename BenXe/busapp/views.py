import smtplib
from email.mime.text import MIMEText

from django.core.mail import send_mail
from rest_framework import viewsets, status, generics, parsers, permissions
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import User, Buses, Payment, Delivery, TransportCompany, Booking, Review, Notification, Comment, Seat
from .serializers import UserSerializer, PaymentSerializer, \
    DeliverySerializer, TransportCompanySerializer, ReviewSerializer, NotificationSerializer, ConfirmUserSerializer, \
    CommentSerializer, UpdateCommentSerializer, BusesSerializer
from .permission import IsSuperAdminOrEmployee, CommentOwner, IsUserorTransportCompany


class BusesViewSet(viewsets.ModelViewSet):
    queryset = Buses.objects.all()
    serializer_class = BusesSerializer

    # Thêm API tính tổng doanh thu của tất cả các chuyến của một tuyến xe
    @action(detail=True, methods=['post'])
    def buses_list(self, request):
        queryset = Buses.objects.all()
        serializer = BusesSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def buses_retrieve(self, request, pk=None):
        queryset = Buses.objects.all()
        route = get_object_or_404(queryset, pk=pk)
        trips = Buses.objects.filter(route=route)
        revenue = 0
        for trip in trips:
            revenue += trip.revenue
        return Response({'revenue': revenue})

    # Thêm API để nhận vé trực tuyến
    @action(detail=True, methods=['post'], url_path='receive_online')
    def receive_online(self, request, pk=None):
        booking = self.get_object()
        # Kiểm tra trạng thái của chuyến xe
        if booking.is_paid_online != 'paid':
            return Response({'message': 'Cannot receive ticket for this trip.'}, status=status.HTTP_400_BAD_REQUEST)

            # Lấy thông tin số lượng vé muốn nhận
            ticket_qty = request.data.get('ticket_qty')
            # Kiểm tra số lượng vé muốn nhận có lớn hơn số lượng vé còn trống của chuyến xe không
            if ticket_qty > booking.available_seats:
                return Response({'message': 'Not enough seats for this trip.'}, status=status.HTTP_400_BAD_REQUEST)

            # Thực hiện việc nhận vé trực tuyến
            for i in range(ticket_qty):
                ticket = Ticket(booking=booking, status='received')
                ticket.save()

            # Cập nhật số lượng vé còn trống của chuyến xe
            schedule.available_seats -= ticket_qty
            schedule.save()

        # Cập nhật trạng thái của chuyến xe
        schedule.status = 'completed'
        schedule.save()

        return Response({'message': 'Ticket received.'})

    def send_order_info_email(email, order_info):
        subject = 'Order Information'
        message = f"Thank you for booking with us. Here's your order information: \n\n {order_info}"
        from_email = 'noreply@gmail.com'
        recipient_list = [email]
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)

    # Thêm API để gửi thông tin đơn hàng cho khách hàng
    @action(detail=True, methods=['post'])
    def send_order_info(self, request, pk=None):
        buses = self.get_object()
        # Kiểm tra trạng thái của chuyến xe
        if buses.status != 'paid':
            return Response({'message': 'Cannot send order info for this trip.'}, status=status.HTTP_400_BAD_REQUEST)

        # Lấy thông tin đơn hàng
        order_info = {
            'buses': buses.name,
            'departure_date': buses.departure_date,
            'departure_time': buses.departure_time,
            'arrival_time': buses.arrival_time,
            'price': buses.price,
        }

        # Gửi thông tin đơn hàng đến khách hàng
        email = request.data.get('email')
        if not email:
            return Response({'message': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        self.send_order_info_email(email, order_info)

        return Response({'message': 'Order info sent.'})


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    # Thêm API để thanh toán trực tuyến cho vé xe
    @action(detail=True, methods=['post'])
    def payment_create(self, request, pk=None):
        # Lấy thông tin về đơn hàng và thông tin khách hàng từ request
        user = request.user
        route = request.data.get('route')
        booking = request.data.get('booking')
        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method')

        # Kiểm tra thông tin đơn hàng và thông tin khách hàng
        if not user or not route or not booking or not amount or not payment_method:
            return Response({'error': 'Invalid order or customer information.'})

        # Tạo giao dịch thanh toán mới
        payment = Payment.objects.create(
            user=user,
            route=route,
            booking=booking,
            amount=amount,
            payment_status='pending',
        )

        # Thực hiện thanh toán
        if payment_method == 'cash':
            # Đánh dấu đơn hàng đã được thanh toán
            booking.is_paid = True
            booking.save()
            # Cập nhật trạng thái của vé
            seats = Seat.objects.filter(booking=booking)
            for seat_number in seats:
                seat_number.is_booked = True
                seat_number.save()
        # Cập nhật trạng thái thanh toán
        payment.payment_status = 'success'
        payment.save()

        # Trả về thông tin giao dịch thanh toán
        serializer = self.serializer_class(payment)
        return Response(serializer.data)

    # Thêm API để xác nhận giao hàng
    @action(detail=True, methods=['post'], url_path='confirm_delivery')
    def confirm_delivery(self, request, pk=None):
        payment = self.get_object()

        # Kiểm tra trạng thái của vé
        if payment.status != 'delivered':
            return Response({'message': 'Cannot confirm delivery for this ticket.'}, status=status.HTTP_400_BAD_REQUEST)

        # Thực hiện xác nhận giao hàng
        serializer = self.get_serializer(payment, data={'status': 'delivered'}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({'message': 'Delivery confirmed.'})


class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer

    # Thêm API lấy danh sách các lô hàng của một nhà xe
    @action(detail=True, methods=['post'], url_path='list_by_owner')
    def list_by_owner(self, request, pk=None, owner_id=None):
        queryset = self.queryset.filter(owner_id=owner_id)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    # Thêm API lấy thông tin lô hàng theo mã số
    @action(detail=True, methods=['post'], url_path='retrieve_by_code')
    def retrieve_by_code(self, request, pk=None, owner_id=None, code=None):
        queryset = self.queryset.filter(owner_id=owner_id, code=code)
        if not queryset.exists():
            return Response({'detail': 'Shipment not found.'}, status=404)
        serializer = self.serializer_class(queryset.first())
        return Response(serializer.data)

    # Thêm API gửi thông tin nhận hàng cho người nhận
    @action(detail=True, methods=['post'], url_path='send_shipment_notification')
    def send_shipment_notification(self, request, pk=None, owner_id=None, code=None):
        queryset = self.queryset.filter(owner_id=owner_id, code=code)
        if not queryset.exists():
            return Response({'detail': 'Shipment not found.'}, status=404)
        shipment = queryset.first()
        if not shipment.recipient_email:
            return Response({'detail': 'Recipient email not found.'}, status=400)
        # Gửi email hoặc sms thông tin đến người nhận
        recipient = shipment.recipient_email
        message = f"Thông tin vận chuyển của đơn hàng {shipment.code}: \n" \
                  f"Địa chỉ gửi: {shipment.sender_address} \n" \
                  f"Địa chỉ nhận: {shipment.recipient_address} \n" \
                  f"Trạng thái: {shipment.status} \n"
        msg = MIMEText(message)
        msg['Subject'] = f"[Thông báo] Đơn hàng {shipment.code} đã được gửi đi"
        msg['From'] = 'youremail@gmail.com'  # Địa chỉ email người gửi
        msg['To'] = recipient
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login('youremail@gmail.com', 'yourpassword')  # Thay đổi email và mật khẩu của bạn tại đây
            server.sendmail('youremail@gmail.com', recipient, msg.as_string())
            server.quit()
            return Response({'detail': 'Notification sent successfully.'})
        except Exception as e:
            return Response({'detail': 'Error sending notification.'}, status=500)


class UserViewSet(viewsets.ModelViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    parser_classes = [parsers.MultiPartParser, ]

    def get_permissions(self):
        if self.action in ['current_user', 'change_password']:
            return [permissions.IsAuthenticated()]
        elif self.action in ['confirm_register', 'confirm']:
            return [IsSuperAdminOrEmployee()]
        return [permissions.AllowAny()]

    @action(methods=['get', 'put'], detail=False, url_path='current-user')
    def current_user(self, request):
        u = request.user
        if request.method.__eq__('PUT'):
            for k, v in request.data.items():
                if k.__eq__('password'):
                    u.set_password(v)
                else:
                    setattr(u, k, v)
            u.save()
        return Response(UserSerializer(u).data)

    @action(methods=['post'], detail=False, url_path='change-password')
    def change_password(self, request):
        u = request.user
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        if u.check_password(old_password):
            u.set_password(new_password)
            u.save()
            return Response({'message': 'Mật khẩu đã thay đổi thành công.'}, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Mật khẩu cũ không đúng!!!'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='notifications')
    def notifications(self, request):
        notifications = Notification.objects.filter(recipient=request.user.id)
        return Response(NotificationSerializer(notifications, many=True).data)

    @action(methods=['get'], detail=False, url_path='confirm-register')
    def confirm_register(self, request):
        u = User.objects.filter(role='S', is_verified=False)
        return Response(ConfirmUserSerializer(u, many=True).data)

    @action(methods=['patch'], detail=True, url_path='confirm')
    def confirm(self, request, pk):
        # u = request.user
        u = User.objects.get(pk=pk)
        if u.is_verified is False:
            u.is_verified = True
        else:
            return Response({'error': 'Tài khoản này đã xác nhận.'}, status=status.HTTP_400_BAD_REQUEST)
        u.save()
        notice = Notification(sender=request.user.id, content="Đã xác nhận tài khoản {} thành công.".format(u.username),
                              recipient=User.objects.filter(pk=pk).first())
        notice.save()
        return Response(ConfirmUserSerializer(u).data)

    # Thêm API để đặt vé trực tuyến
    @action(detail=True, methods=['post'], url_path='book_online')
    def book_online(self, request, pk=None):
        # Lấy thông tin chuyến xe
        buses_id = request.data.get('buses_id')
        try:
            buses = Buses.objects.get(id=buses_id)
        except Buses.DoesNotExist:
            return Response({'message': 'Invalid bus trip ID.'}, status=status.HTTP_400_BAD_REQUEST)

        # Kiểm tra trạng thái của chuyến xe
        if Buses.is_available != 'True':
            return Response({'message': 'This trip is not available for booking.'}, status=status.HTTP_400_BAD_REQUEST)

        # Thực hiện đặt vé trực tuyến
        seat_number = request.data.get('seat_number')
        if buses.check_available_seat(seat_number):  # kiểm tra xem ghế đó có sẵn không
            # Tạo đối tượng vé mới
            ticket = Booking(
                buses=buses,
                user=request.data.get('user'),
                seat_number=seat_number,
                price=buses.name.price
            )
            ticket.save()
            return Response({'message': 'Booking successful.'})
        else:
            return Response({'message': 'Seat is not available.'}, status=status.HTTP_400_BAD_REQUEST)

        # Cập nhật trạng thái của chuyến xe
        Buses.status = 'booked'
        Buses.save()

        return Response({'message': 'Booking successful.'})

    def check_available_seat(self, request, pk=None):
        # Lấy chuyến xe từ pk
        route = get_object_or_404(Buses, pk=pk)

        # Lấy danh sách các ghế trên chuyến xe đó
        seats = Seat.objects.filter(route=route)

        # Lấy danh sách các ghế đã bán
        booked_seats = seats.filter(is_booked=True).values_list('seat_number', flat=True)

        # Trả về danh sách các ghế chưa bán
        available_seats = [seat.seat_number for seat in seats if seat.seat_number not in booked_seats]

        return Response({'available_seats': available_seats})

    # Thêm API để hủy vé trực tuyến
    @action(detail=True, methods=['post'], url_path='cancel_booking_online')
    def cancel_booking_online(self, request, pk=None):
        # Thực hiện hủy vé trực tuyến
        booking_id = request.data.get('booking_id')
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({'message': 'Invalid booking ID.'}, status=status.HTTP_400_BAD_REQUEST)
        # Kiểm tra trạng thái của đơn đặt hàng
        if booking.is_booked != 'booked':
            return Response({'message': 'Cannot cancel booking for this order.'}, status=status.HTTP_400_BAD_REQUEST)

        # Cập nhật trạng thái của chuyến xe
        Buses.is_booked = 'available'
        Buses.save()

        return Response({'message': 'Booking canceled.'})


class TransportCompanyViewSet(viewsets.ModelViewSet):
    queryset = TransportCompany.objects.all()
    serializer_class = TransportCompanySerializer

    @action(detail=True, methods=['post'], url_path='lock_company')
    def lock_company(self, request, pk=None):
        company = self.get_object()
        company.is_active = False
        company.save()
        return Response({'message': f'{company.name} has been locked.'})

    @action(detail=True, methods=['post'], url_path='unlock_company')
    def unlock_company(self, request, pk=None):
        company = self.get_object()
        company.is_active = True
        company.save()
        return Response({'message': f'{company.name} has been unlocked.'})


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CommentViewSet(viewsets.ViewSet, generics.UpdateAPIView, generics.DestroyAPIView, generics.RetrieveAPIView):
    queryset = Comment.objects.filter(active=True)
    serializer_class = CommentSerializer

    # permission_classes = [CommentOwner,]
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return UpdateCommentSerializer
        return self.serializer_class

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [CommentOwner()]
        elif self.action.__eq__('reply_comment'):
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    @action(methods=['post'], detail=True, url_path='reply-comment')
    def reply_comment(self, request, pk):
        reply_to = self.get_object()
        c = Comment(content=request.data['content'], product=reply_to.product, user=request.user, reply_to=reply_to)
        c.save()
        return Response(CommentSerializer(c).data, status=status.HTTP_201_CREATED)
