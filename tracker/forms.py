from django import forms
from .models import MarksRecord, Note, Reminder


class NicknameForm(forms.Form):
    nickname = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your Hunter name...',
            'class': 'form-control game-input',
            'autocomplete': 'off',
        }),
        label='Hunter Name'
    )

    def clean_nickname(self):
        name = self.cleaned_data['nickname'].strip()
        if len(name) < 2:
            raise forms.ValidationError("Name must be at least 2 characters.")
        return name


class MarksForm(forms.ModelForm):
    class Meta:
        model = MarksRecord
        fields = ['subject', 'marks_obtained', 'total_marks', 'topic']
        widgets = {
            'subject': forms.TextInput(attrs={
                'placeholder': 'e.g. Mathematics',
                'class': 'form-control game-input',
            }),
            'marks_obtained': forms.NumberInput(attrs={
                'placeholder': 'Marks obtained',
                'class': 'form-control game-input',
                'min': '0', 'step': '0.5',
            }),
            'total_marks': forms.NumberInput(attrs={
                'placeholder': 'Total marks',
                'class': 'form-control game-input',
                'min': '1', 'step': '0.5',
            }),
            'topic': forms.TextInput(attrs={
                'placeholder': 'Topic (optional)',
                'class': 'form-control game-input',
            }),
        }
        labels = {
            'subject': '⚔️ Subject',
            'marks_obtained': '📊 Marks Obtained',
            'total_marks': '🎯 Total Marks',
            'topic': '📖 Topic (optional)',
        }

    def clean(self):
        cleaned = super().clean()
        obtained = cleaned.get('marks_obtained')
        total = cleaned.get('total_marks')
        if obtained is not None and total is not None:
            if obtained > total:
                raise forms.ValidationError("Marks obtained cannot exceed total marks.")
            if total <= 0:
                raise forms.ValidationError("Total marks must be greater than 0.")
        return cleaned


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'subject', 'content']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Note title...',
                'class': 'form-control game-input',
            }),
            'subject': forms.TextInput(attrs={
                'placeholder': 'Subject (optional)',
                'class': 'form-control game-input',
            }),
            'content': forms.Textarea(attrs={
                'placeholder': 'Write your study notes here...',
                'class': 'form-control game-input',
                'rows': 5,
            }),
        }
        labels = {
            'title': '📝 Title',
            'subject': '📚 Subject',
            'content': '✍️ Content',
        }


class ReminderForm(forms.ModelForm):
    class Meta:
        model = Reminder
        fields = ['title', 'description', 'remind_at']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Reminder title...',
                'class': 'form-control game-input',
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Description (optional)',
                'class': 'form-control game-input',
                'rows': 3,
            }),
            'remind_at': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control game-input',
            }),
        }
        labels = {
            'title': '⏰ Reminder Title',
            'description': '📋 Description',
            'remind_at': '🗓️ Remind At',
        }
