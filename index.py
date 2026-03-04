from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import smtplib
from email.message import EmailMessage
import aiosqlite
import random
import jwt
from datetime import datetime, timedelta
import math
import os

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SECRET_KEY = "super-secret-royal-key"
ALGORITHM = "HS256"

# -- MOCK AI ASSISTANT --
class AIChatRequest(BaseModel):
    message: str

@app.post("/api/ai-assistant")
async def ai_assistant(req: AIChatRequest):
    msg = req.message.lower()
    reply = "I am the Virtual AI assistant for Royal Shop. How can I help you regarding our groceries or your orders?"
    if "price" in msg or "cost" in msg:
        reply = "Our prices are managed dynamically by the administrator to give you the best value. Please check the product page."
    elif "delivery" in msg:
        reply = "We offer free home delivery within a 15km radius! Beyond that, we charge ₹100 per km."
    elif "admin" in msg:
        reply = "The administrator email is siddharths1003@gmail.com."
    return {"reply": reply}

# -- DATABASE --
async def get_db():
    async with aiosqlite.connect("royal.db") as db:
        db.row_factory = aiosqlite.Row
        yield db

# -- AUTHENTICATION & EMAIL --
def send_email_sync(to_email: str, subject: str, body: str, html: bool = False):
    msg = EmailMessage()
    if html:
        msg.add_alternative(body, subtype='html')
    else:
        msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = "siddharths1003@gmail.com"
    msg['To'] = to_email

    print(f"Sending email to {to_email}")
    try:
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        # App password provided by user
        s.login("siddharths1003@gmail.com", "auob ejnr mmzc nisv")
        s.send_message(msg)
        s.quit()
        print("Done")
    except Exception as e:
        print(f"Failed to send email: {e}")

class OTPRequest(BaseModel):
    contact: str # email or phone (phone won't get OTP in this MVP because no SMS gateway, but if email format, we send)
    captcha: str

class OTPVerify(BaseModel):
    contact: str
    otp: str

@app.post("/api/request-otp")
async def request_otp(req: OTPRequest, background_tasks: BackgroundTasks, db: aiosqlite.Connection = Depends(get_db)):
    # Basic captcha validation would go here (or frontend)
    if not req.captcha == "verified":
        raise HTTPException(status_code=400, detail="Invalid CAPTCHA")

    otp_code = str(random.randint(100000, 999999))
    
    # Check if user exists
    cursor = await db.cursor()
    await cursor.execute("SELECT id FROM users WHERE contact = ?", (req.contact,))
    user = await cursor.fetchone()
    
    if user:
        await cursor.execute("UPDATE users SET otp = ? WHERE id = ?", (otp_code, user['id']))
    else:
        await cursor.execute("INSERT INTO users (contact, otp) VALUES (?, ?)", (req.contact, otp_code))
    await db.commit()

    if "@" in req.contact:
        background_tasks.add_task(send_email_sync, req.contact, "Your Royal Shop OTP", f"Your login OTP is: {otp_code}")
    
    return {"message": "OTP sent. Check your email."}

