# brokers/forms.py
from django import forms
from .models import BrokerProfile, BrokerReview


class BrokerProfileForm(forms.ModelForm):
    services = forms.TypedMultipleChoiceField(
        choices=BrokerProfile.SERVICES_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label='Услуги',
        required=True,
        coerce=str
    )

    specializations = forms.TypedMultipleChoiceField(
        choices=BrokerProfile.SPECIALIZATION_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label='Специализация',
        required=True,
        coerce=str
    )

    class Meta:
        model = BrokerProfile
        fields = ['experience', 'about']
        widgets = {
            'about': forms.Textarea(attrs={'rows': 4, 'class': 'custom-input'}),
            'experience': forms.NumberInput(attrs={'class': 'custom-input'}),
        }

    def clean_services(self):
        services = self.cleaned_data.get('services')
        if not services:
            raise forms.ValidationError("Выберите хотя бы одну услугу")
        return services

    def clean_specializations(self):
        specializations = self.cleaned_data.get('specializations')
        if not specializations:
            raise forms.ValidationError("Выберите хотя бы одну специализацию")
        return specializations

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Явно добавляем поля, если они были удалены
        if 'services' not in self.fields:
            self.fields['services'] = forms.TypedMultipleChoiceField(
                choices=BrokerProfile.SERVICES_CHOICES,
                widget=forms.CheckboxSelectMultiple,
                label='Услуги',
                required=True,  # Оставляем обязательным
                coerce=str
            )

        if 'specializations' not in self.fields:
            self.fields['specializations'] = forms.TypedMultipleChoiceField(
                choices=BrokerProfile.SPECIALIZATION_CHOICES,
                widget=forms.CheckboxSelectMultiple,
                label='Специализация',
                required=True,  # Оставляем обязательным
                coerce=str
            )

        # Устанавливаем начальные значения
        if self.instance and self.instance.pk:
            self.fields['services'].initial = self.instance.services or []
            self.fields['specializations'].initial = self.instance.specializations or []

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.services = self.cleaned_data.get('services', [])
        instance.specializations = self.cleaned_data.get('specializations', [])

        if commit:
            instance.save()
        return instance

class BrokerReviewForm(forms.ModelForm):
    class Meta:
        model = BrokerReview
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4}),
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5}),
        }