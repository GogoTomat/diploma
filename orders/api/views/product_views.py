from django.db.models import Q
from rest_framework.generics import ListAPIView, GenericAPIView
from rest_framework.response import Response

from orders.api.models import Category, Shop, ProductInfo
from orders.api.permissions import IsAdminOrReadOnly
from orders.api.serializers import CategorySerializer, ShopSerializer, ProductInfoSerializer


class CategoryView(ListAPIView):
    """
    Класс для просмотра категорий
    """
    permission_classes = (IsAdminOrReadOnly, )
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ShopView(ListAPIView):
    """
    Класс для просмотра списка магазинов
    """
    permission_classes = (IsAdminOrReadOnly,)
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer


class ProductInfoView(GenericAPIView):
    """
    Класс для поиска товаров
    """
    def get(self, request, *args, **kwargs):

        query = Q(shop__state=True)
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

        if shop_id:
            query &= Q(shop_id=shop_id)

        if category_id:
            query &= Q(product__category_id=category_id)

        # фильтруем и отбрасываем дубликаты
        queryset = ProductInfo.objects.filter(
            query).select_related(
            'shop', 'product__category').prefetch_related(
            'product_parameters__parameter').distinct()

        serializer = ProductInfoSerializer(queryset, many=True)

        return Response(serializer.data)
