from django import forms
from models import Package
from models import Project, ProjectCategory

class ProjectForm(forms.Form):

    choices = []   
    for package in Package.objects.all():
        choices.append((package.id, str(package)))

    package = forms.ChoiceField(choices=choices)
    username = forms.CharField(max_length=100)
    repository = forms.CharField(max_length=100)
    branch = forms.CharField(max_length=100)
    
    widget = forms.SelectMultiple(attrs =
            {'class': 'form-control chosen-select',
            'data-placeholder': 'select one or more project categories'})
    categories = forms.ModelMultipleChoiceField(required=False,
            queryset=ProjectCategory.objects.all(),
            widget = widget)

    def clean_package(self):
        id = self.cleaned_data['package']

        value = Package.objects.get(pk = id)
        return value

    def clean_username(self):
        return self.cleaned_data['username'].strip()

    def clean_repository(self):
        return self.cleaned_data['repository'].strip()

    def clean_branch(self):
        return self.cleaned_data['branch'].strip()

    def clean(self):
        cleaned_data = super(ProjectForm, self).clean()
        username = cleaned_data.get('username')
        repository = cleaned_data.get('repository')
        branch = cleaned_data.get('branch')

        if username and repository and branch:
            try:
                Project.objects.get(username__exact = username,
                        repository__exact = repository,
                        branch__exact = branch,
                        deleted = False)
                raise forms.ValidationError('Project already exists')
            except Project.DoesNotExist:
                pass
        return cleaned_data
