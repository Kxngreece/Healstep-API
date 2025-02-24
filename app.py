import os
from fastapi import FastAPI, Body, HTTPException, Query, Request, Response, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, TypeAdapter,BeforeValidator,EmailStr
import psycopg
from datetime import datetime, timedelta, date, time
from fastapi_mail import FastMail, MessageSchema,ConnectionConfig
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv


load_dotenv()

conn = psycopg.connect( dbname=os.getenv("DB_NAME"),
                        host= os.getenv("DB_HOST"),
                        user=os.getenv("DB_USER"),
                        password=os.getenv("DB_PASS"),
                        port=("5432")
)

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
app = FastAPI()
origins = [ "WEBSITE_URL"]

app.add_middleware(
    CORSMiddleware,
    allow_origins= origins,  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EmailSchema(BaseModel):
   email: List[EmailStr]
   
class weekly (BaseModel):
    date: datetime
    avgangle: float
    brace_id: str

class monthrotation (BaseModel):
    month : str
    month_number: int
    avgangle: float
    brace_id: str
    
class Feedback(BaseModel):
    brace_id: str
    body: str
    type: str

class Alert(BaseModel):
    brace_id: str
    type: str
    message: str
    
class alerthistory(BaseModel):
    id: int
    brace_id: str
    type: str
    message: str
    time_stamp: datetime
    
class Appointments(BaseModel):
    id: int
    brace_id: str
    name: str
    email : str
    phone_number: str
    reason: str
    time_stamp: datetime
    
class weekrotation(BaseModel):
    date: datetime
    avgangle: float
    brace_id: str

class anglerotation(BaseModel):
    date: datetime
    angle: float
    brace_id: str
    
class muscleactivity(BaseModel):
    date: datetime
    muscle_reading: float
    brace_id: str

class KneeBraceData(BaseModel):
    angle: float
    muscle_reading: float
    brace_id: str
    
class count(BaseModel):
    number: int
    
    
async def send_mail(email: EmailSchema, location:str, string: str, code: str):
    template = f"""
            <html>
            <body>
            
    
    <p>     <br> URGENT!!!
            <br> Patient with Brace ID :{location} is currently experiencing unusual activity. PLEASE check their status immediately.
            <br>Knee {string} of rotation has been breached.
            <br> Alert Code: {code} </p>
    
    
            </body>
            </html>
            """

    message = MessageSchema(
       subject="Healstep Alert System Notice",
       recipients=email.get("email"),  # List of recipients, as many as you can pass  
       body=template,
       subtype="html"
       )

    fm = FastMail(conf)
    await fm.send_message(message)

    return JSONResponse(status_code=200, content={"message": "email has been sent"})


@app.get("/knee-brace", status_code=200)
async def get_knee_brace():
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT angle, muscle_reading, brace_id FROM knee_brace;")
        knee_brace = cursor.fetchall()
        print(cursor.fetchall())
        cursor.close()
        response = [KneeBraceData(angle=item[0], muscle_reading=item[1], brace_id=item[2]) for item in knee_brace]
        if not knee_brace:
            raise HTTPException(status_code=404, detail="No knee brace data found.")
        return response
    except Exception as e:
        # Handle any errors and return a 500 response
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
@app.get("/angle", status_code=200)
async def get_angle():
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT angle, brace_id FROM knee_brace;")
        angle = cursor.fetchall()
        print(cursor.fetchall())
        response = [anglerotation(angle=item[0], brace_id=item[1]) for item in angle]
        if not angle:
            raise HTTPException(status_code=404, detail="No angle data found.")
        return response
    except Exception as e:
        # Handle any errors and return a 500 response
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
    
@app.get("/emg", status_code=200)
async def get_emg():
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT muscle_reading, brace_id FROM knee_brace;")
        muscle_reading = cursor.fetchall()
        print(cursor.fetchall())
        cursor.close()
        response = [muscleactivity( muscle_reading=item[0], brace_id=item[1]) for item in muscle_reading]
        if not muscle_reading:
            raise HTTPException(status_code=404, detail="No muscle activity data found.")
        return response
    except Exception as e:
        # Handle any errors and return a 500 response
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
    
@app.get("/alert", status_code=200)
async def get_alert():
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM alerts;")
        alert = cursor.fetchall()
        cursor.close()
        response = [count ( number = item[0], ) for item in alert]
        print(cursor.fetchall())
        if not alert:
            raise HTTPException(status_code=404, detail="No alert data found.")
       
        return response
    except Exception as e:
        # Handle any errors and return a 500 response
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
    
    
@app.get("/alert-history", status_code=200)
async def get_alerts():
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts;")
        alerts = cursor.fetchall()
        cursor.close()  
        response = [alerthistory (id=item[0], brace_id =(item[1]), type= item[2], message=item[3], time_stamp=item[4]) for item in alerts]
        print(cursor.fetchall())
        if not alerts:
            raise HTTPException(status_code=404, detail="No alerts data found.")
        return response
    except Exception as e:
        # Handle any errors and return a 500 response
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
    
    
@app.get("/appointments", status_code=200)
async def get_appointments():
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM appointment;")
        appointments = cursor.fetchall()
        cursor.close()
        response = [count ( number = item[0], ) for item in appointments]
        print(cursor.fetchall())
        if not appointments:
            raise HTTPException(status_code=404, detail="No appointments data found.")
        return response
    except Exception as e:
        # Handle any errors and return a 500 response
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    

@app.get("/feedback", status_code=200)
async def get_feedback():
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM feedback;")
        feedback = cursor.fetchall()
        cursor.close()
        response=[Feedback (brace_id = item[0], body = item[1], type = item[2]) for item in feedback]
        print(cursor.fetchall())
        if not feedback:
            raise HTTPException(status_code=404, detail="No feedback data found.")
        return response
    except Exception as e:
        # Handle any errors and return a 500 response
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
    
@app.get("/appointment", status_code=200)
async def get_appoinment():
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM appointment;")
        appointment = cursor.fetchall()
        cursor.close()
        response = [Appointments (id=item[0], brace_id =(item[1]), name= item[2], email=item[3], phone_number=item[4], reason=item[5], time_stamp=item[6]) for item in appointment]
        print(cursor.fetchall())
        if not appointment:
            raise HTTPException(status_code=404, detail="No feedback data found.")
        return  response
    except Exception as e:
        # Handle any errors and return a 500 response
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
    
@app.get("/weeklyrotation", status_code=200)
async def get_weeklyrotation():
    try:
        cursor = conn.cursor()
        cursor.execute("""SELECT 
     DATE(time_stamp) AS day,
        AVG(angle) AS avg_angle,
        brace_id
    FROM 
        knee_brace
    GROUP BY 
        DATE(time_stamp), brace_id
    ORDER BY 
        DATE(time_stamp);""")
        weeklyrotation = cursor.fetchall()
        cursor.close()
        response = [weekly(date = item[0],  avgangle=item[1], brace_id=item[2]) for item in weeklyrotation]
        print(cursor.fetchall())
        if not weeklyrotation:
            raise HTTPException(status_code=404, detail="No weeklyrotation data found.")
        return response
    except Exception as e:
        # Handle any errors and return a 500 response
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
    
@app.get("/monthlyrotation", status_code=200)
async def get_monthlyrotation():
    try:
        cursor = conn.cursor()
        cursor.execute("""WITH monthly_sums AS (
    SELECT
        TO_CHAR(DATE_TRUNC('month', time_stamp), 'Month') AS month_name,
        EXTRACT(MONTH FROM time_stamp) AS month_number,
        AVG(angle) AS angle,
        brace_id
    FROM 
        knee_brace
    WHERE 
        date(time_stamp) >= '2025-01-01'
        AND date(time_stamp) <= '2025-12-31'
    GROUP BY 
        month_name, month_number, brace_id)
    SELECT *
    FROM monthly_sums
    ORDER BY month_number;""")
        monthlyrotation = cursor.fetchall()
        cursor.close()
        response = [monthrotation(month = item[0], month_number = item[1], avgangle=item[2], brace_id=item[3]) for item in monthlyrotation]
        print(cursor.fetchall())
        if not monthlyrotation:
            raise HTTPException(status_code=404, detail="No monthly rotation data found.")
      
        return response
    except Exception as e:
        # Handle any errors and return a 500 response
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
    
    
@app.post("/feedback", status_code=201)
async def post_feedback(feeback:Feedback):
    try:
        cursor = conn.cursor()
        
        brace_id = feeback.brace_id
        body = feeback.body
        type = feeback.type

        query = f"""INSERT INTO feedback 
	                ( brace_id, body, type) 
                    VALUES
                        ('{brace_id}', '{body}', '{type}')
                    """
        
        cursor.execute(query)
        conn.commit()
        await send_mail({"email":["josiah.reece007@gmail.com"]},body, type)

        return JSONResponse(status_code=201, content={"message": "Feedback successfully submitted."})
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()  # Rollback any failed transaction
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    
@app.post("/alerts", status_code=201)
async def post_alerts(alerts:Alert):
    try:
        cursor = conn.cursor()
        
        brace_id = alerts.brace_id
        type = alerts.type
        message= alerts.message

        query = f"""INSERT INTO alerts
	                ( brace_id, type, message) 
                    VALUES
                        ('{brace_id}', '{type}', '{message}')
                    """
                    
        
        cursor.execute(query)
        conn.commit()
        await send_mail({"email":["josiah.reece007@gmail.com"]},brace_id, type, message)

        return JSONResponse(status_code=201, content={"message": "Feedback successfully submitted."})
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()  # Rollback any failed transaction
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.post("/send-mail")
async def send_file(
    # background_tasks: BackgroundTasks,
    file: UploadFile = Form(...)
    # email:EmailStr = Form(...)
    )-> JSONResponse:

    message = MessageSchema(
            subject="Fastapi mail module",
            recipients=["tiffanycampbell1710@gmail.com"],
            body="Simple background task",
            subtype="html",
            attachments=[file])

    fm = FastMail(conf)

    await fm.send_message(message)

    return JSONResponse(status_code=200, content={"message": "email has been sent"})

@app.post("/knee-brace", status_code=201)
async def post_knee_brace(data:KneeBraceData):
    try:
        cursor = conn.cursor()
        angle = data.angle
        muscle_reading = data.muscle_reading
        brace_id = data.brace_id
        
        query = f"""INSERT INTO knee_brace 
                    ( angle, muscle_reading, brace_id) 
                    VALUES
                        ('{angle}', '{muscle_reading}', '{brace_id}')
                    """
        
        cursor.execute(query)
        conn.commit()
        cursor.close()
        return JSONResponse(status_code=201, content={"message": "Knee brace data successfully submitted."})
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()  # Rollback any failed transaction
        raise HTTPException(status_code=500, detail="Internal Server Error")
    