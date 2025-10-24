from django.db import models
from django.contrib.auth.models import User
from profil.models import Profile 

MATCH_STATUS_CHOICES = [
    ('PENDING', 'Pending'),             
    ('ACCEPTED', 'Accepted'),           
    ('REJECTED', 'Rejected'),          
    ('CANCELLED', 'Cancelled by Sender'), 
    ('AUTO_CANCELLED', 'Auto Cancelled by System'), 
]

RESULT_CHOICES = [
    ('PENDING', 'Pending Result'),  
    ('P1_WIN', 'Player 1 Win'),      
    ('P2_WIN', 'Player 2 Win'),      
    ('CANCELLED', 'Match Cancelled'), 
]


class MatchRequest(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')
    
    status = models.CharField(max_length=20, choices=MATCH_STATUS_CHOICES, default='PENDING')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Request from {self.sender.username} to {self.receiver.username} ({self.status})"

class MatchSession(models.Model):
    player1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matches_as_player1')
    player2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matches_as_player2')
    
    request = models.OneToOneField(MatchRequest, on_delete=models.SET_NULL, null=True, blank=True)
    
    date_played = models.DateTimeField(auto_now_add=True)
    
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default='PENDING')
    
    is_confirmed = models.BooleanField(default=False) 

    def __str__(self):
        return f"Session: {self.player1.username} vs {self.player2.username} ({self.result})"