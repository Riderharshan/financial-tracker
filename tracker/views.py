from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Income, Expense, Budget
from .forms import IncomeForm, ExpenseForm, BudgetForm
from collections import defaultdict
import json
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import pagesizes
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
import calendar
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, KeepTogether, PageBreak
)
from reportlab.lib import pagesizes, colors
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.pdfgen import canvas
from django.contrib.auth import login
from .forms import RegisterForm
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from .models import UserProfile
from datetime import datetime
from collections import defaultdict
import json
from django.db.models import Sum
from .models import Income, Expense, Budget
from .models import Profile


@login_required
def dashboard(request):

    selected_month = request.GET.get("month")

    if not selected_month:
        selected_month = datetime.now().month
    elif selected_month != "all":
        selected_month = int(selected_month)

    incomes = Income.objects.filter(user=request.user)
    expenses = Expense.objects.filter(user=request.user)

    if selected_month != "all":
        incomes = incomes.filter(date__month=selected_month)
        expenses = expenses.filter(date__month=selected_month)

    total_income = sum(i.amount for i in incomes)
    total_expense = sum(e.amount for e in expenses)

    budget = None
    alert = None
    budget_percent = 0

    if selected_month != "all":
      budget = Budget.objects.filter(user=request.user, month=selected_month).first()

    if budget:
        if budget.monthly_limit > 0:
            budget_percent = (total_expense / float(budget.monthly_limit)) * 100

        if total_expense >= budget.monthly_limit:
            alert = f"⚠ Budget Exceeded! Limit: ₹{budget.monthly_limit}"

    transactions = []

    for i in incomes:
        transactions.append({
            'id': i.id,
            'model': 'income',
            'date': i.date,
            'category': i.category,
            'amount': i.amount,
            'type': 'Income'
        })

    for e in expenses:
        transactions.append({
            'id': e.id,
            'model': 'expense',
            'date': e.date,
            'category': e.category,
            'amount': e.amount,
            'type': 'Expense'
        })

    transactions.sort(key=lambda x: x['date'], reverse=True)

    category_data = defaultdict(float)

    for e in expenses:
        category_data[e.category] += e.amount

    categories = list(category_data.keys())
    amounts = list(category_data.values())

    monthly_income = defaultdict(float)
    monthly_expense = defaultdict(float)

    for i in incomes:
        month = i.date.strftime("%b")
        monthly_income[month] += i.amount

    for e in expenses:
        month = e.date.strftime("%b")
        monthly_expense[month] += e.amount

    months = sorted(set(list(monthly_income.keys()) + list(monthly_expense.keys())))

    income_data = [monthly_income[m] for m in months]
    expense_data = [monthly_expense[m] for m in months]

    context = {
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': total_income - total_expense,
        'transactions': transactions,
        'categories': json.dumps(categories),
        'amounts': json.dumps(amounts),
        'alert': alert,
        'months': json.dumps(months),
        'income_data': json.dumps(income_data),
        'expense_data': json.dumps(expense_data),
        'selected_month': selected_month,
        'budget': budget,
        'budget_percent': budget_percent
    }

    return render(request, 'dashboard.html', context)


@login_required
def add_income(request):
    form = IncomeForm(request.POST or None)

    if form.is_valid():
        income = form.save(commit=False)
        income.user = request.user
        income.save()
        return redirect('dashboard')

    return render(request, 'add_income.html', {'form': form})


@login_required
def add_expense(request):
    form = ExpenseForm(request.POST or None)

    if form.is_valid():
        expense = form.save(commit=False)
        expense.user = request.user
        expense.save()
        return redirect('dashboard')

    return render(request, 'add_expense.html', {'form': form})


@login_required

def set_budget(request):
    if request.method == "POST":
        month = request.POST.get("month")
        limit = request.POST.get("monthly_limit")

        Budget.objects.update_or_create(
            month=month,
            defaults={"monthly_limit": limit}
        )

        return redirect("dashboard")

    return render(request, "set_budget.html")


