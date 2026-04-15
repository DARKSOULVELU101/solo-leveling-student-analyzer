from django.db import models
from django.utils import timezone


class StudentProfile(models.Model):
    nickname = models.CharField(max_length=50, unique=True)
    xp = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    session_key = models.CharField(max_length=100, blank=True)

    def get_rank(self):
        if self.level <= 2:
            return 'E'
        elif self.level <= 4:
            return 'D'
        elif self.level <= 6:
            return 'C'
        elif self.level <= 8:
            return 'B'
        elif self.level == 9:
            return 'A'
        else:
            return 'S'

    def get_rank_display_full(self):
        rank = self.get_rank()
        rank_names = {
            'E': 'E-Rank Hunter',
            'D': 'D-Rank Hunter',
            'C': 'C-Rank Hunter',
            'B': 'B-Rank Hunter',
            'A': 'A-Rank Hunter',
            'S': 'S-Rank Hunter',
        }
        return rank_names.get(rank, 'E-Rank Hunter')

    def get_xp_for_next_level(self):
        return self.level * 500

    def get_xp_progress_percent(self):
        xp_in_current_level = self.xp % 500
        return min(int((xp_in_current_level / 500) * 100), 100)

    def __str__(self):
        return f"{self.nickname} (Level {self.level} | {self.get_rank()}-Rank)"


class MarksRecord(models.Model):
    GRADE_CHOICES = [
        ('A+', 'A+'), ('A', 'A'), ('B', 'B'),
        ('C', 'C'), ('D', 'D'), ('F', 'F'),
    ]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='marks')
    subject = models.CharField(max_length=100)
    marks_obtained = models.FloatField()
    total_marks = models.FloatField()
    percentage = models.FloatField()
    grade = models.CharField(max_length=2, choices=GRADE_CHOICES)
    topic = models.CharField(max_length=200, blank=True)
    suggestion = models.TextField(blank=True)
    xp_earned = models.IntegerField(default=0)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.nickname} - {self.subject} ({self.percentage:.1f}%)"

    class Meta:
        ordering = ['-date_added']


class Note(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=100, blank=True)
    content = models.TextField()
    xp_earned = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.nickname} - {self.title}"

    class Meta:
        ordering = ['-created_at']


class Reminder(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='reminders')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    remind_at = models.DateTimeField()
    is_complete = models.BooleanField(default=False)
    xp_earned = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_overdue(self):
        return not self.is_complete and self.remind_at < timezone.now()

    def __str__(self):
        return f"{self.student.nickname} - {self.title}"

    class Meta:
        ordering = ['remind_at']
