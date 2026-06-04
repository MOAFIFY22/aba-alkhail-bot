import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
import requests
import io
import csv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# States
SELECTING_DEPARTMENT = 1
SELECTING_REQUEST = 2
SELECTING_STATUS = 3
ENTER_NOTES = 4
UPLOAD_PHOTOS = 5

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "8646021850:AAGsIXcIF7ZtN8Nfv5W8GzLQdx9E86EH9OQ")
YOUR_CHAT_ID = int(os.getenv("YOUR_CHAT_ID", "966539576137"))

# Departments
DEPARTMENTS = {
    "1": "التوصيلات",
    "2": "العمليات والصيانة",
    "3": "الإنشاءات - مشاريع",
    "4": "المشاريع الخاصة"
}

SHEET_ID = "1I9dSX7mpdRly2I-SpadicLxsjcU4V_IyWX_1I6v3gUM"
SHEET_GID = "56484956"  # طلبات الاغلاق

def load_sheets_data():
    """Load data from Google Sheets CSV export"""
    try:
        csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"
        response = requests.get(csv_url, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            reader = csv.DictReader(io.StringIO(response.text))
            return list(reader)
        return []
    except Exception as e:
        logger.error(f"Error loading sheets: {e}")
        return []

def get_requests_by_department(department_id: str):
    """Get requests for specific department"""
    data = load_sheets_data()
    filtered = []
    
    target_status = "تحت معالجة الاستشاري"
    target_dept = DEPARTMENTS.get(department_id, "")
    
    for row in data:
        try:
            status = row.get("حالة الطلب", "").strip()
            dept = row.get("القسم", "").strip()
            
            # Debug logging
            logger.info(f"Checking - Status: '{status}' | Dept: '{dept}' | Target: '{target_status}' | '{target_dept}'")
            
            # Check if status matches and department matches
            if status == target_status and dept == target_dept:
                filtered.append(row)
        except Exception as e:
            logger.error(f"Error processing row: {e}")
            continue
    
    logger.info(f"Found {len(filtered)} requests for department {department_id}")
    return filtered

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("🔌 التوصيلات", callback_data="dept_1")],
        [InlineKeyboardButton("🔧 العمليات والصيانة", callback_data="dept_2")],
        [InlineKeyboardButton("🏗️ الإنشاءات والمشاريع", callback_data="dept_3")],
        [InlineKeyboardButton("📋 المشاريع الخاصة", callback_data="dept_4")],
    ]
    
    await update.message.reply_text(
        "🤖 مرحباً بك في بوت أبا الخيل!\n\nاختر القسم:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECTING_DEPARTMENT

async def select_department(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    dept_id = query.data.split("_")[1]
    requests = get_requests_by_department(dept_id)
    
    if not requests:
        await query.edit_message_text(f"❌ لا توجد رخص في {DEPARTMENTS[dept_id]}")
        return ConversationHandler.END
    
    context.user_data["requests"] = requests
    context.user_data["dept_id"] = dept_id
    context.user_data["req_index"] = 0
    
    await show_request(query, context)
    return SELECTING_REQUEST

async def show_request(query, context):
    requests = context.user_data["requests"]
    index = context.user_data["req_index"]
    req = requests[index]
    
    text = (
        f"📋 الرخصة {index + 1}/{len(requests)}\n\n"
        f"رقم الطلب: {req.get('رقم الطلب', 'N/A')}\n"
        f"رقم الرخصة: {req.get('رقم الرخصة', 'N/A')}\n"
        f"رقم المرجع: {req.get('رقم المرجع', 'N/A')}\n"
        f"رقم المحطة: {req.get('رقم المحطة', 'N/A')}\n"
        f"الحي: {req.get('الحي', 'N/A')}\n"
        f"المقاول: {req.get('اسم المقاول', 'N/A')}\n"
        f"التاريخ: {req.get('تاريخ تقديم الطلب', 'N/A')}\n\n✅ صحيح؟"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ نعم", callback_data="select_yes")],
        [InlineKeyboardButton("⬅️", callback_data="prev"),
         InlineKeyboardButton("➡️", callback_data="next")],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def navigate_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    requests = context.user_data["requests"]
    index = context.user_data["req_index"]
    
    if query.data == "next":
        context.user_data["req_index"] = min(index + 1, len(requests) - 1)
    elif query.data == "prev":
        context.user_data["req_index"] = max(index - 1, 0)
    elif query.data == "select_yes":
        context.user_data["selected_req"] = requests[index]
        keyboard = [
            [InlineKeyboardButton("✅ قبول", callback_data="accept")],
            [InlineKeyboardButton("❌ رفض", callback_data="reject")],
        ]
        await query.edit_message_text(
            "اختر حالة الافادة:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECTING_STATUS
    
    await show_request(query, context)
    return SELECTING_REQUEST

async def select_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    status = "قبول ✅" if query.data == "accept" else "رفض ❌"
    context.user_data["status"] = status
    
    await query.edit_message_text("✍️ اكتب الملاحظات (أو /skip)")
    return ENTER_NOTES

async def enter_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "/skip":
        context.user_data["notes"] = "بدون ملاحظات"
    else:
        context.user_data["notes"] = update.message.text
    
    await update.message.reply_text("📸 أرسل الصور (أو /done)")
    context.user_data["photos"] = []
    return UPLOAD_PHOTOS

async def upload_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "/done":
        # Send report
        req = context.user_data["selected_req"]
        report = (
            f"📋 **تقرير الافادة**\n\n"
            f"رقم الرخصة: {req.get('رقم الرخصة')}\n"
            f"الحالة: {context.user_data['status']}\n"
            f"الملاحظات: {context.user_data['notes']}\n"
            f"الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        await context.bot.send_message(YOUR_CHAT_ID, report, parse_mode="Markdown")
        await update.message.reply_text("✅ تم الإرسال! اكتب /start للبدء مجدداً")
        return ConversationHandler.END
    
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
        context.user_data["photos"].append(file)
        await update.message.reply_text(f"✅ صورة {len(context.user_data['photos'])} محفوظة")
        return UPLOAD_PHOTOS
    
    await update.message.reply_text("❌ أرسل صورة أو /done")
    return UPLOAD_PHOTOS

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
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
    
    app.add_handler(conv_handler)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
