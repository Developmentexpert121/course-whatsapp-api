
# WhatsApp Study App (Django Backend)

A Django-based backend for a **WhatsApp-driven study platform** where users interact only via WhatsApp.  
The app allows creating and managing **courses, chapters, and assessments**, and delivers them seamlessly to learners over WhatsApp.  

---

## 🚀 Features
- **WhatsApp Integration** – All user interaction happens over WhatsApp.  
- **Course Management** – Create and manage courses with multiple chapters.  
- **Assessment Management** – After each chapter, an assessment is delivered to the learner.  
- **Nested Structure** – Each course → multiple chapters → each chapter → one assessment → multiple questions.  
- **User Management** – Onboarding, orientation, and progress tracking for each learner.  

---

## 📂 Project Structure
```
project-root/
│── manage.py
│── requirements.txt
│── README.md
│
│── whatsapp_bot/ # Core Django project (settings, routing, configuration)
│ │── settings.py   # Django project settings
│ │── urls.py       # Root URL configuration
│ └── ...
│
│── whatsapp/   # WhatsApp bot & user interaction logic
│ │── models.py    # Models for WhatsApp users, enrollments, assessment attempts
│ │── views.py     # API views for WhatsApp-related endpoints
│ │── urls.py      # Routes for WhatsApp APIs
│ │...
│ └── services/ # Bot service layer
│     │── ai_response_interpreter.py # AI/OpenAI response handling
│     │── assessment_service.py      # Delivery & evaluation of assessments and quizzes
│     │── course_delivery_manager.py # Orchestrates course, module, assessment, and certificate delivery
│     │── certificates_service.py    # Certificate generation & delivery
│     │── emailing_service.py        # Email sending services
│     │── enrollment_service.py      # User enrollment logic
│     │── messaging.py               # WhatsApp messaging utilities
│     │── module_delivery_service.py # Module delivery & learner progress tracking
│     │── onboarding_manager.py      # User onboarding flow (registration)
│     │── onboarding_manager.py      # User Orentation flow (orientation: enroll ment of courses)
│     │── post_course_manager.py     # Handles user progression to next course after completion
│     │── user.py                    # CRUD operations for WhatsApp users
│
│── courses/   # Course, module & assessment management
│ │── models.py    # Models for courses, modules, assessments, questions
│ │── views.py     # API views for CRUD operations
│ │── urls.py      # Routes for course APIs
│ │...
│ └── services/   # Business logic layer for course management
│     │── course_service.py     # CRUD operations for courses
│     │── module_service.py     # CRUD operations for modules
│     │── topic_service.py     # CRUD operations for topics
│     │── image_service.py     # CRUD operations for images upload delete from s3
│     │── assessment_service.py # CRUD operations for assessments & questions
```
## 🛠️ Setup & Installation

### 1. Clone the Repository
```bash
git clone repo-url
cd repo-name
````

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # For Linux/Mac
venv\Scripts\activate      # For Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Populate .env.example


### 5. Apply Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create Superuser

```bash
python manage.py createsuperuser
```

### 7. Run Development Server

```bash
python manage.py runserver
```

---

## 📱 WhatsApp Integration

* WhatsApp bot is powered via **WhatsApp Cloud API**.
* Incoming messages → handled in `whatsapp/views.py-->WhatsAppWebhookView ->post request`.

---

## 📘 Usage Flow

1. **Onboarding** – Users share personal details (name, email, etc.) on WhatsApp.
2. **Orientation** – Users select courses to enroll in.
3. **Course Delivery** – Chapters are delivered one by one.
4. **Assessments** – After each chapter, an assessment is triggered and questions are asked one by one.
5. **Progress Tracking** – User responses are stored and evaluated.


---

## 📜 License

This project is licensed under the MIT License.

```

