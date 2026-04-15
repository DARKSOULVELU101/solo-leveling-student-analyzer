from django.urls import path
from . import views

urlpatterns = [
    path('', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('marks/add/', views.add_marks, name='add_marks'),
    path('marks/', views.marks_list, name='marks_list'),
    path('analytics/', views.analytics, name='analytics'),
    path('notes/', views.notes, name='notes'),
    path('notes/edit/<int:note_id>/', views.edit_note, name='edit_note'),
    path('notes/delete/<int:note_id>/', views.delete_note, name='delete_note'),
    path('reminders/', views.reminders, name='reminders'),
    path('reminders/complete/<int:reminder_id>/', views.complete_reminder, name='complete_reminder'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('export/', views.export_excel, name='export_excel'),
    path('logout/', views.logout_view, name='logout'),
]
