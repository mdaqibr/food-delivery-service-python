# Food Delivery Service (Django)

A lightweight, high-performance food delivery service built using **Python, Django, and PostgreSQL/MySQL**.  
The project implements a simple **order management system** with users, restaurants, delivery agents, and orders.

---

## Features
- **User Management**: Register as a `customer` or `delivery_agent`
- **Restaurant Management**: Add restaurants and view details
- **Order Management**: Place an order, accept it (by agent), mark as delivered
- **Order History**: Customers can view their past orders
- **REST APIs** with Django views

---

## Tech Stack
- **Backend**: Django 5.x
- **Database**: PostgreSQL (default) / MySQL
- **Language**: Python 3.10+
- **API Testing**: cURL / Postman
- **ORM**: Django ORM

---
## .env File
```
DEBUG=True
SECRET_KEY=your-secret-key
DB_NAME=food_delivery
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=127.0.0.1
DB_PORT=5432

# Rate limiting
RATE_LIMIT_REQ=60
RATE_LIMIT_WINDOW=60

# LOGGING
LOG_LEVEL=INFO
```
---
## requirement.txt
```
Django>=4.2
djangorestframework>=3.14
psycopg2-binary>=2.9
python-decouple>=3.8
```
---

## Create Virtual Environment
- python3 -m venv venv
- source venv/bin/activate   # (Linux/Mac)
- venv\Scripts\activate      # (Windows)
- pip install django djangorestframework psycopg2-binary python-decouple
- django-admin startproject food_delivery_service
- cd food_delivery_service
- python manage.py startapp delivery
- pip freeze > requirements.txt

## Install Dependencies
- pip install -r requirements.txt

## Run Migrations
- python manage.py makemigrations
- python manage.py migrate

## Start Development Server
- python manage.py runserver

## APIs 
 - Find the attached postman json file to import in the postman to get the apis.