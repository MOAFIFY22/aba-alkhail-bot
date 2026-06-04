import os
import json
import csv
import io
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

# Google Sheets & Drive
import gspread
from google.oauth2.service_account import Credentials
import requests

# PDF & Document
from docx import Document
from docx.shared import Inches
from PIL import Image
import pypdf

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# States for conversation
SELECTING_DEPARTMENT = 1
SELECTING_REQUEST = 2
SELECTING_STATUS = 3
ENTER_NOTES = 4
UPLOAD_PHOTOS = 5
CONFIRM_SUBMISSION = 6

# Your bot token
BOT_TOKEN = "8646021850:AAGsIXcIF7ZtN8Nfv5W8GzLQdx9E86EH9OQ"
YOUR_CHAT_ID = 966539576137  # Your Telegram ID

# Google Sheets URL
SHEETS_URL = "https://docs.google.com/spreadsheets/d/1I9dSX7mpdRly2I-SpadicLxsjcU4V_IyWX_1I6v3gUM"

# Departments mapping
DEPARTMENTS = {
    "1": "التوصيلات",
    "2": "العمليات والصيانة",
    "3": "الإنشاءات - مشاريع",
    "4": "المشاريع الخاصة"
}

class AbaAlkhailBot:
    def __init__(self):
        self.sheets_data = []
        self.load_sheets_data()
        
    def load_sheets_data(self):
        """Load data from Google Sheets via CSV export"""
        try:
            # Export sheets as CSV
            sheet_id = "1I9dSX7mpdRly2I-SpadicLxsjcU4V_IyWX_1I6v3gUM"
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            
            response = requests.get(csv_url)
            if response.status_code == 200:
                # Parse CSV
                csv_reader = csv.DictReader(io.StringIO(response.text, encoding='utf-8'))
                self.sheets_data = list(csv_reader)
                logger.info(f"✅ تم تحميل {len(self.sheets_data)} سجل من الشيت")
            else:
                logger.warning(f"⚠️ خطأ في تحميل الشيت: {response.status_code}")
                self.sheets_data = []
        except Exception as e:
            logger.error(f"❌ خطأ في قراءة البيانات: {e}")
            self.sheets_data = []
    
    def get_requests_by_department(self, department: str) -> List[Dict]:
        """Get all requests for a specific department that are under processing"""
        filtered = []
        for row in self.sheets_data:
            # Check if status is "تحت معالجة الاستشاري" and department matches
            status = row.get("حالة الطلب", "").strip()
            dept = row.get("القسم", "").strip()
            
            if "تحت معالجة الاستشاري" in status and dept == DEPARTMENTS[department]:
                filtered.append(row)
        
        return filtered

bot_instance = AbaAlkhailBot()

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for department selection"""
    
    keyboard = [
        [InlineKeyboardButton("🔌 التوصيلات", callback_data="dept_1")],
        [InlineKeyboardButton("🔧 العمليات والصيانة", callback_data="dept_2")],
        [InlineKeyboardButton("🏗️ الإنشاءات والمشاريع", callback_data="dept_3")],
        [InlineKeyboardButton("📋 المشاريع الخاصة", callback_data="dept_4")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 مرحباً بك في بوت أبا الخيل!\n\n"
        "اختر القسم الخاص بك:",
        reply_markup=reply_markup
    )
    
    return SELECTING_DEPARTMENT

# Department selection
async def select_department(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle department selection"""
    query = update.callback_query
    await query.answer()
    
    dept_id = query.data.split("_")[1]
    context.user_data["department"] = dept_id
    context.user_data["dept_name"] = DEPARTMENTS[dept_id]
    
    # Get requests for this department
    requests_list = bot_instance.get_requests_by_department(dept_id)
    
    if not requests_list:
        await query.edit_message_text(
            f"❌ لا توجد رخص تحت المعالجة في قسم {DEPARTMENTS[dept_id]}\n\n"
            "اكتب /start للبدء مجدداً"
        )
        return ConversationHandler.END
    
    # Store requests in context
    context.user_data["requests"] = requests_list
    context.user_data["current_request_index"] = 0
    
    # Show first request
    await show_request(query, context, 0)
    
    return SELECTING_REQUEST

