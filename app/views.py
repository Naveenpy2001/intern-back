from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import WebinarRegistration
from .serializers import WebinarRegistrationSerializer
from django.utils import timezone
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from io import BytesIO
import os
from django.conf import settings


from django.shortcuts import render

def index(request):
    return render(request, 'index.html')

@api_view(['GET'])
def check_registration_status(request, email):
    try:
        registration = WebinarRegistration.objects.get(email=email)
        response_data = {
            'registered': True,
            'payment_status': registration.payment_status,
            'webinar_start_time': registration.webinar_start_time
        }
        return Response(response_data, status=status.HTTP_200_OK)
    except WebinarRegistration.DoesNotExist:
        return Response({'registered': False}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def register(request):
    serializer = WebinarRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Registration successful, please proceed to payment.'}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def payment_success(request):
    email = request.data.get('email')
    amount = request.data.get('amount')

    try:
        registration = WebinarRegistration.objects.get(email=email)
        registration.amount_paid = amount
        registration.payment_status = True
        registration.webinar_start_time = timezone.now() + timezone.timedelta(days=7)
        registration.save()

        # Automatically generate certificate after successful payment
        context = {
            'name': registration.name,
            'email': registration.email,
            'course': registration.course,
            'amount_paid': registration.amount_paid,
            'registration_date': registration.registration_date
        }

        # Load the certificate template
        template = get_template('certificate_template.html')
        html = template.render(context)

        # Define the certificate directory and filename using the user's name
        user_name = registration.name.replace(" ", "_")  # Replace spaces with underscores in the name
        certificate_dir = os.path.join(settings.MEDIA_ROOT, 'certificates')
        if not os.path.exists(certificate_dir):
            os.makedirs(certificate_dir)

        file_path = os.path.join(certificate_dir, f'certificate_{user_name}.pdf')

        # Generate the PDF
        pdf_file = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_file)

        if pisa_status.err:
            return Response({'message': 'Error generating certificate'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Write PDF to file
        with open(file_path, 'wb') as f:
            f.write(pdf_file.getvalue())

        # Save the certificate URL in the database
        certificate_url = f'{settings.MEDIA_URL}certificates/certificate_{user_name}.pdf'
        registration.certificate_pdf = certificate_url
        registration.save()

        # Return JSON response with certificate URL
        response_data = {
            'message': 'Payment successful',
            'start_date': registration.webinar_start_time,
            'certificate_url': certificate_url
        }
        return Response(response_data, status=status.HTTP_200_OK)

    except WebinarRegistration.DoesNotExist:
        return Response({'message': 'Registration not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_user_details(request, email):
    try:
        registration = WebinarRegistration.objects.get(email=email)
        response_data = {
            'name': registration.name,
            'email': registration.email,
            'course': registration.course,
            'amount_paid': registration.amount_paid,
            'registration_date': registration.registration_date,
            'webinar_start_time': registration.webinar_start_time,
            'certificate_url': registration.certificate_pdf.url if registration.certificate_pdf else None
        }
        return Response(response_data, status=status.HTTP_200_OK)
    except WebinarRegistration.DoesNotExist:
        return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def generate_certificate(request, email):
    try:
        registration = WebinarRegistration.objects.get(email=email)

        # Prepare context for the PDF certificate
        context = {
            'name': registration.name,
            'email': registration.email,
            'course': registration.course,
            'amount_paid': registration.amount_paid,
            'registration_date': registration.registration_date
        }

        # Load the template for the certificate
        template = get_template('certificate_template.html')
        html = template.render(context)

        # Define the certificate file path using the user's name
        user_name = registration.name.replace(" ", "_")  # Replace spaces with underscores in the name
        certificate_dir = os.path.join(settings.MEDIA_ROOT, 'certificates')
        if not os.path.exists(certificate_dir):
            os.makedirs(certificate_dir)

        file_path = os.path.join(certificate_dir, f'certificate_{user_name}.pdf')

        # Generate the PDF
        pdf_file = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_file)

        if pisa_status.err:
            return Response({'message': 'Error generating certificate'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save PDF to file
        with open(file_path, 'wb') as f:
            f.write(pdf_file.getvalue())

        # Save the certificate URL in the database
        registration.certificate_pdf = f'certificates/certificate_{user_name}.pdf'
        registration.save()

        # Return the PDF as a response for download with the correct filename
        pdf_file.seek(0)
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="certificate_{user_name}.pdf"'
        return response

    except WebinarRegistration.DoesNotExist:
        return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)





# views.py

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.mail import send_mail
from django.conf import settings
from .models import Registration
from .serializers import RegistrationSerializer
import datetime

class RegisterUserView(APIView):
    def post(self, request):
        data = request.data

        # Extract form data
        email = data.get('email')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        phone = data.get('phone')
        address = data.get('address')
        city = data.get('city')
        state = data.get('state')
        pincode = data.get('pincode')
        course = data.get('course')
        date_of_birth = data.get('date_of_birth')
        gender = data.get('gender')

        # Create user instance
        serializer = RegistrationSerializer(data=data)
        
        if serializer.is_valid():
            user = serializer.save()

            # Send registration confirmation email to the user
            subject_user = "Successfully Registered for Internship"
            message_user = f"Dear {first_name} {last_name},\n\n" \
                           f"You have successfully registered for the ' {course} ' course.\n" \
                           f"We are excited to have you onboard!\n\n" \
                           f"Best Regards,\nThe tsarit Team"
            recipient_user = [email]

            try:
                send_mail(
                    subject_user,
                    message_user,
                    settings.EMAIL_HOST_USER,
                    recipient_user,
                    fail_silently=False,
                )
            except Exception as e:
                return Response({"error": "Failed to send email to user"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Send registration details email to the admin
            subject_admin = "New User Registered for Internship"
            message_admin = f"New user registered:\n\n" \
                            f"Name: {first_name} {last_name}\n" \
                            f"Email: {email}\n" \
                            f"Phone: {phone}\n" \
                            f"Course: {course}\n" \
                            f"Date of Birth: {date_of_birth}\n" \
                            f"Address: {address}, {city}, {state}, {pincode}\n" \
                            f"Gender: {gender}"

            recipient_admin = [settings.EMAIL_HOST_USER]

            try:
                send_mail(
                    subject_admin,
                    message_admin,
                    settings.EMAIL_HOST_USER,
                    recipient_admin,
                    fail_silently=False,
                )
            except Exception as e:
                return Response({"error": "Failed to send email to admin"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({"message": "User successfully registered and emails sent!"}, status=status.HTTP_201_CREATED)
        
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
