from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from transformers import pipeline
from .models import SummarizedNote

# Lazy loading the model so it doesn't block Django startup
_summarizer = None

def get_summarizer():
    global _summarizer
    if _summarizer is None:
        print("Loading Hugging Face model 'facebook/bart-large-cnn'...")
        _summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    return _summarizer

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect("home")
        messages.error(request, "Unsuccessful registration. Invalid information.")
    else:
        form = UserCreationForm()
    return render(request, "register.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"You are now logged in as {username}.")
                return redirect("home")
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, "login.html", {"form": form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("login")

@login_required(login_url='login')
def notessummarizer(request):
    summary = ""

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        
        if text:
            try:
                # Dynamically calculate length parameters based on input size
                word_count = len(text.split())
                if word_count < 20:
                    # Input is too short for the model to summarize meaningfully
                    summary = text
                else:
                    max_len = min(130, word_count // 2)
                    min_len = min(30, max_len - 1) if max_len > 30 else max_len
                    
                    # Generate the summary
                    summarizer = get_summarizer()
                    result = summarizer(text, max_length=max_len, min_length=min_len, do_sample=False)
                    summary = result[0]['summary_text']
                    
                # Save the input and summary to the database, linked to user
                SummarizedNote.objects.create(
                    user=request.user,
                    original_text=text,
                    summarized_text=summary
                )
            except Exception as e:
                summary = f"Error generating summary: {str(e)}"
        else:
            summary = "No text provided."

    return render(request, "index.html", {"summary": summary})

@login_required(login_url='login')
def dashboard(request):
    """View to display all saved historical summaries for logged in user."""
    summaries = SummarizedNote.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "dashboard.html", {"summaries": summaries})