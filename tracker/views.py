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
from django.contrib.auth.forms import PasswordChangeForm
from reportlab.graphics.shapes import Circle, String
from reportlab.platypus import *
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.graphics.shapes import Drawing, Circle, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from django.http import HttpResponse
from collections import defaultdict
import calendar
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker


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

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=30, leftMargin=30,
        topMargin=40, bottomMargin=30
    )

    elements = []
    styles = getSampleStyleSheet()

    # ---------- STYLES ----------
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        alignment=1,
        fontSize=22,
        textColor=colors.HexColor("#38bdf8"),
        spaceAfter=20
    )

    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        textColor=colors.HexColor("#38bdf8"),
        spaceAfter=10
    )

    normal_center = ParagraphStyle(
        'Center',
        parent=styles['Normal'],
        alignment=1,
        textColor=colors.grey
    )

    # ---------- TITLE ----------
    elements.append(Paragraph("Money Mafia Financial Report", title_style))
    elements.append(Paragraph("Generated Summary of Your Finances", normal_center))
    elements.append(Spacer(1, 20))

    # ---------- SUMMARY ----------
    elements.append(Paragraph("Financial Summary", heading_style))

    summary_data = [
        ["Total Income", f"₹ {total_income}"],
        ["Total Expense", f"₹ {total_expense}"],
        ["Balance", f"₹ {balance}"],
    ]

    summary_table = Table(summary_data, colWidths=[250, 200])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ('GRID', (0, 0), (-1, -1), 0.8, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 25))

    # ---------- MOTIVATIONAL SECTION ----------
    motivation_title = Paragraph(
        "Financial Insights & Motivation",
        ParagraphStyle(
            'MotivationTitle',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor("#38bdf8"),
            spaceAfter=12
        )
    )

    motivation_text = Paragraph(
        "Financial success is not about how much you earn, but how wisely you manage and grow your money. "
        "Consistent tracking of your income and expenses gives you clarity, control, and confidence in your financial journey. "
        "By making smart decisions today, you are building a stable and secure future for tomorrow. "
        "Remember, small savings and disciplined habits compound into significant wealth over time.",
        ParagraphStyle(
            'MotivationText',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            spaceAfter=10
        )
    )

    extra_text = Paragraph(
        "A well-planned financial strategy helps you avoid unnecessary stress and prepares you for unexpected situations. "
        "Whether it is saving for personal goals, investing for growth, or managing day-to-day expenses, "
        "every step you take towards financial discipline strengthens your independence and long-term stability.",
        ParagraphStyle(
            'ExtraText',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            spaceAfter=12
        )
    )

    bullet_points = [
        "Track your daily expenses to understand spending patterns",
    "Avoid impulsive purchases and focus on essential needs",
    "Invest consistently to grow your wealth over time",
    "Maintain a clear balance between income and expenses",
    "Build an emergency fund for financial security",
    "Set short-term and long-term financial goals",
    "Review your financial progress regularly",
    "Stay disciplined and committed to your financial plans",
    "Create and follow a monthly budget",
    "Save at least a small portion of your income every month",
    "Differentiate clearly between needs and wants",
    "Avoid unnecessary subscriptions and recurring expenses",
    "Plan your purchases in advance",
    "Compare prices before making buying decisions",
    "Use discounts and offers wisely, not impulsively",
    "Limit the use of credit cards and avoid debt traps"
    
    
    ]

    bullet_list = ListFlowable(
        [
            ListItem(
                Paragraph(point,
                    ParagraphStyle(
                        'BulletText',
                        parent=styles['Normal'],
                        fontSize=11,
                        leading=14
                    )
                )
            )
            for point in bullet_points
        ],
        bulletType='bullet',
        leftIndent=25
    )

    closing_text = Paragraph(
        "Stay focused, stay disciplined, and remember — every small step you take today leads to a financially stronger tomorrow."
        "Managing your money wisely is one of the most powerful skills you can develop in life. "
"By tracking your income and expenses regularly, you gain clarity and control over your financial decisions. "
"Saving consistently, even in small amounts, builds a strong foundation for future security and independence. "
"Discipline in spending helps you avoid unnecessary debt and keeps you focused on what truly matters. "
"Setting clear financial goals gives direction to your efforts and motivates you to stay committed. "
"Over time, these smart habits grow into lasting financial stability and confidence. "
"Remember, every smart choice you make today brings you closer to a secure and stress-free tomorrow.",
        ParagraphStyle(
            'ClosingText',
            parent=styles['Normal'],
            fontSize=11,
            leading=15,
            spaceBefore=12
        )
    )

    elements.append(KeepTogether([
        motivation_title,
        motivation_text,
        extra_text,
        bullet_list,
        closing_text,
        Spacer(1, 20)
    ]))

    elements.append(PageBreak())

    # ---------- CATEGORY DATA ----------
    category_data = defaultdict(float)
    for e in expenses:
        category_data[e.category] += e.amount

    # ---------- MONTHLY DATA ----------
    monthly_income = defaultdict(float)
    monthly_expense = defaultdict(float)

    for i in incomes:
        month = calendar.month_abbr[i.date.month]
        monthly_income[month] += i.amount

    for e in expenses:
        month = calendar.month_abbr[e.date.month]
        monthly_expense[month] += e.amount

    all_months = list(calendar.month_abbr)[1:]
    months = [m for m in all_months if monthly_income[m] > 0 or monthly_expense[m] > 0]

    income_data = [monthly_income[m] for m in months]
    expense_data = [monthly_expense[m] for m in months]

    # ---------- CHART SECTION ----------
    chart_section = []

    if category_data:
        chart_section.append(Paragraph("Expense Distribution (Category Wise)", heading_style))

        pie = Pie()
        pie.width = 200
        pie.height = 200

        values = list(category_data.values())
        labels = list(category_data.keys())
        total = sum(values)

        pie.data = values
        pie.labels = [
            f"{label} (₹{value:.0f}, {value/total*100:.1f}%)"
            for label, value in zip(labels, values)
        ]

        pie_draw = Drawing(400, 250)
        pie.x = 100
        pie.y = 20
        pie_draw.add(pie)

        chart_section.append(pie_draw)
        chart_section.append(Spacer(1, 20))

    if months:
        chart_section.append(Paragraph("Monthly Income vs Expense", heading_style))

        bar = VerticalBarChart()
        bar.x = 50
        bar.y = 50
        bar.height = 200
        bar.width = 300
        bar.data = [income_data, expense_data]
        bar.categoryAxis.categoryNames = months

        bar.valueAxis.valueMin = 0
        bar.valueAxis.valueMax = max(income_data + expense_data) * 1.2

        bar.bars[0].fillColor = colors.green
        bar.bars[1].fillColor = colors.red

        bar_draw = Drawing(400, 320)
        bar_draw.add(bar)

        legend = Legend()
        legend.x = 330
        legend.y = 200
        legend.colorNamePairs = [
            (colors.green, "Income"),
            (colors.red, "Expense"),
        ]
        bar_draw.add(legend)

        chart_section.append(bar_draw)

    if chart_section:
        elements.append(KeepTogether(chart_section))
        elements.append(Spacer(1, 20))

    elements.append(PageBreak())

    # ---------- LINE CHART ----------
    chart_section = []

    elements.append(Paragraph("Monthly Savings Trend", heading_style))

    all_months = list(calendar.month_abbr)[1:]

    monthly_savings = []
    for m in all_months:
        income = monthly_income[m]
        expense = monthly_expense[m]
        monthly_savings.append(income - expense)

    line_data = [[(i + 1, monthly_savings[i]) for i in range(len(all_months))]]

    line = LinePlot()
    line.x = 50
    line.y = 30
    line.height = 180
    line.width = 400
    line.data = line_data

    line.xValueAxis.valueMin = 1
    line.xValueAxis.valueMax = 12
    line.xValueAxis.valueSteps = list(range(1, 13))
    line.xValueAxis.labelTextFormat = lambda x: all_months[int(x) - 1]

    line.yValueAxis.valueMin = min(0, min(monthly_savings))
    line.yValueAxis.valueMax = max(monthly_savings) * 1.2 if max(monthly_savings) != 0 else 1000

    line.lines[0].strokeColor = colors.HexColor("#22c55e")
    line.lines[0].strokeWidth = 2

    line.lines[0].symbol = makeMarker('Circle')
    line.lines[0].symbol.size = 4
    line.lines[0].symbol.fillColor = colors.white
    line.lines[0].symbol.strokeColor = colors.HexColor("#22c55e")

    line_draw = Drawing(500, 250)
    line_draw.add(line)
    from reportlab.graphics.shapes import String

    for i, val in enumerate(monthly_savings):
       x = 50 + (i * (400 / 12))
       y = 30 + (val / line.yValueAxis.valueMax * 180)

       line_draw.add(String(
           x,
           y + 5,
           str(int(val)),
          fontSize=7
       ))
    elements.append(line_draw)
    elements.append(Spacer(1, 10))

    # ---------- BUBBLE CHART ----------
    elements.append(Paragraph("Category Expense Bubble View", heading_style))

    bubble_draw = Drawing(500, 350)
    categories = list(category_data.keys())
    values = list(category_data.values())

    max_value = max(values) if values else 1

    x_positions = [80, 200, 320, 440]
    y_positions = [200, 120, 40]

    index = 0

    for i, value in enumerate(values):
        if index >= len(x_positions) * len(y_positions):
            break

        x = x_positions[index % 4]
        y = y_positions[index // 4]

        radius = 15 + (value / max_value) * 35

        bubble = Circle(x, y, radius)
        bubble.fillColor = colors.HexColor("#38bdf8")
        bubble.strokeColor = colors.white
        bubble.strokeWidth = 1

        bubble_draw.add(bubble)

        # Category name (slightly above center)
        bubble_draw.add(String(
            x,
            y + 5,
            categories[i],
            fontSize=7,
            textAnchor="middle"
        ))

        # Value (below category)
        bubble_draw.add(String(
           x,
           y - 8,
           f"₹{int(value)}",
           fontSize=7,
           textAnchor="middle"
        ))

        index += 1

    elements.append(bubble_draw)
    elements.append(Spacer(1, 20))
    elements.append(PageBreak())
    # ---------- INCOME TABLE ----------
    elements.append(Paragraph("Income Details", heading_style))

    income_table_data = [["Date", "Category", "Amount"]]
    for i in incomes:
        income_table_data.append([str(i.date), i.category, f"₹ {i.amount}"])

    income_table = Table(income_table_data, repeatRows=1)
    income_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.green),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))

    elements.append(income_table)
    elements.append(Spacer(1, 30))

    # ---------- EXPENSE TABLE ----------
    elements.append(Paragraph("Expense Details", heading_style))

    expense_table_data = [["Date", "Category", "Amount"]]
    for e in expenses:
        expense_table_data.append([str(e.date), e.category, f"₹ {e.amount}"])

    expense_table = Table(expense_table_data, repeatRows=1)
    expense_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.red),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))

    elements.append(expense_table)

    # ---------- BUILD ----------
    doc.build(elements)

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

    groceries_trend = []
    personal_care_trend = []
    transport_trend = []
    travel_trend = []
    rent_trend = []
    internet_trend = []
    loan_trend = []
    shopping_trend = []
    entertainment_trend = []
    health_trend = []
    education_trend = []
    bike_service_trend = []

    for i in range(1,13):

       groceries = expenses.filter(date__month=i, category='Groceries').aggregate(Sum('amount'))['amount__sum'] or 0
       personal = expenses.filter(date__month=i, category='Personal Care').aggregate(Sum('amount'))['amount__sum'] or 0
       transport = expenses.filter(date__month=i, category='Transport').aggregate(Sum('amount'))['amount__sum'] or 0
       travel = expenses.filter(date__month=i, category='Travel').aggregate(Sum('amount'))['amount__sum'] or 0
       rent = expenses.filter(date__month=i, category='Rent').aggregate(Sum('amount'))['amount__sum'] or 0
       internet = expenses.filter(date__month=i, category='Internet / Mobile Recharge').aggregate(Sum('amount'))['amount__sum'] or 0
       loan = expenses.filter(date__month=i, category='Loan').aggregate(Sum('amount'))['amount__sum'] or 0
       shopping = expenses.filter(date__month=i, category='Shopping').aggregate(Sum('amount'))['amount__sum'] or 0
       entertainment = expenses.filter(date__month=i, category='Entertainment').aggregate(Sum('amount'))['amount__sum'] or 0
       health = expenses.filter(date__month=i, category='Health / Medical').aggregate(Sum('amount'))['amount__sum'] or 0
       education = expenses.filter(date__month=i, category='Education').aggregate(Sum('amount'))['amount__sum'] or 0
       bike_service = expenses.filter(date__month=i, category='Bike Service').aggregate(Sum('amount'))['amount__sum'] or 0

       groceries_trend.append(float(groceries))
       personal_care_trend.append(float(personal))
       transport_trend.append(float(transport))
       travel_trend.append(float(travel))
       rent_trend.append(float(rent))
       internet_trend.append(float(internet))
       loan_trend.append(float(loan))
       shopping_trend.append(float(shopping))
       entertainment_trend.append(float(entertainment))
       health_trend.append(float(health))
       education_trend.append(float(education))
       bike_service_trend.append(float(bike_service))

        # -------- PIE CHART CATEGORY DATA (DASHBOARD LOGIC) --------

    # -------- CATEGORY DATA BY MONTH (for pie chart dropdown) --------

    category_month_data = defaultdict(lambda: [0]*12)

    for e in expenses:
        month_index = e.date.month - 1
        category_month_data[e.category][month_index] += float(e.amount)

    category_month_data = dict(category_month_data)

    # -------- WEEKLY SPENDING DATA --------

    weekly_spending = {}

    for i in range(1,13):

       week = [0,0,0,0,0,0,0]

       month_expenses = expenses.filter(date__month=i)

       for e in month_expenses:

           day = e.date.weekday()   # Monday=0 ... Sunday=6
           week[day] += float(e.amount)

       weekly_spending[i-1] = week

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

    "weekly_spending": json.dumps(weekly_spending),
    "wealth_growth": json.dumps(savings),

    "top_categories": json.dumps(categories),
    "top_amounts": json.dumps(category_spending),

    "food_trend": json.dumps(food_trend),
    "fuel_trend": json.dumps(fuel_trend),
    "bills_trend": json.dumps(bills_trend),
     
      # 🔴 ADD THESE
    "groceries_trend": json.dumps(groceries_trend),
    "personal_care_trend": json.dumps(personal_care_trend),
    "transport_trend": json.dumps(transport_trend),
    "travel_trend": json.dumps(travel_trend),
    "rent_trend": json.dumps(rent_trend),
    "internet_trend": json.dumps(internet_trend),
    "loan_trend": json.dumps(loan_trend),
    "shopping_trend": json.dumps(shopping_trend),
    "entertainment_trend": json.dumps(entertainment_trend),
    "health_trend": json.dumps(health_trend),
    "education_trend": json.dumps(education_trend),
    "bike_service_trend": json.dumps(bike_service_trend),

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




from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['old_password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter old password'
        })

        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter new password'
        })

        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })


# 🔥 FINAL VIEW (THIS WILL FIX YOUR ISSUE)
class CustomPasswordChangeView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'change_password.html'
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy('profile')

    success_message = "Password changed successfully 🎉"