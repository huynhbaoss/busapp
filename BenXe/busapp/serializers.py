from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import User, Buses, TransportCompany, Review, Comment, Booking, Payment, Notification, Delivery, Seat
from django.db.models import Avg
from .paginators import BusesPaginator
from django.contrib.auth.models import Group


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True, read_only=True)

    def create(self, validated_data):
        data = validated_data.copy()
        u = User(**data)
        u.set_password(u.password)
        if u.role == 'U':
            u.is_verified = True
        elif u.role == 'E':
            u.is_verified = False
        u.save()

        if u.role == 'U':
            g = Group.objects.get(name='User')
            u.groups.add(g)
        elif u.role == 'E':
            g = Group.objects.get(name='Employee')
            u.groups.add(g)
            recipients = User.objects.filter(is_staff=True).all()
            for recipient in recipients:
                notice = Notification(sender=u.id, content="Đăng kí trở thành nhà xe - {}".format(u.username),
                                      recipient=recipient)
                notice.save()
        return u

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'email', 'avatar', 'role', 'groups']
        extra_kwargs = {
            'password': {'write_only': True},
            'role': {'write_only': True}
        }


class ConfirmUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'role', 'is_verified']


class TransportCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportCompany
        fields = '__all__'


class BusesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Buses
        fields = '__all__'


class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = '__all__'


class DeliverySerializer(ModelSerializer):
    class Meta:
        model = Delivery
        fields = '__all__'


class BusesDetailSerializer(BusesSerializer):
    buses = BusesSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)
    buses_count = serializers.SerializerMethodField(read_only=True)

    def get_buses_count(self, obj):
        return Buses.objects.filter(buses=obj).count()

    def create(self, validated_data):
        requests = self.context.get('request')
        if requests:
            data = validated_data.copy()
            data['user_id'] = requests.user.id
            b = Buses(**data)
            b.active = True
            b.save()
            return b

    class Meta:
        model = BusesSerializer.Meta.model
        fields = [BusesSerializer.Meta.fields] + ['description', 'created_date', 'active', 'user', 'buses_count', 'buses']


class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    def validate_rate(self, rate):
        if rate < 0 or rate > 5:
            raise serializers.ValidationError('Giá trị rate phải nằm trong khoảng từ 0 đến 5')
        return rate

    class Meta:
        model = Review
        fields = ['id', 'rate', 'content', 'created_date', 'updated_date', 'user']


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    replies = serializers.SerializerMethodField()

    def get_replies(self, obj):
        replies = Comment.objects.filter(reply_to=obj)
        serializer = CommentSerializer(replies, many=True)
        return serializer.data

    class Meta:
        model = Comment
        fields = ['id', 'content', 'created_date', 'user', 'reply_to', 'replies']


class UpdateCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'content', 'created_date', 'updated_date', 'user']


class PaymentSerializer(ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = '__all__'


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


class BookingSerializer(ModelSerializer):
    user = UserSerializer(read_only=True)
    buses = BusesSerializer()

    class Meta:
        model = Booking
        fields = '__all__'
