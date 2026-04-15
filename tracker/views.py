from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Max, Min, Count
from django.http import JsonResponse, HttpResponse
import pandas as pd
import os
from datetime import date, datetime
from pathlib import Path

from .models import StudentProfile, MarksRecord, Note, Reminder
from .forms import NicknameForm, MarksForm, NoteForm, ReminderForm

EXCEL_FILE = Path(__file__).resolve().parent.parent / 'student_data.xlsx'


# ─── Core Game Logic ──────────────────────────────────────────────────────────

def calculate_xp(percentage):
    """Returns XP based on percentage score."""
    return int(percentage * 10)


def get_rank(level):
    """Returns rank label based on level."""
    if level <= 2:
        return 'E'
    elif level <= 4:
        return 'D'
    elif level <= 6:
        return 'C'
    elif level <= 8:
        return 'B'
    elif level == 9:
        return 'A'
    return 'S'


def get_suggestion(percentage, subject):
    """Returns personalized improvement suggestion."""
    if percentage < 40:
        return (f"⚠️ Critical: Master the basics of {subject}. "
                f"Watch video tutorials and solve 10 basic problems daily. "
                f"Don't skip — consistent practice will rebuild your foundation!")
    elif percentage < 60:
        return (f"📚 Keep going! Practice {subject} for 30 mins daily. "
                f"Focus on common question patterns and revise weak areas. "
                f"You're on your way up!")
    elif percentage < 80:
        return (f"🌟 Great progress in {subject}! Attempt advanced problems. "
                f"Time yourself during practice to build exam speed. "
                f"You're close to mastery!")
    else:
        return (f"🏆 Excellent work in {subject}! Maintain your streak. "
                f"Help 2 classmates to reinforce your understanding and deepen your mastery!")


def get_grade(percentage):
    """Returns letter grade from percentage."""
    if percentage >= 90:
        return 'A+'
    elif percentage >= 80:
        return 'A'
    elif percentage >= 70:
        return 'B'
    elif percentage >= 60:
        return 'C'
    elif percentage >= 40:
        return 'D'
    return 'F'


def update_streak(student):
    """Updates the daily streak counter."""
    today = date.today()
    if student.last_activity_date is None:
        student.streak = 1
    elif student.last_activity_date == today:
        pass  # Same day, no change
    elif (today - student.last_activity_date).days == 1:
        student.streak += 1
    else:
        student.streak = 1
    student.last_activity_date = today
    student.save()


