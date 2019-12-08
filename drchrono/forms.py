from django import forms


class CheckInForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    ssn = forms.CharField(max_length=150, required=False)


class DemographicForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    date_of_birth = forms.CharField(max_length=150, required=False)
    gender = forms.CharField(max_length=150, required=False)
    race = forms.CharField(max_length=150, required=False)
    ethnicity = forms.CharField(max_length=150, required=False)
    email = forms.CharField(max_length=150, required=False)