async def show_request(query, context: ContextTypes.DEFAULT_TYPE, index: int):
    """Show a request and allow selection"""
    requests_list = context.user_data["requests"]
    
    if index >= len(requests_list):
        index = len(requests_list) - 1
    
    request = requests_list[index]
    
    message_text = (
        f"📋 **الرخصة {index + 1} من {len(requests_list)}**\n\n"
        f"رقم الطلب: {request.get('رقم الطلب', 'N/A')}\n"
        f"رقم الرخصة: {request.get('رقم الرخصة', 'N/A')}\n"
        f"رقم المرجع: {request.get('رقم المرجع', 'N/A')}\n"
        f"رقم المحطة: {request.get('رقم المحطة', 'N/A')}\n"
        f"الحي: {request.get('الحي', 'N/A')}\n"
        f"المقاول: {request.get('اسم المقاول', 'N/A')}\n"
        f"التاريخ: {request.get('تاريخ تقديم الطلب', 'N/A')}\n\n"
        f"✅ هل هذه الرخصة صحيحة؟"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ نعم", callback_data=f"select_req_{index}")],
        [InlineKeyboardButton("⬅️ السابقة", callback_data=f"prev_req_{index}"),
         InlineKeyboardButton("➡️ التالية", callback_data=f"next_req_{index}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode="Markdown")

async def navigate_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Navigate between requests"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("next_req_"):
        index = int(data.split("_")[2]) + 1
    elif data.startswith("prev_req_"):
        index = int(data.split("_")[2]) - 1
    else:
        # Select request
        index = int(data.split("_")[2])
        context.user_data["selected_request_index"] = index
        context.user_data["selected_request"] = context.user_data["requests"][index]
        
        # Ask for status
        keyboard = [
            [InlineKeyboardButton("✅ قبول", callback_data="status_accept")],
            [InlineKeyboardButton("❌ رفض", callback_data="status_reject")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"اختر حالة الافادة:\n\n"
            f"الرخصة: {context.user_data['selected_request'].get('رقم الرخصة', 'N/A')}",
            reply_markup=reply_markup
        )
        return SELECTING_STATUS
    
    # Clamp index
    requests_list = context.user_data["requests"]
    if index < 0:
        index = 0
    elif index >= len(requests_list):
        index = len(requests_list) - 1
    
    context.user_data["current_request_index"] = index
    await show_request(query, context, index)
    
    return SELECTING_REQUEST

async def select_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle status selection"""
    query = update.callback_query
    await query.answer()
    
    status = "قبول" if query.data == "status_accept" else "رفض"
    context.user_data["status"] = status
    
    await query.edit_message_text(
        f"✍️ اكتب ملاحظاتك/الافادة:\n\n"
        f"(استخدم /done عندما تنتهي)"
    )
    
    return ENTER_NOTES

async def enter_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle notes entry"""
    if update.message.text == "/done":
        # Ask for photos
        await update.message.reply_text(
            "📸 الآن أرسل الصور:\n\n"
            "(أرسل الصور واحدة تلو الأخرى، ثم اكتب /done عندما تنتهي)"
        )
        context.user_data["photos"] = []
        return UPLOAD_PHOTOS
    else:
        context.user_data["notes"] = update.message.text
        await update.message.reply_text("✅ تم حفظ الملاحظات\n\n📸 الآن أرسل الصور:")
        context.user_data["photos"] = []
        return UPLOAD_PHOTOS

async def upload_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle photo uploads"""
    if update.message.text == "/done":
        # Generate PDF and send
        await generate_and_send_pdf(update, context)
        return ConversationHandler.END
    
    if update.message.photo:
        # Download photo
        file = await update.message.photo[-1].get_file()
        photo_path = f"/tmp/photo_{len(context.user_data['photos'])}.jpg"
        await file.download_to_drive(photo_path)
        context.user_data["photos"].append(photo_path)
        
        await update.message.reply_text(f"✅ تم حفظ الصورة {len(context.user_data['photos'])}")
        return UPLOAD_PHOTOS
    else:
        await update.message.reply_text("❌ أرسل صورة من فضلك")
        return UPLOAD_PHOTOS

async def generate_and_send_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate PDF from template and send to user"""
    try:
        await update.message.reply_text("⏳ جاري إنشاء الـ PDF...")
        
        request_data = context.user_data["selected_request"]
        status = context.user_data["status"]
        notes = context.user_data.get("notes", "")
        photos = context.user_data.get("photos", [])
        
        license_number = request_data.get("رقم الرخصة", "unknown")
        
        # Create a simple PDF with data
        pdf_path = f"/tmp/report_{license_number}.pdf"
        
        # For now, create a simple text file (you can enhance this)
        with open(pdf_path, "w", encoding="utf-8") as f:
            f.write(f"تقرير الافادة\n")
            f.write(f"{'='*50}\n\n")
            f.write(f"رقم الرخصة: {license_number}\n")
            f.write(f"رقم الطلب: {request_data.get('رقم الطلب', 'N/A')}\n")
            f.write(f"الحالة: {status}\n")
            f.write(f"الملاحظات: {notes}\n")
            f.write(f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        
        # Send PDF to user
        with open(pdf_path, "rb") as doc:
            await context.bot.send_document(
                chat_id=YOUR_CHAT_ID,
                document=doc,
                filename=f"{license_number}.pdf",
                caption=f"✅ تقرير الرخصة {license_number}\nالحالة: {status}"
            )
        
        await update.message.reply_text(
            "✅ تم إرسال التقرير!\n\n"
            "اكتب /start للبدء برخصة جديدة"
        )
        
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        await update.message.reply_text(f"❌ خطأ في إنشاء التقرير: {str(e)}")

def main():
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_DEPARTMENT: [CallbackQueryHandler(select_department)],
            SELECTING_REQUEST: [CallbackQueryHandler(navigate_requests)],
            SELECTING_STATUS: [CallbackQueryHandler(select_status)],
            ENTER_NOTES: [MessageHandler(filters.TEXT, enter_notes)],
            UPLOAD_PHOTOS: [
                MessageHandler(filters.PHOTO, upload_photos),
                MessageHandler(filters.TEXT, upload_photos)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    application.add_handler(conv_handler)
    
    # Run with polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
