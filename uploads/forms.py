from pathlib import Path

from django import forms

from .choices import MAX_UPLOAD_SIZE


class CandidateImportForm(forms.Form):
    file = forms.FileField(
        label="Excel file",
        help_text="Upload an .xlsx file up to 2 MB.",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".xlsx",
            }
        ),
    )

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]

        if Path(uploaded_file.name).suffix.lower() != ".xlsx":
            raise forms.ValidationError("Please upload an .xlsx file.")

        if uploaded_file.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError("The Excel file must be 2 MB or smaller.")

        return uploaded_file
