"""
Reports handler for generating and sending reports to admins
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from services.reports import ReportsService
from config import ADMINS

logger = logging.getLogger(__name__)
router = Router()

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMINS

@router.callback_query(F.data == "admin_reports")
async def admin_reports_handler(callback: CallbackQuery, session: AsyncSession):
    """Handle admin reports request"""
    try:
        user_id = callback.from_user.id
        
        if not is_admin(user_id):
            await callback.answer("غير مصرح / Unauthorized")
            return
        
        await callback.message.edit_text(
            "⏳ جاري إنشاء التقارير... / Generating reports..."
        )
        
        # Generate all reports
        reports_service = ReportsService()
        report_files = await reports_service.generate_all_reports(session)
        
        if not report_files:
            await callback.message.edit_text(
                "❌ لم يتم العثور على بيانات لإنشاء التقارير / No data found to generate reports"
            )
            await callback.answer()
            return
        
        await callback.message.edit_text(
            f"✅ تم إنشاء {len(report_files)} ملف تقرير / Generated {len(report_files)} report files"
        )
        
        # Send each report file
        for report_file in report_files:
            try:
                # Send file to admin
                document = FSInputFile(
                    path=str(report_file),
                    filename=report_file.name
                )
                
                await callback.message.answer_document(
                    document=document,
                    caption=f"📊 {report_file.name}"
                )
                
            except Exception as file_error:
                logger.error(f"Error sending report file {report_file}: {file_error}")
                await callback.message.answer(
                    f"❌ خطأ في إرسال ملف / Error sending file: {report_file.name}"
                )
        
        await callback.message.answer(
            "✅ تم إرسال جميع التقارير / All reports sent successfully"
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in admin reports handler: {e}")
        await callback.answer("حدث خطأ / Error occurred")
        try:
            await callback.message.edit_text("❌ حدث خطأ في إنشاء التقارير / Error generating reports")
        except:
            pass