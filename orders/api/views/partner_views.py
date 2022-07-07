import os
from distutils.util import strtobool

import yaml
from django.conf import settings
from django.db.models import Sum, F
from django.http import JsonResponse

from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from orders.api.models import Shop, Category, ProductInfo, Product, Parameter, ProductParameter, Order
from orders.api.permissions import IsShop
from orders.api.serializers import ShopSerializer, OrderSerializer


class PartnerUpdate(GenericAPIView):
    """
    Класс для обновления прайса от поставщика
    """
    def post(self, request, *args, **kwargs):
        permission_classes = (IsAuthenticated, IsShop)
        # authentication_classes = (TokenAuthentication)

        req = request.data.get('url').split('/')
        filename = req[-1]
        dir = req[-2]
        path_to_file = f'{settings.BASE_DIR}/{dir}/{filename}'

        if os.path.exists(path_to_file):
            try:
                with open(path_to_file, 'r') as stream:
                    try:
                        data = yaml.safe_load(stream)
                    except yaml.YAMLError as exc:
                        raise exc
            except FileNotFoundError:
                raise f'File {filename} does not exist'

            shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)
            for category in data['categories']:
                category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                category_object.shops.add(shop.id)
                category_object.save()
            ProductInfo.objects.filter(shop_id=shop.id).delete()
            for item in data['goods']:
                product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

                product_info = ProductInfo.objects.create(product_id=product.id,
                                                          external_id=item['id'],
                                                          model=item['model'],
                                                          price=item['price'],
                                                          price_rrc=item['price_rrc'],
                                                          quantity=item['quantity'],
                                                          shop_id=shop.id)
                for name, value in item['parameters'].items():
                    parameter_object, _ = Parameter.objects.get_or_create(name=name)
                    ProductParameter.objects.create(product_info_id=product_info.id,
                                                    parameter_id=parameter_object.id,
                                                    value=value)

            return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerState(GenericAPIView):
    """
    Класс для работы со статусом поставщика
    """

    permission_classes = (IsAuthenticated, IsShop,)
    serializer_class = ShopSerializer

    def get(self, request, *args, **kwargs):
        """ Метод для получения текущего статуса поставщика """

        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """ Метод для изменения статуса поставщика """

        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=strtobool(state))
                return JsonResponse({'Status': True})
            except ValueError as error:
                return JsonResponse({'Status': False, 'Errors': str(error)})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerOrders(GenericAPIView):
    """
    Класс для получения заказов поставщиками
    """
    permission_classes = (IsAuthenticated, IsShop,)
    serializer_class = OrderSerializer

    def get(self, request):

        order = Order.objects.filter(
            ordered_items__product_info__shop_id=request.user.shop.id).exclude(
            status='basket'
        ).prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)
