import os
import logging
from fastapi import FastAPI, HTTPException, UploadFile, Form, Query, Request, Response, File, Form, Body
import smtplib
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import psycopg
from datetime import datetime
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig


load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

conn = psycopg.connect( dbname=os.getenv("DB_NAME"),
                        host= os.getenv("DB_HOST"),
                        user=os.getenv("DB_USER"),
                        password=os.getenv("DB_PASS"),
                        port=("5432")
)


# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),   
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_PORT=int(os.getenv("MAIL_PORT")),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    MAIL_FROM=os.getenv("MAIL_FROM"),
    USE_CREDENTIALS=True,    
)
fm = FastMail(conf)


app = FastAPI()
origins = os.getenv("WEBSITE_URL", "http://127.0.0.1:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EmailSchema(BaseModel):
    email: List[EmailStr]

class KneeBraceData(BaseModel):
    angle: float
    muscle_reading: int
    brace_id: str

class Alert(BaseModel):
    brace_id: str
    type: str
    message: str
    
class Feedback(BaseModel):
    brace_id: str
    body: str
    type: str

class Appointments(BaseModel):
    brace_id: str
    name: str
    email: str
    phone_number: str
    reason: str
    time_stamp: datetime

class WeeklyRotation(BaseModel):
    date: datetime
    avgangle: float
    brace_id: str

class MonthlyRotation(BaseModel):
    month: str
    month_number: int
    avgangle: float
    brace_id: str
    
class User(BaseModel):
    brace_id: str
    name: str
    email: EmailStr
    contact: str
    
class Settings(BaseModel):
    brace_id: str
    upper_angle_treshold: float
    lower_angle_treshold: float
    contact: str



# Email
async def send_mail(email: EmailSchema, brace: str, alert_type: str, code: str):
    template = f"""
    <html>
    <body>
    <p><strong>URGENT ALERT!</strong></p>
    <p>Dear User,</p>
    <p>We have detected an issue with your knee brace.</p>
    <p>Please take the following action:</p>
    <p>1. Check the knee brace for any visible issues.</p>
    <p>2. Ensure that the brace is properly fitted.</p>
    <p>3. If the issue persists, please contact our support.</p>
    <p>For your reference, here are the details:</p>
    <p><strong>Brace ID: {brace}</strong></p>
    <p><strong>Type: {alert_type}</strong></p>
    <p><strong>Alert Code: {code}</strong></p>
    <p>Thank you for your attention to this matter.</p>
    <p>Best regards,</p>
    <p><i><strong>KneeSync </i></strong> Team</p>
    </body>
    </html>
    """
    message = MessageSchema(subject="KneeSync Alert System Notice", recipients=email.email, body=template, subtype="html")
    try:
        await fm.send_message(message)
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

@app.get("/knee-brace", status_code=200)
async def get_knee_brace():
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT angle, muscle_reading, brace_id FROM knee_brace;")
            knee_brace = cursor.fetchall()
            if not knee_brace:
                raise HTTPException(status_code=404, detail="No knee brace data found.")
        return [KneeBraceData(angle=item[0], muscle_reading=item[1], brace_id=item[2]) for item in knee_brace]
    except Exception as e:
        logging.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/knee-brace", status_code=201)
async def post_knee_brace(data: KneeBraceData):
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                    INSERT INTO knee_brace (angle, muscle_reading, brace_id)
                    VALUES (%s, %s, %s)
                """, (data.angle, data.muscle_reading, data.brace_id))
        conn.commit()
        return JSONResponse(status_code=201, content={"message": "Knee brace data successfully submitted."})
    except Exception as e:
        logging.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/alerts", status_code=201)
async def post_alerts(alert: Alert):
    try:
        with conn.cursor() as cursor:
         cursor.execute("""
                    INSERT INTO alerts (brace_id, type, message)
                    VALUES (%s, %s, %s)
                """, (alert.brace_id, alert.type, alert.message))
        conn.commit()
        await send_mail(EmailSchema(email=["josiah.reece007@gmail.com"]), alert.brace_id, alert.type, alert.message)
        return JSONResponse(status_code=201, content={"message": "Alert successfully submitted."})
    except Exception as e:
        logging.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.get("/alerts", status_code=200)
async def get_alerts():
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM alerts")
            alerts = cursor.fetchall()
        return JSONResponse(status_code=200, content={"alerts": alerts})
    except Exception as e:
        logging.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.post("/send-mail")
async def send_file(file: UploadFile = Form(...)) -> JSONResponse:
    try:
        message = MessageSchema(
            subject="FastAPI Mail Module",
            recipients=["josiah.reece007@gmail.com"],
            body="Simple background task",
            subtype="html",
            attachments=[file]
        )
        await fm.send_message(message)
        return JSONResponse(status_code=200, content={"message": "Email has been sent"})
    except Exception as e:
        logging.error(f"Email error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/appointments")
async def get_appointments():
    try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM appointment ORDER BY time_stamp DESC;")
                appointments = cursor.fetchall()
                response = [Appointments(brace_id=item[1], name=item[2], email=item[3], phone_number=item[4], reason=item[5], time_stamp=item[6]) for item in appointments]
                if not appointments:
                    raise HTTPException(status_code=404, detail="No appointment data found.")
                return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/feedback")
async def get_feedback():
    try:
          with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM feedback;")
            feedback = cursor.fetchall()
            response = [Feedback(brace_id=item[0], body=item[1], type=item[2]) for item in feedback]
            if not feedback:
              raise HTTPException(status_code=404, detail="No feedback data found.")
            return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/weeklyrotation")
async def get_weekly_rotation():
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                    SELECT DATE(time_stamp) AS day, AVG(angle) AS avg_angle, brace_id
                    FROM knee_brace
                    GROUP BY DATE(time_stamp), brace_id
                    ORDER BY DATE(time_stamp);
                """)
        weekly_rotation = cursor.fetchall()
        response = [WeeklyRotation(date=item[0], avgangle=item[1], brace_id=item[2]) for item in weekly_rotation]
        if not weekly_rotation:
                    raise HTTPException(status_code=404, detail="No weekly rotation data found.")
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/monthlyrotation")
async def get_monthly_rotation():
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            SELECT TO_CHAR(DATE_TRUNC('month', time_stamp), 'Month') AS month_name,
                EXTRACT(MONTH FROM time_stamp) AS month_number,
                AVG(angle) AS avg_angle,
                brace_id
            FROM knee_brace
            GROUP BY month_name, month_number, brace_id
            ORDER BY month_number;
        """)
        monthly_rotation = cursor.fetchall()
        response = [MonthlyRotation(month=item[0], month_number=item[1], avgangle=item[2], brace_id=item[3]) for item in monthly_rotation]
        if not monthly_rotation:
                    raise HTTPException(status_code=404, detail="No monthly rotation data found.")
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/users", status_code=201)
async def create_user(user: User):
    try:
        with conn.cursor() as cursor:
            query = """
            INSERT INTO users (brace_id, name, email, contact) 
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (user.brace_id, user.name, user.email, user.contact))
            conn.commit()
            return JSONResponse(status_code=201, content={"message": "User successfully created."})
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/users", status_code=200)
async def get_users():
    try:
        with conn.cursor() as cursor:
         cursor.execute("SELECT id, brace_id, name, email, contact FROM users;")
        users = cursor.fetchall()
        response = [
            {"id": item[0], "brace_id": item[1], "name": item[2], "email": item[3], "contact": item[4]} 
            for item in users
        ]
        if not users:
            raise HTTPException(status_code=404, detail="No user data found.")
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.post("/settings", status_code=201)
async def create_settings(settings: Settings):
    try:
        with conn.cursor() as cursor:
            query = """
            INSERT INTO settings (brace_id, upper_angle_treshold, lower_angle_treshold, contact) 
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (settings.brace_id, settings.upper_angle_treshold, settings.lower_angle_treshold, settings.contact))
        conn.commit()
        return JSONResponse(status_code=201, content={"message": "Settings successfully created."})
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/settings", status_code=200)
async def get_settings():
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, brace_id, upper_angle_treshold, lower_angle_treshold, contact, time_stamp FROM settings;")
            settings = cursor.fetchall()
        response = [
            {"id": item[0], "brace_id": item[1], "upper_angle_treshold": item[2], "lower_angle_treshold": item[3], "contact": item[4], "time_stamp": item[5]} 
            for item in settings
        ]
        if not settings:
            raise HTTPException(status_code=404, detail="No settings data found.")
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
