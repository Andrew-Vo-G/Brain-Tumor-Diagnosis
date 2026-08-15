from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import Any, List
import os
import shutil
import threading
from postgrest.exceptions import APIError

from . import schemas, auth, database

app = FastAPI(title="Brain Tumor AI API (Supabase Edition)")
_warmup_started = False
_warmup_lock = threading.Lock()


def _is_missing_table_error(error: Exception, table_name: str) -> bool:
    msg = str(error)
    return (
        "PGRST205" in msg
        and f"public.{table_name}" in msg
        and "Could not find the table" in msg
    )

@app.on_event("startup")
def preload_models():
    import sys
    should_preload = os.environ.get("PRELOAD_AI_ON_STARTUP", "0") == "1"
    should_preload_async = os.environ.get("PRELOAD_AI_ASYNC", "0") == "1"

    def _do_preload():
        try:
            from . import ai_service
            ai_service.load_models()
            sys.stderr.write("AI Models loaded and ready for Instant Inference!\n")
        except Exception as e:
            # Keep API/UI available even if AI dependencies are temporarily broken.
            sys.stderr.write(f"WARNING: AI model preload skipped due to error: {e}\n")

    if not should_preload:
        if should_preload_async:
            sys.stderr.write("Starting AI preload in background thread...\n")
            threading.Thread(target=_do_preload, daemon=True, name="ai-preload").start()
        else:
            sys.stderr.write("Skipping AI preload on startup (set PRELOAD_AI_ON_STARTUP=1 or PRELOAD_AI_ASYNC=1).\n")
        return

    sys.stderr.write("Pre-loading AI Models into RAM...\n")
    _do_preload()

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/warmup")
def warmup_models():
    global _warmup_started
    with _warmup_lock:
        if _warmup_started:
            return {"status": "warming_or_ready"}
        _warmup_started = True

    def _warmup():
        try:
            from . import ai_service
            ai_service.load_models()
        except Exception:
            # Keep API responsive even if warmup fails.
            pass

    threading.Thread(target=_warmup, daemon=True, name="ai-warmup").start()
    return {"status": "warming_started"}

