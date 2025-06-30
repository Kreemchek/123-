from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.validators import RegexValidator
from .models import User, ContactRequest, Property, Message
from brokers.models import BrokerProfile
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'phone', 'last_name',
                  'first_name', 'patronymic']


class UserAdminChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'
        widgets = {
            'is_blocked': forms.CheckboxInput(attrs={'class': 'checkbox'}),
        }


class RoleSelectionForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=User.UserType.choices,
        widget=forms.RadioSelect(),
        label='Выберите вашу роль',
        required=True
    )

    class Meta:
        model = User
        fields = ['role']  # Только поле роли


        labels = {
            'last_name': 'Фамилия',
            'first_name': 'Имя',
            'patronymic': 'Отчество',
            'phone': 'Телефон',

            'avatar': 'Аватар'
        }
        widgets = {
            'phone': forms.TextInput(attrs={'placeholder': '+7 (999) 999-99-99'}),

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)



class ProfileForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=18,
        validators=[
            RegexValidator(
                regex=r'^\+7\s\(\d{3}\)\s\d{3}-\d{2}-\d{2}$',
                message="Номер должен быть в формате: +7 (XXX) XXX-XX-XX"
            )
        ],
        required=True,
        label='Телефон'

    )

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # Проверка типа файла
            valid_types = ['image/jpeg', 'image/png', 'image/gif']

            # Для новых загрузок (File objects)
            if hasattr(avatar, 'content_type'):
                if avatar.content_type not in valid_types:
                    raise ValidationError('Неподдерживаемый формат файла. Используйте JPG, PNG или GIF.')

                # Проверка размера файла (5MB)
                max_size = 5 * 1024 * 1024  # 5MB
                if avatar.size > max_size:
                    raise ValidationError(
                        f'Размер файла не должен превышать {filesizeformat(max_size)}. '
                        f'Ваш файл имеет размер {filesizeformat(avatar.size)}.'
                    )

            # Для существующих файлов Cloudinary (CloudinaryResource)
            elif not isinstance(avatar, str):  # CloudinaryResource
                # Не проверяем размер для существующих файлов Cloudinary
                pass

        return avatar




    class Meta:
        model = User
        fields = [
            'last_name',
            'first_name',
            'patronymic',
            'phone',

            'avatar'

        ]
        labels = {
            'last_name': 'Фамилия',
            'first_name': 'Имя',
            'patronymic': 'Отчество',
            'phone': 'Телефон',
            'avatar': 'Фотография профиля'
        }
        widgets = {
            'phone': forms.TextInput(attrs={'placeholder': '+7 (999) 999-99-99'}),

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем поля обязательными на уровне формы
        self.fields['last_name'].required = True
        self.fields['first_name'].required = True
        self.fields['phone'].required = True




class ContactRequestForm(forms.ModelForm):
    class Meta:
        model = ContactRequest
        fields = ['broker', 'property']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['broker'].queryset = User.objects.filter(user_type=User.UserType.BROKER)
        self.fields['property'].queryset = Property.objects.filter(is_approved=True)

        if 'broker' in self.data:
            try:
                broker_id = int(self.data.get('broker'))
                self.fields['property'].queryset = Property.objects.filter(broker_id=broker_id)
            except (ValueError, TypeError):
                pass


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['text', 'attachment']


class BrokerProfileForm(forms.ModelForm):


        experience = forms.IntegerField(
            label='Опыт работы (лет)',
            min_value=0,
            required=True,
            widget = forms.NumberInput(attrs={'class': 'custom-input'}),
        )

        about = forms.CharField(
            label='О себе',
            widget=forms.Textarea(attrs={'class': 'custom-input', 'rows': 4}),
            required=True
        )




        class Meta:
            model = BrokerProfile
            fields = ['experience','about']

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
