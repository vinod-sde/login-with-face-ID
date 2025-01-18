from django.shortcuts import render

# Create your views here.
from tempfile import NamedTemporaryFile
import face_recognition
import base64
from django.shortcuts import render,redirect
from django.http import JsonResponse
from django.core.files.base import ContentFile
from .models import *
import os
from django.conf import settings
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def register_page(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        face_image_data = request.POST.get('face_image', '')

        # Validate input
        if not username or not face_image_data:
            return JsonResponse({'status': 'error', 'message': 'Username and face image are required.'})

        # Check if the username already exists
        if User.objects.filter(username=username).exists():
            return JsonResponse({'status': 'error', 'message': 'Username already exists.'})

        try:
            # Convert base64 image data to a file
            face_image_data = face_image_data.split(",")[1]
            face_image = ContentFile(base64.b64decode(face_image_data), name=f'{username}_face.jpg')

            # Save the user and face image in the database
            user = User.objects.create(username=username)  # Use `create` to simplify
            UserImages.objects.create(user=user, face_image=face_image)

            return JsonResponse({'status': 'success', 'message': 'User registered successfully!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'})

    return render(request, 'register.html')
from PIL import Image

@csrf_exempt
def login_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        face_image_data = request.POST.get('face_image')

        # Validate input data
        if not username or not face_image_data:
            return JsonResponse({'status': 'error', 'message': 'Username or face image not provided'})

        # Get the user by username
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User does not exist'})

        try:
            # Convert base64 image data to a file
            face_image_data = face_image_data.split(",")[1]
            uploaded_image = ContentFile(base64.b64decode(face_image_data), name=f'{username}_face.jpg')

            # Save uploaded image temporarily
            temp_path = os.path.join(settings.MEDIA_ROOT, f"{username}_uploaded_face.jpg")
            with open(temp_path, 'wb') as temp_file:
                temp_file.write(uploaded_image.read())

            # Verify and convert image format using Pillow
            with Image.open(temp_path) as img:
                if img.mode not in ['RGB', 'L']:  # Only allow RGB or grayscale
                    img = img.convert('RGB')
                img.save(temp_path)

            # Load the image using face_recognition
            uploaded_face_image = face_recognition.load_image_file(temp_path)

            # Ensure the image is valid and contains face encodings
            uploaded_face_encodings = face_recognition.face_encodings(uploaded_face_image)
            if not uploaded_face_encodings:
                return JsonResponse({'status': 'error', 'message': 'No face detected in the uploaded image'})

            uploaded_face_encoding = uploaded_face_encodings[0]

            # Fetch the stored face image for the user
            user_image = UserImages.objects.filter(user=user).first()
            if not user_image:
                return JsonResponse({'status': 'error', 'message': 'User does not have a registered face image'})

            # Load and validate the stored face image
            stored_face_image = face_recognition.load_image_file(user_image.face_image.path)
            stored_face_encodings = face_recognition.face_encodings(stored_face_image)
            if not stored_face_encodings:
                return JsonResponse({'status': 'error', 'message': 'No face detected in the stored image'})

            stored_face_encoding = stored_face_encodings[0]

            # Compare uploaded face encoding with stored face encoding
            match = face_recognition.compare_faces([stored_face_encoding], uploaded_face_encoding)
            if match[0]:
                return JsonResponse({'status': 'success', 'message': 'Login successful!'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Face recognition failed'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error processing the image: {str(e)}'})

    return render(request, 'login.html')
    

            