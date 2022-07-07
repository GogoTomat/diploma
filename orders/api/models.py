from django.db import models as m
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.tokens import get_token_generator


STATE_CHOICES = (
    ('basket', 'Статус корзины'),
    ('new', 'Новый'),
    ('confirmed', 'Подтвержден'),
    ('assembled', 'Собран'),
    ('sent', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменен'),
)

USER_TYPE_CHOICES = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),

)


class UserManager(BaseUserManager):
    """
    Миксин для управления пользователями
    """
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Стандартная модель пользователей
    """
    REQUIRED_FIELDS = []
    objects = UserManager()
    USERNAME_FIELD = 'email'
    email = m.EmailField(_('email address'), unique=True)
    company = m.CharField(verbose_name='Компания', max_length=40, blank=True)
    position = m.CharField(verbose_name='Должность', max_length=40, blank=True)
    username_validator = UnicodeUsernameValidator()
    username = m.CharField(
        _('username'),
        max_length=150,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    is_active = m.BooleanField(
        _('active'),
        default=False,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    type = m.CharField(verbose_name='Тип пользователя', choices=USER_TYPE_CHOICES, max_length=5, default='buyer')

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = "Список пользователей"
        ordering = ('email',)


class Shop(m.Model):
    name = m.CharField(max_length=80, verbose_name='Название')
    url = m.URLField(verbose_name='Ссылка', null=True, blank=True)
    user = m.OneToOneField('User', verbose_name='Пользователь', blank=True, null=True, on_delete=m.CASCADE)

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = "Список магазинов"
        ordering = ('-name',)

    def __str__(self):
        return self.name


class Category(m.Model):
    name = m.CharField(max_length=80, verbose_name='Название')
    shops = m.ManyToManyField(Shop, verbose_name='Магазины', related_name='categories', blank=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = "Список категорий"
        ordering = ('-name',)

    def __str__(self):
        return self.name


class Product(m.Model):
    name = m.CharField(max_length=80, verbose_name='Название')
    category = m.ForeignKey(Category, verbose_name='Категория', related_name='products', blank=True,
                            on_delete=m.CASCADE)

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = "Список продуктов"
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductInfo(m.Model):
    model = m.CharField(max_length=80, verbose_name='Модель', blank=True)
    quantity = m.PositiveIntegerField(verbose_name='Количество')
    price = m.PositiveIntegerField(verbose_name='Цена')
    price_rrc = m.PositiveIntegerField(verbose_name='Рекомендуемая розничная цена')
    external_id = m.PositiveIntegerField(verbose_name='Внешний ИД')
    product = m.ForeignKey(Product, verbose_name='Продукт', related_name='product_info', blank=True,
                           on_delete=m.CASCADE)
    shop = m.ForeignKey(Shop, verbose_name='Магазин', related_name='product_info', blank=True, on_delete=m.CASCADE)

    class Meta:
        verbose_name = 'Информация о продукте'
        verbose_name_plural = "Информационный список о продуктах"
        constraints = [
            m.UniqueConstraint(fields=['product', 'shop', 'external_id'], name='unique_product_info'),
        ]


class Parameter(m.Model):
    name = m.CharField(max_length=80, verbose_name='Название')

    class Meta:
        verbose_name = 'Имя параметра'
        verbose_name_plural = "Список имен параметров"
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductParameter(m.Model):
    product_info = m.ForeignKey(ProductInfo, verbose_name='Информация о продукте', related_name='product_parameters',
                                blank=True, on_delete=m.CASCADE)
    parameter = m.ForeignKey(Parameter, verbose_name='Параметр', related_name='product_parameters', blank=True,
                             on_delete=m.CASCADE)
    value = m.CharField(verbose_name='Значение', max_length=100)

    class Meta:
        verbose_name = 'Параметр'
        verbose_name_plural = "Список параметров"
        constraints = [
            m.UniqueConstraint(fields=['product_info', 'parameter'], name='unique_product_parameter'),
        ]


class Contact(m.Model):
    user = m.ForeignKey(User, verbose_name='Пользователь', related_name='contacts', blank=True, on_delete=m.CASCADE)
    city = m.CharField(max_length=50, verbose_name='Город')
    street = m.CharField(max_length=100, verbose_name='Улица')
    house = m.CharField(max_length=15, verbose_name='Дом', blank=True)
    structure = m.CharField(max_length=15, verbose_name='Корпус', blank=True)
    building = m.CharField(max_length=15, verbose_name='Строение', blank=True)
    apartment = m.CharField(max_length=15, verbose_name='Квартира', blank=True)
    phone = m.CharField(max_length=20, verbose_name='Телефон')

    class Meta:
        verbose_name = 'Контакты пользователя'
        verbose_name_plural = "Список контактов пользователя"

    def __str__(self):
        return f'{self.city} {self.street} {self.house}'


class Order(m.Model):
    user = m.ForeignKey(User, verbose_name='Пользователь', related_name='orders', blank=True, on_delete=m.CASCADE)
    dt = m.DateTimeField(auto_now_add=True)
    state = m.CharField(verbose_name='Статус', choices=STATE_CHOICES, max_length=15)
    contact = m.ForeignKey(Contact, verbose_name='Контакт', blank=True, null=True, on_delete=m.CASCADE)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = "Список заказ"
        ordering = ('-dt',)

    def __str__(self):
        return str(self.dt)


class OrderItem(m.Model):
    order = m.ForeignKey(Order, verbose_name='Заказ', related_name='ordered_items', blank=True, on_delete=m.CASCADE)
    product_info = m.ForeignKey(ProductInfo, verbose_name='Информация о продукте', related_name='ordered_items',
                                blank=True, on_delete=m.CASCADE)
    quantity = m.PositiveIntegerField(verbose_name='Количество')

    class Meta:
        verbose_name = 'Заказанная позиция'
        verbose_name_plural = "Список заказанных позиций"
        constraints = [
            m.UniqueConstraint(fields=['order_id', 'product_info'], name='unique_order_item'),
        ]

    def __str__(self):
        return f'{self.order}, позиция {self.product_info}'


class ConfirmEmailToken(m.Model):
    class Meta:
        verbose_name = 'Токен подтверждения Email'
        verbose_name_plural = 'Токены подтверждения Email'

    @staticmethod
    def generate_key():
        """ generates a pseudo random code using os.urandom and binascii.hexlify """
        return get_token_generator().generate_token()

    user = m.ForeignKey(
        User,
        related_name='confirm_email_tokens',
        on_delete=m.CASCADE,
        verbose_name=_("The User which is associated to this password reset token")
    )

    created_at = m.DateTimeField(
        auto_now_add=True,
        verbose_name=_("When was this token generated")
    )

    # Key field, though it is not the primary key of the model
    key = m.CharField(
        _("Key"),
        max_length=64,
        db_index=True,
        unique=True
    )

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ConfirmEmailToken, self).save(*args, **kwargs)

    def __str__(self):
        return "Password reset token for user {user}".format(user=self.user)
