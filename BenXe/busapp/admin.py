from django.contrib import admin
from django.utils.html import mark_safe
from .models import User, TransportCompany, Buses, Payment
from ckeditor_uploader.widgets import CKEditorUploadingWidget

# class ScheduleAdmin(admin.ModelAdmin):
#     list_display =


class TransportCompanyAdmin(admin.ModelAdmin):
    class Media:
        css ={
            'all' : ('/static/css/main.css')
        }

    list_display = ["name"]
    readonly_fields = ["image"]

    def image(self, transportcompany):
        return mark_safe("<img src='/static/{img_url}' alt='{alt}' />"
                         .format(img_url=transportcompany.avatar.name, alt=transportcompany.name, width="120"))


admin.site.register(User)
admin.site.register(TransportCompany, TransportCompanyAdmin)
admin.site.register(Buses)
admin.site.register(Payment)