@login_required
def download_report(request):

    incomes = Income.objects.filter(user=request.user)
    expenses = Expense.objects.filter(user=request.user)

    total_income = sum(i.amount for i in incomes)
    total_expense = sum(e.amount for e in expenses)
    balance = total_income - total_expense

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="MoneyMafia_Report.pdf"'

    doc = SimpleDocTemplate(response, pagesize=pagesizes.A4)
    elements = []
    styles = getSampleStyleSheet()

    def add_background(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#989898"))
        canvas.rect(0, 0, pagesizes.A4[0], pagesizes.A4[1], fill=1)
        canvas.restoreState()

    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.white,
        alignment=1,
        spaceAfter=25
    )

    elements.append(Paragraph("Money Mafia Financial Report", title_style))
    elements.append(Spacer(1, 20))

    summary_data = [
        ["Total Income", f"₹ {total_income}"],
        ["Total Expense", f"₹ {total_expense}"],
        ["Balance", f"₹ {balance}"],
    ]

    summary_table = Table(summary_data, colWidths=[250, 180])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor("#334155")),
        ('FONTSIZE', (0, 0), (-1, -1), 13),
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 30))

    category_data = defaultdict(float)
    for e in expenses:
        category_data[e.category] += e.amount

    monthly_income = defaultdict(float)
    monthly_expense = defaultdict(float)

    for i in incomes:
        month = calendar.month_abbr[i.date.month]
        monthly_income[month] += i.amount

    for e in expenses:
        month = calendar.month_abbr[e.date.month]
        monthly_expense[month] += e.amount

    months = sorted(set(list(monthly_income.keys()) + list(monthly_expense.keys())))

    if months:
        income_data = [monthly_income[m] for m in months]
        expense_data = [monthly_expense[m] for m in months]

        drawing = Drawing(500, 300)

        if category_data:
            pie = Pie()
            pie.x = 40
            pie.y = 60
            pie.width = 170
            pie.height = 170
            pie.data = list(category_data.values())
            pie.labels = list(category_data.keys())
            drawing.add(pie)

        bar = VerticalBarChart()
        bar.x = 260
        bar.y = 60
        bar.height = 170
        bar.width = 200
        bar.data = [income_data, expense_data]
        bar.categoryAxis.categoryNames = months

        drawing.add(bar)
        elements.append(drawing)

    elements.append(PageBreak())

    data = [["Date", "Category", "Amount", "Type"]]

    for i in incomes:
        data.append([str(i.date), i.category, f"₹ {i.amount}", "Income"])

    for e in expenses:
        data.append([str(e.date), e.category, f"₹ {e.amount}", "Expense"])

    table = Table(data, repeatRows=1)

    elements.append(table)

    doc.build(elements, onFirstPage=add_background, onLaterPages=add_background)

    return response


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


class CustomLoginView(LoginView):
    def form_valid(self, form):
        messages.success(self.request, "Logged in successfully!")
        return super().form_valid(form)


from django.shortcuts import get_object_or_404


@login_required
def delete_transaction(request, model, pk):

    if model == "income":
        obj = get_object_or_404(Income, pk=pk, user=request.user)
    else:
        obj = get_object_or_404(Expense, pk=pk, user=request.user)

    obj.delete()
    return redirect('dashboard')


