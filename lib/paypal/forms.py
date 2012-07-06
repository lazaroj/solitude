from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django import forms

from lib.buyers.models import Buyer
from lib.paypal.constants import PAYPAL_CURRENCIES
from lib.sellers.models import Seller
from lib.transactions.models import PaypalTransaction

from solitude.base import get_object_or_404


class ArgForm(forms.Form):

    def args(self):
        return [self.cleaned_data.get(k) for k in self._args]

    def kwargs(self):
        return dict([(k, self.cleaned_data.get(k)) for k in self._kwargs])


class PreapprovalValidation(ArgForm):
    start = forms.DateField()
    end = forms.DateField()
    return_url = forms.URLField()
    cancel_url = forms.URLField()
    uuid = forms.ModelChoiceField(queryset=Buyer.objects.all(),
                                  to_field_name='uuid')

    _args = ('start', 'end', 'return_url', 'cancel_url')


class MissingModelField(forms.ModelChoiceField):
    """
    This is a model choice field that allows values that does not exist.
    It will try and do a lookup on the object and if it fails, just set it
    to None.
    """
    def to_python(self, *args, **kwargs):
        try:
            return super(MissingModelField, self).to_python(*args, **kwargs)
        except forms.ValidationError:
            pass


class PayValidation(ArgForm):
    seller = forms.ModelChoiceField(queryset=Seller.objects.all(),
                                    to_field_name='uuid')
    buyer = MissingModelField(queryset=Buyer.objects.all(),
                                     to_field_name='uuid', required=False)
    # Note these amounts apply to all currencies.
    amount = forms.DecimalField(min_value=Decimal('0.1'),
                                max_value=Decimal('5000'))
    return_url = forms.URLField()
    cancel_url = forms.URLField()
    ipn_url = forms.URLField()
    currency = forms.ChoiceField(choices=[(c, c) for c in
                                          PAYPAL_CURRENCIES.keys()])
    memo = forms.CharField()
    uuid = forms.CharField(required=False)

    _args = ('seller_email', 'amount', 'ipn_url', 'cancel_url', 'return_url')
    _kwargs = ('currency', 'preapproval', 'memo', 'uuid')

    def clean_seller(self):
        seller = self.cleaned_data['seller']
        self.cleaned_data['seller_email'] = ''
        try:
            self.cleaned_data['seller_email'] = seller.paypal.paypal_id
        except ObjectDoesNotExist:
            pass
        if not self.cleaned_data['seller_email']:
            raise forms.ValidationError('No seller email found.')
        return seller

    def clean_buyer(self):
        buyer = self.cleaned_data['buyer']
        self.cleaned_data['preapproval'] = ''
        try:
            self.cleaned_data['preapproval'] = buyer.paypal.key
        except (AttributeError, ObjectDoesNotExist):
            pass
        return buyer

    def clean_uuid(self):
        uuid = self.cleaned_data['uuid']
        if PaypalTransaction.objects.filter(uuid=uuid).exists():
            raise forms.ValidationError('Unique uuid needed.')
        return uuid


class GetPermissionURL(ArgForm):
    url = forms.URLField()
    scope = forms.CharField()

    _args = ('url', 'scope')


class CheckPermission(ArgForm):
    token = forms.CharField()
    permissions = forms.CharField()

    _args = ('token', 'permissions')


class GetPermissionToken(ArgForm):
    token = forms.CharField()
    code = forms.CharField()

    _args = ('token', 'code')


class KeyValidation(forms.Form):
    pay_key = forms.CharField(required=False)
    uuid = forms.CharField(required=False)

    def clean(self):
        pay_key = self.cleaned_data.get('pay_key', '')
        uuid = self.cleaned_data.get('uuid', '')
        if not pay_key and not uuid:
            raise forms.ValidationError('A pay_key or a uuid is required.')
        elif pay_key and uuid:
            raise forms.ValidationError('Cannot specify pay_key and uuid.')
        return self.cleaned_data

    def args(self):
        pay_key = self.cleaned_data.get('pay_key', '')
        if not pay_key:
            uuid = get_object_or_404(PaypalTransaction,
                                     uuid=self.cleaned_data['uuid'])
            pay_key = uuid.pay_key
        return [pay_key]


class GetPersonal(ArgForm):
    token = forms.CharField()

    _args = ('token',)


class IPNForm(forms.Form):
    data = forms.CharField(required=True)