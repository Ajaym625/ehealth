from django import forms

from shop.models import Product, Package, Image


class CheckProductsForm(forms.Form):
    aic = forms.CharField(max_length=9,
                          widget=forms.TextInput(attrs={
                              'class': 'form-control mb-3 border-primary',
                              'placeholder': "AIC"
                          }))


class CreateProductsForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        max_extra_fields = kwargs.pop('MAX_EXTRA_FIELDS')
        super(CreateProductsForm, self).__init__(*args, **kwargs)

        self.fields["active_substance"] = forms.CharField(label="Principio attivo", max_length=100,
                                                              widget=forms.TextInput(attrs={
                                                                  'class': 'form-control mb-3 border-primary',
                                                                  'placeholder': "Principio attivo"
                                                              }))

        for i in range(max_extra_fields):
            required = i == 0
            self.fields[f'excipient_{i}'] = forms.CharField(label="Eccipiente", required=required, max_length=100,
                                                              widget=forms.TextInput(attrs={
                                                                  'class': 'form-control mb-3 border-primary',
                                                                  'placeholder': "Eccipiente"
                                                              }))
        for i in range(max_extra_fields):
            required = i == 0
            self.fields[f'illness_{i}'] = forms.CharField(label="Malattia da curare", required=required, max_length=100,
                                                            widget=forms.TextInput(attrs={
                                                                'class': 'form-control mb-3 border-primary',
                                                                'placeholder': "Malattia da curare"
                                                            }))

    class Meta:
        model = Product

        exclude = ["slug", "active_substance", "excipients", "illnesses", "has_sponsor"]

        labels = {
            "aic": "Codice autorizzazione all'immissione in commercio (AIC)",
            "name": "Nome",
            "description": "Descrizione",
            "needs_prescription": "Prescrizione medica richiesta",
            "lot": "Lotto",
            "category": "Categoria",
            "excipient": "Eccipiente"

        }
        error_messages = {

        }

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
                                           'placeholder': labels['name']}),
            'aic': forms.TextInput( attrs={'class': 'form-control mb-3 border-primary',
                                           'placeholder': labels['aic']}),
            'description': forms.Textarea(attrs={'class': 'form-control mb-3 border-primary',
                                                 'placeholder': labels['description'], 'rows': 15, 'cols': 500}),


            'lot': forms.NumberInput(attrs={'class': 'form-control mb-3 border-primary',
                                            'placeholder': labels['lot']}),
            'category': forms.Select(attrs={'class': 'form-control mb-3 border-primary',
                                            'placeholder': labels['category']},
                                     ),
            'excipient': forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
                                                'placeholder': labels['excipient']}),

        }

    field_order = Meta.labels.keys()


class CreateProductsPackagesForm(forms.ModelForm):

    class Meta:
        model = Package

        exclude = ["product", "seller", "is_sponsored"]

        labels = {
            "type": "Tipo (compresse, bustine ecc.) ",
            "amount": "Quantità per tipo",
            "dosage": "Dosaggio (mg)",
            "price": "Prezzo Totale (IVA compresa)",
            "vat_percentage": "IVA (%)",
            "vat_price": "Prezzo IVA",
            "available_quantity": "Quantità disponibile",

        }
        error_messages = {

        }

        widgets = {
            'type': forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
                                           'placeholder': labels['type']}),
            'amount': forms.NumberInput( attrs={'class': 'form-control mb-3 border-primary',
                                                'placeholder': labels['amount']}),
            'dosage': forms.NumberInput(attrs={'class': 'form-control mb-3 border-primary',
                                               'placeholder': labels['dosage']}),

            'price': forms.NumberInput(attrs={'class': 'form-control mb-3 border-primary',
                                              'placeholder': labels['price']}),

            'vat_percentage': forms.NumberInput(attrs={'class': 'form-control mb-3 border-primary',
                                                       'placeholder': labels['vat_percentage']}),

            'vat_price': forms.NumberInput(attrs={'class': 'form-control mb-3 border-primary',
                                                  'placeholder': labels['vat_price']}),

            'available_quantity': forms.NumberInput(attrs={'class': 'form-control mb-3 border-primary',
                                                           'placeholder': labels['available_quantity']}),



        }


    field_order = Meta.labels.keys()


class CreateProductsImagesForm(forms.ModelForm):
    file = forms.FileField(label="Seleziona una o più immagini:", widget=forms.ClearableFileInput(attrs={'multiple': True}))

    class Meta:
        model = Image

        exclude = ["product", "is_main"]

        labels = {

        }
        error_messages = {

        }

        widgets = {

        }
