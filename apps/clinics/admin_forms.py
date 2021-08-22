from ckeditor.fields import RichTextFormField
from django.forms import forms


class ImportServicePricesForm(forms.Form):
    # csv_file = forms.FileField()
    prices = RichTextFormField(
        required=True, help_text="Одна строка = 1 название цены + число.\n" "см пример ниже"
    )
    prices_example = RichTextFormField(
        required=False,
        disabled=True,
        initial="первичный прием 1100 руб.\n" "повторный прием 1000 руб",
    )