# Allows CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount the uploads directory to serve static images
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Static frontend mounting will be at the bottom of the file to avoid routing conflicts.
@app.post("/api/auth/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Any = Depends(database.get_db)):
    db_user = auth.get_user(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = auth.get_password_hash(user.password)

    payload = {
        "username": user.username,
        "hashed_password": hashed_password,
        "full_name": user.full_name,
        "role": user.role,
        "height": 0,
        "weight": 0,
    }

    try:
        response = db.table('users').insert(payload).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create user in Supabase")
        return response.data[0]
    except HTTPException:
        raise
    except Exception:
        data = database.load_local_data()
        local_user = {
            "id": database.next_local_id(data["users"]),
            **payload,
        }
        data["users"].append(local_user)
        database.save_local_data(data)
        return local_user

@app.post("/api/auth/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Any = Depends(database.get_db)):
    user_dict = auth.get_user(db, username=form_data.username)
    if not user_dict or not auth.verify_password(form_data.password, user_dict["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user_dict["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user": user_dict}

@app.get("/api/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user = Depends(auth.get_current_user), db: Any = Depends(database.get_db)):
    # Fetch fresh user data from DB to include height/weight
    user_dict = auth.get_user(db, username=current_user.username)
    if not user_dict:
        raise HTTPException(status_code=404, detail="User not found")
    return user_dict

class ProfileUpdate(schemas.BaseModel):
    height: float
    weight: float

@app.put("/api/users/profile", response_model=schemas.UserResponse)
def update_user_profile(
    profile: ProfileUpdate,
    current_user = Depends(auth.get_current_user),
    db: Any = Depends(database.get_db)
):
    payload = {
        "height": profile.height,
        "weight": profile.weight
    }
    try:
        response = db.table('users').update(payload).eq('id', current_user.id).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update profile")
        return response.data[0]
    except HTTPException:
        raise
    except Exception:
        data = database.load_local_data()
        for user in data["users"]:
            if user.get("id") == current_user.id:
                user.update(payload)
                database.save_local_data(data)
                return user
        raise HTTPException(status_code=404, detail="User not found")

@app.put("/api/users/password")
def change_password(
    data: schemas.PasswordChange,
    current_user = Depends(auth.get_current_user),
    db: Any = Depends(database.get_db)
):
    hashed_password = auth.get_password_hash(data.new_password)
    try:
        response = db.table('users').update({
            "hashed_password": hashed_password
        }).eq('id', current_user.id).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update password")
        return {"message": "Password updated successfully"}
    except HTTPException:
        raise
    except Exception:
        local_data = database.load_local_data()
        for user in local_data["users"]:
            if user.get("id") == current_user.id:
                user["hashed_password"] = hashed_password
                database.save_local_data(local_data)
                return {"message": "Password updated successfully"}
        raise HTTPException(status_code=404, detail="User not found")

@app.get("/api/users/patients", response_model=List[schemas.UserResponse])
def get_patients(current_user = Depends(auth.get_current_user), db: Any = Depends(database.get_db)):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can view patient list")

    try:
        response = db.table('users').select('*').eq('role', 'patient').execute()
        return response.data
    except Exception:
        local_data = database.load_local_data()
        return [u for u in local_data["users"] if u.get("role") == "patient"]

@app.put("/api/users/{user_id}/profile", response_model=schemas.UserResponse)
def update_patient_profile(
    user_id: int,
    profile: ProfileUpdate,
    current_user = Depends(auth.get_current_user),
    db: Any = Depends(database.get_db)
):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can update other profiles")
        
    payload = {
        "height": profile.height,
        "weight": profile.weight
    }
    try:
        response = db.table('users').update(payload).eq('id', user_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Patient not found or failed to update")
        return response.data[0]
    except HTTPException:
        raise
    except Exception:
        local_data = database.load_local_data()
        for user in local_data["users"]:
            if user.get("id") == user_id:
                user.update(payload)
                database.save_local_data(local_data)
                return user
        raise HTTPException(status_code=404, detail="Patient not found or failed to update")

@app.post("/api/predict", response_model=schemas.HealthRecordResponse)
def predict_tumor(
    file: UploadFile = File(...),
    patient_id: int = Form(...),
    notes: str = Form(None),
    model_choice: str = Form('ensemble'),
    current_user = Depends(auth.get_current_user),
    db: Any = Depends(database.get_db)
):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can perform diagnosis")

    try:
        # 1. Đọc và lưu file local
        from . import ai_service
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Xử lý AI, trả về 5 giá trị
        prediction, confidence, annotated_path, gradcam_path, zoom_path = ai_service.predict_image(file_path, model_choice)
        
        # 3. Lấy tên bệnh nhân
        patient_record = db.table('users').select('full_name').eq('id', patient_id).execute()
        patient_name = patient_record.data[0]['full_name'] if patient_record.data else "Unknown"

        # 4. Lưu vào Supabase Database
        response = db.table('health_records').insert({
            "user_id": patient_id,
            "image_path": os.path.basename(annotated_path),
            "prediction_result": prediction,
            "confidence": confidence,
            "notes": notes
        }).execute()
        
        record = response.data[0]
        record['patient_name'] = patient_name
        record['gradcam_path'] = os.path.basename(gradcam_path) if gradcam_path else None
        record['zoom_path'] = os.path.basename(zoom_path) if zoom_path else None
        return record
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/records", response_model=List[schemas.HealthRecordResponse])
def get_user_records(
    patient_id: int | None = Query(default=None),
    current_user = Depends(auth.get_current_user),
    db: Any = Depends(database.get_db)
):
    try:
        if current_user.role == "doctor":
            # Bác sĩ có thể xem tất cả hồ sơ hoặc lọc theo bệnh nhân.
            query = db.table('health_records').select('*')
            if patient_id:
                query = query.eq('user_id', patient_id)
            response = query.order('created_at', desc=True).execute()
        else:
            # Bệnh nhân chỉ xem được hồ sơ của mình
            response = db.table('health_records').select('*').eq('user_id', current_user.id).order('created_at', desc=True).execute()
        records = response.data
    except Exception:
        local_data = database.load_local_data()
        if current_user.role == "doctor":
            records = local_data["health_records"]
            if patient_id:
                records = [r for r in records if r.get("user_id") == patient_id]
        else:
            records = [r for r in local_data["health_records"] if r.get("user_id") == current_user.id]

    if not records:
        return []

    user_ids = sorted({r.get('user_id') for r in records if r.get('user_id') is not None})
    names_by_id = {}
    if user_ids:
        try:
            users_res = db.table('users').select('id, full_name').in_('id', user_ids).execute()
            for u in users_res.data or []:
                names_by_id[u.get('id')] = u.get('full_name')
        except Exception:
            local_data = database.load_local_data()
            for u in local_data["users"]:
                if u.get("id") in user_ids:
                    names_by_id[u.get("id")] = u.get("full_name")

    for r in records:
        r['patient_name'] = names_by_id.get(r.get('user_id'), "Unknown")
    return records

@app.put("/api/records/{record_id}", response_model=schemas.HealthRecordResponse)
def update_record(
    record_id: int,
    payload: schemas.HealthRecordUpdate,
    current_user = Depends(auth.get_current_user),
    db: Any = Depends(database.get_db)
):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can update diagnosis notes")

    update_data = {}
    if payload.notes is not None:
        update_data["notes"] = payload.notes

    if not update_data:
        raise HTTPException(status_code=400, detail="No update fields provided")

    response = db.table('health_records').update(update_data).eq('id', record_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Record not found")

    record = response.data[0]
    patient_record = db.table('users').select('full_name').eq('id', record['user_id']).execute()
    if patient_record.data:
        record['patient_name'] = patient_record.data[0].get('full_name')
    return record

@app.delete("/api/records/{record_id}")
def delete_record(
    record_id: int,
    current_user = Depends(auth.get_current_user),
    db: Any = Depends(database.get_db)
):
    # Retrieve the record first to check authorization
    record_response = db.table('health_records').select('*').eq('id', record_id).execute()
    if not record_response.data:
        raise HTTPException(status_code=404, detail="Record not found")
        
    record = record_response.data[0]
    
    # Check permissions: must be owner or doctor
    if current_user.role != "doctor" and record['user_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this record")
        
    # Optional: Delete the file from local storage
    try:
        filename = os.path.basename(record['image_path'])
        full_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(full_path):
            os.remove(full_path)
    except Exception:
        pass # Ignore errors during file deletion
        
    # Delete from DB
    delete_response = db.table('health_records').delete().eq('id', record_id).execute()
    if not delete_response.data:
         # Depending on supabase client, success might also just mean no exception but data empty. We'll ignore empty data if no error thrown
         pass
         
    return {"message": "Record deleted successfully"}

@app.post("/api/messages", response_model=schemas.MessageResponse)
def send_message(
    msg: schemas.MessageCreate,
    current_user = Depends(auth.get_current_user),
    db: Any = Depends(database.get_db)
):
    try:
        response = db.table('messages').insert({
            "sender_id": current_user.id,
            "receiver_id": msg.receiver_id,
            "content": msg.content
        }).execute()
    except APIError as e:
        if _is_missing_table_error(e, "messages"):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Messaging feature is not initialized yet. "
                    "Missing database table: public.messages. "
                    "Run the SQL setup from backend/supabase_setup.py in Supabase SQL Editor."
                )
            )
        raise
    
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to send message")
    return response.data[0]

@app.get("/api/messages/contacts", response_model=List[schemas.UserResponse])
def get_chat_contacts(
    current_user = Depends(auth.get_current_user),
    db: Any = Depends(database.get_db)
):
    # Nếu là bác sĩ, trả về danh sách bệnh nhân. Nếu là bệnh nhân, trả về danh sách bác sĩ.
    target_role = "patient" if current_user.role == "doctor" else "doctor"
    response = db.table('users').select('*').eq('role', target_role).execute()
    return response.data

@app.get("/api/messages/{other_user_id}", response_model=List[schemas.MessageResponse])
def get_messages(
    other_user_id: int,
    current_user = Depends(auth.get_current_user),
    db: Any = Depends(database.get_db)
):
    # Lấy tin nhắn giữa hai người
    # Supabase không hỗ trợ trực tiếp điều kiện OR phức tạp qua ORM python một cách dễ dàng,
    # nhưng chúng ta có thể gọi .or_()
    # (sender_id = X AND receiver_id = Y) OR (sender_id = Y AND receiver_id = X)
    try:
        response = db.table('messages')\
            .select('*')\
            .or_(f"and(sender_id.eq.{current_user.id},receiver_id.eq.{other_user_id}),and(sender_id.eq.{other_user_id},receiver_id.eq.{current_user.id})")\
            .order('created_at', desc=False)\
            .execute()
        return response.data
    except APIError as e:
        if _is_missing_table_error(e, "messages"):
            return []
        raise

@app.post("/api/symptoms", response_model=schemas.SymptomResponse)
def log_symptom(
    symptom: schemas.SymptomCreate,
    current_user = Depends(auth.get_current_user),
    db: Any = Depends(database.get_db)
):
    try:
        response = db.table('symptoms').insert({
            "user_id": current_user.id,
            "symptom_name": symptom.symptom_name,
            "severity": symptom.severity,
            "notes": symptom.notes
        }).execute()
    except APIError as e:
        if _is_missing_table_error(e, "symptoms"):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Symptoms feature is not initialized yet. "
                    "Missing database table: public.symptoms. "
                    "Run the SQL setup from backend/supabase_setup.py in Supabase SQL Editor."
                )
            )
        raise
    
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to log symptom")
    return response.data[0]

@app.get("/api/symptoms", response_model=List[schemas.SymptomResponse])
def get_symptoms(
    current_user = Depends(auth.get_current_user),
    db: Any = Depends(database.get_db)
):
    try:
        response = db.table('symptoms').select('*').eq('user_id', current_user.id).order('logged_at', desc=True).execute()
        return response.data
    except APIError as e:
        if _is_missing_table_error(e, "symptoms"):
            return []
        raise

@app.get("/api/doctors", response_model=List[schemas.UserResponse])
def get_doctors(
    current_user = Depends(auth.get_current_user),
    db: Any = Depends(database.get_db)
):
    # Returns all users with role 'doctor'
    response = db.table('users').select('*').eq('role', 'doctor').execute()
    return response.data

@app.post("/api/appointments", response_model=schemas.AppointmentResponse)
def book_appointment(
    apt: schemas.AppointmentCreate,
    current_user = Depends(auth.get_current_user),
    db: Any = Depends(database.get_db)
):
    try:
        response = db.table('appointments').insert({
            "patient_id": current_user.id,
            "doctor_id": apt.doctor_id,
            "appointment_date": apt.appointment_date.isoformat(),
            "notes": apt.notes,
            "status": "pending"
        }).execute()
    except APIError as e:
        if _is_missing_table_error(e, "appointments"):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Appointments feature is not initialized yet. "
                    "Missing database table: public.appointments. "
                    "Run the SQL setup from backend/supabase_setup.py in Supabase SQL Editor."
                )
            )
        raise
    
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to book appointment")
    
    # Fetch doctor name for the response
    dr_record = db.table('users').select('full_name').eq('id', apt.doctor_id).execute()
    record = response.data[0]
    record['doctor_name'] = dr_record.data[0]['full_name'] if dr_record.data else "Unknown Doctor"
    
    return record

@app.get("/api/appointments", response_model=List[schemas.AppointmentResponse])
def get_appointments(
    current_user = Depends(auth.get_current_user),
    db: Any = Depends(database.get_db)
):
    try:
        # Determine the view based on role
        if current_user.role == "doctor":
            # Doctors see appointments booked with them. Join on patient_id to get patient name.
            response = db.table('appointments').select('*, users!patient_id(full_name)').eq('doctor_id', current_user.id).order('appointment_date', desc=False).execute()
            data = response.data
            for item in data:
                if 'users' in item and item['users']:
                    item['patient_name'] = item['users'].get('full_name')
        else:
            # Patients see their own appointments (join with users for doctor info)
            response = db.table('appointments').select('*, users!doctor_id(full_name)').eq('patient_id', current_user.id).order('appointment_date', desc=False).execute()
            data = response.data
            for item in data:
                if 'users' in item and item['users']:
                    item['doctor_name'] = item['users'].get('full_name')
        return data
    except APIError as e:
        if _is_missing_table_error(e, "appointments"):
            # Keep patient/doctor UI usable even when appointments table has not been created yet.
            return []
        raise

@app.get("/")
def serve_main_ui():
    return FileResponse(os.path.join("frontend", "doctor-dashboard.html"))

@app.get("/index.html")
def serve_index_alias():
    return FileResponse(os.path.join("frontend", "doctor-dashboard.html"))

# Mount the frontend directory to serve static files (Must be at the bottom)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
