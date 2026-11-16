from django import forms


class ContactForm(forms.Form):
    TOPICS = [
        ("general", "General question"),
        ("data", "Data issue or correction"),
        ("education", "Education / research use"),
        ("partnership", "Partnership or data source"),
    ]
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    topic = forms.ChoiceField(choices=TOPICS)
    message = forms.CharField(widget=forms.Textarea, max_length=4000)
    # Honeypot: real visitors never see or fill this in; simple bots do.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    def clean_website(self):
        if self.cleaned_data["website"]:
            raise forms.ValidationError("Spam detected.")
        return ""
