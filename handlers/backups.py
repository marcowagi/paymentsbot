"""
Backups handler for creating and sending backups to admins
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from services.backup import BackupService
from config import ADMINS

logger = logging.getLogger(__name__)
router = Router()

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMINS

@router.callback_query(F.data == "admin_backups")
async def admin_backups_handler(callback: CallbackQuery):
    """Handle admin backups request"""
    try:
        user_id = callback.from_user.id
        
        if not is_admin(user_id):
            await callback.answer("غير مصرح / Unauthorized")
            return
        
        await callback.message.edit_text(
            "⏳ جاري إنشاء النسخة الاحتياطية... / Creating backup..."
        )
        
        # Create full backup
        backup_service = BackupService()
        
        try:
            backup_file = await backup_service.create_full_backup()
            
            await callback.message.edit_text(
                f"✅ تم إنشاء النسخة الاحتياطية / Backup created successfully\n"
                f"📄 File: {backup_file.name}"
            )
            
            # Send backup file to admin
            try:
                document = FSInputFile(
                    path=str(backup_file),
                    filename=backup_file.name
                )
                
                await callback.message.answer_document(
                    document=document,
                    caption=(
                        f"💾 النسخة الاحتياطية الكاملة / Full Backup\n"
                        f"📅 Created: {backup_file.stat().st_mtime}\n"
                        f"📊 Size: {backup_file.stat().st_size / 1024:.1f} KB"
                    )
                )
                
                # Clean up old backups (keep last 10)
                backup_service.cleanup_old_backups(keep_count=10)
                
                await callback.message.answer(
                    "✅ تم إرسال النسخة الاحتياطية بنجاح / Backup sent successfully"
                )
                
            except Exception as send_error:
                logger.error(f"Error sending backup file: {send_error}")
                await callback.message.answer(
                    f"❌ خطأ في إرسال النسخة الاحتياطية / Error sending backup\n"
                    f"File: {backup_file.name}"
                )
        
        except FileNotFoundError:
            await callback.message.edit_text(
                "❌ لم يتم العثور على قاعدة البيانات أو التقارير / Database or reports not found"
            )
        
        except Exception as backup_error:
            logger.error(f"Error creating backup: {backup_error}")
            await callback.message.edit_text(
                "❌ حدث خطأ في إنشاء النسخة الاحتياطية / Error creating backup"
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in admin backups handler: {e}")
        await callback.answer("حدث خطأ / Error occurred")
        try:
            await callback.message.edit_text("❌ حدث خطأ في النسخ الاحتياطي / Backup error")
        except:
            pass