@login_required
def edit_transaction(request, model, pk):

    if model == "income":
        obj = get_object_or_404(Income, pk=pk, user=request.user)
        form_class = IncomeForm
    else:
        obj = get_object_or_404(Expense, pk=pk, user=request.user)
        form_class = ExpenseForm

    if request.method == "POST":
        form = form_class(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = form_class(instance=obj)

    return render(request, "edit_transaction.html", {"form": form})


@login_required
def profile(request):

    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":

        request.user.username = request.POST.get('username')
        request.user.email = request.POST.get('email')
        request.user.save()

        profile.phone_number = request.POST.get('phone_number')

        if 'profile_image' in request.FILES:
            profile.profile_image = request.FILES['profile_image']

        profile.save()

        messages.success(request, "Profile updated successfully!")

        return redirect('profile')

    return render(request, 'profile.html', {'profile': profile})


@login_required
def insights(request):

    incomes = Income.objects.filter(user=request.user)
    expenses = Expense.objects.filter(user=request.user)

    # Months
    months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

    # Monthly income
    monthly_income = []
    monthly_expense = []
    savings = []

    for i in range(1,13):

        income = incomes.filter(date__month=i).aggregate(Sum('amount'))['amount__sum'] or 0
        expense = expenses.filter(date__month=i).aggregate(Sum('amount'))['amount__sum'] or 0

        monthly_income.append(float(income))
        monthly_expense.append(float(expense))

        savings.append(float(income - expense))


    # Category totals
    categories = ['Food','Fuel / Petrol','Loan','Health / Medical','Internet / Mobile Recharge','Entertainment','Bike Service','Travel']
    category_spending = []

    for c in categories:
        total = expenses.filter(category=c).aggregate(Sum('amount'))['amount__sum'] or 0
        category_spending.append(float(total))


    # -------- CATEGORY MONTHLY TRENDS --------

    food_trend = []
    fuel_trend = []
    bills_trend = []

    for i in range(1,13):

        food = expenses.filter(date__month=i, category='Food').aggregate(Sum('amount'))['amount__sum'] or 0
        fuel = expenses.filter(date__month=i, category='Fuel / Petrol').aggregate(Sum('amount'))['amount__sum'] or 0
        bills = expenses.filter(date__month=i, category='Internet / Mobile Recharge').aggregate(Sum('amount'))['amount__sum'] or 0

        food_trend.append(float(food))
        fuel_trend.append(float(fuel))
        bills_trend.append(float(bills))


    # -------- MONTHLY BUDGET DATA (FIXED) --------

    monthly_budget_limits = []

    for i in range(1,13):

        budget = Budget.objects.filter(
            user=request.user,
            month=i
        ).first()

        if budget:
            monthly_budget_limits.append(float(budget.monthly_limit))
        else:
            monthly_budget_limits.append(0)
    # -------- EXTRA CATEGORY TRENDS (FOR PIE CHART) --------

    groceries_trend = [0]*12
    personal_care_trend = [0]*12
    transport_trend = [0]*12
    travel_trend = [0]*12
    rent_trend = [0]*12
    internet_trend = [0]*12
    loan_trend = [0]*12
    shopping_trend = [0]*12
    entertainment_trend = [0]*12
    health_trend = [0]*12
    education_trend = [0]*12
    bike_service_trend = [0]*12

        # -------- PIE CHART CATEGORY DATA (DASHBOARD LOGIC) --------

    # -------- CATEGORY DATA BY MONTH (for pie chart dropdown) --------

    category_month_data = defaultdict(lambda: [0]*12)

    for e in expenses:
        month_index = e.date.month - 1
        category_month_data[e.category][month_index] += float(e.amount)

    category_month_data = dict(category_month_data)

    context = {

    "months": json.dumps(months),
    "savings": json.dumps(savings),

    "income_data": json.dumps(monthly_income),
    "expense_data": json.dumps(monthly_expense),

    "categories": json.dumps(categories),
    "category_spending": json.dumps(category_spending),

    
    "category_month_data": json.dumps(category_month_data),

    "income_expense_ratio": json.dumps([
        sum(monthly_expense),
        sum(savings)
    ]),

    "weekly_spending": json.dumps([1200,1500,900,2000,800,2500,1400]),

    "wealth_growth": json.dumps(savings),

    "top_categories": json.dumps(categories),
    "top_amounts": json.dumps(category_spending),

    "food_trend": json.dumps(food_trend),
    "fuel_trend": json.dumps(fuel_trend),
    "bills_trend": json.dumps(bills_trend),

    "budget_limits": json.dumps(monthly_budget_limits)
}

    return render(request,'tracker/insights.html',context)

@login_required
def settings_page(request):
    return render(request,'settings.html')




@login_required
def edit_profile(request):

    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":

        username = request.POST.get("username")
        email = request.POST.get("email")
        phone = request.POST.get("phone_number")

        request.user.username = username
        request.user.email = email
        request.user.save()

        profile.phone_number = phone

        if 'profile_image' in request.FILES:
            profile.profile_image = request.FILES['profile_image']

        profile.save()

        return redirect("profile")

    return render(request, "edit_profile.html", {"profile": profile})