def add_xp(student, xp_amount):
    """Adds XP and handles level-ups. Returns True if leveled up."""
    old_level = student.level
    student.xp += xp_amount
    student.level = max(1, student.xp // 500) + 1
    student.level = min(student.level, 10)
    leveled_up = student.level > old_level
    student.save()
    return leveled_up


# ─── Excel Handling ───────────────────────────────────────────────────────────

def ensure_excel_file():
    """Creates Excel file with headers if it doesn't exist."""
    if not EXCEL_FILE.exists():
        df = pd.DataFrame(columns=[
            'Nickname', 'Subject', 'Marks Obtained', 'Total Marks',
            'Percentage', 'Grade', 'Date', 'Topic', 'Suggestion Given'
        ])
        df.to_excel(EXCEL_FILE, index=False)


def save_to_excel(student, marks_record, suggestion):
    """Appends a marks record to the Excel file."""
    ensure_excel_file()
    try:
        df = pd.read_excel(EXCEL_FILE)
    except Exception:
        df = pd.DataFrame(columns=[
            'Nickname', 'Subject', 'Marks Obtained', 'Total Marks',
            'Percentage', 'Grade', 'Date', 'Topic', 'Suggestion Given'
        ])
    new_row = {
        'Nickname': student.nickname,
        'Subject': marks_record.subject,
        'Marks Obtained': marks_record.marks_obtained,
        'Total Marks': marks_record.total_marks,
        'Percentage': round(marks_record.percentage, 2),
        'Grade': marks_record.grade,
        'Date': marks_record.date_added.strftime('%Y-%m-%d %H:%M'),
        'Topic': marks_record.topic or '',
        'Suggestion Given': suggestion,
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_excel(EXCEL_FILE, index=False)


def get_trend_data(student):
    """Reads historical data from Excel for trend analysis."""
    ensure_excel_file()
    try:
        df = pd.read_excel(EXCEL_FILE)
        student_df = df[df['Nickname'] == student.nickname]
        return student_df.to_dict('records')
    except Exception:
        return []


# ─── Session Helpers ──────────────────────────────────────────────────────────

def get_student_from_session(request):
    """Returns StudentProfile or None from session."""
    nickname = request.session.get('nickname')
    if nickname:
        try:
            return StudentProfile.objects.get(nickname=nickname)
        except StudentProfile.DoesNotExist:
            pass
    return None


def require_student(view_func):
    """Decorator: redirect to register if no student in session."""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        student = get_student_from_session(request)
        if not student:
            return redirect('register')
        return view_func(request, *args, student=student, **kwargs)
    return wrapper


# ─── Views ────────────────────────────────────────────────────────────────────

def register(request):
    """Nickname registration / welcome page."""
    if get_student_from_session(request):
        return redirect('dashboard')

    form = NicknameForm()
    if request.method == 'POST':
        form = NicknameForm(request.POST)
        if form.is_valid():
            nickname = form.cleaned_data['nickname']
            student, created = StudentProfile.objects.get_or_create(nickname=nickname)
            request.session['nickname'] = nickname
            request.session.modified = True
            if created:
                messages.success(request, f"🎮 Welcome, Hunter {nickname}! Your journey begins!")
            else:
                messages.info(request, f"⚔️ Welcome back, {nickname}! Continue your quest!")
            return redirect('dashboard')

    return render(request, 'tracker/register.html', {'form': form})


@require_student
def dashboard(request, student=None):
    """Main dashboard."""
    recent_marks = MarksRecord.objects.filter(student=student)[:5]
    upcoming_reminders = Reminder.objects.filter(
        student=student, is_complete=False, remind_at__gte=timezone.now()
    )[:3]
    recent_notes = Note.objects.filter(student=student)[:3]

    # Subject averages
    subject_avgs = (
        MarksRecord.objects.filter(student=student)
        .values('subject')
        .annotate(avg=Avg('percentage'), count=Count('id'))
        .order_by('-avg')
    )
    overall_avg = MarksRecord.objects.filter(student=student).aggregate(avg=Avg('percentage'))['avg'] or 0

    leveled_up = request.session.pop('leveled_up', False)
    new_rank = request.session.pop('new_rank', None)

    xp_in_level = student.xp % 500
    xp_needed = 500

    return render(request, 'tracker/dashboard.html', {
        'student': student,
        'recent_marks': recent_marks,
        'upcoming_reminders': upcoming_reminders,
        'recent_notes': recent_notes,
        'subject_avgs': subject_avgs,
        'overall_avg': round(overall_avg, 1),
        'leveled_up': leveled_up,
        'new_rank': new_rank,
        'xp_in_level': xp_in_level,
        'xp_needed': xp_needed,
        'rank': student.get_rank(),
    })


@require_student
def add_marks(request, student=None):
    """Add a new marks record."""
    form = MarksForm()
    if request.method == 'POST':
        form = MarksForm(request.POST)
        if form.is_valid():
            marks = form.save(commit=False)
            marks.student = student
            marks.percentage = (marks.marks_obtained / marks.total_marks) * 100
            marks.grade = get_grade(marks.percentage)
            marks.suggestion = get_suggestion(marks.percentage, marks.subject)
            xp = calculate_xp(marks.percentage)
            marks.xp_earned = xp
            marks.save()

            save_to_excel(student, marks, marks.suggestion)

            leveled_up = add_xp(student, xp)
            update_streak(student)

            if leveled_up:
                request.session['leveled_up'] = True
                request.session['new_rank'] = student.get_rank()

            messages.success(
                request,
                f"✅ Marks recorded! +{xp} XP earned! Grade: {marks.grade}"
            )
            return redirect('dashboard')

    return render(request, 'tracker/add_marks.html', {'form': form, 'student': student})


@require_student
def marks_list(request, student=None):
    """All marks records with subject filter."""
    subject_filter = request.GET.get('subject', '')
    marks = MarksRecord.objects.filter(student=student)
    if subject_filter:
        marks = marks.filter(subject__icontains=subject_filter)

    subjects = MarksRecord.objects.filter(student=student).values_list('subject', flat=True).distinct()
    return render(request, 'tracker/marks_list.html', {
        'marks': marks,
        'student': student,
        'subjects': subjects,
        'subject_filter': subject_filter,
    })


@require_student
def analytics(request, student=None):
    """Analytics dashboard."""
    all_marks = MarksRecord.objects.filter(student=student)
    total_entries = all_marks.count()
    overall_avg = all_marks.aggregate(avg=Avg('percentage'))['avg'] or 0

    subject_stats = (
        all_marks
        .values('subject')
        .annotate(
            avg=Avg('percentage'),
            count=Count('id'),
            best=Max('percentage'),
            worst=Min('percentage'),
        )
        .order_by('-avg')
    )

    grade_dist = {}
    for m in all_marks:
        grade_dist[m.grade] = grade_dist.get(m.grade, 0) + 1

    # Weak subjects (avg < 60) and strong subjects (avg >= 80)
    weak = [s for s in subject_stats if s['avg'] < 60]
    strong = [s for s in subject_stats if s['avg'] >= 80]

    # Time series: marks by date
    marks_timeline = list(all_marks.order_by('date_added').values(
        'date_added', 'subject', 'percentage', 'grade'
    ))

    return render(request, 'tracker/analytics.html', {
        'student': student,
        'total_entries': total_entries,
        'overall_avg': round(overall_avg, 1),
        'subject_stats': subject_stats,
        'grade_dist': grade_dist,
        'weak_subjects': weak,
        'strong_subjects': strong,
        'marks_timeline': marks_timeline,
        'rank': student.get_rank(),
    })


@require_student
def notes(request, student=None):
    """Notes list and add."""
    form = NoteForm()
    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.student = student
            note.save()
            add_xp(student, 10)
            messages.success(request, "📝 Note saved! +10 XP earned!")
            return redirect('notes')

    all_notes = Note.objects.filter(student=student)
    return render(request, 'tracker/notes.html', {
        'form': form, 'notes': all_notes, 'student': student
    })


@require_student
def edit_note(request, note_id, student=None):
    """Edit a note."""
    note = get_object_or_404(Note, id=note_id, student=student)
    form = NoteForm(instance=note)
    if request.method == 'POST':
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Note updated!")
            return redirect('notes')
    return render(request, 'tracker/edit_note.html', {
        'form': form, 'note': note, 'student': student
    })


@require_student
def delete_note(request, note_id, student=None):
    """Delete a note."""
    note = get_object_or_404(Note, id=note_id, student=student)
    if request.method == 'POST':
        note.delete()
        messages.success(request, "🗑️ Note deleted.")
    return redirect('notes')


@require_student
def reminders(request, student=None):
    """Reminders list and add."""
    form = ReminderForm()
    if request.method == 'POST':
        form = ReminderForm(request.POST)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.student = student
            reminder.save()
            add_xp(student, 5)
            messages.success(request, "⏰ Reminder set! +5 XP earned!")
            return redirect('reminders')

    upcoming = Reminder.objects.filter(student=student, is_complete=False).order_by('remind_at')
    completed = Reminder.objects.filter(student=student, is_complete=True).order_by('-remind_at')[:5]
    now = timezone.now()

    return render(request, 'tracker/reminders.html', {
        'form': form,
        'upcoming': upcoming,
        'completed': completed,
        'student': student,
        'now': now,
    })


@require_student
def complete_reminder(request, reminder_id, student=None):
    """Mark reminder as complete."""
    reminder = get_object_or_404(Reminder, id=reminder_id, student=student)
    if not reminder.is_complete:
        reminder.is_complete = True
        reminder.save()
        messages.success(request, "✅ Reminder completed! Quest done!")
    return redirect('reminders')


@require_student
def leaderboard(request, student=None):
    """Top players leaderboard."""
    top_players = StudentProfile.objects.order_by('-level', '-xp')[:10]
    return render(request, 'tracker/leaderboard.html', {
        'players': top_players,
        'student': student,
    })


@require_student
def export_excel(request, student=None):
    """Export student's data as Excel download."""
    ensure_excel_file()
    try:
        df = pd.read_excel(EXCEL_FILE)
        student_df = df[df['Nickname'] == student.nickname]
    except Exception:
        student_df = pd.DataFrame()

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{student.nickname}_report.xlsx"'
    student_df.to_excel(response, index=False)
    return response


def logout_view(request):
    """Clear session."""
    request.session.flush()
    messages.info(request, "👋 Logged out. See you next time, Hunter!")
    return redirect('register')