@app.post("/api/verify-otp")
async def verify_otp(req: OTPVerify, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.cursor()
    await cursor.execute("SELECT id, role, otp FROM users WHERE contact = ?", (req.contact,))
    user = await cursor.fetchone()

    if not user or user['otp'] != req.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    await cursor.execute("UPDATE users SET otp = NULL, verified = 1 WHERE id = ?", (user['id'],))
    await db.commit()

    # Generate JWT
    access_token_expires = timedelta(days=7)
    expire = datetime.utcnow() + access_token_expires
    to_encode = {"sub": str(user['id']), "role": user['role'], "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": encoded_jwt, "token_type": "bearer", "role": user['role']}

async def get_current_user(request: Request, db: aiosqlite.Connection = Depends(get_db)):
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        return None
    token = token.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        cursor = await db.cursor()
        await cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()
        return user
    except Exception:
        return None

# -- PRODUCTS --
@app.get("/api/products")
async def get_products(query: str | None = None, user_id: int | None = None, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.cursor()
    if query:
        # Search exact or like
        await cursor.execute("SELECT * FROM products WHERE name LIKE ? AND available = 1", (f"%{query}%",))
        items = await cursor.fetchall()
        
        # Log search history if logged in
        if user_id:
            await cursor.execute("INSERT INTO search_history (user_id, search_query) VALUES (?, ?)", (user_id, query))
            await db.commit()

        # If not found, simulated fetch logic (per user instructions: "if available take stock image from browser")
        if not items:
            # We can auto-add it with a random price as requested? 
            # "if it is there list of objects available ... take a stock image ... display price ... if not then show not available"
            return {"items": [], "message": "Not available, sorry for inconvenience."}
        
        return {"items": [dict(i) for i in items]}

    # Return recommendations or recent items
    if user_id:
        await cursor.execute("SELECT search_query FROM search_history WHERE user_id = ? ORDER BY id DESC LIMIT 5", (user_id,))
        recent_searches = await cursor.fetchall()
        # Build recommendation based on searches...
        # For simplicity, returning all available items for now.
    
    await cursor.execute("SELECT * FROM products WHERE available = 1")
    items = await cursor.fetchall()
    return {"items": [dict(i) for i in items]}

# -- CHECKOUT --
class CheckoutRequest(BaseModel):
    items: list
    delivery_type: str # 'home' or 'shop'
    address: str | None = None
    distance_km: float = 0.0

@app.post("/api/checkout")
async def checkout(req: CheckoutRequest, background_tasks: BackgroundTasks, db: aiosqlite.Connection = Depends(get_db), current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not logged in")

    # calculate cost
    subtotal = sum([item['price'] * item['quantity'] for item in req.items])
    delivery_charge = 0.0
    
    if req.delivery_type == "home":
        if req.distance_km > 15:
            delivery_charge = (req.distance_km - 15) * 100
        else:
            delivery_charge = 0 # free delivery msg handled by frontend
    
    total = subtotal + delivery_charge

    # generate unique code (4 digits + 2 letters)
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    code = f"{random.randint(1000, 9999)}{random.choice(letters)}{random.choice(letters)}"

    cursor = await db.cursor()
    await cursor.execute('''
        INSERT INTO orders (user_id, delivery_type, address, distance, delivery_charge, subtotal, total, unique_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (current_user['id'], req.delivery_type, req.address, req.distance_km, delivery_charge, subtotal, total, code))
    
    await db.commit()

    # If collect from shop, send admin email
    if req.delivery_type == "shop":
        items_rows = ""
        for i in req.items:
            items_rows += f"<tr><td style='border: 1px solid black; padding: 5px;'>{i['name']}</td><td style='border: 1px solid black; padding: 5px;'>{i['quantity']}</td><td style='border: 1px solid black; padding: 5px;'>₹{i['price']}</td></tr>"

        html_body = f"""
        <html>
            <body>
                <h2>New 'Collect from Shop' Order</h2>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <th style="border: 1px solid black; padding: 5px; text-align: left;">User</th>
                        <td style="border: 1px solid black; padding: 5px;">{current_user['contact']}</td>
                    </tr>
                    <tr>
                        <th style="border: 1px solid black; padding: 5px; text-align: left;">Subtotal</th>
                        <td style="border: 1px solid black; padding: 5px;">₹{subtotal}</td>
                    </tr>
                    <tr>
                        <th style="border: 1px solid black; padding: 5px; text-align: left;">Total</th>
                        <td style="border: 1px solid black; padding: 5px;">₹{total}</td>
                    </tr>
                </table>
                <br>
                <h3>Items:</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <th style="border: 1px solid black; padding: 5px; text-align: left;">Item</th>
                        <th style="border: 1px solid black; padding: 5px; text-align: left;">Quantity</th>
                        <th style="border: 1px solid black; padding: 5px; text-align: left;">Price</th>
                    </tr>
                    {items_rows}
                </table>
                <br>
                <p>Unique Code: <strong>{code}</strong></p>
            </body>
        </html>
        """
        background_tasks.add_task(send_email_sync, "siddharths1003@gmail.com", f"New Order - {code}", html_body, True)

    return {
        "message": "Order placed successfully!",
        "unique_code": code,
        "delivery_charge": delivery_charge,
        "total": total
    }

# -- ADMIN AREA --
@app.get("/api/admin/setup")
async def admin_setup(db: aiosqlite.Connection = Depends(get_db), user=Depends(get_current_user)):
    if not user or user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # admin fetch products
    cursor = await db.cursor()
    await cursor.execute("SELECT * FROM products")
    products = await cursor.fetchall()
    return {"products": [dict(p) for p in products]}

class AdminProductUpdate(BaseModel):
    id: int
    price: float
    available: bool

@app.post("/api/admin/update-product")
async def update_product(payload: AdminProductUpdate, db: aiosqlite.Connection = Depends(get_db), user=Depends(get_current_user)):
    if not user or user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Forbidden")

    cursor = await db.cursor()
    await cursor.execute("UPDATE products SET price = ?, available = ? WHERE id = ?", (payload.price, int(payload.available), payload.id))
    await db.commit()
    return {"success": True}

# -- FRONTEND ROUTES --
@app.get("/", response_class=HTMLResponse)
async def serve_frontend(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

