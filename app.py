import os
import logging
from fastapi import FastAPI, HTTPException, UploadFile, Form, Query, Request, Response, File, Form, Body
import smtplib
import datetime
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import psycopg
from datetime import date, datetime, time
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
WEBSITE_URL = os.getenv("WEBSITE_URL")
API_URL = os.getenv("API_URL")

origins = [WEBSITE_URL, API_URL, "http://127.0.0.1:8000", "http://localhost:8000", "http://127.0.0.1:5502"]
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
    timestamp: datetime 
    display_name: str 

class Alert(BaseModel):
    brace_id: str
    type: str
    message: str
    time_stamp: datetime
    
class Alerts(BaseModel):
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

class DeviceInfo(BaseModel):
    brace_id: str
    display_name: str





@app.post("/test", status_code=200)
async def handle_test():
    return {"message": "Post request received", "status": "success"}


# Email
async def send_mail(email: EmailSchema, brace: str, alert_type: str, code: str, ):
    template = f"""
   <!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>HealStep Alert Notification</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      background-color: #f4f7fa;
      margin: 0;
      padding: 20px;
      color: #333;
    }}
    .container {{
      background-color: #ffffff;
      padding: 30px;
      max-width: 600px;
      margin: auto;
      border-radius: 8px;
      box-shadow: 0 4px 8px rgba(0,0,0,0.05);
    }}
    h2 {{
      color: #2c3e50;
    }}
    .alert {{
      background-color: #ffe6e6;
      border-left: 6px solid #e74c3c;
      padding: 15px;
      margin-top: 20px;
    }}
    .footer {{
      font-size: 0.9em;
      color: #777;
      margin-top: 30px;
      text-align: center;
    }}
    .label {{
      font-weight: bold;
      color: #2c3e50;
    }}
  </style>
</head>
<body>
  <div class="container">
    <h2>🚨 KneeSync Alert Notification</h2>
    <p>Hello,</p>
    <p>This is an automated alert from the KneeSync Assistive Knee Brace system. An abnormal reading has been detected.</p>
    
    <div class="alert">
      <p><span class="label">Brace ID:</span> {brace}</p>
      <p><span class="label">Alert Type:</span> {alert_type}</p>
      <p><span class="label">Message:</span> {code}</p>
    </div>

    <p>Please review the patient's data and take necessary actions if needed.</p>

    <div class="footer">
      KneeSync Monitoring System <br>
      Powered by HealStep | healstep.support@example.com
    </div>
  </div>
</body>
</html>
    """
    message = MessageSchema(subject="KneeSync Alert System Notice", recipients=email.email, body=template, subtype="html")
    try:
        await fm.send_message(message)
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

@app.get("/knee-brace", response_model=List[KneeBraceData], status_code=200)
async def get_knee_brace_data(
    brace_id: Optional[str] = Query(None, description="Filter by brace ID. Returns latest reading.")
):
    try:
        with conn.cursor() as cursor:
            base_query = """
                SELECT k.angle, k.muscle_reading, k.brace_id, k.time_stamp,
                       d.display_name
                FROM knee_brace k
                LEFT JOIN devices d ON k.brace_id = d.brace_id
                {where_clause}
                ORDER BY k.time_stamp DESC
            """
            
            if brace_id:
                cursor.execute(f"""
                    {base_query.format(where_clause="WHERE k.brace_id = %s")}
                """, (brace_id,))
            else:
                cursor.execute(base_query.format(where_clause=""))

            result = cursor.fetchall()
            
        if not result:
            detail = f"No data found{' for ' + brace_id if brace_id else ''}"
            raise HTTPException(status_code=404, detail=detail)
            
        return [{
            "angle": float(result[0]),
            "muscle_reading": result[1],
            "brace_id": result[2],
            "timestamp": result[3].isoformat(),
            "display_name": result[4] or result[2]
        }]

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


@app.get("/devices", status_code=200)
async def get_devices():
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT ON (k.brace_id) k.brace_id, 
                       COALESCE(d.display_name, k.brace_id) as display_name
                FROM knee_brace k
                LEFT JOIN devices d ON k.brace_id = d.brace_id
                ORDER BY k.brace_id, k.time_stamp DESC 
            """)
            devices = cursor.fetchall()
            if not devices:
                raise HTTPException(status_code=404, detail="No devices found.")
        
        devices_list = []
        for record in devices:
            mac_address = record[0]
            bracename = f"Brace {mac_address.replace(':', '')[-6:]}" 
            devices_list.append(DeviceInfo(brace_id=mac_address, display_name=bracename))  
        
        return devices_list

    except Exception as e:
        logging.error(f"Error fetching list of devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve device list.")
    
@app.post("/alerts", status_code=201)
async def post_alerts(alert: Alerts):
    try:
        with conn.cursor() as cursor:
         cursor.execute("""
                    INSERT INTO alerts (brace_id, type, message)
                    VALUES (%s, %s, %s)
                """, (alert.brace_id, alert.type, alert.message))
        conn.commit()
        await send_mail(EmailSchema(email=["josiah.reece007@gmail.com", "jaleel.morgan101@gmail.com"]), alert.brace_id, alert.type, alert.message)
        return JSONResponse(status_code=201, content={"message": "Alert successfully submitted."})
    except Exception as e:
        logging.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.get("/alerts", status_code=200)
async def get_alerts():
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT brace_id, type, message, time_stamp FROM alerts")
            alerts = cursor.fetchall()
            response = [Alert(brace_id=item[0], type=item[1], message=item[2], time_stamp=item[3]) for item in alerts]
            if not alerts:
                raise HTTPException(status_code=404, detail="No alert data found.")
            return response
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


@app.get("/settings/{brace_id}", status_code=200)
async def get_device_settings(brace_id: str):
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT upper_angle_treshold, lower_angle_treshold
                FROM settings 
                WHERE brace_id = %s 
                ORDER BY time_stamp DESC 
                LIMIT 1
            """, (brace_id,))
            result = cursor.fetchone()
            
        if not result:
            raise HTTPException(status_code=404, detail="No settings found for this device")
            
        return {
            "brace_id": brace_id,
            "upper_angle_treshold": result[0],
            "lower_angle_treshold": result[1]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")