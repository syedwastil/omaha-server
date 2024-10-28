# Use official Python image as base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run migrations during container build (not recommended for production)
RUN python omaha-server/manage.py makemigrations && python omaha-server/manage.py migrate

# Collect static files
RUN python omaha-server/manage.py collectstatic --noinput

# Create a user to run the application
RUN echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('USAdmin', 'raai.backend@gmail.com', 'Raaibackend1!')" | python omaha-server/manage.py shell

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define the command to run on container start
CMD ["python", "omaha-server/manage.py", "runserver", "0.0.0.0:8000"]