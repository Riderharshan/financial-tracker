from django.urls import path
from . import views
from .views import CustomLoginView

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('add-income/', views.add_income, name='add_income'),
    path('add-expense/', views.add_expense, name='add_expense'),
    path('set-budget/', views.set_budget, name='set_budget'),
    path('download-report/', views.download_report, name='download_report'),
    path('register/', views.register, name='register'),
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('delete/<str:model>/<int:pk>/', views.delete_transaction, name='delete_transaction'),
    path('edit/<str:model>/<int:pk>/', views.edit_transaction, name='edit_transaction'),
    path('profile/', views.profile, name='profile'),
    path('insights/', views.insights, name='insights'),
    path('settings/', views.settings_page, name='settings_page'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    
]